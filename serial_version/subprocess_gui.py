#!/usr/bin/env python3
"""
Subprocess-based GUI for JSON Layout to EM Simulation

This GUI runs in any Python environment and delegates all ADS/EMPro operations
to subprocess calls using the ADS Python interpreter.

Author: ADS Python API Guide
Date: 2025
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import json
import subprocess
import threading
import queue
import os
import sys
import traceback
from pathlib import Path
import tempfile
import webbrowser

# Try to import matplotlib for GUI, fallback gracefully
matplotlib_available = True
try:
    import matplotlib
    matplotlib.use('TkAgg')
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
except ImportError:
    matplotlib_available = False

class EnvironmentManager:
    """Manage ADS/EMPro environment detection and subprocess calls"""
    
    def __init__(self):
        self.ads_python_exe = None
        self.worker_script = Path(__file__).parent / "subprocess_worker.py"
        self.detect_environments()

    def _build_candidate_paths(self) -> List[str]:
        """Build ADS Python candidate paths from environment variables and common installs."""
        candidates = []

        env_python = os.environ.get("ADS_PYTHON", "").strip()
        if env_python:
            candidates.append(env_python)

        ads_root = os.environ.get("ADS_INSTALL_DIR", "").strip() or os.environ.get("HPEESOF_DIR", "").strip()
        if ads_root:
            base = Path(ads_root)
            candidates.extend([
                str(base / "tools" / "python" / "python.exe"),
                *[str(path) for path in base.glob("fem/*/win32_64/bin/tools/win32/python/python.exe")]
            ])

        common_roots = []
        for env_var in ("ProgramFiles", "ProgramW6432", "ProgramFiles(x86)"):
            value = os.environ.get(env_var, "").strip()
            if value:
                common_roots.append(Path(value) / "Keysight")

        common_roots.extend([
            Path(r"C:\Keysight"),
            Path(r"D:\Keysight"),
        ])

        for root in common_roots:
            if not root.exists():
                continue

            for ads_dir in root.glob("ADS*"):
                candidates.append(str(ads_dir / "tools" / "python" / "python.exe"))
                candidates.extend(
                    str(path)
                    for path in ads_dir.glob("fem/*/win32_64/bin/tools/win32/python/python.exe")
                )

        return candidates
    
    def detect_environments(self):
        """Detect available ADS Python environments"""
        for path in self._build_candidate_paths():
            if Path(path).exists():
                if self._validate_python(path):
                    self.ads_python_exe = path
                    break
    
    def _validate_python(self, python_exe: str) -> bool:
        """Validate ADS Python environment"""
        try:
            test_cmd = [
                python_exe, '-c',
                'import sys; print("ADS Python OK"); sys.exit(0)'
            ]
            
            result = subprocess.run(test_cmd, capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except:
            return False
    
    def is_available(self) -> bool:
        """Check if ADS Python environment is available"""
        return self.ads_python_exe is not None
    
    def get_python_exe(self) -> str:
        """Get ADS Python executable path"""
        if not self.is_available():
            raise RuntimeError("ADS Python environment not found")
        return self.ads_python_exe
    
    def run_subprocess_task(self, task_type: str, task_data: dict, 
                          progress_callback=None) -> dict:
        """Run task in subprocess"""
        if not self.is_available():
            return {'success': False, 'error': 'ADS Python environment not found'}
        
        # Create task package
        task_package = {
            'task_type': task_type,
            **task_data
        }
        
        # Write task to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(task_package, f)
            task_file = f.name
        
        try:
            cmd = [self.ads_python_exe, str(self.worker_script), task_file]
            
            # Run subprocess
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=tempfile.gettempdir()
            )
            
            # Monitor progress
            stdout, stderr = process.communicate()
            
            # Parse result
            if process.returncode == 0:
                # Find JSON result in output
                lines = stdout.strip().split('\n')
                json_line = None
                for line in lines:
                    if line.startswith('JSON_RESULT:'):
                        json_line = line[12:]
                        break
                
                if json_line:
                    return json.loads(json_line)
                else:
                    return {'success': False, 'error': 'No result found in subprocess output'}
            else:
                return {
                    'success': False,
                    'error': f'Subprocess failed: {stderr}',
                    'stdout': stdout,
                    'stderr': stderr
                }
                
        finally:
            Path(task_file).unlink(missing_ok=True)

class JSONParser:
    """Parse JSON layout files from RFIC layout generator"""
    
    def __init__(self, json_file: str):
        self.json_file = json_file
        self.data = None
        self.load_json()
    
    def load_json(self):
        """Load and validate JSON file"""
        try:
            with open(self.json_file, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
        except Exception as e:
            raise RuntimeError(f"Failed to load JSON: {e}")
    
    def get_info(self) -> dict:
        """Get basic info about the JSON file with border consideration"""
        if not self.data:
            return {}
        
        matrices = self.data.get('layout_matrices', {})
        ports = self.data.get('port_definitions', [])
        metadata = self.data.get('metadata', {})
        
        # Get matrix dimensions from actual data
        matrix_shape = None
        actual_shape = None
        if matrices:
            first_layer = list(matrices.values())[0]
            if isinstance(first_layer, list) and first_layer:
                rows = len(first_layer)
                cols = len(first_layer[0]) if rows > 0 else 0
                matrix_shape = [rows, cols]
                # Include border for actual layout dimensions
                actual_shape = [rows + 2, cols + 2]
        
        pixel_size_um = metadata.get('pixel_size_um', 14.0)
        
        # Calculate actual dimensions including border
        actual_width_um = None
        actual_height_um = None
        if actual_shape:
            actual_width_um = actual_shape[1] * pixel_size_um
            actual_height_um = actual_shape[0] * pixel_size_um
        
        return {
            'layers': list(matrices.keys()),
            'ports': len(ports),
            'shape': matrix_shape,
            'actual_shape': actual_shape,
            'design_id': self.data.get('design_id', 'unknown'),
            'pixel_size_um': pixel_size_um,
            'process': metadata.get('process', 'Unknown'),
            'description': metadata.get('description', 'No description'),
            'actual_width_um': actual_width_um,
            'actual_height_um': actual_height_um,
            'unit': 'um'
        }
    
    def convert_to_geometry(self) -> dict:
        """Convert matrix layout to geometry data for ADS with proper border and um units"""
        if not self.data:
            return {}
        
        matrices = self.data.get('layout_matrices', {})
        ports = self.data.get('port_definitions', [])
        metadata = self.data.get('metadata', {})
        
        # Use um as base unit to avoid complex unit conversion
        pixel_size_um = metadata.get('pixel_size_um', 14.0)
        
        geometry_data = {
            'layers': {},
            'ports': [],
            'metadata': {
                'pixel_size_um': pixel_size_um,
                'design_id': self.data.get('design_id', 'unknown'),
                'unit': 'um'  # Explicitly set unit to um
            }
        }
        
        # Convert matrices to polygons with border consideration
        for layer_name, matrix in matrices.items():
            if not isinstance(matrix, list) or not matrix:
                continue
                
            polygons = []
            rows = len(matrix)
            cols = len(matrix[0]) if rows > 0 else 0
            
            # Add border for port placement - actual matrix starts at (1,1)
            border_offset = 1
            
            for row in range(rows):
                for col in range(cols):
                    if matrix[row][col] == 1:
                        # Create rectangle for each pixel with border offset
                        # Coordinates are in um
                        x1 = (col + border_offset) * pixel_size_um
                        y1 = (rows - row - 1 + border_offset) * pixel_size_um  # Flip Y for ADS coordinates
                        x2 = (col + border_offset + 1) * pixel_size_um
                        y2 = (rows - row + border_offset) * pixel_size_um
                        
                        polygons.append({
                            'type': 'rectangle',
                            'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2,
                            'unit': 'um'
                        })
            
            geometry_data['layers'][layer_name] = polygons
        
        # Convert port definitions with square pixel placement
        for port in ports:
            layer = port.get('layer', 'L1')
            edge = port.get('edge', 'left')
            pos_idx = port.get('position_index', 0)
            
            # Calculate port position based on edge and index
            if layer in matrices:
                matrix = matrices[layer]
                rows = len(matrix)
                cols = len(matrix[0]) if rows > 0 else 0
                
                # Port positions are in the border area (0 or N+1 positions)
                # Each port is a square pixel centered at the border position
                port_pixel_size = pixel_size_um  # Same size as regular pixels
                
                if edge == 'left':
                    # Left border, port pixel at x=0
                    x = 0
                    y = (rows - pos_idx - 1 + 1) * pixel_size_um  # +1 for border offset
                    # Port pixel spans from x=0 to x=pixel_size_um
                    port_x1 = 0
                    port_y1 = y
                    port_x2 = pixel_size_um
                    port_y2 = y + pixel_size_um
                elif edge == 'right':
                    # Right border, port pixel at x=cols+1
                    x = (cols + 1) * pixel_size_um
                    y = (rows - pos_idx - 1 + 1) * pixel_size_um
                    port_x1 = x
                    port_y1 = y
                    port_x2 = x + pixel_size_um
                    port_y2 = y + pixel_size_um
                elif edge == 'bottom':
                    # Bottom border, port pixel at y=0
                    x = (pos_idx + 1) * pixel_size_um  # +1 for border offset
                    y = 0
                    port_x1 = x
                    port_y1 = 0
                    port_x2 = x + pixel_size_um
                    port_y2 = pixel_size_um
                elif edge == 'top':
                    # Top border, port pixel at y=rows+1
                    x = (pos_idx + 1) * pixel_size_um
                    y = (rows + 1) * pixel_size_um
                    port_x1 = x
                    port_y1 = y
                    port_x2 = x + pixel_size_um
                    port_y2 = y + pixel_size_um
                else:
                    continue
                
                # Port pixels use the same layer as their associated layer
                # Use the original layer name so it gets mapped through layer_mapping
                if layer not in geometry_data['layers']:
                    geometry_data['layers'][layer] = []
                
                geometry_data['layers'][layer].append({
                    'type': 'rectangle',
                    'x1': port_x1, 'y1': port_y1, 
                    'x2': port_x2, 'y2': port_y2,
                    'unit': 'um',
                    'is_port': True,
                    'port_id': port.get('port_id', 1)
                })
                
                # Port center position for ADS port creation
                port_center_x = (port_x1 + port_x2) / 2
                port_center_y = (port_y1 + port_y2) / 2
                
                geometry_data['ports'].append({
                    'name': port.get('name', f"P{port.get('port_id', 1)}"),
                    'layer': layer,
                    'x': port_center_x,
                    'y': port_center_y,
                    'edge': edge,
                    'port_pixel_bounds': {
                        'x1': port_x1, 'y1': port_y1, 
                        'x2': port_x2, 'y2': port_y2
                    }
                })
        
        return geometry_data

class ProgressDialog(tk.Toplevel):
    """Progress dialog for subprocess operations"""
    
    def __init__(self, parent, title="Operation Progress"):
        super().__init__(parent)
        self.title(title)
        self.geometry("600x400")
        self.resizable(False, False)
        
        self.setup_ui()
        self.transient(parent)
        self.grab_set()
        
    def setup_ui(self):
        """Setup progress UI"""
        main = ttk.Frame(self, padding="20")
        main.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main, text="Operation in progress...", 
                 font=('Arial', 12, 'bold')).pack(pady=(0, 10))
        
        # Progress bar
        self.progress = ttk.Progressbar(main, mode='indeterminate', length=400)
        self.progress.pack(pady=10)
        self.progress.start()
        
        # Log area
        log_frame = ttk.LabelFrame(main, text="Log Output")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, width=70,
                                                font=('Consolas', 9))
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Cancel button
        ttk.Button(main, text="Cancel", command=self.destroy).pack(pady=10)
    
    def log_message(self, message: str):
        """Add message to log"""
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.update()

class SubprocessEMGUI:
    """Main GUI application using subprocess architecture"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("JSON Layout to EM Simulation - PDK Edition")
        self.root.geometry("1200x800")
        
        self.env_manager = EnvironmentManager()
        self.json_file = tk.StringVar()
        self.workspace_dir = tk.StringVar()
        self.library_name = tk.StringVar(value="EM_Design_Lib")
        self.cell_name = tk.StringVar()
        
        # PDK configuration
        self.use_pdk = tk.BooleanVar(value=False)
        self.pdk_loc = tk.StringVar()
        self.pdk_tech_loc = tk.StringVar()
        self.ref_lib_loc = tk.StringVar()
        self.substrate_name = tk.StringVar()
        
        # Layer mapping
        self.layer_mapping = {}
        self.layer_mapping_file = tk.StringVar()
        
        self.setup_ui()
        self.check_environment()
    
    def setup_ui(self):
        """Setup main UI"""
        # Environment status
        env_frame = ttk.Frame(self.root)
        env_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.env_label = ttk.Label(env_frame, text="Checking environment...")
        self.env_label.pack(side=tk.LEFT)
        
        # Main notebook
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Create tabs
        self.create_input_tab(notebook)
        self.create_config_tab(notebook)
        self.create_pdk_tab(notebook)
        self.create_layer_tab(notebook)
        self.create_results_tab(notebook)
    
    def create_input_tab(self, notebook):
        """Create input file selection tab"""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="📁 Input")
        
        # File selection
        file_frame = ttk.LabelFrame(frame, text="JSON Layout File", padding=10)
        file_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Entry(file_frame, textvariable=self.json_file, width=60).pack(
            side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(file_frame, text="Browse", command=self.browse_json).pack(
            side=tk.LEFT, padx=5)
        ttk.Button(file_frame, text="Load", command=self.load_json).pack(
            side=tk.LEFT, padx=5)
        
        # JSON preview
        preview_frame = ttk.LabelFrame(frame, text="JSON Preview", padding=10)
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.json_text = scrolledtext.ScrolledText(preview_frame, height=20, width=80,
                                                  font=('Consolas', 9))
        self.json_text.pack(fill=tk.BOTH, expand=True)
        
        # Info display
        info_frame = ttk.LabelFrame(frame, text="Information", padding=10)
        info_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.info_label = ttk.Label(info_frame, text="No JSON file loaded")
        self.info_label.pack()
    
    def create_config_tab(self, notebook):
        """Create configuration tab"""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="⚙️ Configuration")
        
        # Workspace settings
        ws_frame = ttk.LabelFrame(frame, text="Workspace Settings", padding=10)
        ws_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(ws_frame, text="Workspace:").grid(row=0, column=0, sticky="w")
        ttk.Entry(ws_frame, textvariable=self.workspace_dir, width=50).grid(
            row=0, column=1, sticky="ew", padx=5)
        ttk.Button(ws_frame, text="Browse", command=self.browse_workspace).grid(
            row=0, column=2, padx=5)
        
        ttk.Label(ws_frame, text="Library:").grid(row=1, column=0, sticky="w")
        ttk.Entry(ws_frame, textvariable=self.library_name, width=30).grid(
            row=1, column=1, sticky="w", padx=5, pady=2)
        
        ttk.Label(ws_frame, text="Cell:").grid(row=2, column=0, sticky="w")
        ttk.Entry(ws_frame, textvariable=self.cell_name, width=30).grid(
            row=2, column=1, sticky="w", padx=5, pady=2)
        
        ws_frame.columnconfigure(1, weight=1)
        
        # Run buttons
        run_frame = ttk.Frame(frame)
        run_frame.pack(fill=tk.X, padx=5, pady=20)
        
        ttk.Button(run_frame, text="🚀 Run Complete Workflow", 
                  command=self.run_complete_workflow,
                  style="Accent.TButton").pack(pady=5)
        
        ttk.Button(run_frame, text="📊 Create ADS Design Only", 
                  command=self.create_design_only).pack(pady=5)
        
        ttk.Button(run_frame, text="⚡ Run EM Simulation Only", 
                  command=self.run_simulation_only).pack(pady=5)
    
    def create_pdk_tab(self, notebook):
        """Create PDK configuration tab"""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="🔧 PDK Config")
        
        # PDK mode selection
        mode_frame = ttk.LabelFrame(frame, text="Technology Mode", padding=10)
        mode_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Radiobutton(mode_frame, text="Use PDK", variable=self.use_pdk, 
                       value=True, command=self.toggle_pdk_mode).pack(anchor=tk.W)
        ttk.Radiobutton(mode_frame, text="Use Reference Library", variable=self.use_pdk, 
                       value=False, command=self.toggle_pdk_mode).pack(anchor=tk.W)
        
        # PDK configuration
        pdk_frame = ttk.LabelFrame(frame, text="PDK Configuration", padding=10)
        pdk_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # PDK Location
        ttk.Label(pdk_frame, text="PDK Library Location:").grid(row=0, column=0, sticky="w")
        ttk.Entry(pdk_frame, textvariable=self.pdk_loc, width=50).grid(
            row=0, column=1, sticky="ew", padx=5)
        ttk.Button(pdk_frame, text="Browse", command=self.browse_pdk_loc).grid(
            row=0, column=2, padx=5)
        
        # PDK Tech Location
        ttk.Label(pdk_frame, text="PDK Tech Location:").grid(row=1, column=0, sticky="w")
        ttk.Entry(pdk_frame, textvariable=self.pdk_tech_loc, width=50).grid(
            row=1, column=1, sticky="ew", padx=5)
        ttk.Button(pdk_frame, text="Browse", command=self.browse_pdk_tech_loc).grid(
            row=1, column=2, padx=5)
        
        # Reference Library Location
        ref_frame = ttk.LabelFrame(frame, text="Reference Library Configuration", padding=10)
        ref_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(ref_frame, text="Reference Library Location:").grid(row=0, column=0, sticky="w")
        ttk.Entry(ref_frame, textvariable=self.ref_lib_loc, width=50).grid(
            row=0, column=1, sticky="ew", padx=5)
        ttk.Button(ref_frame, text="Browse", command=self.browse_ref_lib_loc).grid(
            row=0, column=2, padx=5)
        
        # Substrate selection
        substrate_frame = ttk.LabelFrame(frame, text="Substrate Selection", padding=10)
        substrate_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(substrate_frame, text="Substrate:").grid(row=0, column=0, sticky="w")
        self.substrate_combo = ttk.Combobox(substrate_frame, textvariable=self.substrate_name, 
                                          width=47, state="readonly")
        self.substrate_combo.grid(row=0, column=1, sticky="ew", padx=5)
        ttk.Button(substrate_frame, text="Refresh", command=self.refresh_substrates).grid(
            row=0, column=2, padx=5)
        
        # Auto-detect paths
        auto_frame = ttk.Frame(frame)
        auto_frame.pack(fill=tk.X, padx=5, pady=10)
        
        ttk.Button(auto_frame, text="Auto-detect ADS PDKs", 
                  command=self.auto_detect_pdks).pack(pady=5)
        
        # Configure grid columns
        pdk_frame.columnconfigure(1, weight=1)
        ref_frame.columnconfigure(1, weight=1)
        substrate_frame.columnconfigure(1, weight=1)
        
        # Initial state
        self.toggle_pdk_mode()
    
    def create_layer_tab(self, notebook):
        """Create layer mapping tab"""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="🗂️ Layer Mapping")
        
        # Layer mapping file
        file_frame = ttk.LabelFrame(frame, text="Layer Mapping Configuration", padding=10)
        file_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(file_frame, text="Mapping File:").grid(row=0, column=0, sticky="w")
        ttk.Entry(file_frame, textvariable=self.layer_mapping_file, width=50).grid(
            row=0, column=1, sticky="ew", padx=5)
        ttk.Button(file_frame, text="Browse", command=self.browse_layer_mapping).grid(
            row=0, column=2, padx=5)
        ttk.Button(file_frame, text="Load", command=self.load_layer_mapping).grid(
            row=0, column=3, padx=5)
        
        # Manual layer mapping
        manual_frame = ttk.LabelFrame(frame, text="Manual Layer Mapping", padding=10)
        manual_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create treeview for layer mapping
        self.layer_tree = ttk.Treeview(manual_frame, columns=('json_layer', 'ads_layer', 'purpose'), 
                                     show='headings', height=10)
        self.layer_tree.heading('json_layer', text='JSON Layer')
        self.layer_tree.heading('ads_layer', text='ADS Layer')
        self.layer_tree.heading('purpose', text='Purpose')
        self.layer_tree.column('json_layer', width=150)
        self.layer_tree.column('ads_layer', width=150)
        self.layer_tree.column('purpose', width=150)
        
        scrollbar = ttk.Scrollbar(manual_frame, orient="vertical", command=self.layer_tree.yview)
        self.layer_tree.configure(yscrollcommand=scrollbar.set)
        
        self.layer_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, padx=5)
        
        # Add default mappings - ports use same layer mapping as geometry
        # self.layer_tree.insert('', 'end', values=('L1', 'cond', 'drawing'))
        # self.layer_tree.insert('', 'end', values=('L2', 'via', 'drawing'))
        # self.layer_tree.insert('', 'end', values=('GND', 'ground', 'drawing'))
        
        # Buttons
        button_frame = ttk.Frame(manual_frame)
        button_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(button_frame, text="Add Mapping", command=self.add_layer_mapping).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Edit Mapping", command=self.edit_layer_mapping).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Remove Mapping", command=self.remove_layer_mapping).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Save Mapping", command=self.save_layer_mapping).pack(side=tk.LEFT, padx=5)
        
        file_frame.columnconfigure(1, weight=1)
        manual_frame.columnconfigure(0, weight=1)
        manual_frame.rowconfigure(0, weight=1)
    
    def create_results_tab(self, notebook):
        """Create results tab with optimized layout"""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="📊 Results")
        
        # === TOP CONFIGURATION BAR ===
        config_frame = ttk.LabelFrame(frame, text="Export Configuration", padding=10)
        config_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Path mode selection
        ttk.Label(config_frame, text="Path Mode:").grid(row=0, column=0, sticky="w", padx=5)
        self.path_mode = tk.StringVar(value="absolute")
        path_mode_frame = ttk.Frame(config_frame)
        path_mode_frame.grid(row=0, column=1, sticky="w", padx=5)
        ttk.Radiobutton(path_mode_frame, text="Absolute Path", variable=self.path_mode, 
                       value="absolute").pack(side=tk.LEFT)
        ttk.Radiobutton(path_mode_frame, text="Relative to Library", variable=self.path_mode, 
                       value="relative").pack(side=tk.LEFT)
        
        # Export path configuration
        ttk.Label(config_frame, text="Export Path:").grid(row=0, column=2, sticky="w", padx=5)
        self.export_path = tk.StringVar()
        ttk.Entry(config_frame, textvariable=self.export_path, width=40).grid(
            row=0, column=3, sticky="ew", padx=5)
        ttk.Button(config_frame, text="Browse", command=self.browse_export_path).grid(
            row=0, column=4, padx=5)
        
        # Export type selection
        ttk.Label(config_frame, text="Export Types:").grid(row=0, column=5, sticky="w", padx=5)
        export_type_frame = ttk.Frame(config_frame)
        export_type_frame.grid(row=0, column=6, sticky="w", padx=5)
        
        self.export_touchstone = tk.BooleanVar(value=True)
        self.export_dataset = tk.BooleanVar(value=False)
        self.export_csv = tk.BooleanVar(value=False)
        
        ttk.Checkbutton(export_type_frame, text="Touchstone (.sNp)", 
                       variable=self.export_touchstone).pack(side=tk.LEFT, padx=2)
        ttk.Checkbutton(export_type_frame, text="Dataset (.ds)", 
                       variable=self.export_dataset).pack(side=tk.LEFT, padx=2)
        ttk.Checkbutton(export_type_frame, text="CSV", 
                       variable=self.export_csv).pack(side=tk.LEFT, padx=2)
        
        config_frame.columnconfigure(3, weight=1)
        
        # === MAIN CONTENT AREA ===
        main_container = ttk.Frame(frame)
        main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left sidebar for metadata and controls (narrower)
        sidebar = ttk.Frame(main_container, width=200)
        sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        sidebar.pack_propagate(False)
        
        # Right side for plots
        plot_container = ttk.Frame(main_container)
        plot_container.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # === SIDEBAR CONTENT ===
        
        # Metadata display
        meta_frame = ttk.LabelFrame(sidebar, text="Simulation Info", padding=8)
        meta_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.meta_labels = {}
        meta_items = [
            ("Frequency:", "freq_range"),
            ("Points:", "freq_points"),
            ("Ports:", "num_ports"),
            ("Format:", "file_format"),
            ("Updated:", "last_updated")
        ]
        
        for i, (label, key) in enumerate(meta_items):
            ttk.Label(meta_frame, text=label, font=('Arial', 9, 'bold')).grid(
                row=i, column=0, sticky="w", pady=1)
            self.meta_labels[key] = ttk.Label(meta_frame, text="N/A", 
                                            foreground="blue", font=('Arial', 8))
            self.meta_labels[key].grid(row=i, column=1, sticky="w", padx=(5, 0), pady=1)
        
        # Port names (separate section for better layout)
        port_frame = ttk.LabelFrame(sidebar, text="Port Names", padding=8)
        port_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.port_names_label = ttk.Label(port_frame, text="N/A", 
                                         foreground="blue", font=('Arial', 8),
                                         wraplength=180)
        self.port_names_label.pack()
        
        # Control buttons
        button_frame = ttk.Frame(sidebar)
        button_frame.pack(fill=tk.X, padx=5, pady=10)
        
        ttk.Button(button_frame, text="🔄 Refresh", 
                  command=self.refresh_results).pack(fill=tk.X, pady=2)
        ttk.Button(button_frame, text="🗑️ Clear", 
                  command=self.clear_results).pack(fill=tk.X, pady=2)
        
        # === PLOT AREA ===
        if matplotlib_available:
            # Create matplotlib figure
            plot_frame = ttk.LabelFrame(plot_container, text="S-Parameter Results")
            plot_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            self.fig = Figure(figsize=(12, 8), dpi=100)
            self.canvas = FigureCanvasTkAgg(self.fig, master=plot_frame)
            self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            # Initialize empty plot
            self.clear_plot()
        else:
            # Fallback text display
            text_frame = ttk.LabelFrame(plot_container, text="Results (matplotlib not available)")
            text_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            self.results_text = scrolledtext.ScrolledText(text_frame, height=20, width=80)
            self.results_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    def check_environment(self):
        """Check ADS environment availability"""
        if self.env_manager.is_available():
            self.env_label.config(
                text=f"✅ ADS Python found: {Path(self.env_manager.get_python_exe()).parent.parent.parent}",
                foreground="green"
            )
            
            # Set default PDK paths only if they exist
            ads_base = Path(self.env_manager.get_python_exe()).parent.parent.parent
            demo_pdk = ads_base / "examples" / "DesignKit" / "DemoKit_Non_Linear" / "DemoKit_Non_Linear_v2.0" / "DemoKit_Non_Linear"
            demo_tech = ads_base / "examples" / "DesignKit" / "DemoKit_Non_Linear" / "DemoKit_Non_Linear_v2.0" / "DemoKit_Non_Linear_tech"
            
            if demo_pdk.exists():
                self.pdk_loc.set(str(demo_pdk))
            if demo_tech.exists():
                self.pdk_tech_loc.set(str(demo_tech))
                # Only refresh substrates if in PDK mode and path exists
                if self.use_pdk.get():
                    self.refresh_substrates()
            
        else:
            self.env_label.config(
                text="❌ ADS Python environment not found. Please install Keysight ADS 2025.",
                foreground="red"
            )
    
    def browse_json(self):
        """Browse for JSON file"""
        filename = filedialog.askopenfilename(
            title="Select JSON Layout File",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            self.json_file.set(filename)
    
    def browse_workspace(self):
        """Browse for workspace directory"""
        directory = filedialog.askdirectory(title="Select Workspace Directory")
        if directory:
            self.workspace_dir.set(directory)
    
    def browse_pdk_loc(self):
        """Browse for PDK library location"""
        directory = filedialog.askdirectory(title="Select PDK Library Directory")
        if directory:
            self.pdk_loc.set(directory)
            self.refresh_substrates()
    
    def browse_pdk_tech_loc(self):
        """Browse for PDK tech location"""
        directory = filedialog.askdirectory(title="Select PDK Tech Directory")
        if directory:
            self.pdk_tech_loc.set(directory)
    
    def browse_ref_lib_loc(self):
        """Browse for reference library location"""
        directory = filedialog.askdirectory(title="Select Reference Library Directory")
        if directory:
            self.ref_lib_loc.set(directory)
            self.refresh_substrates()
    
    def browse_layer_mapping(self):
        """Browse for layer mapping file"""
        filename = filedialog.askopenfilename(
            title="Select Layer Mapping File",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            self.layer_mapping_file.set(filename)
    
    def browse_export_path(self):
        """Browse for export directory"""
        directory = filedialog.askdirectory(title="Select Export Directory")
        if directory:
            self.export_path.set(directory)
    
        
    def clear_results(self):
        """Clear results display"""
        if matplotlib_available:
            self.fig.clear()
            self.canvas.draw()
        else:
            self.results_text.delete(1.0, tk.END)
    
    def parse_touchstone_file(self, filename):
        """Parse Touchstone file and extract S-parameters for display"""
        try:
            import math
            import cmath
            import re
            
            frequencies = []
            s_params = {}
            num_ports = 0
            data_format = "MA"  # Default to Magnitude-Angle format
            
            with open(filename, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Parse header line to get format and number of ports
            for line in lines:
                line = line.strip()
                if line.startswith('#'):
                    # Parse format line like: "# Hz S RI R 50"
                    header_parts = line.split()
                    if len(header_parts) >= 4 and header_parts[2] == 'S':
                        data_format = header_parts[3]  # RI, MA, DB
                        impedance = header_parts[4] if len(header_parts) > 4 else '50'
                break
            
            # Extract number of ports from filename
            if '.s' in filename and 'p' in filename:
                match = re.search(r'\.s(\d+)p', filename.lower())
                if match:
                    num_ports = int(match.group(1))
            
            if num_ports == 0:
                print(f"Warning: Could not determine number of ports from filename: {filename}")
                return None
            
            print(f"Parsing {num_ports}-port Touchstone file with {data_format} format")
            
            # Collect all data lines (skip comments and empty lines)
            data_lines = []
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#') and not line.startswith('!'):
                    # Split into parts and filter out empty strings
                    parts = [p for p in line.split() if p]
                    data_lines.extend(parts)
            
            # Parse frequency and S-parameter data
            total_params = num_ports * num_ports
            data_index = 0
            
            while data_index < len(data_lines):
                if data_index + total_params * 2 + 1 > len(data_lines):
                    break  # Not enough data for complete frequency point
                
                # First value is frequency
                try:
                    freq = float(data_lines[data_index])
                    frequencies.append(freq)
                    data_index += 1
                except (ValueError, IndexError):
                    break
                
                # Parse S-parameters for all ports
                for i in range(num_ports):
                    for j in range(num_ports):
                        param_name = f"S{i+1}{j+1}"
                        
                        if data_index + 1 >= len(data_lines):
                            break
                        
                        try:
                            if data_format == "RI":
                                # Real-Imaginary format
                                real = float(data_lines[data_index])
                                imag = float(data_lines[data_index + 1])
                                complex_val = complex(real, imag)
                                magnitude = abs(complex_val)
                                phase = cmath.phase(complex_val)
                                data_index += 2
                            elif data_format == "MA":
                                # Magnitude-Angle format (angle in degrees)
                                magnitude = float(data_lines[data_index])
                                phase_deg = float(data_lines[data_index + 1])
                                phase = math.radians(phase_deg)
                                complex_val = cmath.rect(magnitude, phase)
                                data_index += 2
                            else:
                                print(f"Unsupported data format: {data_format}")
                                break
                            
                            # Initialize parameter storage if needed
                            if param_name not in s_params:
                                s_params[param_name] = {
                                    'magnitude': [], 
                                    'magnitude_db': [], 
                                    'phase_deg': [], 
                                    'complex': []
                                }
                            
                            # Store all representations
                            s_params[param_name]['magnitude'].append(magnitude)
                            s_params[param_name]['magnitude_db'].append(20 * math.log10(max(magnitude, 1e-12)))
                            s_params[param_name]['phase_deg'].append(math.degrees(phase))
                            s_params[param_name]['complex'].append(complex_val)
                            
                        except (ValueError, IndexError) as e:
                            print(f"Error parsing {param_name} at frequency {freq}: {e}")
                            break
            
            # Convert frequencies to GHz
            freq_ghz = [f/1e9 for f in frequencies]
            
            # Calculate VSWR for diagonal parameters (S11, S22, etc.)
            vswr_data = {}
            for i in range(num_ports):
                param_name = f"S{i+1}{i+1}"
                if param_name in s_params:
                    sii_mag = s_params[param_name]['magnitude']
                    vswr_values = []
                    for mag in sii_mag:
                        if mag < 1.0:  # Avoid division by zero or negative VSWR
                            vswr_values.append((1 + mag) / (1 - mag))
                        else:
                            vswr_values.append(float('inf'))
                    vswr_data[f"Port{i+1}_VSWR"] = vswr_values
            
            result = {
                'frequencies': frequencies,
                'frequencies_ghz': freq_ghz,
                's_parameters': s_params,
                'vswr': vswr_data,
                'num_ports': num_ports,
                'port_names': [f"P{i+1}" for i in range(num_ports)],
                'data_format': data_format
            }
            
            print(f"Successfully parsed {len(frequencies)} frequency points for {num_ports}-port network")
            return result
            
        except Exception as e:
            print(f"Error parsing touchstone file: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def parse_and_display_results(self, touchstone_file):
        """Parse Touchstone file and display results"""
        try:
            # Store current file for refresh functionality
            self.current_touchstone_file = touchstone_file
            
            # Parse the touchstone file
            results = self.parse_touchstone_file(touchstone_file)
            
            if results:
                self.display_results(results)
                print(f"✅ Successfully displayed results from {touchstone_file}")
            else:
                error_msg = f"Failed to parse Touchstone file: {touchstone_file}"
                print(f"❌ {error_msg}")
                if hasattr(self, 'results_text'):
                    self.results_text.delete(1.0, tk.END)
                    self.results_text.insert(1.0, f"Error: {error_msg}\n\nThe Touchstone file may be corrupted or in an unsupported format.")
                else:
                    messagebox.showerror("Parse Error", f"Failed to parse Touchstone file: {touchstone_file}")
                
        except Exception as e:
            error_msg = f"Error parsing/displaying results: {str(e)}"
            print(f"❌ {error_msg}")
            if hasattr(self, 'results_text'):
                self.results_text.delete(1.0, tk.END)
                self.results_text.insert(1.0, f"Error: {error_msg}")
            else:
                messagebox.showerror("Display Error", f"Error parsing/displaying results: {str(e)}")
    
    def toggle_pdk_mode(self):
        """Toggle between PDK and reference library modes"""
        if self.use_pdk.get():
            # Enable PDK fields, disable reference library
            self.enable_pdk_fields()
            # Auto-refresh substrates if PDK path exists
            if self.pdk_tech_loc.get() and Path(self.pdk_tech_loc.get()).exists():
                self.refresh_substrates()
        else:
            # Enable reference library, disable PDK fields
            self.enable_ref_fields()
            # Auto-refresh substrates if reference library path exists
            if self.ref_lib_loc.get() and Path(self.ref_lib_loc.get()).exists():
                self.refresh_substrates()
    
    def enable_pdk_fields(self):
        """Enable PDK fields and disable reference library"""
        # This would be implemented in the actual GUI
        pass
    
    def enable_ref_fields(self):
        """Enable reference library fields and disable PDK"""
        # This would be implemented in the actual GUI
        pass
    
    def refresh_substrates(self):
        """Refresh substrate list from library"""
        library_path = None
        
        if self.use_pdk.get():
            library_path = self.pdk_tech_loc.get()
        else:
            library_path = self.ref_lib_loc.get()
        
        if not library_path or not Path(library_path).exists():
            messagebox.showwarning("Warning", "Library path not found. Cannot refresh substrates.")
            return
        
        try:
            # Find .subst files
            substrate_files = []
            for subst_file in Path(library_path).rglob("*.subst"):
                substrate_files.append(subst_file.stem)
            
            if substrate_files:
                self.substrate_combo['values'] = substrate_files
                self.substrate_name.set(substrate_files[0])
                messagebox.showinfo("Success", f"Found {len(substrate_files)} substrates")
            else:
                messagebox.showwarning("Warning", "No .subst files found in library")
                self.substrate_combo['values'] = []
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to refresh substrates: {e}")
    
    def auto_detect_pdks(self):
        """Auto-detect ADS PDKs"""
        ads_paths = []

        ads_root = os.environ.get("ADS_INSTALL_DIR", "").strip() or os.environ.get("HPEESOF_DIR", "").strip()
        if ads_root:
            ads_paths.append(str(Path(ads_root) / "examples" / "DesignKit"))

        common_roots = []
        for env_var in ("ProgramFiles", "ProgramW6432", "ProgramFiles(x86)"):
            value = os.environ.get(env_var, "").strip()
            if value:
                common_roots.append(Path(value) / "Keysight")

        common_roots.extend([
            Path(r"C:\Keysight"),
            Path(r"D:\Keysight"),
        ])

        for root in common_roots:
            if not root.exists():
                continue
            for ads_dir in root.glob("ADS*"):
                ads_paths.append(str(ads_dir / "examples" / "DesignKit"))
        
        detected_pdks = []
        
        for ads_path in ads_paths:
            if Path(ads_path).exists():
                # Look for common PDK patterns
                for pdk_dir in Path(ads_path).rglob("*Non_Linear*"):
                    if pdk_dir.is_dir():
                        tech_dir = pdk_dir.parent / f"{pdk_dir.name}_tech"
                        if tech_dir.exists():
                            detected_pdks.append({
                                'pdk': str(pdk_dir),
                                'tech': str(tech_dir),
                                'name': pdk_dir.name
                            })
        
        if detected_pdks:
            # Show selection dialog
            selection = self.select_pdk_dialog(detected_pdks)
            if selection:
                self.pdk_loc.set(selection['pdk'])
                self.pdk_tech_loc.set(selection['tech'])
                self.refresh_substrates()
        else:
            messagebox.showinfo("No PDKs Found", "No ADS PDKs found in standard locations")
    
    def select_pdk_dialog(self, pdks):
        """Show PDK selection dialog"""
        # This would be implemented as a proper dialog
        # For now, return the first PDK
        return pdks[0] if pdks else None
    
    def load_layer_mapping(self):
        """Load layer mapping from JSON file"""
        if not self.layer_mapping_file.get():
            messagebox.showwarning("Warning", "Please select a layer mapping file")
            return
        
        try:
            with open(self.layer_mapping_file.get(), 'r') as f:
                self.layer_mapping = json.load(f)
            
            # Update treeview
            for item in self.layer_tree.get_children():
                self.layer_tree.delete(item)
            
            for json_layer, mapping in self.layer_mapping.items():
                self.layer_tree.insert('', 'end', 
                                     values=(json_layer, mapping['layer_name'], mapping['layer_purpose']))
            
            messagebox.showinfo("Success", "Layer mapping loaded successfully")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load layer mapping: {e}")
    
    def add_layer_mapping(self):
        """Add new layer mapping"""
        # Simple dialog for adding mapping
        dialog = tk.Toplevel(self.root)
        dialog.title("Add Layer Mapping")
        dialog.geometry("300x200")
        
        ttk.Label(dialog, text="JSON Layer:").pack(pady=5)
        json_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=json_var).pack(pady=5)
        
        ttk.Label(dialog, text="ADS Layer:").pack(pady=5)
        ads_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=ads_var).pack(pady=5)
        
        ttk.Label(dialog, text="Purpose:").pack(pady=5)
        purpose_var = tk.StringVar()
        purpose_var.set("drawing")
        ttk.Entry(dialog, textvariable=purpose_var).pack(pady=5)
        
        def save_mapping():
            json_layer = json_var.get().strip()
            ads_layer = ads_var.get().strip()
            purpose = purpose_var.get().strip()
            
            if json_layer and ads_layer and purpose:
                self.layer_mapping[json_layer] = {
                    'layer_name': ads_layer,
                    'layer_purpose': purpose
                }
                self.layer_tree.insert('', 'end', values=(json_layer, ads_layer, purpose))
                dialog.destroy()
        
        ttk.Button(dialog, text="Save", command=save_mapping).pack(pady=10)
        dialog.transient(self.root)
        dialog.grab_set()
    
    def edit_layer_mapping(self):
        """Edit selected layer mapping"""
        selected = self.layer_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a layer mapping to edit")
            return
        
        item = self.layer_tree.item(selected[0])
        values = item['values']
        
        # Similar to add_layer_mapping but with existing values
        dialog = tk.Toplevel(self.root)
        dialog.title("Edit Layer Mapping")
        dialog.geometry("300x200")
        
        ttk.Label(dialog, text="JSON Layer:").pack(pady=5)
        json_var = tk.StringVar(value=values[0])
        ttk.Entry(dialog, textvariable=json_var, state="readonly").pack(pady=5)
        
        ttk.Label(dialog, text="ADS Layer:").pack(pady=5)
        ads_var = tk.StringVar(value=values[1])
        ttk.Entry(dialog, textvariable=ads_var).pack(pady=5)
        
        ttk.Label(dialog, text="Purpose:").pack(pady=5)
        purpose_var = tk.StringVar(value=values[2])
        ttk.Entry(dialog, textvariable=purpose_var).pack(pady=5)
        
        def update_mapping():
            json_layer = json_var.get().strip()
            ads_layer = ads_var.get().strip()
            purpose = purpose_var.get().strip()
            
            if json_layer and ads_layer and purpose:
                self.layer_mapping[json_layer] = {
                    'layer_name': ads_layer,
                    'layer_purpose': purpose
                }
                self.layer_tree.item(selected[0], values=(json_layer, ads_layer, purpose))
                dialog.destroy()
        
        ttk.Button(dialog, text="Update", command=update_mapping).pack(pady=10)
        dialog.transient(self.root)
        dialog.grab_set()
    
    def remove_layer_mapping(self):
        """Remove selected layer mapping"""
        selected = self.layer_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a layer mapping to remove")
            return
        
        item = self.layer_tree.item(selected[0])
        json_layer = item['values'][0]
        
        if messagebox.askyesno("Confirm", f"Remove mapping for {json_layer}?"):
            del self.layer_mapping[json_layer]
            self.layer_tree.delete(selected[0])
    
    def save_layer_mapping(self):
        """Save layer mapping to file"""
        filename = filedialog.asksaveasfilename(
            title="Save Layer Mapping",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'w') as f:
                    json.dump(self.layer_mapping, f, indent=2)
                messagebox.showinfo("Success", "Layer mapping saved successfully")
                self.layer_mapping_file.set(filename)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save layer mapping: {e}")
    
    def load_json(self):
        """Load and display JSON file"""
        if not self.json_file.get():
            messagebox.showwarning("Warning", "Please select a JSON file first")
            return
        
        try:
            parser = JSONParser(self.json_file.get())
            info = parser.get_info()
            
            # Display JSON content
            with open(self.json_file.get(), 'r', encoding='utf-8') as f:
                content = f.read()
                self.json_text.delete(1.0, tk.END)
                self.json_text.insert(1.0, content)
            
            # Update info with border dimensions
            info_text = f"Layers: {info['layers']} | Ports: {info['ports']} | " \
                       f"Matrix: {info['shape']} | Layout: {info['actual_shape']} | " \
                       f"Size: {info['actual_width_um']}×{info['actual_height_um']} µm"
            self.info_label.config(text=info_text)
            
            # Auto-fill cell name
            if not self.cell_name.get():
                self.cell_name.set(info['design_id'])
            
            # Auto-fill workspace
            if not self.workspace_dir.get():
                default_ws = Path(self.json_file.get()).parent / f"{info['design_id']}_EM_Simulation"
                self.workspace_dir.set(str(default_ws))
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load JSON: {str(e)}")
    
    def run_task_in_background(self, task_type: str, task_data: dict, 
                              progress_dialog: 'ProgressDialog'):
        """Run task in background thread with enhanced logging"""
        try:
            progress_dialog.log_message(f"Starting {task_type}...")
            progress_dialog.log_message(f"Using ADS Python: {self.env_manager.get_python_exe()}")
            
            def progress_callback(line):
                """Real-time progress callback"""
                progress_dialog.log_message(line)
            
            result = self.env_manager.run_subprocess_task(task_type, task_data, progress_callback)
            
            if result['success']:
                progress_dialog.log_message(f"✅ {task_type} completed successfully")
                if 'log_file' in result:
                    progress_dialog.log_message(f"Log file: {result['log_file']}")
                self.root.after(0, lambda: self.handle_success(task_type, result))
            else:
                error_details = result.get('error', 'Unknown error')
                full_output = result.get('full_output', '')
                
                progress_dialog.log_message(f"❌ {task_type} failed: {error_details}")
                if full_output:
                    progress_dialog.log_message(f"Full output:\n{full_output}")
                
                if 'log_file' in result and Path(result['log_file']).exists():
                    progress_dialog.log_message(f"Log file: {result['log_file']}")
                    
                self.root.after(0, lambda: self.handle_error(task_type, result))
                
        except Exception as e:
            error_msg = f"❌ Critical Error: {str(e)}"
            progress_dialog.log_message(error_msg)
            progress_dialog.log_message(traceback.format_exc())
            self.root.after(0, lambda: messagebox.showerror("Critical Error", str(e)))
        
        finally:
            progress_dialog.progress.stop()
            progress_dialog.title("Operation Complete")
    
    def run_complete_workflow(self):
        """Run complete workflow: design creation → EM simulation → results processing"""
        if not self.validate_inputs():
            return
        
        if not self.export_path.get():
            messagebox.showwarning("Warning", "Please specify an export path for results")
            return
        
        # Parse JSON and convert to geometry
        try:
            parser = JSONParser(self.json_file.get())
            geometry_data = parser.convert_to_geometry()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to parse JSON: {e}")
            return
        
        # Prepare PDK configuration
        pdk_config = {
            'use_pdk': self.use_pdk.get(),
            'ref_lib_loc': self.ref_lib_loc.get(),
            'pdk_loc': self.pdk_loc.get(),
            'pdk_tech_loc': self.pdk_tech_loc.get(),
            'substrate_name': self.substrate_name.get(),
            'ref_library_name': Path(self.pdk_loc.get()).name if self.use_pdk.get() and self.pdk_loc.get() else Path(self.ref_lib_loc.get()).name if self.ref_lib_loc.get() else 'Reference'
        }
        
        # Build layer mapping from treeview
        layer_mapping = {}
        for item in self.layer_tree.get_children():
            values = self.layer_tree.item(item)['values']
            if len(values) >= 3:
                json_layer = values[0]
                ads_layer = values[1]
                purpose = values[2]
                layer_mapping[json_layer] = {
                    'layer_name': ads_layer,
                    'layer_purpose': purpose
                }
        
        progress = ProgressDialog(self.root, "Complete Workflow")
        
        thread = threading.Thread(
            target=self.run_complete_workflow_sequence,
            args=(geometry_data, pdk_config, layer_mapping, progress)
        )
        thread.daemon = True
        thread.start()
    
    def run_complete_workflow_sequence(self, geometry_data, pdk_config, layer_mapping, progress_dialog):
        """Run complete workflow sequence with proper error handling"""
        try:
            # Step 1: Create ADS design
            progress_dialog.log_message("Step 1: Creating ADS design...")
            
            design_task_data = {
                'json_file': self.json_file.get(),
                'workspace_dir': self.workspace_dir.get(),
                'library_name': self.library_name.get(),
                'cell_name': self.cell_name.get(),
                'geometry_data': geometry_data,
                'pdk_config': pdk_config,
                'layer_mapping': layer_mapping
            }
            
            design_result = self.env_manager.run_subprocess_task("create_ads_design", design_task_data)
            
            if not design_result['success']:
                raise RuntimeError(f"Design creation failed: {design_result.get('error', 'Unknown error')}")
            
            progress_dialog.log_message("✅ ADS design created successfully")
            
            # Step 2: Run EM simulation
            progress_dialog.log_message("Step 2: Running EM simulation...")
            
            # Build export configuration
            export_types = []
            if self.export_touchstone.get():
                export_types.append('touchstone')
            if self.export_dataset.get():
                export_types.append('dataset')
            if self.export_csv.get():
                export_types.append('csv')
            
            sim_task_data = {
                'workspace_dir': self.workspace_dir.get(),
                'library_name': self.library_name.get(),
                'cell_name': self.cell_name.get(),
                'em_view_name': 'rfpro_view',
                'export_config': {
                    'export_path': self.export_path.get(),
                    'export_types': export_types,
                    'path_mode': self.path_mode.get()
                }
            }
            
            sim_result = self.env_manager.run_subprocess_task("run_em_simulation", sim_task_data)
            
            if not sim_result['success']:
                raise RuntimeError(f"EM simulation failed: {sim_result.get('error', 'Unknown error')}")
            
            progress_dialog.log_message("✅ EM simulation completed successfully")
            
            # Check if results were exported and try to parse for display
            if sim_result.get('export_results'):
                progress_dialog.log_message("✅ Results exported successfully")
                
                # Try to parse and display touchstone file if available
                touchstone_file = sim_result['export_results'].get('touchstone')
                if touchstone_file and Path(touchstone_file).exists():
                    progress_dialog.log_message("📊 Parsing results for display...")
                    # Parse and display in main thread
                    self.root.after(0, lambda: self.parse_and_display_results(touchstone_file))
                else:
                    progress_dialog.log_message("⚠️ No Touchstone file available for display")
            else:
                progress_dialog.log_message("⚠️ No results exported")
            
            progress_dialog.log_message("🎉 Complete workflow finished successfully!")
            
            # Display workflow completion message in main thread
            self.root.after(0, lambda: self.handle_workflow_success(design_result, sim_result))
            
        except Exception as e:
            error_msg = f"❌ Workflow failed: {str(e)}"
            progress_dialog.log_message(error_msg)
            progress_dialog.log_message(traceback.format_exc())
            self.root.after(0, lambda: messagebox.showerror("Workflow Error", str(e)))
        
        finally:
            progress_dialog.progress.stop()
            progress_dialog.title("Workflow Complete")
    
    def handle_workflow_success(self, design_result, sim_result):
        """Handle successful complete workflow"""
        # Results are already displayed automatically during workflow execution
        # Just show summary message
        summary = f"Complete workflow finished successfully!\n\n"
        summary += f"✅ Design created in: {design_result.get('workspace_dir', self.workspace_dir.get())}\n"
        summary += f"✅ EM simulation completed\n"
        summary += f"✅ Results processed and exported to: {self.export_path.get()}\n\n"
        
        # Handle export results from sim_result
        export_results = None
        if sim_result and sim_result.get('export_results'):
            export_results = sim_result['export_results']
            
        if export_results:
            summary += "Exported files:\n"
            for export_type, file_path in export_results.items():
                if file_path:
                    summary += f"  • {export_type}: {file_path}\n"
        
        messagebox.showinfo("Workflow Complete", summary)
    
    def create_design_only(self):
        """Create ADS design only"""
        if not self.validate_inputs():
            return
        
        # Parse JSON and convert to geometry
        try:
            parser = JSONParser(self.json_file.get())
            geometry_data = parser.convert_to_geometry()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to parse JSON: {e}")
            return
        
        # Prepare PDK configuration
        pdk_config = {
            'use_pdk': self.use_pdk.get(),
            'ref_lib_loc': self.ref_lib_loc.get(),
            'pdk_loc': self.pdk_loc.get(),
            'pdk_tech_loc': self.pdk_tech_loc.get(),
            'substrate_name': self.substrate_name.get(),
            'ref_library_name': Path(self.pdk_loc.get()).name if self.use_pdk.get() and self.pdk_loc.get() else Path(self.ref_lib_loc.get()).name if self.ref_lib_loc.get() else 'Reference'
        }
        
        # Build layer mapping from treeview
        layer_mapping = {}
        for item in self.layer_tree.get_children():
            values = self.layer_tree.item(item)['values']
            if len(values) >= 3:
                json_layer = values[0]
                ads_layer = values[1]
                purpose = values[2]
                layer_mapping[json_layer] = {
                    'layer_name': ads_layer,
                    'layer_purpose': purpose
                }
        
        task_data = {
            'json_file': self.json_file.get(),
            'workspace_dir': self.workspace_dir.get(),
            'library_name': self.library_name.get(),
            'cell_name': self.cell_name.get(),
            'geometry_data': geometry_data,
            'pdk_config': pdk_config,
            'layer_mapping': layer_mapping
        }
        
        progress = ProgressDialog(self.root, "Create ADS Design")
        
        thread = threading.Thread(
            target=self.run_task_in_background,
            args=("create_ads_design", task_data, progress)
        )
        thread.daemon = True
        thread.start()
    
    def run_simulation_only(self):
        """Run EM simulation only"""
        if not self.validate_inputs():
            return
        
        # Build export configuration
        export_types = []
        if self.export_touchstone.get():
            export_types.append('touchstone')
        if self.export_dataset.get():
            export_types.append('dataset')
        if self.export_csv.get():
            export_types.append('csv')
        
        task_data = {
            'workspace_dir': self.workspace_dir.get(),
            'library_name': self.library_name.get(),
            'cell_name': self.cell_name.get(),
            'em_view_name': 'rfpro_view',
            'export_config': {
                'export_path': self.export_path.get(),
                'export_types': export_types,
                'path_mode': self.path_mode.get()
            }
        }
        
        progress = ProgressDialog(self.root, "Run EM Simulation")
        
        thread = threading.Thread(
            target=self.run_task_in_background,
            args=("run_em_simulation", task_data, progress)
        )
        thread.daemon = True
        thread.start()
    
    def validate_inputs(self) -> bool:
        """Validate user inputs"""
        if not self.env_manager.is_available():
            messagebox.showerror("Error", "ADS Python environment not found")
            return False
        
        if not self.json_file.get():
            messagebox.showwarning("Warning", "Please select a JSON file")
            return False
        
        if not Path(self.json_file.get()).exists():
            messagebox.showerror("Error", "JSON file does not exist")
            return False
        
        if not self.workspace_dir.get():
            messagebox.showwarning("Warning", "Please specify workspace directory")
            return False
        
        if not self.library_name.get():
            messagebox.showwarning("Warning", "Please specify library name")
            return False
        
        if not self.cell_name.get():
            messagebox.showwarning("Warning", "Please specify cell name")
            return False
        
        return True

    def handle_success(self, task_type: str, result: dict):
        """Handle successful task completion"""
        if task_type == "create_ads_design":
            messagebox.showinfo("Success", f"ADS design created in: {result.get('workspace_dir', self.workspace_dir.get())}")
        elif task_type == "run_em_simulation":
            # Check if results were exported and try to parse for display
            if result.get('export_results'):
                # Try to parse and display touchstone file if available
                touchstone_file = result['export_results'].get('touchstone')
                if touchstone_file and Path(touchstone_file).exists():
                    self.parse_and_display_results(touchstone_file)
                    
                    export_info = "\n\nExported files:\n"
                    for export_type, file_path in result['export_results'].items():
                        if file_path:
                            export_info += f"  {export_type}: {file_path}\n"
                    messagebox.showinfo("Success", f"EM simulation completed with automatic results processing{export_info}")
                else:
                    export_info = ""
                    if result.get('export_results'):
                        export_info = "\n\nExported files:\n"
                        for export_type, file_path in result['export_results'].items():
                            if file_path:
                                export_info += f"  {export_type}: {file_path}\n"
                    messagebox.showinfo("Success", f"EM simulation completed{export_info}")
            else:
                messagebox.showinfo("Success", "EM simulation completed")
        
    def display_results(self, result: dict):
        """Display S-parameter results using improved single-plot layout"""
        if result is None:
            if hasattr(self, 'results_text'):
                self.results_text.delete(1.0, tk.END)
                self.results_text.insert(1.0, "No results data available. The simulation may not have completed successfully.")
            return
            
        if not matplotlib_available:
            # Fallback to text display
            if hasattr(self, 'results_text'):
                self.results_text.delete(1.0, tk.END)
                
                # Display basic info
                info_text = f"Results Summary:\n"
                info_text += f"Number of ports: {result['num_ports']}\n"
                info_text += f"Port names: {', '.join(result['port_names'])}\n"
                info_text += f"Frequency range: {result['frequencies_ghz'][0]:.2f} - {result['frequencies_ghz'][-1]:.2f} GHz\n"
                info_text += f"Data points: {len(result['frequencies'])}\n\n"
                
                # Display export results
                if result.get('export_results'):
                    info_text += "Exported files:\n"
                    for export_type, file_path in result['export_results'].items():
                        if file_path:
                            info_text += f"  {export_type}: {file_path}\n"
                    info_text += "\n"
                
                # Display sample S-parameter data
                info_text += "Sample S-parameters (first 5 points):\n"
                for i in range(min(5, len(result['frequencies_ghz']))):
                    freq = result['frequencies_ghz'][i]
                    info_text += f"  {freq:.2f} GHz: "
                    for port_name in result['port_names']:
                        s11_key = f"S{port_name[-1]}{port_name[-1]}"  # S11, S22, etc.
                        if s11_key in result['s_parameters']:
                            s11_db = result['s_parameters'][s11_key]['magnitude_db'][i]
                            info_text += f"{s11_key}={s11_db:.2f}dB "
                    info_text += "\n"
                
                self.results_text.insert(1.0, info_text)
            return
        
        # Use improved matplotlib plotting
        self.fig.clear()
        
        # Single plot for all S-parameters
        ax = self.fig.add_subplot(111)
        
        # Color and style mapping for different parameter types
        import matplotlib.pyplot as plt
        import numpy as np
        colors = plt.cm.Set3(np.linspace(0, 1, max(12, len(result['s_parameters']))))
        
        # Plot all S-parameters with intelligent styling
        for idx, (param_name, param_data) in enumerate(result['s_parameters'].items()):
            i, j = int(param_name[1]) - 1, int(param_name[2]) - 1
            
            # Determine line style based on parameter type
            if i == j:  # Reflection parameters (diagonal)
                line_style = '-'
                line_width = 2.5
                alpha = 0.9
            elif i < j:  # Upper triangle (forward transmission)
                line_style = '--'
                line_width = 2.0
                alpha = 0.8
            else:  # Lower triangle (reverse transmission)
                line_style = ':'
                line_width = 1.5
                alpha = 0.7
            
            # Plot the parameter
            ax.plot(result['frequencies_ghz'], param_data['magnitude_db'], 
                   label=f'{param_name}', 
                   color=colors[idx],
                   linestyle=line_style,
                   linewidth=line_width,
                   alpha=alpha)
        
        # Formatting
        ax.set_xlabel('Frequency (GHz)', fontsize=12, fontweight='bold')
        ax.set_ylabel('Magnitude (dB)', fontsize=12, fontweight='bold')
        ax.set_title(f'S-Parameters - {result["num_ports"]}-Port Network', fontsize=14, fontweight='bold')
        
        # Legend with intelligent placement
        if len(result['s_parameters']) <= 10:
            ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=8)
        else:
            # For many parameters, show only important ones in legend
            important_params = [k for k in result['s_parameters'].keys() 
                              if k[1] == k[2] or (int(k[1]) <= 2 and int(k[2]) <= 2)]
            handles = []
            labels = []
            for line in ax.lines:
                label = line.get_label()
                if any(param in label for param in important_params):
                    handles.append(line)
                    labels.append(label)
            if handles:
                ax.legend(handles, labels, bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=8)
        
        ax.grid(True, alpha=0.3)
        ax.tick_params(axis='both', which='major', labelsize=10)
        
        # Adjust layout to prevent legend cutoff
        self.fig.tight_layout()
        self.canvas.draw()
        
        # Update metadata sidebar
        self.update_metadata_display(result)
    
    def update_metadata_display(self, result):
        """Update the metadata display with simulation information"""
        import datetime
        
        # Frequency range
        freq_min = min(result['frequencies_ghz'])
        freq_max = max(result['frequencies_ghz'])
        self.meta_labels['freq_range'].config(text=f"{freq_min:.1f}-{freq_max:.1f} GHz")
        
        # Frequency points
        self.meta_labels['freq_points'].config(text=f"{len(result['frequencies_ghz'])}")
        
        # Number of ports
        self.meta_labels['num_ports'].config(text=f"{result['num_ports']}")
        
        # Port names (in separate section)
        port_names_str = ", ".join(result['port_names'])
        self.port_names_label.config(text=port_names_str)
        
        # File format (assuming Touchstone)
        self.meta_labels['file_format'].config(text=f"S{result['num_ports']}P")
        
        # Last updated
        now = datetime.datetime.now().strftime("%H:%M:%S")
        self.meta_labels['last_updated'].config(text=now)
    
    def clear_plot(self):
        """Clear the plot and show empty state"""
        if matplotlib_available:
            self.fig.clear()
            ax = self.fig.add_subplot(111)
            ax.text(0.5, 0.5, 'No S-parameter data loaded', 
                   ha='center', va='center', fontsize=16, alpha=0.5)
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis('off')
            self.canvas.draw()
    
    def refresh_results(self):
        """Refresh current results by reprocessing the data file"""
        if hasattr(self, 'current_touchstone_file') and self.current_touchstone_file:
            if Path(self.current_touchstone_file).exists():
                print(f"🔄 Refreshing results from: {self.current_touchstone_file}")
                self.parse_and_display_results(self.current_touchstone_file)
            else:
                messagebox.showwarning("Refresh Error", 
                                     f"Data file not found:\n{self.current_touchstone_file}")
        else:
            messagebox.showinfo("Refresh", "No data file to refresh. Please run a simulation first.")
    
        
    def clear_results(self):
        """Clear all results and reset display"""
        print("🗑️ Clearing all results")
        self.clear_plot()
        
        # Reset metadata display
        for key in self.meta_labels:
            self.meta_labels[key].config(text="N/A")
        
        # Reset port names display
        self.port_names_label.config(text="N/A")
        
        # Clear current file reference
        if hasattr(self, 'current_touchstone_file'):
            delattr(self, 'current_touchstone_file')
    
    def handle_error(self, task_type: str, result: dict):
        """Handle task error"""
        error_msg = result.get('error', 'Unknown error')
        traceback_msg = result.get('traceback', '')
        
        messagebox.showerror(
            f"{task_type} Error", 
            f"Operation failed:\n\n{error_msg}\n\n{traceback_msg[:500]}..."
        )

def main():
    """Main application entry point"""
    root = tk.Tk()
    root.title("JSON Layout to EM Simulation - Subprocess Edition")
    root.geometry("1100x800")
    
    # Configure style
    try:
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Accent.TButton", foreground="white", background="#0078d4")
    except:
        pass
    
    app = SubprocessEMGUI(root)
    
    # Check environment on startup
    if not app.env_manager.is_available():
        messagebox.showwarning(
            "ADS Not Found",
            "ADS Python environment not detected.\n\n"
            "Please ensure Keysight ADS 2025 is installed.\n"
            "The application will run, but EM simulation features won't work."
        )
    
    root.mainloop()

if __name__ == "__main__":
    main()
