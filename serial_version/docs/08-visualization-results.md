# Visualization and Results Processing

## Overview

The visualization and results processing system provides comprehensive tools for analyzing RFIC EM simulation results, including S-parameter extraction, plotting, and export capabilities. The system supports multiple output formats and provides real-time visualization for immediate design feedback.

## Results Processing Pipeline

### Complete Results Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    Results Processing Pipeline               │
├─────────────────────────────────────────────────────────────┤
│ 1. 📊 ADS Results            │ 2. 🔄 Data Processing        │
│    ├── EM simulation         │    ├── Touchstone parsing   │
│    ├── S-parameter export   │    ├── Data validation      │
│    └── Dataset generation   │    └── Format conversion    │
├─────────────────────────────────────────────────────────────┤
│ 3. 📈 Visualization         │ 4. 📤 Export Options         │
│    ├── Real-time plots      │    ├── Touchstone (.sNp)   │
│    ├── Interactive charts   │    ├── CSV format          │
│    └── Comparison tools     │    ├── MATLAB format       │
└─────────────────────────────────────────────────────────────┘
```

## S-Parameter Processing

### Touchstone File Processing

```python
class TouchstoneProcessor:
    """Comprehensive Touchstone file processing"""
    
    def __init__(self):
        self.supported_formats = ['s2p', 's3p', 's4p', 'sNp']
        self.precision = 12
    
    def parse_touchstone(self, file_path):
        """Parse Touchstone file with comprehensive validation"""
        
        try:
            # Try using scikit-rf for robust parsing
            import skrf as rf
            network = rf.Network(file_path)
            
            return {
                'success': True,
                'frequency': network.f,
                's_parameters': network.s,
                'z0': network.z0,
                'ports': network.nports,
                'comments': network.comments
            }
            
        except ImportError:
            # Fallback to manual parsing
            return self._manual_parse_touchstone(file_path)
        
        except Exception as e:
            return {
                'success': False,
                'error': f"Failed to parse Touchstone file: {e}"
            }
    
    def _manual_parse_touchstone(self, file_path):
        """Manual Touchstone file parsing as fallback"""
        
        with open(file_path, 'r') as f:
            lines = f.readlines()
        
        # Parse header
        header_info = self._parse_header(lines)
        
        # Parse data
        frequency_data = []
        s_data = []
        
        for line in lines:
            if line.strip() and not line.startswith('!'):
                values = line.strip().split()
                if values:
                    frequency_data.append(float(values[0]))
                    s_data.append([float(x) for x in values[1:]])
        
        # Convert to complex S-parameters
        s_parameters = self._convert_to_complex(s_data, header_info['format'])
        
        return {
            'success': True,
            'frequency': np.array(frequency_data),
            's_parameters': s_parameters,
            'ports': header_info['ports']
        }
    
    def _parse_header(self, lines):
        """Parse Touchstone file header"""
        
        for line in lines:
            if line.startswith('#'):
                parts = line.strip().split()
                return {
                    'frequency_unit': parts[1],
                    'parameter': parts[2],
                    'format': parts[3],
                    'z0': float(parts[5]) if len(parts) > 5 else 50.0,
                    'ports': int(parts[2][1]) if len(parts[2]) > 1 else 2
                }
        
        return {'frequency_unit': 'Hz', 'parameter': 'S', 'format': 'MA', 'z0': 50.0, 'ports': 2}
    
    def _convert_to_complex(self, data, format_type):
        """Convert raw data to complex S-parameters"""
        
        if format_type.upper() == 'MA':
            # Magnitude-Angle format
            return data[::2] * np.exp(1j * np.radians(data[1::2]))
        elif format_type.upper() == 'DB':
            # dB-Angle format
            magnitude = 10**(data[::2] / 20)
            return magnitude * np.exp(1j * np.radians(data[1::2]))
        elif format_type.upper() == 'RI':
            # Real-Imaginary format
            return data[::2] + 1j * data[1::2]
        
        return np.array(data).reshape(-1, 2, 2)
```

## Visualization Components

### Real-time Plotting System

```python
class ResultsVisualizer:
    """Comprehensive results visualization with real-time updates"""
    
    def __init__(self, parent_widget):
        self.parent = parent_widget
        self.figure = None
        self.axes = None
        self.canvas = None
        self.current_data = None
        self.plot_config = {}
        
        self._setup_plotting_backend()
    
    def _setup_plotting_backend(self):
        """Setup matplotlib backend for embedding"""
        
        try:
            import matplotlib
            matplotlib.use('TkAgg')
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            from matplotlib.figure import Figure
            
            self.figure = Figure(figsize=(10, 6), dpi=100)
            self.canvas = FigureCanvasTkAgg(self.figure, self.parent)
            self.canvas.get_tk_widget().pack(fill='both', expand=True)
            
            # Setup navigation toolbar
            from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk
            self.toolbar = NavigationToolbar2Tk(self.canvas, self.parent)
            self.toolbar.update()
            
        except ImportError:
            # Fallback to text-based display
            self._setup_text_display()
    
    def plot_s_parameters(self, data, plot_type='magnitude', selected_params=None):
        """Plot S-parameters with multiple visualization options"""
        
        if not data:
            return
        
        frequency = data['frequency']
        s_params = data['s_parameters']
        ports = data['ports']
        
        # Clear previous plots
        self.figure.clear()
        
        # Create subplots
        if plot_type == 'all':
            self._create_combined_plot(frequency, s_params, ports)
        else:
            self._create_single_plot(frequency, s_params, ports, plot_type, selected_params)
        
        self.figure.tight_layout()
        self.canvas.draw()
    
    def _create_combined_plot(self, frequency, s_params, ports):
        """Create combined plot with multiple parameter types"""
        
        # Create 2x2 subplot layout
        axes = self.figure.subplots(2, 2, figsize=(12, 8))
        
        # Magnitude plot
        self._plot_magnitude(axes[0, 0], frequency, s_params, ports)
        axes[0, 0].set_title('Magnitude (dB)')
        
        # Phase plot
        self._plot_phase(axes[0, 1], frequency, s_params, ports)
        axes[0, 1].set_title('Phase (degrees)')
        
        # Smith chart
        self._plot_smith_chart(axes[1, 0], s_params)
        axes[1, 0].set_title('Smith Chart')
        
        # VSWR plot
        self._plot_vswr(axes[1, 1], frequency, s_params, ports)
        axes[1, 1].set_title('VSWR')
    
    def _plot_magnitude(self, ax, frequency, s_params, ports):
        """Plot magnitude in dB"""
        
        colors = plt.cm.Set3(np.linspace(0, 1, ports * ports))
        
        for i in range(ports):
            for j in range(ports):
                s_ij = s_params[:, i, j]
                magnitude_db = 20 * np.log10(np.abs(s_ij))
                
                ax.plot(
                    frequency / 1e9, 
                    magnitude_db,
                    color=colors[i * ports + j],
                    label=f'S{i+1}{j+1}',
                    linewidth=2
                )
        
        ax.set_xlabel('Frequency (GHz)')
        ax.set_ylabel('Magnitude (dB)')
        ax.grid(True, alpha=0.3)
        ax.legend()
    
    def _plot_phase(self, ax, frequency, s_params, ports):
        """Plot phase in degrees"""
        
        colors = plt.cm.Set3(np.linspace(0, 1, ports * ports))
        
        for i in range(ports):
            for j in range(ports):
                s_ij = s_params[:, i, j]
                phase_deg = np.angle(s_ij, deg=True)
                
                ax.plot(
                    frequency / 1e9,
                    phase_deg,
                    color=colors[i * ports + j],
                    label=f'S{i+1}{j+1}',
                    linewidth=2
                )
        
        ax.set_xlabel('Frequency (GHz)')
        ax.set_ylabel('Phase (degrees)')
        ax.grid(True, alpha=0.3)
        ax.legend()
    
    def _plot_smith_chart(self, ax, s_params):
        """Create Smith chart visualization"""
        
        from matplotlib.patches import Circle
        
        # Create Smith chart background
        smith_circle = Circle((0, 0), 1, fill=False, color='black', linewidth=1)
        ax.add_patch(smith_circle)
        
        # Plot S-parameters
        for i in range(s_params.shape[1]):
            for j in range(s_params.shape[2]):
                s_ij = s_params[:, i, j]
                ax.plot(np.real(s_ij), np.imag(s_ij), 
                       label=f'S{i+1}{j+1}', linewidth=2)
        
        ax.set_xlim(-1.2, 1.2)
        ax.set_ylim(-1.2, 1.2)
        ax.set_aspect('equal')
        ax.grid(True, alpha=0.3)
        ax.legend()
    
    def _plot_vswr(self, ax, frequency, s_params, ports):
        """Plot Voltage Standing Wave Ratio"""
        
        colors = plt.cm.Set3(np.linspace(0, 1, ports))
        
        for i in range(ports):
            s_ii = s_params[:, i, i]
            vswr = (1 + np.abs(s_ii)) / (1 - np.abs(s_ii))
            
            ax.plot(
                frequency / 1e9,
                vswr,
                color=colors[i],
                label=f'S{i+1}{i+1}',
                linewidth=2
            )
        
        ax.set_xlabel('Frequency (GHz)')
        ax.set_ylabel('VSWR')
        ax.set_ylim(1, 10)
        ax.grid(True, alpha=0.3)
        ax.legend()
```

## Interactive Features

### Real-time Parameter Selection

```python
class InteractiveParameterSelector:
    """Interactive parameter selection with dynamic updates"""
    
    def __init__(self, parent_frame):
        self.parent = parent_frame
        self.parameter_vars = {}
        self.callback = None
        
        self._create_parameter_controls()
    
    def _create_parameter_controls(self):
        """Create interactive parameter controls"""
        
        control_frame = ttk.LabelFrame(self.parent, text="Parameter Selection")
        control_frame.pack(fill="x", padx=10, pady=5)
        
        # Parameter type selection
        type_frame = ttk.Frame(control_frame)
        type_frame.pack(fill="x", padx=5, pady=5)
        
        self.plot_type_var = tk.StringVar(value="magnitude")
        plot_types = [
            ("Magnitude (dB)", "magnitude"),
            ("Phase (°)", "phase"),
            ("Real Part", "real"),
            ("Imaginary Part", "imag"),
            ("Smith Chart", "smith"),
            ("VSWR", "vswr"),
            ("Group Delay", "group_delay")
        ]
        
        for label, value in plot_types:
            ttk.Radiobutton(
                type_frame,
                text=label,
                variable=self.plot_type_var,
                value=value,
                command=self._on_parameter_change
            ).pack(side="left", padx=5)
        
        # Frequency range controls
        range_frame = ttk.Frame(control_frame)
        range_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Label(range_frame, text="Frequency Range:").pack(side="left", padx=5)
        
        self.freq_start_var = tk.StringVar(value="Auto")
        self.freq_stop_var = tk.StringVar(value="Auto")
        
        ttk.Entry(range_frame, textvariable=self.freq_start_var, width=10).pack(side="left", padx=2)
        ttk.Label(range_frame, text="to").pack(side="left", padx=2)
        ttk.Entry(range_frame, textvariable=self.freq_stop_var, width=10).pack(side="left", padx=2)
        
        ttk.Button(range_frame, text="Apply", command=self._on_parameter_change).pack(side="left", padx=10)
    
    def set_available_parameters(self, ports):
        """Create parameter checkboxes based on port count"""
        
        # Clear existing checkboxes
        for widget in self.parent.winfo_children():
            if isinstance(widget, ttk.LabelFrame) and widget['text'] == "Parameters":
                widget.destroy()
        
        param_frame = ttk.LabelFrame(self.parent, text="Parameters")
        param_frame.pack(fill="x", padx=10, pady=5)
        
        self.parameter_vars = {}
        
        # Create parameter checkboxes
        for i in range(ports):
            for j in range(ports):
                param_name = f"S{i+1}{j+1}"
                var = tk.BooleanVar(value=(i == j))  # Diagonal elements default to True
                self.parameter_vars[param_name] = var
                
                chk = ttk.Checkbutton(
                    param_frame,
                    text=param_name,
                    variable=var,
                    command=self._on_parameter_change
                )
                chk.pack(side="left", padx=2)
    
    def _on_parameter_change(self):
        """Handle parameter change callback"""
        
        selected_params = [name for name, var in self.parameter_vars.items() if var.get()]
        plot_type = self.plot_type_var.get()
        
        if self.callback:
            self.callback(selected_params, plot_type)
```

## Export Capabilities

### Multi-format Export System

```python
class ResultsExporter:
    """Comprehensive results export in multiple formats"""
    
    def __init__(self):
        self.supported_formats = {
            'touchstone': self._export_touchstone,
            'csv': self._export_csv,
            'matlab': self._export_matlab,
            'excel': self._export_excel,
            'plot': self._export_plot
        }
    
    def export_results(self, data, output_path, format_type, **kwargs):
        """Export results in specified format"""
        
        if format_type not in self.supported_formats:
            raise ValueError(f"Unsupported format: {format_type}")
        
        return self.supported_formats[format_type](data, output_path, **kwargs)
    
    def _export_touchstone(self, data, output_path, **kwargs):
        """Export to Touchstone format"""
        
        frequency = data['frequency']
        s_parameters = data['s_parameters']
        
        ports = s_parameters.shape[2]
        extension = f".s{ports}p"
        
        if not output_path.endswith(extension):
            output_path += extension
        
        with open(output_path, 'w') as f:
            # Write header
            f.write("# GHz S MA R 50\n")
            
            # Write data
            for i, freq in enumerate(frequency):
                line = f"{freq/1e9:.6f}"
                
                for j in range(ports):
                    for k in range(ports):
                        s_ij = s_parameters[i, j, k]
                        magnitude = abs(s_ij)
                        angle_deg = np.angle(s_ij, deg=True)
                        line += f" {magnitude:.6f} {angle_deg:.6f}"
                
                f.write(line + "\n")
        
        return output_path
    
    def _export_csv(self, data, output_path, **kwargs):
        """Export to CSV format"""
        
        import csv
        
        frequency = data['frequency']
        s_parameters = data['s_parameters']
        ports = s_parameters.shape[2]
        
        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)
            
            # Write header
            header = ['Frequency (Hz)']
            for i in range(ports):
                for j in range(ports):
                    header.extend([f'S{i+1}{j+1}_mag', f'S{i+1}{j+1}_phase'])
            writer.writerow(header)
            
            # Write data
            for i, freq in enumerate(frequency):
                row = [freq]
                for j in range(ports):
                    for k in range(ports):
                        s_ij = s_parameters[i, j, k]
                        row.extend([abs(s_ij), np.angle(s_ij, deg=True)])
                writer.writerow(row)
        
        return output_path
    
    def _export_matlab(self, data, output_path, **kwargs):
        """Export to MATLAB format"""
        
        try:
            from scipy.io import savemat
            
            matlab_data = {
                'frequency': data['frequency'],
                's_parameters': data['s_parameters'],
                'ports': data['ports'],
                'z0': data.get('z0', 50.0)
            }
            
            savemat(output_path, matlab_data)
            return output_path
            
        except ImportError:
            raise RuntimeError("scipy required for MATLAB export")
```

## Advanced Analysis Features

### Group Delay Analysis

```python
class GroupDelayAnalyzer:
    """Advanced group delay analysis"""
    
    def __init__(self):
        self.window_functions = {
            'rectangular': lambda x: np.ones_like(x),
            'hamming': np.hamming,
            'hanning': np.hanning,
            'blackman': np.blackman
        }
    
    def calculate_group_delay(self, s_parameters, frequency, port_pair=(0, 0), 
                            window='hamming', smooth_factor=1.0):
        """Calculate group delay with smoothing options"""
        
        # Extract S-parameter for specified port pair
        s_ij = s_parameters[:, port_pair[0], port_pair[1]]
        
        # Calculate phase
        phase_rad = np.unwrap(np.angle(s_ij))
        
        # Calculate group delay: τg = -dφ/dω
        omega = 2 * np.pi * frequency
        d_phase = np.gradient(phase_rad, omega)
        group_delay = -d_phase
        
        # Apply smoothing if requested
        if smooth_factor > 1.0:
            window_size = int(len(frequency) / smooth_factor)
            if window_size > 1:
                window_func = self.window_functions.get(window, np.hamming)
                w = window_func(window_size)
                group_delay = np.convolve(group_delay, w/w.sum(), mode='same')
        
        return {
            'frequency': frequency,
            'group_delay': group_delay,
            'unit': 'seconds'
        }
    
    def calculate_quality_factor(self, s_parameters, frequency, resonance_freq):
        """Calculate quality factor from S-parameters"""
        
        # Find resonance index
        idx = np.argmin(np.abs(frequency - resonance_freq))
        
        # Extract S21 at resonance
        s21 = s_parameters[:, 1, 0] if s_parameters.shape[1] > 1 else s_parameters[:, 0, 0]
        
        # Calculate insertion loss
        il_db = 20 * np.log10(np.abs(s21))
        
        # Find 3dB bandwidth
        resonance_il = il_db[idx]
        threshold = resonance_il + 3
        
        # Find bandwidth points
        mask = il_db <= threshold
        if np.any(mask):
            bandwidth_indices = np.where(mask)[0]
            f_lower = frequency[bandwidth_indices[0]]
            f_upper = frequency[bandwidth_indices[-1]]
            bandwidth = f_upper - f_lower
            
            q_factor = resonance_freq / bandwidth
        else:
            q_factor = np.inf
        
        return {
            'resonance_frequency': resonance_freq,
            'quality_factor': q_factor,
            'bandwidth': bandwidth,
            'insertion_loss': resonance_il
        }
```

## Batch Processing and Comparison

### Results Comparison System

```python
class ResultsComparator:
    """Compare multiple simulation results"""
    
    def __init__(self):
        self.comparison_data = {}
    
    def add_results(self, name, data, metadata=None):
        """Add results for comparison"""
        
        self.comparison_data[name] = {
            'data': data,
            'metadata': metadata or {}
        }
    
    def create_comparison_plot(self, parameter='S11', plot_type='magnitude'):
        """Create comparison plot across multiple datasets"""
        
        fig, ax = plt.subplots(figsize=(12, 8))
        
        colors = plt.cm.Set1(np.linspace(0, 1, len(self.comparison_data)))
        
        for i, (name, dataset) in enumerate(self.comparison_data.items()):
            data = dataset['data']
            frequency = data['frequency']
            s_params = data['s_parameters']
            
            # Extract parameter
            param_data = self._extract_parameter(s_params, parameter, plot_type)
            
            ax.plot(
                frequency / 1e9,
                param_data,
                color=colors[i],
                label=name,
                linewidth=2,
                marker='o',
                markersize=4,
                markevery=20
            )
        
        ax.set_xlabel('Frequency (GHz)')
        ax.set_ylabel(f'{parameter} ({plot_type})')
        ax.set_title(f'{parameter} Comparison')
        ax.grid(True, alpha=0.3)
        ax.legend()
        
        return fig
    
    def generate_comparison_report(self, output_path):
        """Generate comprehensive comparison report"""
        
        report = {
            'summary': {
                'datasets': len(self.comparison_data),
                'parameters_analyzed': ['S11', 'S21', 'S12', 'S22']
            },
            'detailed_analysis': {}
        }
        
        for param in ['S11', 'S21', 'S12', 'S22']:
            report['detailed_analysis'][param] = self._analyze_parameter(param)
        
        # Save report
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2, cls=NumpyEncoder)
        
        return output_path
    
    def _extract_parameter(self, s_params, parameter, plot_type):
        """Extract specific parameter data"""
        
        # Parse parameter notation (e.g., S11 -> [0,0])
        row = int(parameter[1]) - 1
        col = int(parameter[2]) - 1
        
        s_ij = s_params[:, row, col]
        
        if plot_type == 'magnitude':
            return 20 * np.log10(np.abs(s_ij))
        elif plot_type == 'phase':
            return np.angle(s_ij, deg=True)
        elif plot_type == 'real':
            return np.real(s_ij)
        elif plot_type == 'imag':
            return np.imag(s_ij)
        
        return np.abs(s_ij)

class NumpyEncoder(json.JSONEncoder):
    """JSON encoder for numpy arrays"""
    
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return json.JSONEncoder.default(self, obj)
```

This comprehensive visualization and results processing system provides professional-grade tools for RFIC EM simulation analysis with support for multiple formats, real-time updates, and advanced analysis capabilities.