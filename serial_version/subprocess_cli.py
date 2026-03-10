#!/usr/bin/env python3
"""
Command-line interface for JSON Layout to EM Simulation

This CLI tool runs in any Python environment and delegates all ADS/EMPro operations
to subprocess calls using the ADS Python interpreter.

Usage: python subprocess_cli.py --help

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
            
            # Run subprocess
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=tempfile.gettempdir()
            )
            
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

class EMCLI:
    """Command-line interface for EM simulation workflow"""
    
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

    def infer_reference_library_name(self, args) -> str:
        """Infer the reference library name from the provided PDK/reference paths."""
        if getattr(args, 'use_pdk', False):
            pdk_tech_loc = getattr(args, 'pdk_tech_loc', '') or ''
            if pdk_tech_loc:
                return Path(pdk_tech_loc).name

            pdk_loc = getattr(args, 'pdk_loc', '') or ''
            if pdk_loc:
                return Path(pdk_loc).name

        ref_lib_loc = getattr(args, 'ref_lib_loc', '') or ''
        if ref_lib_loc:
            return Path(ref_lib_loc).name

        return 'Reference'
    
    def run_complete_workflow(self, args) -> bool:
        """Run complete workflow: design creation → EM simulation → results processing"""
        if not self.check_environment():
            return False
        
        # Parse JSON and convert to geometry
        try:
            parser = JSONParser(args.json_file)
            geometry_data = parser.convert_to_geometry()
            info = parser.get_info()
            self.logger.info(f"Loaded JSON: {info['design_id']} - {info['layers']} layers, {info['ports']} ports")
        except Exception as e:
            self.logger.error(f"Failed to parse JSON: {e}")
            return False
        
        # Prepare PDK configuration
        pdk_config = {
            'use_pdk': args.use_pdk,
            'ref_lib_loc': args.ref_lib_loc or '',
            'pdk_loc': args.pdk_loc or '',
            'pdk_tech_loc': args.pdk_tech_loc or '',
            'substrate_name': args.substrate or 'microstrip_substrate',
            'ref_library_name': self.infer_reference_library_name(args)
        }
        
        # Load layer mapping
        layer_mapping = self.load_layer_mapping(args.layer_mapping)
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
            'json_file': args.json_file,
            'workspace_dir': args.workspace_dir,
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
        
        self.logger.info("✅ ADS design created successfully")
        
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
        
        sim_task_data = {
            'workspace_dir': args.workspace_dir,
            'library_name': args.library,
            'cell_name': args.cell,
            'em_view_name': 'rfpro_view',
            'export_config': {
                'export_path': args.export_path,
                'export_types': export_types,
                'path_mode': 'absolute'
            }
        }
        
        sim_result = self.env_manager.run_subprocess_task("run_em_simulation", sim_task_data)
        
        if not sim_result['success']:
            self.logger.error(f"EM simulation failed: {sim_result.get('error', 'Unknown error')}")
            return False
        
        self.logger.info("✅ EM simulation completed successfully")
        
        # Display results
        export_results = sim_result.get('export_results', {})
        if export_results:
            self.logger.info("📊 Exported files:")
            for export_type, file_path in export_results.items():
                if file_path:
                    self.logger.info(f"  • {export_type}: {file_path}")
        
        return True
    
    def create_design_only(self, args) -> bool:
        """Create ADS design only"""
        if not self.check_environment():
            return False
        
        # Parse JSON and convert to geometry
        try:
            parser = JSONParser(args.json_file)
            geometry_data = parser.convert_to_geometry()
        except Exception as e:
            self.logger.error(f"Failed to parse JSON: {e}")
            return False
        
        # Prepare PDK configuration
        pdk_config = {
            'use_pdk': args.use_pdk,
            'ref_lib_loc': args.ref_lib_loc or '',
            'pdk_loc': args.pdk_loc or '',
            'pdk_tech_loc': args.pdk_tech_loc or '',
            'substrate_name': args.substrate or 'microstrip_substrate',
            'ref_library_name': self.infer_reference_library_name(args)
        }
        
        # Load layer mapping
        layer_mapping = self.load_layer_mapping(args.layer_mapping)
        if not layer_mapping:
            layer_mapping = {
                'L1': {'layer_name': 'cond', 'layer_purpose': 'drawing'},
                'L2': {'layer_name': 'via', 'layer_purpose': 'drawing'},
                'GND': {'layer_name': 'ground', 'layer_purpose': 'drawing'}
            }
        
        task_data = {
            'json_file': args.json_file,
            'workspace_dir': args.workspace_dir,
            'library_name': args.library,
            'cell_name': args.cell,
            'geometry_data': geometry_data,
            'pdk_config': pdk_config,
            'layer_mapping': layer_mapping
        }
        
        result = self.env_manager.run_subprocess_task("create_ads_design", task_data)
        
        if result['success']:
            self.logger.info(f"✅ ADS design created in: {args.workspace_dir}")
            return True
        else:
            self.logger.error(f"❌ Design creation failed: {result.get('error', 'Unknown error')}")
            return False
    
    def run_simulation_only(self, args) -> bool:
        """Run EM simulation only"""
        if not self.check_environment():
            return False
        
        # Build export configuration
        export_types = []
        if args.export_touchstone:
            export_types.append('touchstone')
        if args.export_dataset:
            export_types.append('dataset')
        if args.export_csv:
            export_types.append('csv')
        
        task_data = {
            'workspace_dir': args.workspace_dir,
            'library_name': args.library,
            'cell_name': args.cell,
            'em_view_name': 'rfpro_view',
            'export_config': {
                'export_path': args.export_path,
                'export_types': export_types,
                'path_mode': 'absolute'
            }
        }
        
        result = self.env_manager.run_subprocess_task("run_em_simulation", task_data)
        
        if result['success']:
            self.logger.info("✅ EM simulation completed")
            export_results = result.get('export_results', {})
            if export_results:
                self.logger.info("📊 Exported files:")
                for export_type, file_path in export_results.items():
                    if file_path:
                        self.logger.info(f"  • {export_type}: {file_path}")
            return True
        else:
            self.logger.error(f"❌ EM simulation failed: {result.get('error', 'Unknown error')}")
            return False

def create_parser() -> argparse.ArgumentParser:
    """Create argument parser"""
    parser = argparse.ArgumentParser(
        description="Command-line interface for JSON Layout to EM Simulation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run complete workflow
  python subprocess_cli.py complete --json design.json --workspace ./workspace
  
  # Create design only
  python subprocess_cli.py design --json design.json --workspace ./workspace
  
  # Run simulation only (requires existing design)
  python subprocess_cli.py simulate --workspace ./workspace --library EM_Design_Lib --cell my_design
  
  # Use PDK
  python subprocess_cli.py complete --json design.json --workspace ./workspace --use-pdk --pdk-loc /path/to/pdk
  
  # Export multiple formats
  python subprocess_cli.py complete --json design.json --workspace ./workspace --export-csv --export-dataset
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Complete workflow
    complete_parser = subparsers.add_parser('complete', help='Run complete workflow')
    complete_parser.add_argument('--json', required=True, dest='json_file', help='JSON layout file')
    complete_parser.add_argument('--workspace', required=True, dest='workspace_dir', help='Workspace directory')
    complete_parser.add_argument('--library', default='EM_Design_Lib', help='Library name')
    complete_parser.add_argument('--cell', help='Cell name (auto-detected from JSON if not provided)')
    complete_parser.add_argument('--substrate', default='microstrip_substrate', help='Substrate name')
    complete_parser.add_argument('--use-pdk', action='store_true', help='Use PDK mode')
    complete_parser.add_argument('--pdk-loc', help='PDK library location')
    complete_parser.add_argument('--pdk-tech-loc', help='PDK tech location')
    complete_parser.add_argument('--ref-lib-loc', help='Reference library location')
    complete_parser.add_argument('--layer-mapping', help='Layer mapping JSON file')
    complete_parser.add_argument('--export-path', default='./results', help='Export directory')
    complete_parser.add_argument('--export-touchstone', action='store_true', default=True, help='Export Touchstone format')
    complete_parser.add_argument('--export-dataset', action='store_true', help='Export ADS dataset')
    complete_parser.add_argument('--export-csv', action='store_true', help='Export CSV format')
    
    # Create design only
    design_parser = subparsers.add_parser('design', help='Create ADS design only')
    design_parser.add_argument('--json', required=True, dest='json_file', help='JSON layout file')
    design_parser.add_argument('--workspace', required=True, dest='workspace_dir', help='Workspace directory')
    design_parser.add_argument('--library', default='EM_Design_Lib', help='Library name')
    design_parser.add_argument('--cell', help='Cell name (auto-detected from JSON if not provided)')
    design_parser.add_argument('--substrate', default='microstrip_substrate', help='Substrate name')
    design_parser.add_argument('--use-pdk', action='store_true', help='Use PDK mode')
    design_parser.add_argument('--pdk-loc', help='PDK library location')
    design_parser.add_argument('--pdk-tech-loc', help='PDK tech location')
    design_parser.add_argument('--ref-lib-loc', help='Reference library location')
    design_parser.add_argument('--layer-mapping', help='Layer mapping JSON file')
    
    # Run simulation only
    sim_parser = subparsers.add_parser('simulate', help='Run EM simulation only')
    sim_parser.add_argument('--workspace', required=True, dest='workspace_dir', help='Workspace directory')
    sim_parser.add_argument('--library', required=True, dest='library_name', help='Library name')
    sim_parser.add_argument('--cell', required=True, dest='cell_name', help='Cell name')
    sim_parser.add_argument('--export-path', default='./results', help='Export directory')
    sim_parser.add_argument('--export-touchstone', action='store_true', default=True, help='Export Touchstone format')
    sim_parser.add_argument('--export-dataset', action='store_true', help='Export ADS dataset')
    sim_parser.add_argument('--export-csv', action='store_true', help='Export CSV format')
    
    return parser

def main():
    """Main CLI entry point"""
    parser = create_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    cli = EMCLI()
    
    # Auto-detect cell name from JSON if not provided
    if hasattr(args, 'cell') and not args.cell and hasattr(args, 'json_file'):
        try:
            parser_obj = JSONParser(args.json_file)
            info = parser_obj.get_info()
            args.cell = info['design_id']
            print(f"Auto-detected cell name: {args.cell}")
        except:
            args.cell = "my_design"
            print(f"Using default cell name: {args.cell}")
    
    success = False
    
    try:
        if args.command == 'complete':
            success = cli.run_complete_workflow(args)
        elif args.command == 'design':
            success = cli.create_design_only(args)
        elif args.command == 'simulate':
            success = cli.run_simulation_only(args)
    except KeyboardInterrupt:
        print("\n❌ Operation cancelled by user")
        return 1
    except Exception as e:
        print(f"❌ Critical error: {e}")
        if hasattr(cli, 'logger'):
            cli.logger.error(traceback.format_exc())
        return 1
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
