#!/usr/bin/env python3
"""
Parallel Command-line interface for JSON Layout to EM Simulation

Enhanced version supporting:
1. create_workspace_lib: Create workspace and library only
2. create_design_only: Create design in existing library  
3. run_simulation_only: Run EM simulation for specific design
4. Original complete workflow functions (preserved)

Usage: python subprocess_cli_parallel.py --help

Author: ADS Python API Guide
Date: 2025
"""

import json
import subprocess
import os
import sys
import argparse
import logging
from pathlib import Path
import tempfile
import traceback
from typing import Dict, List, Any, Optional

class EnvironmentManager:
    """Manage ADS/EMPro environment detection and subprocess calls"""
    
    @staticmethod
    def to_absolute_path(path: str) -> str:
        """Convert path to absolute path if it's not already absolute"""
        path_obj = Path(path)
        if path_obj.is_absolute():
            return str(path_obj)
        else:
            return str(Path.cwd() / path_obj)
    
    def __init__(self):
        self.ads_python_exe = None
        self.worker_script = Path(__file__).parent / "subprocess_worker_parallel.py"
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
        seen = set()
        for candidate in self._build_candidate_paths():
            if not candidate or candidate in seen:
                continue
            seen.add(candidate)
            
            path = Path(candidate)
            if path.exists() and self._validate_python(str(path)):
                self.ads_python_exe = str(path)
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
            raise RuntimeError("ADS Python environment not found. Set ADS_PYTHON or ADS_INSTALL_DIR to override auto-detection.")
        return self.ads_python_exe
    
    def run_subprocess_task(self, task_type: str, task_data: dict) -> dict:
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
            
            # Run subprocess with proper encoding handling
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace',
                cwd=Path.cwd()
            )
            
            stdout, stderr = process.communicate()
            
            # Parse result
            if process.returncode == 0 and stdout:
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
            elif stdout is None:
                return {'success': False, 'error': 'Subprocess returned no output'}
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

class EMCLI:
    """Enhanced Command-line interface for EM simulation workflow with parallel support"""
    
    def __init__(self):
        self.env_manager = EnvironmentManager()
        self.setup_logging()
    
    def setup_logging(self):
        """Setup logging for CLI with UTF-8 encoding"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
        # Fix encoding for Windows
        try:
            import locale
            locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
        except:
            pass
    
    def check_environment(self) -> bool:
        """Check if ADS environment is available"""
        if self.env_manager.is_available():
            self.logger.info(f"ADS Python found: {Path(self.env_manager.get_python_exe()).parent.parent.parent}")
            return True
        else:
            self.logger.error("ADS Python environment not found. Please install Keysight ADS 2025.")
            return False
    
    def load_layer_mapping(self, mapping_file: str) -> Dict[str, Dict[str, str]]:
        """Load layer mapping from JSON file"""
        if not mapping_file or not Path(mapping_file).exists():
            return {}
        
        try:
            with open(mapping_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.logger.warning(f"Failed to load layer mapping: {e}")
            return {}

    def infer_reference_library(self, workspace_dir: str, library_name: str) -> str:
        """Infer the best reference library from an existing workspace."""
        workspace_path = Path(self.env_manager.to_absolute_path(workspace_dir))
        lib_defs_path = workspace_path / "lib.defs"
        if not lib_defs_path.exists():
            return library_name

        define_paths: Dict[str, str] = {}
        read_only_libs: List[str] = []

        try:
            for raw_line in lib_defs_path.read_text(encoding="utf-8", errors="replace").splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue

                parts = line.split()
                if len(parts) >= 3 and parts[0] == "DEFINE":
                    define_paths[parts[1]] = parts[2]
                elif len(parts) >= 4 and parts[0] == "ASSIGN" and parts[2] == "libMode" and parts[3] == "readOnly":
                    read_only_libs.append(parts[1])
        except Exception as e:
            self.logger.warning(f"Failed to inspect lib.defs for reference library inference: {e}")
            return library_name

        candidates = [name for name in read_only_libs if name != library_name]
        tech_candidates = [name for name in candidates if name.lower().endswith("_tech")]
        preferred = tech_candidates[0] if tech_candidates else (candidates[0] if candidates else library_name)

        if preferred != library_name:
            lib_path = define_paths.get(preferred, "")
            self.logger.info(f"Inferred reference library: {preferred}" + (f" ({lib_path})" if lib_path else ""))

        return preferred
    
    # === NEW PARALLEL FUNCTIONS ===
    
    def create_workspace_lib_only(self, args) -> bool:
        """Create workspace and library only (Task Type A)"""
        if not self.check_environment():
            return False
        
        self.logger.info("Creating workspace and library...")
        
        task_data = {
            'workspace_dir': self.env_manager.to_absolute_path(args.workspace_dir),
            'library_name': args.library_name,
            'use_pdk': args.use_pdk,
            'pdk_loc': getattr(args, 'pdk_loc', '') or getattr(args, 'pdk_dir', '') or '',
            'pdk_tech_loc': getattr(args, 'pdk_tech_loc', '') or getattr(args, 'pdk_tech_dir', '') or ''
        }
        
        result = self.env_manager.run_subprocess_task('create_workspace_lib', task_data)
        
        if result['success']:
            self.logger.info("SUCCESS: Workspace and library created successfully")
            return True
        else:
            self.logger.error(f"Failed to create workspace and library: {result.get('error', 'Unknown error')}")
            return False
    
    def create_design_only(self, args) -> bool:
        """Create design in existing library (Task Type B)"""
        if not self.check_environment():
            return False
        
        # Parse JSON and convert to geometry
        try:
            json_file_abs = self.env_manager.to_absolute_path(args.json_file)
            parser = JSONParser(json_file_abs)
            geometry_data = parser.convert_to_geometry()
            info = parser.get_info()
            self.logger.info(f"Loaded JSON: {info['design_id']} - {info['layers']} layers, {info['ports']} ports")
        except Exception as e:
            self.logger.error(f"Failed to parse JSON: {e}")
            return False
        
        # Load layer mapping
        layer_mapping_abs = self.env_manager.to_absolute_path(args.layer_mapping) if args.layer_mapping else None
        layer_mapping = self.load_layer_mapping(layer_mapping_abs)
        if not layer_mapping:
            # Default layer mapping
            layer_mapping = {
                'L1': {'layer_name': 'cond', 'layer_purpose': 'drawing'},
                'L2': {'layer_name': 'via', 'layer_purpose': 'drawing'},
                'GND': {'layer_name': 'ground', 'layer_purpose': 'drawing'}
            }
        
        self.logger.info(f"Creating design: {args.library_name}:{args.cell_name}")

        ref_library_name = args.ref_library_name or self.infer_reference_library(
            args.workspace_dir, args.library_name
        )
        
        task_data = {
            'workspace_dir': self.env_manager.to_absolute_path(args.workspace_dir),
            'library_name': args.library_name,
            'cell_name': args.cell_name,
            'geometry_data': geometry_data,
            'ref_library_name': ref_library_name,
            'substrate_name': args.substrate or 'microstrip_substrate',
            'layer_mapping': layer_mapping
        }
        
        result = self.env_manager.run_subprocess_task('create_design_only', task_data)
        
        if result['success']:
            self.logger.info("SUCCESS: Design created successfully")
            return True
        else:
            self.logger.error(f"Failed to create design: {result.get('error', 'Unknown error')}")
            return False
    
    def load_frequency_config(self, args) -> dict:
        """Load frequency configuration from JSON string or file"""
        if not args.frequency_config:
            # Return default configuration
            return {
                "global_frequency_plan_type": "Interpolating_AllFields",
                "frequency_plans": [
                    {
                        "compute_type": "Simulated",
                        "sweep_type": "Adaptive",
                        "near_field_type": "NoNearFields",
                        "far_field_type": "NoFarFields",
                        "start_frequency": "0 Hz",
                        "stop_frequency": "10 GHz",
                        "number_of_points": 201,
                        "sample_points_limit": 300,
                        "points_per_decade": 5
                    }
                ]
            }
        
        try:
            # Try to parse as JSON string first
            config = json.loads(args.frequency_config)
            return config
        except json.JSONDecodeError:
            # If not a valid JSON string, try as file path
            try:
                config_path = Path(args.frequency_config)
                if config_path.exists():
                    with open(config_path, 'r', encoding='utf-8') as f:
                        return json.load(f)
                else:
                    self.logger.warning(f"Frequency config file not found: {args.frequency_config}")
                    return {}
            except Exception as e:
                self.logger.error(f"Failed to load frequency config: {e}")
                return {}

    def run_simulation_only(self, args) -> bool:
        """Run EM simulation for specific design"""
        try:
            self.logger.info(f"Running simulation for design: {args.cell_name}")
            
            # Load frequency configuration
            frequency_config = self.load_frequency_config(args)
            
            # Prepare task data
            task_data = {
                "workspace_dir": args.workspace_dir,
                "library_name": args.library_name,
                "cell_name": args.cell_name,
                "frequency_config": frequency_config,
                "export_config": {
                    "export_path": args.export_path,
                    "export_touchstone": args.export_touchstone,
                    "export_dataset": args.export_dataset,
                    "export_csv": args.export_csv
                }
            }
            
            # Run simulation task using subprocess
            result = self.env_manager.run_subprocess_task('run_em_simulation_only', task_data)
            
            if not result["success"]:
                self.logger.error(f"Simulation failed: {result['message']}")
                print(f"ERROR: {result['message']}", file=sys.stderr)
                return False
                
            self.logger.info("Simulation completed successfully")
            
            # Log export results if available
            export_results = result.get('export_results', {})
            if export_results:
                self.logger.info(" Exported files:")
                for export_type, file_path in export_results.items():
                    if file_path:
                        self.logger.info(f"  - {export_type}: {file_path}")
            
            return True
            
        except Exception as e:
            error_msg = f"Error running simulation: {str(e)}\n{traceback.format_exc()}"
            self.logger.error(error_msg)
            print(f"ERROR: {error_msg}", file=sys.stderr)
            return False
    
    # === ORIGINAL FUNCTIONS (PRESERVED) ===
    
    def run_complete_workflow(self, args) -> bool:
        """Run complete workflow: design creation → EM simulation → results processing"""
        if not self.check_environment():
            return False
        
        # Parse JSON and convert to geometry
        try:
            json_file_abs = self.env_manager.to_absolute_path(args.json_file)
            parser = JSONParser(json_file_abs)
            geometry_data = parser.convert_to_geometry()
            info = parser.get_info()
            self.logger.info(f"Loaded JSON: {info['design_id']} - {info['layers']} layers, {info['ports']} ports")
        except Exception as e:
            self.logger.error(f"Failed to parse JSON: {e}")
            return False
        
        # Prepare PDK configuration with absolute paths
        pdk_config = {
            'use_pdk': args.use_pdk,
            'ref_lib_loc': self.env_manager.to_absolute_path(args.ref_lib_loc) if args.ref_lib_loc else '',
            'pdk_loc': self.env_manager.to_absolute_path(args.pdk_loc) if args.pdk_loc else '',
            'pdk_tech_loc': self.env_manager.to_absolute_path(args.pdk_tech_loc) if args.pdk_tech_loc else '',
            'substrate_name': args.substrate or 'microstrip_substrate',
            'ref_library_name': Path(args.pdk_loc).name if args.use_pdk and args.pdk_loc else Path(args.ref_lib_loc).name if args.ref_lib_loc else 'Reference'
        }
        
        # Load layer mapping
        layer_mapping_abs = self.env_manager.to_absolute_path(args.layer_mapping) if args.layer_mapping else None
        layer_mapping = self.load_layer_mapping(layer_mapping_abs)
        if not layer_mapping:
            # Default layer mapping
            layer_mapping = {
                'L1': {'layer_name': 'cond', 'layer_purpose': 'drawing'},
                'L2': {'layer_name': 'via', 'layer_purpose': 'drawing'},
                'GND': {'layer_name': 'ground', 'layer_purpose': 'drawing'}
            }
        
        # Step 1: Create ADS design
        self.logger.info("Step 1: Creating ADS design...")
        design_task_data = {
            'json_file': json_file_abs,
            'workspace_dir': self.env_manager.to_absolute_path(args.workspace_dir),
            'library_name': args.library,
            'cell_name': args.cell,
            'geometry_data': geometry_data,
            'pdk_config': pdk_config,
            'layer_mapping': layer_mapping
        }
        
        design_result = self.env_manager.run_subprocess_task("create_ads_design", design_task_data)
        
        if not design_result['success']:
            self.logger.error(f"Design creation failed: {design_result.get('error', 'Unknown error')}")
            return False
        
        self.logger.info("SUCCESS: ADS design created successfully")
        
        # Step 2: Run EM simulation
        self.logger.info("Step 2: Running EM simulation...")
        
        # Build export configuration
        export_types = []
        if args.export_touchstone:
            export_types.append('touchstone')
        if args.export_dataset:
            export_types.append('dataset')
        if args.export_csv:
            export_types.append('csv')
        
        export_path_abs = self.env_manager.to_absolute_path(args.export_path) if args.export_path else None
        
        # Load frequency configuration for complete workflow
        frequency_config = {}
        if hasattr(args, 'frequency_config') and args.frequency_config:
            frequency_config = self.load_frequency_config(args)
        
        sim_task_data = {
            'workspace_dir': self.env_manager.to_absolute_path(args.workspace_dir),
            'library_name': args.library,
            'cell_name': args.cell,
            'em_view_name': 'rfpro_view',
            'frequency_config': frequency_config,
            'export_config': {
                'export_path': export_path_abs,
                'export_types': export_types,
                'path_mode': 'absolute'
            }
        }
        
        sim_result = self.env_manager.run_subprocess_task("run_em_simulation", sim_task_data)
        
        if not sim_result['success']:
            self.logger.error(f"EM simulation failed: {sim_result.get('error', 'Unknown error')}")
            return False
        
        self.logger.info("SUCCESS: EM simulation completed successfully")
        
        # Display results
        export_results = sim_result.get('export_results', {})
        if export_results:
            self.logger.info(" Exported files:")
            for export_type, file_path in export_results.items():
                if file_path:
                    self.logger.info(f"  - {export_type}: {file_path}")
        
        return True
    
    def create_design_only_original(self, args) -> bool:
        """Create ADS design only (original function)"""
        if not self.check_environment():
            return False
        
        # Parse JSON and convert to geometry
        try:
            json_file_abs = self.env_manager.to_absolute_path(args.json_file)
            parser = JSONParser(json_file_abs)
            geometry_data = parser.convert_to_geometry()
        except Exception as e:
            self.logger.error(f"Failed to parse JSON: {e}")
            return False
        
        # Prepare PDK configuration with absolute paths
        pdk_config = {
            'use_pdk': args.use_pdk,
            'ref_lib_loc': self.env_manager.to_absolute_path(args.ref_lib_loc) if args.ref_lib_loc else '',
            'pdk_loc': self.env_manager.to_absolute_path(args.pdk_loc) if args.pdk_loc else '',
            'pdk_tech_loc': self.env_manager.to_absolute_path(args.pdk_tech_loc) if args.pdk_tech_loc else '',
            'substrate_name': args.substrate or 'microstrip_substrate',
            'ref_library_name': Path(args.pdk_loc).name if args.use_pdk and args.pdk_loc else Path(args.ref_lib_loc).name if args.ref_lib_loc else 'Reference'
        }
        
        # Load layer mapping
        layer_mapping_abs = self.env_manager.to_absolute_path(args.layer_mapping) if args.layer_mapping else None
        layer_mapping = self.load_layer_mapping(layer_mapping_abs)
        if not layer_mapping:
            layer_mapping = {
                'L1': {'layer_name': 'cond', 'layer_purpose': 'drawing'},
                'L2': {'layer_name': 'via', 'layer_purpose': 'drawing'},
                'GND': {'layer_name': 'ground', 'layer_purpose': 'drawing'}
            }
        
        task_data = {
            'json_file': json_file_abs,
            'workspace_dir': self.env_manager.to_absolute_path(args.workspace_dir),
            'library_name': args.library,
            'cell_name': args.cell,
            'geometry_data': geometry_data,
            'pdk_config': pdk_config,
            'layer_mapping': layer_mapping
        }
        
        result = self.env_manager.run_subprocess_task("create_ads_design", task_data)
        
        if result['success']:
            self.logger.info("SUCCESS: ADS design created successfully")
            return True
        else:
            self.logger.error(f"Design creation failed: {result.get('error', 'Unknown error')}")
            return False

def create_parser():
    """Create command line argument parser with enhanced options"""
    parser = argparse.ArgumentParser(
        description="Parallel JSON Layout to EM Simulation CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create workspace and library only
  python subprocess_cli_parallel.py create-workspace-lib \\
    --workspace-dir "./test_workspace" \\
    --library-name "Test_Lib" \\
    --use-pdk \\
    --pdk-dir "path/to/pdk" \\
    --pdk-tech-dir "path/to/tech"

  # Create design in existing library
  python subprocess_cli_parallel.py create-design-only \\
    --workspace-dir "./shared_workspace" \\
    --library-name "Shared_Lib" \\
    --cell-name "Design1" \\
    --json-file "design1.json"

  # Run simulation for specific design
  python subprocess_cli_parallel.py run-simulation-only \\
    --workspace-dir "./shared_workspace" \\
    --library-name "Shared_Lib" \\
    --cell-name "Design1" \\
    --export-path "./results"

  # Original complete workflow
  python subprocess_cli_parallel.py complete-workflow \\
    --json-file "design.json" \\
    --workspace-dir "./workspace" \\
    --library "MyLib" \\
    --cell "MyDesign"
        """
    )
    
    # Global arguments
    parser.add_argument('--workspace-dir', type=str, 
                       help='Workspace directory path')
    parser.add_argument('--library-name', '--library', type=str,
                       help='Library name')
    parser.add_argument('--cell-name', '--cell', type=str,
                       help='Cell name')
    parser.add_argument('--json-file', type=str,
                       help='JSON layout file path')
    parser.add_argument('--export-path', type=str,
                       help='Export directory path')
    parser.add_argument('--use-pdk', action='store_true',
                       help='Use PDK library')
    parser.add_argument('--pdk-dir', '--pdk-loc', type=str,
                       help='PDK library directory')
    parser.add_argument('--pdk-tech-dir', '--pdk-tech-loc', type=str,
                       help='PDK technology library directory')
    parser.add_argument('--ref-lib-loc', type=str,
                       help='Reference library directory')
    parser.add_argument('--substrate', type=str, default='microstrip_substrate',
                       help='Substrate name')
    parser.add_argument('--layer-mapping', type=str,
                       help='Layer mapping JSON file')
    parser.add_argument('--ref-library-name', type=str,
                       help='Reference library name')
    parser.add_argument('--em-view-name', type=str,
                       help='EM view name (default: rfpro_view)')
    
    # Export options
    parser.add_argument('--export-touchstone', action='store_true',
                       help='Export Touchstone format')
    parser.add_argument('--export-dataset', action='store_true',
                       help='Export ADS dataset format')
    parser.add_argument('--export-csv', action='store_true',
                       help='Export CSV format')
    
    # Subcommands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # New parallel commands
    create_ws_parser = subparsers.add_parser('create-workspace-lib', 
                                           help='Create workspace and library only')
    create_ws_parser.add_argument('--workspace-dir', type=str, required=True,
                                help='Workspace directory path')
    create_ws_parser.add_argument('--library-name', type=str, required=True,
                                help='Library name')
    create_ws_parser.add_argument('--use-pdk', action='store_true',
                                help='Use PDK library')
    create_ws_parser.add_argument('--pdk-dir', '--pdk-loc', type=str,
                                help='PDK library directory')
    create_ws_parser.add_argument('--pdk-tech-dir', '--pdk-tech-loc', type=str,
                                help='PDK technology library directory')
    create_ws_parser.set_defaults(func=lambda args: emcli.create_workspace_lib_only(args))
    
    create_design_parser = subparsers.add_parser('create-design-only',
                                               help='Create design in existing library')
    create_design_parser.add_argument('--workspace-dir', type=str, required=True,
                                    help='Workspace directory path')
    create_design_parser.add_argument('--library-name', type=str, required=True,
                                    help='Library name')
    create_design_parser.add_argument('--cell-name', type=str, required=True,
                                    help='Cell name')
    create_design_parser.add_argument('--json-file', type=str, required=True,
                                    help='JSON layout file path')
    create_design_parser.add_argument('--substrate', type=str, default='microstrip_substrate',
                                    help='Substrate name')
    create_design_parser.add_argument('--layer-mapping', type=str,
                                    help='Layer mapping JSON file')
    create_design_parser.add_argument('--ref-library-name', type=str,
                                    help='Reference library name')
    create_design_parser.set_defaults(func=lambda args: emcli.create_design_only(args))
    
    run_sim_parser = subparsers.add_parser('run-simulation-only',
                                         help='Run EM simulation for specific design')
    run_sim_parser.add_argument('--workspace-dir', type=str, required=True,
                              help='Workspace directory path')
    run_sim_parser.add_argument('--library-name', type=str, required=True,
                              help='Library name')
    run_sim_parser.add_argument('--cell-name', type=str, required=True,
                              help='Cell name')
    run_sim_parser.add_argument('--export-path', type=str,
                              help='Export directory path')
    run_sim_parser.add_argument('--export-touchstone', action='store_true',
                              help='Export Touchstone format')
    run_sim_parser.add_argument('--export-dataset', action='store_true',
                              help='Export ADS dataset format')
    run_sim_parser.add_argument('--export-csv', action='store_true',
                              help='Export CSV format')
    run_sim_parser.add_argument('--em-view-name', type=str,
                              help='EM view name (default: rfpro_view)')
    run_sim_parser.add_argument('--frequency-config', type=str,
                              help='Frequency configuration JSON string')
    run_sim_parser.set_defaults(func=lambda args: emcli.run_simulation_only(args))
    
    # Original commands
    complete_parser = subparsers.add_parser('complete-workflow',
                                          help='Run complete workflow (original)')
    complete_parser.add_argument('--json-file', type=str, required=True,
                                help='JSON layout file path')
    complete_parser.add_argument('--workspace-dir', type=str, required=True,
                                help='Workspace directory path')
    complete_parser.add_argument('--library', '--library-name', type=str, required=True,
                                help='Library name')
    complete_parser.add_argument('--cell', '--cell-name', type=str, required=True,
                                help='Cell name')
    complete_parser.add_argument('--use-pdk', action='store_true',
                                help='Use PDK library')
    complete_parser.add_argument('--pdk-dir', '--pdk-loc', type=str,
                                help='PDK library directory')
    complete_parser.add_argument('--pdk-tech-dir', '--pdk-tech-loc', type=str,
                                help='PDK technology library directory')
    complete_parser.add_argument('--ref-lib-loc', type=str,
                                help='Reference library directory')
    complete_parser.add_argument('--substrate', type=str, default='microstrip_substrate',
                                help='Substrate name')
    complete_parser.add_argument('--layer-mapping', type=str,
                                help='Layer mapping JSON file')
    complete_parser.add_argument('--export-path', type=str,
                                help='Export directory path')
    complete_parser.add_argument('--export-touchstone', action='store_true',
                                help='Export Touchstone format')
    complete_parser.add_argument('--export-dataset', action='store_true',
                                help='Export ADS dataset format')
    complete_parser.add_argument('--export-csv', action='store_true',
                                help='Export CSV format')
    complete_parser.add_argument('--frequency-config', type=str,
                                help='Frequency configuration JSON string or file path')
    complete_parser.set_defaults(func=lambda args: emcli.run_complete_workflow(args))
    
    design_only_parser = subparsers.add_parser('design-only-original',
                                             help='Create design only (original)')
    design_only_parser.add_argument('--json-file', type=str, required=True,
                                  help='JSON layout file path')
    design_only_parser.add_argument('--workspace-dir', type=str, required=True,
                                  help='Workspace directory path')
    design_only_parser.add_argument('--library', '--library-name', type=str, required=True,
                                  help='Library name')
    design_only_parser.add_argument('--cell', '--cell-name', type=str, required=True,
                                  help='Cell name')
    design_only_parser.add_argument('--use-pdk', action='store_true',
                                  help='Use PDK library')
    design_only_parser.add_argument('--pdk-dir', '--pdk-loc', type=str,
                                  help='PDK library directory')
    design_only_parser.add_argument('--pdk-tech-dir', '--pdk-tech-loc', type=str,
                                  help='PDK technology library directory')
    design_only_parser.add_argument('--ref-lib-loc', type=str,
                                  help='Reference library directory')
    design_only_parser.add_argument('--substrate', type=str, default='microstrip_substrate',
                                  help='Substrate name')
    design_only_parser.add_argument('--layer-mapping', type=str,
                                  help='Layer mapping JSON file')
    design_only_parser.set_defaults(func=lambda args: emcli.create_design_only_original(args))
    
    return parser

def main():
    """Main entry point"""
    global emcli
    emcli = EMCLI()
    
    parser = create_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    try:
        success = args.func(args)
        return 0 if success else 1
    except Exception as e:
        emcli.logger.error(f"Unexpected error: {e}")
        emcli.logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    sys.exit(main())
