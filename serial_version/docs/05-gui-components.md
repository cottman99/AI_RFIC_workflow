# GUI Components and User Interface Patterns

## Overview

The RFIC Layout-to-EM Simulation GUI implements a sophisticated, multi-tabbed interface designed for professional RFIC design workflows. The interface follows modern UX principles with progressive disclosure, real-time feedback, and comprehensive error handling throughout the design-to-simulation pipeline.

## Main Application Structure

### Tabbed Interface Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  RFIC Layout-to-EM Simulation System                            │
├─────────────────────────────────────────────────────────────────┤
│ 📁 Input  │ ⚙️ Config  │ 🔧 PDK  │ 🗂️ Mapping  │ 📊 Results │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  [Active Tab Content Area]                                     │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │ Status Bar: [Progress: 45%] [Process: ADS Context]      │  │
│  └─────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Tab Specifications

| Tab | Purpose | Key Features | User Journey |
|-----|---------|--------------|--------------|
| **📁 Input** | JSON file management | File browser, preview, validation | Design import and verification |
| **⚙️ Configuration** | Simulation setup | Workspace paths, frequency ranges | Environment configuration |
| **🔧 PDK Config** | Technology selection | PDK vs reference library modes | Technology setup |
| **🗂️ Layer Mapping** | Technology mapping | JSON→ADS layer mapping | Layer configuration |
| **📊 Results** | S-parameter analysis | Touchstone parsing, plotting | Results visualization |

## Input Tab Components

### File Management Interface

```python
class InputTab(ttk.Frame):
    """Comprehensive input management with validation"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.current_file = None
        self.validation_status = tk.StringVar(value="No file selected")
        
        self._create_file_section()
        self._create_preview_section()
        self._create_validation_section()
    
    def _create_file_section(self):
        """File selection and management"""
        
        file_frame = ttk.LabelFrame(self, text="Layout File Management")
        file_frame.pack(fill="x", padx=10, pady=5)
        
        # File selection
        ttk.Label(file_frame, text="JSON Layout File:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        
        self.file_path_var = tk.StringVar()
        file_entry = ttk.Entry(file_frame, textvariable=self.file_path_var, width=60)
        file_entry.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Button(file_frame, text="Browse", command=self._browse_file).grid(row=0, column=2, padx=5, pady=5)
        ttk.Button(file_frame, text="Recent", command=self._show_recent_files).grid(row=0, column=3, padx=5, pady=5)
        
        # File operations
        operation_frame = ttk.Frame(file_frame)
        operation_frame.grid(row=1, column=0, columnspan=4, pady=10)
        
        ttk.Button(operation_frame, text="Validate", command=self._validate_file).pack(side="left", padx=5)
        ttk.Button(operation_frame, text="Preview", command=self._preview_layout).pack(side="left", padx=5)
        ttk.Button(operation_frame, text="Edit", command=self._edit_layout).pack(side="left", padx=5)
    
    def _create_preview_section(self):
        """Real-time layout preview"""
        
        preview_frame = ttk.LabelFrame(self, text="Layout Preview")
        preview_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Preview canvas
        self.preview_canvas = tk.Canvas(preview_frame, width=400, height=300, bg="white")
        self.preview_canvas.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Layer controls
        layer_frame = ttk.Frame(preview_frame)
        layer_frame.pack(fill="x", padx=5, pady=5)
        
        self.layer_vars = {}
        self.create_layer_controls(layer_frame)
    
    def create_layer_controls(self, parent):
        """Create layer visibility controls"""
        
        ttk.Label(parent, text="Layer Visibility:").pack(side="left", padx=5)
        
        # Dynamic layer controls based on loaded file
        self.layer_frame = ttk.Frame(parent)
        self.layer_frame.pack(side="left", fill="x", expand=True)
    
    def update_layer_controls(self, layers):
        """Update layer controls based on loaded file"""
        
        # Clear existing controls
        for widget in self.layer_frame.winfo_children():
            widget.destroy()
        
        self.layer_vars = {}
        
        for layer in layers:
            var = tk.BooleanVar(value=True)
            self.layer_vars[layer] = var
            
            chk = ttk.Checkbutton(
                self.layer_frame, 
                text=layer, 
                variable=var,
                command=lambda l=layer: self._toggle_layer_visibility(l)
            )
            chk.pack(side="left", padx=2)
```

### Real-time Validation

```python
class ValidationPanel(ttk.Frame):
    """Real-time validation with detailed feedback"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.validation_tree = None
        self._create_validation_ui()
    
    def _create_validation_ui(self):
        """Create validation interface"""
        
        validation_frame = ttk.LabelFrame(self, text="Validation Results")
        validation_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Validation tree
        self.validation_tree = ttk.Treeview(
            validation_frame,
            columns=('severity', 'message', 'location'),
            show='tree headings',
            height=8
        )
        
        self.validation_tree.heading('#0', text='Item')
        self.validation_tree.heading('severity', text='Severity')
        self.validation_tree.heading('message', text='Message')
        self.validation_tree.heading('location', text='Location')
        
        self.validation_tree.column('#0', width=150)
        self.validation_tree.column('severity', width=80)
        self.validation_tree.column('message', width=300)
        self.validation_tree.column('location', width=150)
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(validation_frame, orient="vertical", command=self.validation_tree.yview)
        h_scrollbar = ttk.Scrollbar(validation_frame, orient="horizontal", command=self.validation_tree.xview)
        
        self.validation_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        self.validation_tree.pack(side="left", fill="both", expand=True)
        v_scrollbar.pack(side="right", fill="y")
        h_scrollbar.pack(side="bottom", fill="x")
    
    def update_validation_results(self, results):
        """Update validation tree with results"""
        
        # Clear existing items
        for item in self.validation_tree.get_children():
            self.validation_tree.delete(item)
        
        # Add validation results
        for category, items in results.items():
            category_id = self.validation_tree.insert('', 'end', text=category)
            
            for item in items:
                self.validation_tree.insert(
                    category_id, 'end',
                    values=(item['severity'], item['message'], item.get('location', ''))
                )
```

## Configuration Tab Components

### Workspace Configuration

```python
class ConfigurationTab(ttk.Frame):
    """Comprehensive configuration management"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.config_vars = {}
        self._create_workspace_config()
        self._create_simulation_config()
        self._create_advanced_config()
    
    def _create_workspace_config(self):
        """Workspace and project configuration"""
        
        workspace_frame = ttk.LabelFrame(self, text="Workspace Configuration")
        workspace_frame.pack(fill="x", padx=10, pady=5)
        
        # Workspace path
        ttk.Label(workspace_frame, text="Workspace Path:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        
        self.workspace_var = tk.StringVar()
        workspace_entry = ttk.Entry(workspace_frame, textvariable=self.workspace_var, width=50)
        workspace_entry.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Button(workspace_frame, text="Browse", command=self._browse_workspace).grid(row=0, column=2, padx=5, pady=5)
        
        # Project settings
        ttk.Label(workspace_frame, text="Library Name:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.library_var = tk.StringVar(value="RFIC_Lib")
        ttk.Entry(workspace_frame, textvariable=self.library_var, width=30).grid(row=1, column=1, padx=5, pady=5)
        
        ttk.Label(workspace_frame, text="Cell Name:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.cell_var = tk.StringVar(value="TestCell")
        ttk.Entry(workspace_frame, textvariable=self.cell_var, width=30).grid(row=2, column=1, padx=5, pady=5)
    
    def _create_simulation_config(self):
        """Simulation parameters configuration"""
        
        sim_frame = ttk.LabelFrame(self, text="Simulation Configuration")
        sim_frame.pack(fill="x", padx=10, pady=5)
        
        # Frequency settings
        freq_frame = ttk.Frame(sim_frame)
        freq_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Label(freq_frame, text="Frequency Range:").pack(side="left", padx=5)
        
        self.freq_start_var = tk.StringVar(value="1MHz")
        self.freq_stop_var = tk.StringVar(value="50GHz")
        
        ttk.Entry(freq_frame, textvariable=self.freq_start_var, width=15).pack(side="left", padx=2)
        ttk.Label(freq_frame, text="to").pack(side="left", padx=2)
        ttk.Entry(freq_frame, textvariable=self.freq_stop_var, width=15).pack(side="left", padx=2)
        
        # Points configuration
        points_frame = ttk.Frame(sim_frame)
        points_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Label(points_frame, text="Frequency Points:").pack(side="left", padx=5)
        self.points_var = tk.StringVar(value="1000")
        ttk.Entry(points_frame, textvariable=self.points_var, width=10).pack(side="left", padx=5)
    
    def _create_advanced_config(self):
        """Advanced configuration options"""
        
        advanced_frame = ttk.LabelFrame(self, text="Advanced Options")
        advanced_frame.pack(fill="x", padx=10, pady=5)
        
        # Solver selection
        solver_frame = ttk.Frame(advanced_frame)
        solver_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Label(solver_frame, text="Solver:").pack(side="left", padx=5)
        self.solver_var = tk.StringVar(value="momentum")
        solver_combo = ttk.Combobox(
            solver_frame, 
            textvariable=self.solver_var,
            values=["momentum", "rfpro", "fem"],
            state="readonly",
            width=15
        )
        solver_combo.pack(side="left", padx=5)
        
        # Mesh settings
        mesh_frame = ttk.Frame(advanced_frame)
        mesh_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Label(mesh_frame, text="Mesh Density:").pack(side="left", padx=5)
        self.mesh_var = tk.StringVar(value="50 cpw")
        mesh_combo = ttk.Combobox(
            mesh_frame,
            textvariable=self.mesh_var,
            values=["25 cpw", "50 cpw", "100 cpw", "200 cpw"],
            state="readonly",
            width=15
        )
        mesh_combo.pack(side="left", padx=5)
```

## PDK Configuration Tab

### Technology Selection

```python
class PDKConfigTab(ttk.Frame):
    """PDK and technology configuration"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.pdk_vars = {}
        self._create_technology_selection()
        self._create_pdk_browser()
        self._create_reference_config()
    
    def _create_technology_selection(self):
        """Technology selection interface"""
        
        tech_frame = ttk.LabelFrame(self, text="Technology Selection")
        tech_frame.pack(fill="x", padx=10, pady=5)
        
        # Mode selection
        mode_frame = ttk.Frame(tech_frame)
        mode_frame.pack(fill="x", padx=5, pady=5)
        
        self.mode_var = tk.StringVar(value="reference")
        
        ttk.Radiobutton(
            mode_frame,
            text="Reference Library",
            variable=self.mode_var,
            value="reference",
            command=self._update_mode
        ).pack(side="left", padx=20)
        
        ttk.Radiobutton(
            mode_frame,
            text="PDK Mode",
            variable=self.mode_var,
            value="pdk",
            command=self._update_mode
        ).pack(side="left", padx=20)
    
    def _create_pdk_browser(self):
        """PDK file browser and configuration"""
        
        pdk_frame = ttk.LabelFrame(self, text="PDK Configuration")
        pdk_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # PDK selection
        selection_frame = ttk.Frame(pdk_frame)
        selection_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Label(selection_frame, text="PDK Path:").pack(side="left", padx=5)
        
        self.pdk_path_var = tk.StringVar()
        pdk_entry = ttk.Entry(selection_frame, textvariable=self.pdk_path_var, width=50)
        pdk_entry.pack(side="left", padx=5, fill="x", expand=True)
        
        ttk.Button(selection_frame, text="Browse", command=self._browse_pdk).pack(side="left", padx=5)
        
        # PDK information display
        info_frame = ttk.Frame(pdk_frame)
        info_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.pdk_info_text = tk.Text(info_frame, height=10, width=60)
        self.pdk_info_text.pack(side="left", fill="both", expand=True)
        
        scrollbar = ttk.Scrollbar(info_frame, command=self.pdk_info_text.yview)
        scrollbar.pack(side="right", fill="y")
        self.pdk_info_text.configure(yscrollcommand=scrollbar.set)
    
    def _create_reference_config(self):
        """Reference library configuration"""
        
        ref_frame = ttk.LabelFrame(self, text="Reference Library")
        ref_frame.pack(fill="x", padx=10, pady=5)
        
        # Technology selection
        tech_frame = ttk.Frame(ref_frame)
        tech_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Label(tech_frame, text="Technology:").pack(side="left", padx=5)
        self.tech_var = tk.StringVar(value="microstrip")
        tech_combo = ttk.Combobox(
            tech_frame,
            textvariable=self.tech_var,
            values=["microstrip", "stripline", "coplanar"],
            state="readonly",
            width=15
        )
        tech_combo.pack(side="left", padx=5)
        
        # Substrate parameters
        substrate_frame = ttk.Frame(ref_frame)
        substrate_frame.pack(fill="x", padx=5, pady=5)
        
        # Dielectric settings
        self._create_substrate_controls(substrate_frame)
```

## Layer Mapping Tab

### Interactive Layer Mapping

```python
class LayerMappingTab(ttk.Frame):
    """Interactive layer mapping between JSON and ADS"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.mapping_vars = {}
        self._create_mapping_interface()
    
    def _create_mapping_interface(self):
        """Create interactive mapping interface"""
        
        mapping_frame = ttk.LabelFrame(self, text="Layer Mapping Configuration")
        mapping_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Mapping tree
        self.mapping_tree = ttk.Treeview(
            mapping_frame,
            columns=('json_layer', 'ads_layer', 'unit', 'status'),
            show='tree headings',
            height=15
        )
        
        self.mapping_tree.heading('#0', text='#')
        self.mapping_tree.heading('json_layer', text='JSON Layer')
        self.mapping_tree.heading('ads_layer', text='ADS Layer')
        self.mapping_tree.heading('unit', text='Unit')
        self.mapping_tree.heading('status', text='Status')
        
        self.mapping_tree.column('#0', width=50)
        self.mapping_tree.column('json_layer', width=150)
        self.mapping_tree.column('ads_layer', width=150)
        self.mapping_tree.column('unit', width=80)
        self.mapping_tree.column('status', width=100)
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(mapping_frame, orient="vertical", command=self.mapping_tree.yview)
        h_scrollbar = ttk.Scrollbar(mapping_frame, orient="horizontal", command=self.mapping_tree.xview)
        
        self.mapping_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        self.mapping_tree.pack(side="left", fill="both", expand=True)
        v_scrollbar.pack(side="right", fill="y")
        h_scrollbar.pack(side="bottom", fill="x")
        
        # Mapping controls
        controls_frame = ttk.Frame(mapping_frame)
        controls_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Button(controls_frame, text="Auto Map", command=self._auto_map_layers).pack(side="left", padx=5)
        ttk.Button(controls_frame, text="Load Mapping", command=self._load_mapping).pack(side="left", padx=5)
        ttk.Button(controls_frame, text="Save Mapping", command=self._save_mapping).pack(side="left", padx=5)
        ttk.Button(controls_frame, text="Reset", command=self._reset_mapping).pack(side="left", padx=5)
    
    def update_mapping_display(self, json_layers, ads_layers):
        """Update mapping display with current layers"""
        
        # Clear existing items
        for item in self.mapping_tree.get_children():
            self.mapping_tree.delete(item)
        
        # Add mapping items
        for i, json_layer in enumerate(json_layers):
            ads_layer = self.mapping_vars.get(json_layer, tk.StringVar())
            
            # Default mapping
            if not ads_layer.get():
                ads_layer.set(self._find_best_match(json_layer, ads_layers))
            
            status = "mapped" if ads_layer.get() else "unmapped"
            
            self.mapping_tree.insert('', 'end', text=str(i+1), values=(
                json_layer,
                ads_layer.get(),
                "um",
                status
            ))
    
    def _find_best_match(self, json_layer, ads_layers):
        """Find best matching ADS layer"""
        
        # Simple name matching
        for ads_layer in ads_layers:
            if json_layer.lower() in ads_layer.lower() or ads_layer.lower() in json_layer.lower():
                return ads_layer
        
        return ads_layers[0] if ads_layers else ""
```

## Results Tab Components

### S-Parameter Visualization

```python
class ResultsTab(ttk.Frame):
    """Comprehensive S-parameter results visualization"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.results_data = None
        self.plot_config = {}
        self._create_results_interface()
    
    def _create_results_interface(self):
        """Create results visualization interface"""
        
        # Results file selection
        file_frame = ttk.LabelFrame(self, text="Results File")
        file_frame.pack(fill="x", padx=10, pady=5)
        
        self.results_file_var = tk.StringVar()
        ttk.Entry(file_frame, textvariable=self.results_file_var, width=60).pack(side="left", padx=5, pady=5)
        ttk.Button(file_frame, text="Browse", command=self._browse_results).pack(side="left", padx=5)
        ttk.Button(file_frame, text="Refresh", command=self._refresh_results).pack(side="left", padx=5)
        
        # Plot configuration
        config_frame = ttk.LabelFrame(self, text="Plot Configuration")
        config_frame.pack(fill="x", padx=10, pady=5)
        
        self._create_plot_controls(config_frame)
        
        # Plot area
        plot_frame = ttk.LabelFrame(self, text="S-Parameter Results")
        plot_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self._create_plot_area(plot_frame)
    
    def _create_plot_controls(self, parent):
        """Create plot configuration controls"""
        
        controls_frame = ttk.Frame(parent)
        controls_frame.pack(fill="x", padx=5, pady=5)
        
        # Parameter selection
        param_frame = ttk.Frame(controls_frame)
        param_frame.pack(side="left", padx=5)
        
        ttk.Label(param_frame, text="Parameters:").pack(side="left", padx=2)
        self.param_vars = {}
        
        # Plot type
        type_frame = ttk.Frame(controls_frame)
        type_frame.pack(side="left", padx=20)
        
        self.plot_type_var = tk.StringVar(value="magnitude")
        ttk.Radiobutton(type_frame, text="Magnitude", variable=self.plot_type_var, value="magnitude").pack(side="left", padx=2)
        ttk.Radiobutton(type_frame, text="dB", variable=self.plot_type_var, value="db").pack(side="left", padx=2)
        ttk.Radiobutton(type_frame, text="Phase", variable=self.plot_type_var, value="phase").pack(side="left", padx=2)
        
        # Update button
        ttk.Button(controls_frame, text="Update Plot", command=self._update_plot).pack(side="right", padx=5)
    
    def _create_plot_area(self, parent):
        """Create matplotlib plot area"""
        
        try:
            import matplotlib.pyplot as plt
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            
            self.figure, self.axes = plt.subplots(2, 1, figsize=(8, 6))
            self.canvas = FigureCanvasTkAgg(self.figure, master=parent)
            self.canvas.get_tk_widget().pack(fill="both", expand=True)
            
        except ImportError:
            # Fallback to text display
            self.text_display = tk.Text(parent, height=20, width=80)
            self.text_display.pack(fill="both", expand=True)
    
    def load_touchstone_file(self, file_path):
        """Load and parse Touchstone file"""
        
        try:
            import skrf as rf
            
            self.network = rf.Network(file_path)
            self.results_data = {
                'frequency': self.network.f,
                's_parameters': self.network.s,
                'ports': self.network.nports
            }
            
            self._update_parameter_list()
            self._update_plot()
            
        except ImportError:
            self._load_text_results(file_path)
    
    def _update_parameter_list(self):
        """Update parameter selection based on loaded data"""
        
        if not self.results_data:
            return
        
        ports = self.results_data['ports']
        
        # Clear existing checkboxes
        for widget in self.param_frame.winfo_children():
            if isinstance(widget, ttk.Checkbutton):
                widget.destroy()
        
        # Create parameter checkboxes
        self.param_vars = {}
        for i in range(ports):
            for j in range(ports):
                param_name = f"S{i+1}{j+1}"
                var = tk.BooleanVar(value=(i == j))
                self.param_vars[param_name] = var
                
                chk = ttk.Checkbutton(
                    self.param_frame,
                    text=param_name,
                    variable=var,
                    command=self._update_plot
                )
                chk.pack(side="left", padx=2)
    
    def _update_plot(self):
        """Update plot with current configuration"""
        
        if not self.results_data:
            return
        
        try:
            import matplotlib.pyplot as plt
            
            # Clear plots
            self.axes[0].clear()
            self.axes[1].clear()
            
            frequency = self.results_data['frequency']
            s_parameters = self.results_data['s_parameters']
            
            # Plot selected parameters
            selected_params = [name for name, var in self.param_vars.items() if var.get()]
            
            colors = plt.cm.Set3(np.linspace(0, 1, len(selected_params)))
            
            for i, param_name in enumerate(selected_params):
                # Extract parameter indices
                row = int(param_name[1]) - 1
                col = int(param_name[2]) - 1
                
                s_param = s_parameters[:, row, col]
                
                if self.plot_type_var.get() == "magnitude":
                    data = np.abs(s_param)
                    label = f"|{param_name}|"
                elif self.plot_type_var.get() == "db":
                    data = 20 * np.log10(np.abs(s_param))
                    label = f"|{param_name}| (dB)"
                else:  # phase
                    data = np.angle(s_param, deg=True)
                    label = f"∠{param_name} (°)"
                
                # Plot on appropriate axis
                if self.plot_type_var.get() in ["magnitude", "db"]:
                    self.axes[0].plot(frequency / 1e9, data, color=colors[i], label=label)
                else:
                    self.axes[1].plot(frequency / 1e9, data, color=colors[i], label=label)
            
            # Format plots
            self.axes[0].set_xlabel('Frequency (GHz)')
            self.axes[0].set_ylabel('Magnitude (dB)')
            self.axes[0].set_title('S-Parameters')
            self.axes[0].legend()
            self.axes[0].grid(True)
            
            self.axes[1].set_xlabel('Frequency (GHz)')
            self.axes[1].set_ylabel('Phase (°)')
            self.axes[1].set_title('Phase Response')
            self.axes[1].legend()
            self.axes[1].grid(True)
            
            self.figure.tight_layout()
            self.canvas.draw()
            
        except Exception as e:
            messagebox.showerror("Plot Error", f"Failed to update plot: {e}")
```

## Status Bar and Progress Indicators

### Real-time Status Display

```python
class StatusBar(ttk.Frame):
    """Comprehensive status bar with progress indicators"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.progress_var = tk.DoubleVar()
        self.status_var = tk.StringVar(value="Ready")
        self.process_var = tk.StringVar()
        
        self._create_status_elements()
    
    def _create_status_elements(self):
        """Create status bar elements"""
        
        # Status text
        status_label = ttk.Label(self, textvariable=self.status_var, relief="sunken")
        status_label.pack(side="left", fill="x", expand=True, padx=2)
        
        # Process indicator
        process_label = ttk.Label(self, textvariable=self.process_var, relief="sunken", width=20)
        process_label.pack(side="left", padx=2)
        
        # Progress bar
        self.progress_bar = ttk.Progressbar(self, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(side="left", fill="x", expand=True, padx=2)
        
        # Memory usage
        self.memory_label = ttk.Label(self, text="Mem: 0MB", relief="sunken", width=15)
        self.memory_label.pack(side="left", padx=2)
    
    def update_status(self, message, progress=None, process=None):
        """Update status bar with new information"""
        
        self.status_var.set(message)
        
        if progress is not None:
            self.progress_var.set(progress)
        
        if process:
            self.process_var.set(process)
        
        # Update memory usage
        self._update_memory_usage()
    
    def _update_memory_usage(self):
        """Update memory usage display"""
        
        try:
            import psutil
            memory_mb = psutil.Process().memory_info().rss / 1024 / 1024
            self.memory_label.config(text=f"Mem: {memory_mb:.0f}MB")
        except ImportError:
            self.memory_label.config(text="Mem: N/A")
```

## Responsive Design Patterns

### Adaptive Layout Management

```python
class ResponsiveLayout:
    """Handle responsive layout adjustments"""
    
    def __init__(self, root):
        self.root = root
        self.min_width = 800
        self.min_height = 600
        
        self._setup_responsive_behavior()
    
    def _setup_responsive_behavior(self):
        """Setup responsive behavior"""
        
        # Configure root window
        self.root.minsize(self.min_width, self.min_height)
        
        # Bind resize events
        self.root.bind('<Configure>', self._on_resize)
        
        # Configure grid weights
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
    
    def _on_resize(self, event):
        """Handle window resize events"""
        
        # Calculate optimal font sizes
        width = event.width
        height = event.height
        
        # Adjust UI elements based on size
        self._adjust_font_sizes(width, height)
        self._adjust_control_sizes(width, height)
    
    def _adjust_font_sizes(self, width, height):
        """Adjust font sizes based on window dimensions"""
        
        base_size = min(width // 80, height // 60, 12)
        
        # Update all widget fonts
        default_font = ('TkDefaultFont', base_size)
        
        for widget in self.root.winfo_children():
            self._update_widget_fonts(widget, default_font)
    
    def _update_widget_fonts(self, widget, font):
        """Recursively update widget fonts"""
        
        try:
            widget.configure(font=font)
        except tk.TclError:
            pass  # Widget doesn't support font configuration
        
        # Update child widgets
        for child in widget.winfo_children():
            self._update_widget_fonts(child, font)
```

This comprehensive GUI component documentation provides the foundation for building professional-grade RFIC design automation interfaces with excellent user experience and robust functionality.