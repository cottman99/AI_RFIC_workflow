# Error Handling and Validation Patterns

## Overview

The RFIC Layout-to-EM Simulation system implements a comprehensive, multi-layered error handling architecture designed for production-grade reliability. This system provides graceful degradation, detailed diagnostics, and user-friendly recovery mechanisms throughout the entire workflow.

## Error Classification System

### Error Taxonomy

```python
class ErrorClassification:
    """Comprehensive error classification for the RFIC system"""
    
    ERROR_CATEGORIES = {
        'ENVIRONMENTAL': {
            'ADS_NOT_FOUND': 'ADS installation not detected',
            'PYTHON_PATH_ERROR': 'ADS Python path configuration issue',
            'LICENSE_UNAVAILABLE': 'ADS license not available',
            'PERMISSION_DENIED': 'Insufficient file system permissions'
        },
        'VALIDATION': {
            'JSON_SCHEMA_ERROR': 'JSON layout schema validation failed',
            'GEOMETRY_ERROR': 'Invalid geometry specification',
            'PORT_PLACEMENT_ERROR': 'Port placement validation failed',
            'PARAMETER_ERROR': 'Invalid simulation parameters'
        },
        'SUBPROCESS': {
            'PROCESS_TIMEOUT': 'Subprocess execution timeout',
            'COMMUNICATION_ERROR': 'Inter-process communication failure',
            'CONTEXT_SWITCH_ERROR': 'ADS/EMPro context switching error',
            'RESOURCE_LEAK': 'Resource cleanup failure'
        },
        'ADS_INTEGRATION': {
            'WORKSPACE_ERROR': 'ADS workspace creation/management error',
            'LIBRARY_ERROR': 'ADS library creation/access error',
            'TECHNOLOGY_ERROR': 'Technology setup failure',
            'SIMULATION_ERROR': 'EM simulation execution error'
        },
        'DATA_PROCESSING': {
            'TOUCHSTONE_PARSE_ERROR': 'S-parameter file parsing error',
            'PLOT_GENERATION_ERROR': 'Results visualization error',
            'EXPORT_ERROR': 'Data export failure',
            'MEMORY_ERROR': 'Memory allocation/processing error'
        }
    }
    
    @classmethod
    def classify_error(cls, error):
        """Classify error based on type and context"""
        
        error_str = str(error).lower()
        
        # Environmental errors
        if any(keyword in error_str for keyword in ['ads', 'keysight', 'license', 'python']):
            return 'ENVIRONMENTAL'
        
        # Validation errors
        if any(keyword in error_str for keyword in ['json', 'schema', 'validation', 'geometry']):
            return 'VALIDATION'
        
        # Subprocess errors
        if any(keyword in error_str for keyword in ['process', 'timeout', 'communication']):
            return 'SUBPROCESS'
        
        # ADS integration errors
        if any(keyword in error_str for keyword in ['workspace', 'library', 'technology', 'simulation']):
            return 'ADS_INTEGRATION'
        
        # Data processing errors
        if any(keyword in error_str for keyword in ['touchstone', 'plot', 'export', 'memory']):
            return 'DATA_PROCESSING'
        
        return 'GENERAL'
```

## Multi-Level Error Handling

### Level 1: GUI-Level Error Handling

```python
class GUIErrorHandler:
    """User-friendly GUI error handling with recovery suggestions"""
    
    def __init__(self, parent_window):
        self.parent = parent_window
        self.error_dialog = None
        self.recovery_actions = {}
    
    def handle_error(self, error, context=None):
        """Handle errors with user-friendly messages and recovery options"""
        
        error_info = self._analyze_error(error, context)
        
        # Show appropriate dialog based on severity
        if error_info['severity'] == 'CRITICAL':
            self._show_critical_error_dialog(error_info)
        elif error_info['severity'] == 'WARNING':
            self._show_warning_dialog(error_info)
        elif error_info['severity'] == 'INFO':
            self._show_info_dialog(error_info)
    
    def _analyze_error(self, error, context):
        """Analyze error and provide detailed information"""
        
        error_type = ErrorClassification.classify_error(error)
        
        analysis = {
            'type': error_type,
            'severity': self._determine_severity(error, error_type),
            'message': str(error),
            'traceback': traceback.format_exc(),
            'recovery_options': self._get_recovery_options(error_type, context),
            'technical_details': self._get_technical_details(error, context)
        }
        
        return analysis
    
    def _show_critical_error_dialog(self, error_info):
        """Show critical error dialog with recovery options"""
        
        dialog = tk.Toplevel(self.parent)
        dialog.title("Critical Error")
        dialog.geometry("600x400")
        dialog.transient(self.parent)
        dialog.grab_set()
        
        # Error icon
        icon_label = ttk.Label(dialog, text="⚠️", font=('Arial', 24))
        icon_label.pack(pady=10)
        
        # Error message
        msg_frame = ttk.LabelFrame(dialog, text="Error Details")
        msg_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        msg_text = tk.Text(msg_frame, height=8, wrap=tk.WORD)
        msg_text.pack(fill="both", expand=True, padx=5, pady=5)
        msg_text.insert(1.0, error_info['message'])
        msg_text.config(state=tk.DISABLED)
        
        # Recovery options
        recovery_frame = ttk.LabelFrame(dialog, text="Recovery Options")
        recovery_frame.pack(fill="x", padx=10, pady=5)
        
        for i, option in enumerate(error_info['recovery_options']):
            btn = ttk.Button(
                recovery_frame,
                text=option['label'],
                command=lambda o=option: self._execute_recovery(o)
            )
            btn.pack(fill="x", padx=5, pady=2)
        
        # Technical details expander
        details_frame = ttk.LabelFrame(dialog, text="Technical Details")
        details_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        details_text = tk.Text(details_frame, height=10, wrap=tk.WORD)
        details_text.pack(fill="both", expand=True, padx=5, pady=5)
        details_text.insert(1.0, error_info['technical_details'])
        details_text.config(state=tk.DISABLED)
        
        # Close button
        ttk.Button(dialog, text="Close", command=dialog.destroy).pack(pady=10)
```

### Level 2: Subprocess Error Handling

```python
class SubprocessErrorHandler:
    """Robust error handling for subprocess operations"""
    
    def __init__(self):
        self.timeout_handler = TimeoutHandler()
        self.retry_handler = RetryHandler()
        self.cleanup_handler = CleanupHandler()
    
    def execute_with_error_handling(self, operation, *args, **kwargs):
        """Execute operation with comprehensive error handling"""
        
        try:
            # Setup timeout
            timeout = kwargs.pop('timeout', 300)
            
            with self.timeout_handler.timeout_context(timeout):
                result = operation(*args, **kwargs)
                
            return {'success': True, 'result': result}
            
        except subprocess.TimeoutExpired as e:
            return {
                'success': False,
                'error': 'PROCESS_TIMEOUT',
                'message': f'Operation timed out after {timeout}s',
                'recovery': self.retry_handler.get_retry_strategy('timeout')
            }
            
        except subprocess.CalledProcessError as e:
            return {
                'success': False,
                'error': 'PROCESS_ERROR',
                'message': f'Process failed with exit code {e.returncode}',
                'details': e.stderr,
                'recovery': self._get_process_recovery(e.returncode)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': 'GENERAL_ERROR',
                'message': str(e),
                'recovery': self.retry_handler.get_retry_strategy('general')
            }
        
        finally:
            # Ensure cleanup
            self.cleanup_handler.cleanup_resources()

class TimeoutHandler:
    """Timeout handling with graceful degradation"""
    
    def __init__(self):
        self.default_timeout = 300
        self.operation_timeouts = {
            'create_design': 300,
            'run_simulation': 1800,
            'export_results': 60
        }
    
    def timeout_context(self, timeout=None):
        """Context manager for timeout handling"""
        
        if timeout is None:
            timeout = self.default_timeout
        
        @contextlib.contextmanager
        def timeout_manager():
            import signal
            
            def timeout_handler(signum, frame):
                raise subprocess.TimeoutExpired("Subprocess", timeout)
            
            # Set timeout
            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(timeout)
            
            try:
                yield
            finally:
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)
        
        return timeout_manager()

class RetryHandler:
    """Intelligent retry strategies"""
    
    def __init__(self):
        self.retry_strategies = {
            'timeout': {
                'max_retries': 3,
                'backoff_factor': 2.0,
                'initial_delay': 1.0
            },
            'general': {
                'max_retries': 2,
                'backoff_factor': 1.5,
                'initial_delay': 0.5
            }
        }
    
    def get_retry_strategy(self, error_type):
        """Get appropriate retry strategy for error type"""
        
        strategy = self.retry_strategies.get(error_type, self.retry_strategies['general'])
        
        return {
            'type': 'retry',
            'strategy': strategy,
            'execute': lambda: self._execute_retry(strategy)
        }
    
    def _execute_retry(self, strategy):
        """Execute retry with exponential backoff"""
        
        import time
        
        def retry_wrapper(operation, *args, **kwargs):
            delay = strategy['initial_delay']
            
            for attempt in range(strategy['max_retries']):
                try:
                    return operation(*args, **kwargs)
                except Exception as e:
                    if attempt == strategy['max_retries'] - 1:
                        raise e
                    
                    time.sleep(delay)
                    delay *= strategy['backoff_factor']
        
        return retry_wrapper
```

### Level 3: ADS-Level Error Handling

```python
class ADSErrorHandler:
    """Specialized ADS/EMPro error handling"""
    
    def __init__(self):
        self.error_patterns = self._initialize_error_patterns()
        self.recovery_strategies = self._initialize_recovery_strategies()
    
    def handle_ads_error(self, error, operation_context):
        """Handle ADS-specific errors with context-aware recovery"""
        
        error_type = self._identify_ads_error(error)
        
        if error_type == 'WORKSPACE_LOCK':
            return self._handle_workspace_lock(operation_context)
        elif error_type == 'LICENSE_EXPIRED':
            return self._handle_license_expired(operation_context)
        elif error_type == 'TECHNOLOGY_MISSING':
            return self._handle_technology_missing(operation_context)
        elif error_type == 'PORT_CONFIGURATION_ERROR':
            return self._handle_port_configuration_error(operation_context)
        
        return self._handle_generic_ads_error(error, operation_context)
    
    def _initialize_error_patterns(self):
        """Initialize ADS-specific error patterns"""
        
        return {
            'WORKSPACE_LOCK': [
                r'workspace.*locked',
                r'cannot.*open.*workspace',
                r'workspace.*already.*open'
            ],
            'LICENSE_EXPIRED': [
                r'license.*expired',
                r'license.*not.*available',
                r'license.*error'
            ],
            'TECHNOLOGY_MISSING': [
                r'technology.*not.*found',
                r'pdk.*not.*available',
                r'technology.*error'
            ],
            'PORT_CONFIGURATION_ERROR': [
                r'port.*not.*found',
                r'invalid.*port',
                r'port.*configuration'
            ]
        }
    
    def _handle_workspace_lock(self, context):
        """Handle workspace lock conflicts"""
        
        return {
            'type': 'workspace_lock',
            'message': 'Workspace is locked by another process',
            'recovery': [
                {
                    'label': 'Force unlock workspace',
                    'action': lambda: self._force_unlock_workspace(context['workspace_path'])
                },
                {
                    'label': 'Use different workspace',
                    'action': lambda: self._create_new_workspace(context)
                }
            ]
        }
    
    def _force_unlock_workspace(self, workspace_path):
        """Force unlock ADS workspace"""
        
        try:
            import keysight.ads.de as de
            
            # Try to close any open workspace
            if de.workspace_is_open():
                workspace = de.active_workspace()
                workspace.close()
            
            # Remove lock files
            lock_files = [
                os.path.join(workspace_path, '.lock'),
                os.path.join(workspace_path, 'workspace.lock')
            ]
            
            for lock_file in lock_files:
                if os.path.exists(lock_file):
                    os.remove(lock_file)
            
            return True
            
        except Exception as e:
            raise RuntimeError(f"Failed to unlock workspace: {e}")
```

## Validation System

### Comprehensive Validation Framework

```python
class ValidationFramework:
    """Comprehensive validation system with staged validation"""
    
    def __init__(self):
        self.validators = {
            'environment': EnvironmentValidator(),
            'json': JSONValidator(),
            'geometry': GeometryValidator(),
            'simulation': SimulationValidator(),
            'results': ResultsValidator()
        }
    
    def validate_complete_workflow(self, workflow_data):
        """Run complete workflow validation"""
        
        validation_results = {
            'summary': {'total': 0, 'passed': 0, 'failed': 0, 'warnings': 0},
            'details': {},
            'recommendations': []
        }
        
        validation_stages = [
            ('environment', 'Environment validation'),
            ('json', 'JSON layout validation'),
            ('geometry', 'Geometry validation'),
            ('simulation', 'Simulation parameters validation'),
            ('results', 'Results validation')
        ]
        
        for stage, description in validation_stages:
            result = self.validators[stage].validate(workflow_data)
            
            validation_results['details'][stage] = result
            validation_results['summary']['total'] += result['total']
            validation_results['summary']['passed'] += result['passed']
            validation_results['summary']['failed'] += result['failed']
            validation_results['summary']['warnings'] += result['warnings']
            
            if result['recommendations']:
                validation_results['recommendations'].extend(result['recommendations'])
        
        return validation_results

class JSONValidator:
    """Comprehensive JSON layout validation"""
    
    def validate(self, workflow_data):
        """Validate JSON layout structure"""
        
        results = {
            'total': 0,
            'passed': 0,
            'failed': 0,
            'warnings': 0,
            'recommendations': []
        }
        
        try:
            # Schema validation
            schema_result = self._validate_schema(workflow_data['json_layout'])
            results.update(schema_result)
            
            # Geometry validation
            geometry_result = self._validate_geometry(workflow_data['json_layout'])
            results.update(geometry_result)
            
            # Port validation
            port_result = self._validate_ports(workflow_data['json_layout'])
            results.update(port_result)
            
        except Exception as e:
            results['failed'] += 1
            results['recommendations'].append(f"JSON validation failed: {e}")
        
        return results
    
    def _validate_geometry(self, layout_data):
        """Validate geometry specifications"""
        
        results = {'passed': 0, 'failed': 0, 'warnings': 0, 'recommendations': []}
        
        matrices = layout_data.get('layout_matrices', {})
        metadata = layout_data.get('metadata', {})
        
        base_shape = metadata.get('base_matrix_shape', [0, 0])
        
        for layer_name, matrix in matrices.items():
            # Check matrix dimensions
            if len(matrix) != base_shape[0] or len(matrix[0]) != base_shape[1]:
                results['failed'] += 1
                results['recommendations'].append(
                    f"Layer {layer_name} dimensions don't match base shape"
                )
            
            # Check for empty layers
            if not any(any(row) for row in matrix):
                results['warnings'] += 1
                results['recommendations'].append(
                    f"Layer {layer_name} contains no geometry"
                )
            
            # Check connectivity
            if self._check_connectivity(matrix):
                results['passed'] += 1
            else:
                results['warnings'] += 1
                results['recommendations'].append(
                    f"Layer {layer_name} has disconnected geometry"
                )
        
        return results
    
    def _check_connectivity(self, matrix):
        """Check geometry connectivity"""
        
        import numpy as np
        from scipy.ndimage import label
        
        arr = np.array(matrix)
        labeled, num_features = label(arr)
        
        return num_features <= 1
```

## Logging and Diagnostics

### Comprehensive Logging System

```python
class LoggingManager:
    """Comprehensive logging for debugging and diagnostics"""
    
    def __init__(self, log_dir):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        self.setup_logging()
    
    def setup_logging(self):
        """Setup comprehensive logging configuration"""
        
        # Create formatters
        detailed_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        simple_formatter = logging.Formatter(
            '%(levelname)s: %(message)s'
        )
        
        # File handler for detailed logging
        file_handler = logging.FileHandler(
            self.log_dir / f'ads_gui_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)
        
        # Console handler for user messages
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(simple_formatter)
        
        # Setup logger
        self.logger = logging.getLogger('RFIC_GUI')
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def log_workflow_event(self, event_type, details):
        """Log workflow events with structured data"""
        
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'event_type': event_type,
            'details': details,
            'system_info': self._get_system_info()
        }
        
        self.logger.info(f"Workflow Event: {json.dumps(log_entry, indent=2)}")
    
    def _get_system_info(self):
        """Get system information for diagnostics"""
        
        return {
            'platform': platform.platform(),
            'python_version': sys.version,
            'ads_version': self._get_ads_version(),
            'memory_usage': psutil.virtual_memory().percent if 'psutil' in sys.modules else 'N/A'
        }
    
    def _get_ads_version(self):
        """Get ADS version information"""
        
        try:
            import keysight.ads.de as de
            return de.get_version()
        except:
            return 'ADS not available'
```

This comprehensive error handling and validation system ensures robust, reliable operation of the RFIC Layout-to-EM Simulation system with excellent user experience and detailed diagnostics for troubleshooting.