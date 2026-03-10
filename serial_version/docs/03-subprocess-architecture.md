# Subprocess Architecture and Communication Protocol

## Overview

The subprocess architecture is the cornerstone of the RFIC Layout-to-EM Simulation GUI system, providing complete isolation between the user interface and the specialized ADS/EMPro Python environments. This architecture ensures compatibility, security, and robust error handling while maintaining excellent performance.

## Architecture Design

### Process Isolation Model

```
┌─────────────────────────────────────────────────────────────────┐
│                        GUI Process                               │
│  ┌─────────────────┐  ┌──────────────────┐  ┌────────────────┐ │
│  │   Tkinter GUI   │  │  Communication   │  │    Logging     │ │
│  │   Components    │  │     Manager      │  │   & Metrics    │ │
│  └─────────────────┘  └──────────────────┘  └────────────────┘ │
└──────────────────────────────┬──────────────────────────────────┘
                               │ JSON over Stdio/Temp Files
┌──────────────────────────────┴──────────────────────────────────┐
│                     Bridge Process                               │
│  ┌─────────────────┐  ┌──────────────────┐  ┌────────────────┐ │
│  │  Environment    │  │   Task Router    │  │   Exception    │ │
│  │    Manager      │  │   & Validator   │  │   Handler      │ │
│  └─────────────────┘  └──────────────────┘  └────────────────┘ │
└──────────────────────────────┬──────────────────────────────────┘
                               │ Context Switching
┌──────────────────────────────┴──────────────────────────────────┐
│                     ADS/EMPro Process                            │
│  ┌─────────────────┐  ┌──────────────────┐  ┌────────────────┐ │
│  │   ADS Context   │  │  EMPro Context   │  │   PDK Ops      │ │
│  │   Operations    │  │   Operations     │  │   Support      │ │
│  └─────────────────┘  └──────────────────┘  └────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

## Communication Protocol

### JSON-RPC Style Protocol

The system implements a JSON-RPC style communication protocol with the following structure:

#### Request Structure
```json
{
  "jsonrpc": "2.0",
  "method": "create_design",
  "params": {
    "workspace_path": "C:\\Path\\To\\Workspaces\\Test",
    "library_name": "TestLib",
    "cell_name": "TestCell",
    "json_layout": {
      "design_id": "test_design",
      "layout_matrices": {...},
      "port_definitions": [...]
    },
    "config": {
      "technology": "TSMC65nm",
      "simulation_type": "momentum",
      "frequency_range": ["1MHz", "50GHz"]
    }
  },
  "id": "req_12345",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

#### Response Structure
```json
{
  "jsonrpc": "2.0",
  "result": {
    "workspace_path": "C:\\Path\\To\\Workspaces\\Test",
    "library_name": "TestLib",
    "cell_name": "TestCell",
    "em_view": "rfpro_view",
    "s_parameters": "C:\\Path\\To\\Workspaces\\Test\\TestLib\\TestCell\\rfpro_view\\ds\\S_Params.s2p",
    "execution_time": 45.3,
    "memory_usage": "256MB"
  },
  "error": {
    "code": -32000,
    "message": "ADS Exception",
    "data": {
      "type": "PortConfigurationError",
      "message": "Port P1 not found in layout",
      "traceback": "Traceback (most recent call last):..."
    }
  },
  "id": "req_12345"
}
```

## Process Management

### Environment Detection and Setup

```python
class ProcessEnvironmentManager:
    """Manages subprocess environment detection and setup"""
    
    def __init__(self):
        self.python_executable = None
        self.environment_info = {}
        self._detect_environment()
    
    def _detect_environment(self):
        """Comprehensive environment detection"""
        
        # Check for ADS Python installations
        ads_paths = [
            r"C:\Path\To\ADS2026_Update1",
            r"C:\Path\To\ADS2025",
            r"C:\Path\To\ADS2025_Update2"
        ]
        
        for base_path in ads_paths:
            python_paths = [
                os.path.join(base_path, "tools", "python", "python.exe"),
                os.path.join(base_path, "fem", "2025.20", "win32_64", "bin", "tools", "win32", "python", "python.exe")
            ]
            
            for python_path in python_paths:
                if os.path.exists(python_path):
                    self.python_executable = python_path
                    self.environment_info = {
                        'ads_version': self._get_ads_version(base_path),
                        'python_version': self._get_python_version(python_path),
                        'architecture': platform.architecture()[0],
                        'base_path': base_path
                    }
                    return
        
        raise EnvironmentError("No suitable ADS Python environment found")
    
    def _get_ads_version(self, base_path):
        """Extract ADS version from installation"""
        version_file = os.path.join(base_path, "version.txt")
        if os.path.exists(version_file):
            with open(version_file, 'r') as f:
                return f.read().strip()
        return "Unknown"
    
    def _get_python_version(self, python_path):
        """Get Python version from executable"""
        try:
            result = subprocess.run([python_path, '--version'], 
                                  capture_output=True, text=True)
            return result.stdout.strip()
        except:
            return "Unknown"
```

### Subprocess Launch and Management

```python
class SubprocessManager:
    """Manages subprocess lifecycle and communication"""
    
    def __init__(self, python_executable, worker_script):
        self.python_executable = python_executable
        self.worker_script = worker_script
        self.process = None
        self.reader_thread = None
        self.writer_thread = None
        self.response_queue = queue.Queue()
        self.is_running = False
    
    def start(self):
        """Start the subprocess with proper initialization"""
        
        try:
            # Create subprocess with proper environment
            env = os.environ.copy()
            env.update({
                'PYTHONPATH': self._get_ads_python_path(),
                'HPEESOF_DIR': self._get_ads_base_path(),
                'ADS_LICENSE_FILE': self._get_license_path()
            })
            
            self.process = subprocess.Popen(
                [self.python_executable, self.worker_script],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                env=env
            )
            
            # Start communication threads
            self._start_communication_threads()
            self.is_running = True
            
            # Wait for initialization
            self._wait_for_initialization()
            
        except Exception as e:
            self._cleanup()
            raise RuntimeError(f"Failed to start subprocess: {e}")
    
    def _start_communication_threads(self):
        """Start reader and writer threads for async communication"""
        
        self.reader_thread = threading.Thread(
            target=self._read_responses,
            daemon=True
        )
        self.writer_thread = threading.Thread(
            target=self._write_requests,
            daemon=True
        )
        
        self.reader_thread.start()
        self.writer_thread.start()
    
    def _read_responses(self):
        """Background thread for reading responses"""
        
        buffer = ""
        while self.is_running and self.process:
            try:
                chunk = self.process.stdout.read(1)
                if not chunk:
                    break
                
                buffer += chunk
                
                # Parse complete JSON messages
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line.strip():
                        try:
                            response = json.loads(line.strip())
                            self.response_queue.put(response)
                        except json.JSONDecodeError as e:
                            logger.error(f"Invalid JSON received: {e}")
                            
            except Exception as e:
                logger.error(f"Error reading from subprocess: {e}")
                break
    
    def send_request(self, method, params, timeout=300):
        """Send request and wait for response"""
        
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat()
        }
        
        # Send request
        request_json = json.dumps(request) + '\n'
        self.process.stdin.write(request_json)
        self.process.stdin.flush()
        
        # Wait for response
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = self.response_queue.get(timeout=1)
                if response.get('id') == request['id']:
                    return response
            except queue.Empty:
                continue
        
        raise TimeoutError(f"Request timed out after {timeout}s")
```

## Worker Process Implementation

### Task Router and Validation

```python
class WorkerTaskRouter:
    """Routes and validates tasks in the worker process"""
    
    def __init__(self):
        self.task_handlers = {
            'create_design': self._handle_create_design,
            'run_simulation': self._handle_run_simulation,
            'export_results': self._handle_export_results,
            'validate_layout': self._handle_validate_layout,
            'get_ads_info': self._handle_get_ads_info
        }
        self.validator = TaskValidator()
    
    def process_request(self, request):
        """Process incoming request with validation and routing"""
        
        try:
            # Validate request structure
            self.validator.validate_request(request)
            
            # Route to appropriate handler
            method = request['method']
            params = request['params']
            
            if method not in self.task_handlers:
                raise ValueError(f"Unknown method: {method}")
            
            handler = self.task_handlers[method]
            result = handler(params)
            
            return {
                "jsonrpc": "2.0",
                "result": result,
                "id": request['id']
            }
            
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32000,
                    "message": str(e),
                    "data": {
                        "type": type(e).__name__,
                        "traceback": traceback.format_exc()
                    }
                },
                "id": request.get('id', 'unknown')
            }
    
    def _handle_create_design(self, params):
        """Handle design creation task"""
        
        with multi_python.ads_context() as ads_ctx:
            return ads_ctx.call(
                create_design_task,
                args=[params],
                timeout=300
            )
    
    def _handle_run_simulation(self, params):
        """Handle simulation execution task"""
        
        with multi_python.xxpro_context() as empro_ctx:
            return empro_ctx.call(
                run_em_simulation_task,
                args=[params],
                timeout=1800
            )
```

### Context Isolation and Management

```python
class ContextManager:
    """Manages ADS and EMPro contexts with proper isolation"""
    
    def __init__(self):
        self.active_context = None
        self.context_stack = []
    
    def ads_context(self):
        """ADS context manager with automatic cleanup"""
        
        import keysight.edatoolbox.multi_python as multi_python
        
        @contextlib.contextmanager
        def manager():
            try:
                self.active_context = 'ads'
                context = multi_python.ads_context()
                yield context
            finally:
                self.active_context = None
                # Force garbage collection
                import gc
                gc.collect()
        
        return manager()
    
    def empro_context(self):
        """EMPro context manager with automatic cleanup"""
        
        import keysight.edatoolbox.multi_python as multi_python
        
        @contextlib.contextmanager
        def manager():
            try:
                self.active_context = 'empro'
                context = multi_python.xxpro_context()
                yield context
            finally:
                self.active_context = None
                # Force garbage collection
                import gc
                gc.collect()
        
        return manager()
```

## Error Handling and Recovery

### Multi-level Error Handling

```python
class SubprocessErrorHandler:
    """Comprehensive error handling for subprocess operations"""
    
    def __init__(self):
        self.error_types = {
            'environment_error': EnvironmentErrorHandler(),
            'ads_error': ADSErrorHandler(),
            'validation_error': ValidationErrorHandler(),
            'timeout_error': TimeoutErrorHandler()
        }
    
    def handle_error(self, error, context):
        """Handle errors with appropriate recovery strategies"""
        
        error_type = self._classify_error(error)
        handler = self.error_types.get(error_type)
        
        if handler:
            return handler.handle(error, context)
        else:
            return self._handle_generic_error(error, context)
    
    def _classify_error(self, error):
        """Classify error type for appropriate handling"""
        
        error_str = str(error).lower()
        
        if 'environment' in error_str or 'path' in error_str:
            return 'environment_error'
        elif 'ads' in error_str or 'empro' in error_str:
            return 'ads_error'
        elif 'validation' in error_str or 'invalid' in error_str:
            return 'validation_error'
        elif 'timeout' in error_str or 'time' in error_str:
            return 'timeout_error'
        else:
            return 'generic_error'

class EnvironmentErrorHandler:
    """Handle environment-related errors"""
    
    def handle(self, error, context):
        return {
            'recoverable': True,
            'suggestion': 'Check ADS installation and Python paths',
            'fallback': 'Try manual ADS Python path specification',
            'details': str(error)
        }

class ADSErrorHandler:
    """Handle ADS-specific errors"""
    
    def handle(self, error, context):
        return {
            'recoverable': False,
            'suggestion': 'Check ADS license and workspace permissions',
            'fallback': 'Restart ADS and retry',
            'details': str(error)
        }
```

## Performance Monitoring

### Real-time Performance Tracking

```python
class PerformanceMonitor:
    """Real-time performance monitoring for subprocess operations"""
    
    def __init__(self):
        self.metrics = {
            'request_count': 0,
            'response_times': [],
            'error_count': 0,
            'memory_usage': [],
            'cpu_usage': []
        }
        self.start_time = time.time()
    
    def track_request(self, method, duration, success=True):
        """Track request performance metrics"""
        
        self.metrics['request_count'] += 1
        self.metrics['response_times'].append({
            'method': method,
            'duration': duration,
            'success': success,
            'timestamp': time.time()
        })
        
        if not success:
            self.metrics['error_count'] += 1
    
    def get_performance_summary(self):
        """Get comprehensive performance summary"""
        
        if not self.metrics['response_times']:
            return {'status': 'no_data'}
        
        successful_times = [
            r['duration'] for r in self.metrics['response_times'] 
            if r['success']
        ]
        
        return {
            'total_requests': self.metrics['request_count'],
            'successful_requests': len(successful_times),
            'error_count': self.metrics['error_count'],
            'average_response_time': sum(successful_times) / len(successful_times) if successful_times else 0,
            'max_response_time': max(successful_times) if successful_times else 0,
            'min_response_time': min(successful_times) if successful_times else 0,
            'uptime': time.time() - self.start_time
        }
```

## Security and Isolation

### Process Security

```python
class SecurityManager:
    """Manages security and isolation for subprocess operations"""
    
    def __init__(self):
        self.allowed_paths = []
        self.max_execution_time = 3600  # 1 hour
        self.max_memory_usage = 2 * 1024 * 1024 * 1024  # 2GB
    
    def validate_request(self, request):
        """Validate request against security policies"""
        
        # Check path safety
        for path_key in ['workspace_path', 'json_file', 'output_path']:
            if path_key in request.get('params', {}):
                path = Path(request['params'][path_key])
                if not self._is_path_safe(path):
                    raise ValueError(f"Unsafe path: {path}")
        
        # Check execution time
        if request.get('timeout', 0) > self.max_execution_time:
            raise ValueError(f"Timeout exceeds maximum: {self.max_execution_time}")
    
    def _is_path_safe(self, path):
        """Check if path is within allowed directories"""
        
        if not self.allowed_paths:
            return True  # Allow all if no restrictions
        
        return any(path.is_relative_to(allowed) for allowed in self.allowed_paths)
```

## Best Practices and Optimization

### Resource Management

```python
class ResourceManager:
    """Comprehensive resource management for subprocess operations"""
    
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp(prefix="ads_worker_")
        self.resource_tracker = {}
    
    def cleanup_resources(self):
        """Comprehensive cleanup of all resources"""
        
        try:
            # Clean temporary files
            shutil.rmtree(self.temp_dir, ignore_errors=True)
            
            # Close ADS workspaces
            self._close_all_workspaces()
            
            # Force garbage collection
            import gc
            gc.collect()
            
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
    
    def _close_all_workspaces(self):
        """Close all open ADS workspaces"""
        try:
            import keysight.ads.de as de
            if de.workspace_is_open():
                workspace = de.active_workspace()
                workspace.close()
        except Exception as e:
            logger.warning(f"Error closing workspace: {e}")
```

This comprehensive subprocess architecture ensures robust, secure, and efficient communication between the GUI and ADS environments while maintaining complete isolation and excellent error handling capabilities.
