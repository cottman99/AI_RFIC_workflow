#!/usr/bin/env python3
"""
Enhanced Subprocess Worker for Parallel ADS/EMPro Operations

This enhanced version supports:
1. create_workspace_lib: Create workspace and library only
2. create_design_only: Create design in existing library
3. run_em_simulation_only: Run EM simulation for specific design
4. create_ads_design: Original complete workflow (preserved)
5. run_em_simulation: Original simulation workflow (preserved)
6. manage_workspace_conflict: Handle workspace conflicts in ADS context

Usage: python subprocess_worker_parallel.py <task_json>
"""

import sys
import json
import traceback
import os
import math
from pathlib import Path

import logging
import datetime
import tempfile
import keysight.edatoolbox.multi_python as multi_python

def setup_logging(console_level=logging.INFO):
    """Setup comprehensive logging with different levels for file and console"""
    log_filename = Path(tempfile.gettempdir()) / f"ads_parallel_worker_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    # Create logger
    logger = logging.getLogger('ads_parallel_worker')
    logger.setLevel(logging.DEBUG)
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # File handler - DEBUG level (detailed)
    file_handler = logging.FileHandler(log_filename, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    
    # Console handler - INFO level (concise)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level)
    console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger, log_filename

def setup_ads_environment():
    """Setup ADS Python environment"""
    logger = logging.getLogger('ads_parallel_worker')
    try:
        # Get ADS installation path from executable location
        python_exe = Path(sys.executable)
        
        # Determine correct ADS base path
        if "tools\\python" in str(python_exe):
            # ADS tools python
            ads_base = python_exe.parent.parent.parent
        elif "fem" in str(python_exe):
            # FEM python
            ads_base = python_exe.parent.parent.parent.parent.parent.parent.parent
        else:
            ads_base = python_exe.parent.parent
            
        logger.debug(f"ADS Base Path: {ads_base}")
        
        # Set environment variables
        os.environ["HPEESOF_DIR"] = str(ads_base)
        
        # Add required paths
        ads_python_path = str(python_exe.parent)
        if ads_python_path not in sys.path:
            sys.path.insert(0, ads_python_path)
            
        # Add ADS packages path
        ads_packages = str(ads_base / "tools" / "python" / "packages")
        if ads_packages not in sys.path:
            sys.path.insert(0, ads_packages)
            
        # Set PATH for DLL loading - use full ADS base path
        bin_path = str(ads_base / "bin")
        if os.path.exists(bin_path):
            if bin_path not in os.environ.get('PATH', ''):
                os.environ['PATH'] = bin_path + os.pathsep + os.environ.get('PATH', '')
        else:
            # Try alternative bin paths
            alt_bins = [
                str(ads_base / "fem" / "2025.20" / "win32_64" / "bin"),
                str(ads_base / "tools" / "bin"),
            ]
            for alt_bin in alt_bins:
                if os.path.exists(alt_bin):
                    os.environ['PATH'] = alt_bin + os.pathsep + os.environ.get('PATH', '')
                    break
            
        logger.debug("ADS environment setup successful")
        return True
    except Exception as e:
        logger.error(f"Failed to setup ADS environment: {e}")
        return False

def create_workspace_lib_task(task_data):
    """Create workspace and library only (Task Type A)"""
    logger, log_filename = setup_logging(console_level=logging.WARNING)
    
    try:
        logger.debug("Starting workspace and library creation task")
        logger.debug(f"Task data: {task_data}")
        
        import keysight.ads.de as de
        
        workspace_dir = task_data['workspace_dir']
        library_name = task_data['library_name']
        
        # PDK configuration
        use_pdk = task_data.get('use_pdk', False)
        pdk_loc = task_data.get('pdk_loc', '')
        pdk_tech_loc = task_data.get('pdk_tech_loc', '')
        
        logger.debug(f"Creating workspace: {workspace_dir}")
        logger.debug(f"Creating library: {library_name}")
        logger.debug(f"Using PDK: {use_pdk}")
        
        # Create workspace path
        workspace_path = Path(workspace_dir)
        library_path = workspace_path / library_name
        
        # Clean existing workspace if it exists
        if workspace_path.exists():
            import shutil
            shutil.rmtree(workspace_path)
            
        # Create workspace
        workspace = de.create_workspace(str(workspace_path))
        workspace.open()
        
        # Create library
        de.create_new_library(library_name, str(library_path))
        workspace.add_library(library_name, str(library_path), de.LibraryMode.SHARED)
        library = workspace.open_library(library_name, str(library_path), de.LibraryMode.SHARED)
        
        # Setup technology
        library.setup_schematic_tech()
        
        # Setup PDK or reference library
        if use_pdk:
            ref_library_name = setup_pdk_library(workspace, library, pdk_loc, pdk_tech_loc, logger)
        else:
            ref_library_name = library_name  # Use self as reference
            # Create layout technology for non-PDK case
            library.create_layout_tech_std_ads("millimeter", 10000, False)
        
        workspace.close()
        
        logger.info("Workspace and library creation completed successfully")
        
        return {
            'success': True,
            'workspace_dir': str(workspace_path),
            'library_name': library_name,
            'ref_library_name': ref_library_name,
            'message': 'Workspace and library created successfully',
            'log_file': str(log_filename)
        }
        
    except Exception as e:
        logger.error(f"Workspace and library creation failed: {e}")
        logger.error(traceback.format_exc())
        return {
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc(),
            'log_file': str(log_filename)
        }

def setup_pdk_library(workspace, library, pdk_loc, pdk_tech_loc, logger):
    """Setup PDK library, configure technology, and return reference library name"""

    import keysight.ads.de as de

    try:
        if pdk_loc and Path(pdk_loc).exists() and pdk_tech_loc and Path(pdk_tech_loc).exists():
            # Add tech library first (critical for PDK references)
            tech_lib_name = Path(pdk_tech_loc).name
            workspace.add_library(tech_lib_name, str(pdk_tech_loc), de.LibraryMode.READ_ONLY)
            ref_library_name = tech_lib_name
            
            # Then add main PDK library
            pdk_lib_name = Path(pdk_loc).name
            workspace.add_library(pdk_lib_name, str(pdk_loc), de.LibraryMode.READ_ONLY)
            pdk_library = workspace.open_library(pdk_lib_name, str(pdk_loc), de.LibraryMode.READ_ONLY)
            
            # Create layout technology from PDK (关键步骤！)
            library.create_layout_tech_from_pdk(pdk_library, copy_tech=False)
            
            logger.info(f"PDK libraries added: {pdk_lib_name}, {tech_lib_name}")
            logger.info("PDK technology configured for new library")
            return ref_library_name
            
        else:
            logger.warning("PDK paths not found, using library self as reference")
            return library.name
            
    except Exception as e:
        logger.warning(f"Failed to setup PDK library: {e}")
        return library.name

def manage_workspace_conflict_task(task_data):
    """Handle workspace conflicts using ADS context (Task Type C)"""
    logger, log_filename = setup_logging()
    
    try:
        logger.info("Starting workspace conflict management task")
        
        import keysight.ads.de as de
        
        target_workspace_dir = task_data['workspace_dir']
        action = task_data.get('action', 'check_and_switch')  # 'check_only', 'close_current', 'check_and_switch', 'verify_only'
        
        logger.info(f"Workspace management action: {action}")
        logger.info(f"Target workspace: {target_workspace_dir}")
        
        target_workspace_path = Path(target_workspace_dir).resolve()
        
        result = {
            'action': action,
            'target_workspace': str(target_workspace_path),
            'workspace_managed': False,
            'workspace_exists': False,
            'previous_workspace': None,
            'current_workspace': None,
            'workspace_handle': None
        }
        
        # New verify_only mode - just get workspace handle without opening
        if action == 'verify_only':
            try:
                workspace = de.open_workspace(str(target_workspace_path))
                # Don't call workspace.open()
                result['workspace_exists'] = True
                result['workspace_handle'] = workspace
                result['message'] = f"Got workspace handle at: {target_workspace_path}"
                logger.info(f"✓ Got workspace handle: {target_workspace_path}")
            except Exception as e:
                result['workspace_exists'] = False
                result['message'] = f"Workspace does not exist: {target_workspace_path}"
                result['error'] = str(e)
                logger.warning(f"✗ Failed to get workspace handle: {e}")
            return result
        
        # Check if a workspace is currently open
        current_workspace = None
        try:
            if de.workspace_is_open():
                current_workspace = de.active_workspace()
                if current_workspace:
                    current_workspace_path = Path(current_workspace.path).resolve()
                    result['previous_workspace'] = str(current_workspace_path)
                    logger.info(f"Current workspace: {current_workspace_path}")
                    
                    if current_workspace_path == target_workspace_path:
                        logger.info("✓ Current workspace matches target workspace, reusing")
                        result['workspace_managed'] = True
                        result['current_workspace'] = str(current_workspace_path)
                        result['message'] = 'Workspace already matches target'
                        return result
                    else:
                        logger.info(f"⚠ Current workspace differs from target")
                        if action in ['close_current', 'check_and_switch']:
                            logger.info(f"Closing current workspace: {current_workspace_path}")
                            current_workspace.close()
                            result['previous_workspace_closed'] = True
                            logger.info("✓ Current workspace closed")
                else:
                    logger.info("No workspace currently open despite workspace_is_open() returning True")
            else:
                logger.info("No workspace currently open")
        except Exception as e:
            logger.info(f"Could not check workspace state: {e}")
            result['check_error'] = str(e)
        
        # Open target workspace if needed
        if action in ['check_and_switch', 'open_target']:
            try:
                logger.info(f"Opening target workspace: {target_workspace_path}")
                workspace = de.open_workspace(str(target_workspace_path))
                workspace.open()
                logger.info("✓ Target workspace opened successfully")
                result['workspace_managed'] = True
                result['current_workspace'] = str(target_workspace_path)
                result['message'] = 'Target workspace opened successfully'
            except Exception as e:
                logger.error(f"Failed to open target workspace: {e}")
                result['error'] = str(e)
        else:
            result['message'] = 'Workspace check completed'
        
        return result
        
    except Exception as e:
        logger.error(f"Workspace management failed: {e}")
        logger.error(traceback.format_exc())
        return {
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc(),
            'log_file': str(log_filename)
        }

def create_design_task(task_data):
    """Create design in existing library (Task Type B)"""
    logger, log_filename = setup_logging()
    
    try:
        logger.info("Starting design creation task")
        logger.info(f"Task data: {task_data}")
        
        import keysight.ads.de as de
        import keysight.ads.emtools as em
        from keysight.ads.de import db_uu as db
        
        workspace_dir = task_data['workspace_dir']
        library_name = task_data['library_name']
        cell_name = task_data['cell_name']
        geometry_data = task_data['geometry_data']
        
        # Additional configuration
        ref_library_name = task_data.get('ref_library_name', library_name)
        substrate_name = task_data.get('substrate_name', 'microstrip_substrate')
        layer_mapping = task_data.get('layer_mapping', {})
        
        logger.info(f"Creating design: {library_name}:{cell_name}")
        logger.info(f"Workspace: {workspace_dir}")
        logger.info(f"Reference library: {ref_library_name}")
        logger.info(f"Substrate: {substrate_name}")
        
        # Handle workspace verification - just get handle without opening
        verify_task = {
            'workspace_dir': workspace_dir,
            'action': 'verify_only'
        }
        try:
            verify_result = manage_workspace_conflict_task(verify_task)
            if verify_result.get('workspace_exists', False):
                workspace = verify_result['workspace_handle']
                logger.info(f"Got workspace handle: {workspace_dir}")
            else:
                logger.error(f"Workspace {workspace_dir} does not exist, please create it first")
                raise Exception(verify_result.get('message', 'Workspace does not exist'))
        except Exception as e:
            logger.error(f"Failed to verify workspace: {e}")
            raise
        
        # Open existing library
        library_path = Path(workspace_dir) / library_name
        library = workspace.open_library(library_name, str(library_path), de.LibraryMode.SHARED)
        
        # Create cell
        cell = library.create_cell(cell_name)
        
        # Get technology information
        tech_info = get_technology_info(library)
        layout_units = tech_info['units']
        
        # Create layout
        layout_design = db.create_layout(f"{library_name}:{cell_name}:layout")
        
        # Build layout from geometry data
        layers = geometry_data.get('layers', {})
        ports = geometry_data.get('ports', [])
        metadata = geometry_data.get('metadata', {})
        
        # Use um as base unit from metadata
        pixel_size_um = metadata.get('pixel_size_um', 14.0)
        source_unit = 'um'
        
        # Convert from source units to layout units
        unit_converter = UnitConverter(source_unit, layout_units)
        
        # Create geometry with proper layer mapping
        for layer_name, polygons in layers.items():
            # Map layer name to ADS tech layer
            ads_layer_info = layer_mapping.get(layer_name, {})
            ads_layer_name = ads_layer_info.get('layer_name', 'cond')
            ads_layer_purpose = ads_layer_info.get('layer_purpose', 'drawing')
            
            # Get actual ADS layer
            try:
                ads_layer = db.LayerId.create_layer_id_from_library(library, 
                                                                  ads_layer_name, 
                                                                  ads_layer_purpose)
            except Exception as e:
                logger.warning(f"Layer {ads_layer_name}:{ads_layer_purpose} not found, using default")
                ads_layer = db.LayerId.create_layer_id_from_library(library, "cond", "drawing")
            
            # Create geometry
            for polygon in polygons:
                if polygon['type'] == 'rectangle':
                    # Convert units from source to target
                    x1 = unit_converter.convert(polygon['x1'])
                    y1 = unit_converter.convert(polygon['y1'])
                    x2 = unit_converter.convert(polygon['x2'])
                    y2 = unit_converter.convert(polygon['y2'])
                    
                    layout_design.add_rectangle(
                        ads_layer,
                        (x1, y1),
                        (x2, y2)
                    )
        
        # Create ports from geometry data
        for port in ports:
            port_name = port.get('name', 'P1')
            x_um = port.get('x', 0)
            y_um = port.get('y', 0)
            edge = port.get('edge', 'left')
            port_layer = port.get('layer', 'L1')
            
            # Convert units
            x = unit_converter.convert(x_um)
            y = unit_converter.convert(y_um)
            
            # Map port layer using the same layer mapping as geometry
            ads_layer_info = layer_mapping.get(port_layer, {})
            ads_layer_name = ads_layer_info.get('layer_name', 'cond')
            ads_layer_purpose = ads_layer_info.get('layer_purpose', 'drawing')
            
            try:
                port_ads_layer = db.LayerId.create_layer_id_from_library(library, 
                                                                       ads_layer_name, 
                                                                       ads_layer_purpose)
            except Exception as e:
                logger.warning(f"Port layer {ads_layer_name}:{ads_layer_purpose} not found, using default")
                port_ads_layer = db.LayerId.create_layer_id_from_library(library, "cond", "drawing")
            
            net = layout_design.find_or_add_net(port_name)
            term = layout_design.add_term(net, port_name)
            dot = layout_design.add_dot(port_ads_layer, (x, y))
            
            # Set port angle based on edge
            angles = {'left': 180.0, 'right': 0.0, 'bottom': 270.0, 'top': 90.0}
            angle = angles.get(edge, 0.0)
            
            layout_design.add_pin(term, dot, angle=angle)
        
        layout_design.save_design()
        
        # Try to create EM view
        em_view_created = False
        try:
            logger.info("Creating RFPro view")
            em.create_empro_view(
                (library_name, cell_name, "rfpro_view"),
                "rfpro",
                (library_name, cell_name, "layout"),
                (ref_library_name, substrate_name)
            )
            em_view_created = True
            logger.info("RFPro view created successfully")
        except Exception as em_error:
            logger.warning(f"Could not create RFPro view: {em_error}")
            logger.info("Layout view created successfully (EM view skipped)")
        
        workspace.close()
        
        logger.info("Design creation completed successfully")
        
        return {
            'success': True,
            'library_name': library_name,
            'cell_name': cell_name,
            'layout_view': 'layout',
            'em_view': 'rfpro_view' if em_view_created else None,
            'substrate_name': substrate_name,
            'message': 'Design created successfully',
            'em_view_created': em_view_created,
            'log_file': str(log_filename)
        }
        
    except Exception as e:
        logger.error(f"Design creation failed: {e}")
        logger.error(traceback.format_exc())
        return {
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc(),
            'log_file': str(log_filename)
        }

def run_em_simulation_only_task(task_data):
    """Run EM simulation for specific design (Task Type C)"""
    logger = logging.getLogger('ads_parallel_worker')
    
    try:
        # Import required modules for EMPro environment
        import keysight.edatoolbox.multi_python as multi_python
        import empro
        import empro.toolkit.analysis as empro_analysis
        import keysight.edatoolbox.xxpro as xxpro
        import keysight.edatoolbox.ads as ads
        
        # Extract parameters
        workspace_dir = task_data['workspace_dir']
        library_name = task_data['library_name']
        cell_name = task_data['cell_name']
        em_view_name = task_data.get('em_view_name', 'rfpro_view')
        frequency_config = task_data.get('frequency_config', {})
        export_config = task_data.get('export_config', {})

        # Load workspace and design using xxpro
        logger.info(f"Opening workspace: {workspace_dir}")
        xxpro.use_workspace(workspace_dir)
        pro_lcv = ads.LibraryCellView(library=library_name, cell=cell_name, view=em_view_name)
        xxpro.load_pro_view(pro_lcv)
        
        project = empro.activeProject
        project.saveActiveProject()
        
        # Clear existing analyses
        project.analyses.clear()
        
        # Create analysis
        analysis = empro.analysis.Analysis()
        analysis.name = f'{cell_name}_EM_Analysis'
        analysis.analysisType = empro.analysis.Analysis.EMFUAnalysisType
        

         # Configure ports
        portList = analysis.ports
        
        # Extract port names from RFPro layout view
        port_names = extract_port_names_from_rfpro()
        
        for i, port_name in enumerate(port_names, 1):
            plus_pins = [port_name]
            minus_pins = ['Reference Pin On Cover']
            
            port = empro_analysis.createPortFromPins(plus_pins, minus_pins)
            port.name = port_name
            port.referenceImpedance = empro.core.Expression(50.0)
            port.feedType = 'Auto'
            portList.append(port)
        
        # Configure simulation settings
        options = analysis.simulationSettings

        # Configure frequency plans
        options = analysis.simulationSettings
        configure_frequency_plans(options, frequency_config)
        
        # Add analysis and run
        project.analyses.append(analysis)
        project.saveActiveProject()
        
        # Run simulation
        active_analysis = project.analyses[-1]
        empro_analysis.runAnalysis(
            active_analysis,
            waitForConfirmation=False,
            saveProject=True,
            reuseExistingIfPossible=False
        )
        
        # Start simulation queue
        project.simulations.isQueueHeld = False
        active_simulation = project.simulations[-1]
        empro.toolkit.simulation.wait(active_simulation)
        
        # Export results
        export_results = {}
        if export_config:
            export_path = Path(export_config.get('export_path', Path(workspace_dir) / 'results'))
            export_path.mkdir(parents=True, exist_ok=True)
            
            results = empro.analysis.CircuitResults(active_analysis)
            if export_config.get('export_touchstone'):
                touchstone_file = export_path / f"{cell_name}.s2p"
                results.write(str(touchstone_file), "touchstone", 6)
                logger.info(f"Exported touchstone file: {touchstone_file}")
                export_results['touchstone'] = str(touchstone_file)
            
            if export_config.get('export_dataset'):
                dataset_file = export_path / f"{cell_name}_results.ds"
                results.write(str(dataset_file), "ads_dataset", 8)
                logger.info(f"Exported dataset file: {dataset_file}")
                export_results['dataset'] = str(dataset_file)
            
            if export_config.get('export_csv'):
                csv_file = export_path / f"{cell_name}_results.csv"
                # 使用通用的 export_s_parameters_csv 函数导出所有 S 参数
                export_s_parameters_csv(results, str(csv_file))
                logger.info(f"Exported CSV file: {csv_file}")
                export_results['csv'] = str(csv_file)
        
        return {
            'success': True,
            'message': 'Simulation completed successfully',
            'results_path': str(export_path) if export_config else str(Path(workspace_dir) / 'results'),
            'export_results': export_results
        }
        
    except Exception as e:
        error_msg = f"Simulation failed: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        return {
            'success': False,
            'message': error_msg
        }

# Import utility functions from original worker
# These functions are copied from the original subprocess_worker.py
class UnitConverter:
    """Handle unit conversions for layout dimensions with comprehensive unit support"""
    
    UNIT_ALIASES = {
        'um': ['um', 'micron', 'microns', 'µm', 'μm'],
        'mm': ['mm', 'millimeter', 'millimeters', 'millimetre', 'millimetres'],
        'meter': ['m', 'meter', 'meters', 'metre', 'metres'],
        'mil': ['mil', 'mils', 'thou', 'thous'],
        'inch': ['in', 'inch', 'inches']
    }
    
    TO_UM = {
        'um': 1.0, 'micron': 1.0, 'microns': 1.0, 'µm': 1.0, 'μm': 1.0,
        'mm': 1000.0, 'millimeter': 1000.0, 'millimeters': 1000.0,
        'millimetre': 1000.0, 'millimetres': 1000.0,
        'm': 1000000.0, 'meter': 1000000.0, 'meters': 1000000.0,
        'metre': 1000000.0, 'metres': 1000000.0,
        'mil': 25.4, 'mils': 25.4, 'thou': 25.4, 'thous': 25.4,
        'in': 25400.0, 'inch': 25400.0, 'inches': 25400.0
    }
    
    def __init__(self, source_unit, target_unit):
        self.source_unit = self._normalize_unit(source_unit)
        self.target_unit = self._normalize_unit(target_unit)
    
    def _normalize_unit(self, unit_str):
        """Normalize any unit string to standard format"""
        if not unit_str:
            return 'mm'
        
        unit_str = str(unit_str).strip().lower()
        
        # Direct match
        if unit_str in self.TO_UM:
            return unit_str
        
        # Check aliases
        for standard_unit, aliases in self.UNIT_ALIASES.items():
            if unit_str in [alias.lower() for alias in aliases]:
                return standard_unit
        
        # Try partial match
        for standard_unit in self.TO_UM:
            if unit_str in standard_unit or standard_unit in unit_str:
                return standard_unit
        
        # Default fallback
        print(f"Warning: Unknown unit '{unit_str}', using 'mm' as fallback")
        return 'mm'
    
    def convert(self, value):
        """Convert value from source unit to target unit"""
        if self.source_unit == self.target_unit:
            return value
        
        value_um = value * self.TO_UM.get(self.source_unit, 1000.0)
        target_factor = self.TO_UM.get(self.target_unit, 1000.0)
        
        if target_factor == 0:
            return value
        
        return value_um / target_factor

def get_technology_info(library):
    """Get technology information including units and available layers"""
    try:
        if not library.has_tech:
            return {
                'units': 'mm',
                'dbu_per_unit': 10000,
                'layers': [{'layer_name': 'cond', 'layer_purpose': 'drawing', 'layer_number': 1, 'purpose_number': 0, 'process_role': 'conductor', 'is_physical': True, 'is_derived': False}],
                'num_layers': 1,
                'error': 'Library has no technology database'
            }
        
        tech_db = library.tech
        
        layout_units = tech_db.user_units.lower() if tech_db.user_units else 'mm'
        schematic_units = tech_db.user_units_sch.lower() if tech_db.user_units_sch else layout_units
        dbu_per_layout_unit = tech_db.dbu_per_uu if hasattr(tech_db, 'dbu_per_uu') else 1000
        
        layers = []
        
        try:
            all_layer_numbers = tech_db.layer_numbers(local=False)
        except:
            all_layer_numbers = tech_db.layer_numbers()
        
        for layer_num in all_layer_numbers:
            try:
                layer = tech_db.layer(layer_num, local=False)
                if layer:
                    try:
                        all_purpose_numbers = tech_db.purpose_numbers(local=False)
                    except:
                        all_purpose_numbers = tech_db.purpose_numbers()
                    
                    for purpose_num in all_purpose_numbers:
                        try:
                            purpose = tech_db.purpose(purpose_num, local=False)
                            if purpose:
                                layers.append({
                                    'layer_name': layer.name,
                                    'layer_purpose': purpose.name,
                                    'layer_number': layer.number,
                                    'purpose_number': purpose.number,
                                    'process_role': layer.process_role.str,
                                    'is_physical': hasattr(layer, 'is_physical') and layer.is_physical,
                                    'is_derived': hasattr(layer, 'is_derived') and layer.is_derived
                                })
                        except Exception as e:
                            layers.append({
                                'layer_name': layer.name,
                                'layer_purpose': f'purpose_{purpose_num}',
                                'layer_number': layer.number,
                                'purpose_number': purpose_num,
                                'process_role': str(layer.process_role),
                                'is_physical': True,
                                'is_derived': False
                            })
            except Exception as e:
                continue
        
        if not layers:
            layers = [
                {'layer_name': 'cond', 'layer_purpose': 'drawing', 'layer_number': 1, 'purpose_number': 0, 'process_role': 'conductor', 'is_physical': True, 'is_derived': False},
                {'layer_name': 'via', 'layer_purpose': 'drawing', 'layer_number': 2, 'purpose_number': 0, 'process_role': 'conductor_via', 'is_physical': True, 'is_derived': False},
                {'layer_name': 'ground', 'layer_purpose': 'drawing', 'layer_number': 3, 'purpose_number': 0, 'process_role': 'conductor', 'is_physical': True, 'is_derived': False}
            ]
        
        return {
            'units': layout_units,
            'schematic_units': schematic_units,
            'dbu_per_layout_unit': dbu_per_layout_unit,
            'dbu_per_schematic_unit': 1000,
            'layers': layers,
            'num_layers': len(layers),
            'referenced_libraries': tech_db.referenced_lib_names if hasattr(tech_db, 'referenced_lib_names') else []
        }
    except Exception as e:
        return {
            'units': 'mm',
            'schematic_units': 'mm',
            'dbu_per_layout_unit': 10000,
            'dbu_per_schematic_unit': 1000,
            'layers': [
                {'layer_name': 'cond', 'layer_purpose': 'drawing', 'layer_number': 1, 'purpose_number': 0, 'process_role': 'conductor', 'is_physical': True, 'is_derived': False},
                {'layer_name': 'via', 'layer_purpose': 'drawing', 'layer_number': 2, 'purpose_number': 0, 'process_role': 'conductor_via', 'is_physical': True, 'is_derived': False},
                {'layer_name': 'ground', 'layer_purpose': 'drawing', 'layer_number': 3, 'purpose_number': 0, 'process_role': 'conductor', 'is_physical': True, 'is_derived': False}
            ],
            'num_layers': 3,
            'error': str(e)
        }

def extract_port_names_from_rfpro():
    """Extract port names from RFPro layout view using EMPro API"""
    try:
        import empro
        import empro.layout_wrapper
        
        layout_index = 0
        layout = empro.activeProject.geometry[layout_index]
        layout_obj = empro.layout_wrapper.LayoutWrapper(layout)
        top_level_pins = layout_obj.topLevelPins
        
        port_names = []
        for pin in top_level_pins:
            pin_name = pin.name
            if pin_name != "Reference Pin On Cover" and not pin_name.startswith("Reference"):
                port_names.append(pin_name)
        
        return port_names
        
    except Exception as e:
        print(f"Warning: Could not extract port names from layout: {e}")
        # Return default port names as fallback
        return ['P1', 'P2']

def configure_frequency_plans(options, frequency_config):
    """配置多个频率计划"""
    import empro  # 添加本地导入

    frequencyPlanList = options.femFrequencyPlanList()
    frequencyPlanList.clear()
    
    # 设置全局频率计划类型
    frequencyPlanList._frequencyPlanType = frequency_config.get('global_frequency_plan_type', 'Interpolating_AllFields')

    
    # 创建各个频率计划
    for plan_config in frequency_config.get('frequency_plans', []):
        plan = empro.simulation.FrequencyPlan()
        plan.computeType = plan_config.get('compute_type', 'Simulated')
        plan.sweepType = plan_config.get('sweep_type', 'Adaptive')
        plan.nearFieldType = plan_config.get('near_field_type', 'NoNearFields')
        plan.farFieldType = plan_config.get('far_field_type', 'NoFarFields')
        plan.startFrequency = empro.core.Expression(plan_config.get('start_frequency', '0 Hz'))
        plan.stopFrequency = empro.core.Expression(plan_config.get('stop_frequency', '10 GHz'))
        plan.numberOfFrequencyPoints = plan_config.get('number_of_points', 201)
        plan.samplePointsLimit = plan_config.get('sample_points_limit', 300)
        plan.pointsPerDecade = plan_config.get('points_per_decade', 5)
        frequencyPlanList.append(plan)
    
    # 设置全局参数
    options.nearFieldsSaveFor = frequency_config.get('near_fields_save_for', 'AsDefinedByFrequencyPlans')
    options.farFieldsSaveFor = frequency_config.get('far_fields_save_for', 'AsDefinedByFrequencyPlans')
    options.farFieldAngularResolution = empro.core.Expression(frequency_config.get('far_field_angular_resolution', '5 deg'))
    options.adaptiveFpMaxSamples = frequency_config.get('adaptive_fp_max_samples', 200)
    options.adaptiveFpSaveFieldsFor = frequency_config.get('adaptive_fp_save_fields_for', 'AllFrequencies')

    # RFPro/Momentum settings
    options.setPresetByName('Momentum RF')
    
    # Matrix solver
    momMatrixSolver = options.momMatrixSolver
    momMatrixSolver.solveMatrixType = 'DirectCompressed'
    
    # Mesh settings
    momMeshSettings = options.momMeshSettings
    momMeshSettings.meshGranularity = empro.core.Expression('50 cpw')
    momMeshSettings.edgeMesh = 'Automatic'
    
    # Resource settings
    resourceSettings = empro.simulation.LocalResourceSettings()
    resourceSettings.numberOfWorkers = 1
    resourceSettings.numberOfThreads = 0
    options.resourceSettings = resourceSettings

def export_s_parameters_csv(results, filename):
    """Export S-parameters to CSV file"""
    import csv
    import math
    
    num_ports = results.numberOfPorts()
    frequencies = list(results.frequencies())
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        
        header = ['Frequency_Hz']
        for i in range(num_ports):
            for j in range(num_ports):
                header.extend([f"S{i+1}{j+1}_mag_db", f"S{i+1}{j+1}_phase_deg"])
        writer.writerow(header)
        
        for freq_idx, freq in enumerate(frequencies):
            row = [freq]
            for i in range(num_ports):
                for j in range(num_ports):
                    mag = results.Src(i, j, "ComplexMagnitude")[freq_idx]
                    phase = results.Src(i, j, "Phase")[freq_idx]
                    mag_db = 20 * math.log10(max(float(mag), 1e-12))
                    phase_deg = math.degrees(float(phase))
                    row.extend([mag_db, phase_deg])
            writer.writerow(row)

# Import original functions for backward compatibility
def create_ads_design_task(task_data):
    """Original complete design creation workflow (preserved)"""
    # This would import the original function from subprocess_worker.py
    # For now, we'll implement a simplified version that calls the new functions
    logger, log_filename = setup_logging()
    
    try:
        logger.info("Running original complete workflow")
        
        # Step 1: Create workspace and library
        workspace_lib_result = create_workspace_lib_task(task_data)
        if not workspace_lib_result['success']:
            return workspace_lib_result
        
        # Step 2: Create design
        design_task = {
            'workspace_dir': task_data['workspace_dir'],
            'library_name': task_data['library_name'],
            'cell_name': task_data['cell_name'],
            'geometry_data': task_data['geometry_data'],
            'ref_library_name': workspace_lib_result.get('ref_library_name', task_data['library_name']),
            'substrate_name': task_data.get('substrate_name', 'microstrip_substrate'),
            'layer_mapping': task_data.get('layer_mapping', {})
        }
        design_result = create_design_task(design_task)
        
        return design_result
        
    except Exception as e:
        logger.error(f"Original workflow failed: {e}")
        return {
            'success': False,
            'error': str(e),
            'log_file': str(log_filename)
        }

def run_em_simulation_task(task_data):
    """Original EM simulation workflow (preserved)"""
    # For now, we'll redirect to the new modified version
    return run_em_simulation_only_task(task_data)

def main():
    """Main entry point for enhanced subprocess worker"""
    # Setup logging first with INFO level for console
    logger, log_filename = setup_logging(console_level=logging.INFO)
    
    if len(sys.argv) != 2:
        logger.error("Usage: python subprocess_worker_parallel.py <task_json_file>")
        sys.exit(1)
    
    try:
        # Parse task JSON from file
        task_file = sys.argv[1]
        logger.debug(f"Parsing task file: {task_file}")
        with open(task_file, 'r', encoding='utf-8') as f:
            task_data = json.load(f)
        
        # Setup environment
        if not setup_ads_environment():
            result = {
                'success': False,
                'error': 'Failed to setup ADS environment'
            }
            logger.error("Environment setup failed")
            print("JSON_RESULT:" + json.dumps(result))
            sys.exit(1)
        
        # Execute task based on type
        task_type = task_data.get('task_type')
        logger.debug(f"Executing task type: {task_type}")
        
        # Map task types to product contexts.
        # The worker is launched through one ADS-bundled Python interpreter,
        # then keysight.edatoolbox.multi_python switches between ADS and
        # RFPro/EMPro execution contexts for different task classes.
        ads_tasks = ['create_workspace_lib', 'create_design_only', 'create_ads_design', 'manage_workspace_conflict']
        empro_tasks = ['run_em_simulation_only', 'run_em_simulation']
        
        if task_type in ads_tasks:
            # Use ADS context for design-related tasks
            with multi_python.ads_context() as ads_ctx:
                if task_type == 'create_workspace_lib':
                    result = ads_ctx.call(create_workspace_lib_task, args=[task_data])
                elif task_type == 'create_design_only':
                    result = ads_ctx.call(create_design_task, args=[task_data])
                elif task_type == 'create_ads_design':
                    result = ads_ctx.call(create_ads_design_task, args=[task_data])
                elif task_type == 'manage_workspace_conflict':
                    result = ads_ctx.call(manage_workspace_conflict_task, args=[task_data])
                    
        elif task_type in empro_tasks:
            # Use EMPro context for simulation tasks
            with multi_python.xxpro_context() as empro_ctx:
                if task_type == 'run_em_simulation_only':
                    result = empro_ctx.call(run_em_simulation_only_task, args=[task_data])
                elif task_type == 'run_em_simulation':
                    result = empro_ctx.call(run_em_simulation_task, args=[task_data])
                    
        else:
            logger.error(f"Unknown task type: {task_type}")
            result = {
                'success': False,
                'error': f'Unknown task type: {task_type}'
            }
        
        # Output result as JSON
        logger.debug(f"Task completed with result: {result.get('success', False)}")
        print("JSON_RESULT:" + json.dumps(result))
        
    except Exception as e:
        logger.error(f"Task execution failed: {e}")
        logger.error(traceback.format_exc())
        error_result = {
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }
        print("JSON_RESULT:" + json.dumps(error_result))
        sys.exit(1)

if __name__ == "__main__":
    main()
