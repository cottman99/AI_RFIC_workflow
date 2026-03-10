#!/usr/bin/env python3
"""
Subprocess Worker for ADS/EMPro Operations

This script runs within ADS/EMPro Python environments to execute specific tasks.
It receives JSON-formatted commands and returns JSON-formatted results.

Usage: python subprocess_worker.py <task_json>
"""

import sys
import json
import traceback
import os
from pathlib import Path

import logging
import datetime
import tempfile

def setup_logging():
    """Setup comprehensive logging"""
    log_filename = Path(tempfile.gettempdir()) / f"ads_subprocess_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    return logging.getLogger('ads_worker'), log_filename

def setup_ads_environment():
    """Setup ADS Python environment"""
    logger = logging.getLogger('ads_worker')
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
            
        logger.info(f"ADS Base Path: {ads_base}")
        
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
            
        logger.info("ADS environment setup successful")
        return True
    except Exception as e:
        logger.error(f"Failed to setup ADS environment: {e}")
        return False

def create_ads_design_task(task_data):
    """Create ADS design from JSON data using PDK technology"""
    logger, log_filename = setup_logging()
    
    try:
        logger.info("Starting ADS design creation task")
        logger.info(f"Task data: {task_data}")
        
        import keysight.ads.de as de
        import keysight.ads.emtools as em
        from keysight.ads.de import db_uu as db
        import numpy as np
        
        workspace_dir = task_data['workspace_dir']
        library_name = task_data['library_name']
        cell_name = task_data['cell_name']
        geometry_data = task_data['geometry_data']
        
        # PDK configuration
        pdk_config = task_data.get('pdk_config', {})
        use_pdk = pdk_config.get('use_pdk', False)
        ref_lib_loc = pdk_config.get('ref_lib_loc', '')
        pdk_loc = pdk_config.get('pdk_loc', '')
        pdk_tech_loc = pdk_config.get('pdk_tech_loc', '')
        substrate_name = pdk_config.get('substrate_name', '')
        ref_library_name = pdk_config.get('ref_library_name', '')
        
        logger.info(f"Creating design: {library_name}:{cell_name}")
        logger.info(f"Workspace: {workspace_dir}")
        logger.info(f"Using PDK: {use_pdk}")
        if use_pdk:
            logger.info(f"PDK Location: {pdk_loc}")
            logger.info(f"PDK Tech Location: {pdk_tech_loc}")
            logger.info(f"Substrate: {substrate_name}")
        else:
            logger.info(f"Reference Library: {ref_lib_loc}")
            logger.info(f"Substrate: {substrate_name}")
        
        # Create workspace
        workspace_path = Path(workspace_dir)
        library_path = workspace_path / library_name
        
        # Clean existing workspace if it exists
        if workspace_path.exists():
            import shutil
            shutil.rmtree(workspace_path)
            
        workspace = de.create_workspace(str(workspace_path))
        workspace.open()
        
        # Create target library
        de.create_new_library(library_name, str(library_path))
        workspace.add_library(library_name, str(library_path), de.LibraryMode.SHARED)
        library = workspace.open_library(library_name, str(library_path), de.LibraryMode.SHARED)
        
        # Setup technology from PDK or reference library
        library.setup_schematic_tech()
        
        # # Ensure layout tech is properly configured
        # try:
        #     library.create_layout_tech_std_ads("millimeter", 10000, False)
        # except Exception as e:
        #     logger.warning(f"Could not create standard layout tech: {e}")
        #     # Continue with existing tech or PDK tech
        
        if use_pdk:
            # Add PDK libraries with actual directory names - TECH FIRST!
            if pdk_loc and Path(pdk_loc).exists() and pdk_tech_loc and Path(pdk_tech_loc).exists():
                # Add tech library first (critical for PDK references)
                tech_lib_name = Path(pdk_tech_loc).name
                workspace.add_library(tech_lib_name, str(pdk_tech_loc), de.LibraryMode.READ_ONLY)
                ref_library_name = tech_lib_name
                
                # Then add main PDK library
                pdk_lib_name = Path(pdk_loc).name
                workspace.add_library(pdk_lib_name, str(pdk_loc), de.LibraryMode.READ_ONLY)
                pdk_library = workspace.open_library(pdk_lib_name, str(pdk_loc), de.LibraryMode.READ_ONLY)
                
            else:
                # Use relative path from ADS installation
                ads_base = Path(os.environ.get("HPEESOF_DIR", ""))
                pdk_full_path = ads_base / pdk_loc
                pdk_tech_full_path = ads_base / pdk_tech_loc
                
                # Add tech library first
                if pdk_tech_full_path.exists():
                    tech_lib_name = pdk_tech_full_path.name
                    workspace.add_library(tech_lib_name, str(pdk_tech_full_path), de.LibraryMode.READ_ONLY)
                    ref_library_name = tech_lib_name
                
                # Then add main PDK library
                if pdk_full_path.exists():
                    pdk_lib_name = pdk_full_path.name
                    workspace.add_library(pdk_lib_name, str(pdk_full_path), de.LibraryMode.READ_ONLY)
                    pdk_library = workspace.open_library(pdk_lib_name, str(pdk_full_path), de.LibraryMode.READ_ONLY)
                    
                else:
                    raise RuntimeError(f"PDK not found at: {pdk_full_path}")
            
            # Create layout technology from PDK
            library.create_layout_tech_from_pdk(pdk_library, copy_tech=False)
            
        else:
            # Use reference library
            if ref_lib_loc and Path(ref_lib_loc).exists():
                ref_lib_name = Path(ref_lib_loc).name
                workspace.add_library(ref_lib_name, str(ref_lib_loc), de.LibraryMode.READ_ONLY)
                ref_library = workspace.open_library(ref_lib_name, str(ref_lib_loc), de.LibraryMode.READ_ONLY)
                ref_library_name = ref_lib_name
            else:
                # Use relative path from ADS installation
                ads_base = Path(os.environ.get("HPEESOF_DIR", ""))
                ref_lib_full_path = ads_base / ref_lib_loc
                ref_lib_name = ref_lib_full_path.name
                
                if ref_lib_full_path.exists():
                    workspace.add_library(ref_lib_name, str(ref_lib_full_path), de.LibraryMode.READ_ONLY)
                    ref_library = workspace.open_library(ref_lib_name, str(ref_lib_full_path), de.LibraryMode.READ_ONLY)
                    ref_library_name = ref_lib_name
                else:
                    raise RuntimeError(f"Reference library not found at: {ref_lib_full_path}")
            
            # Create layout technology from reference library
            library.create_layout_tech_from_library(ref_library, copy_tech=False)
        
        # Create cell
        cell = library.create_cell(cell_name)
        
        # Get technology units and layer mapping
        tech_info = get_technology_info(library)
        layout_units = tech_info['units']
        layer_mapping = task_data.get('layer_mapping', {})
        
        # Create layout
        layout_design = db.create_layout(f"{library_name}:{cell_name}:layout")
        
        # Build layout from geometry data (pre-processed)
        geometry_data = task_data.get('geometry_data', {})
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
        
        # Create ports from geometry data - use same layer mapping as geometry
        for port in ports:
            port_name = port.get('name', 'P1')
            x_um = port.get('x', 0)  # Position in um
            y_um = port.get('y', 0)
            edge = port.get('edge', 'left')
            port_layer = port.get('layer', 'L1')  # Port's associated layer
            
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
        
        # Try to create EM view using reference library and selected substrate
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
            em_view_created = False
            logger.info("Layout view created successfully (EM view skipped)")
        
        workspace.close()
        
        logger.info("ADS design creation completed successfully")
        
        return {
            'success': True,
            'layout_view': 'layout',
            'em_view': 'rfpro_view' if em_view_created else None,
            'substrate_name': substrate_name,
            'message': 'ADS design created successfully',
            'em_view_created': em_view_created,
            'log_file': str(log_filename)
        }
        
    except Exception as e:
        logger.error(f"ADS design creation failed: {e}")
        logger.error(traceback.format_exc())
        return {
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc(),
            'log_file': str(log_filename)
        }

def extract_port_names_from_rfpro():
    """Extract port names from RFPro layout view using EMPro API"""
    try:
        import empro
        import empro.layout_wrapper
        
        # Get layout object from active project
        layout_index = 0  # Assume first layout is the target
        layout = empro.activeProject.geometry[layout_index]
        
        # Wrap layout for easier pin access
        layout_obj = empro.layout_wrapper.LayoutWrapper(layout)
        
        # Get all top-level pins
        top_level_pins = layout_obj.topLevelPins
        
        # Extract pin names, excluding reference pins
        port_names = []
        for pin in top_level_pins:
            pin_name = pin.name
            # Exclude reference pins (like "Reference Pin On Cover")
            if pin_name != "Reference Pin On Cover" and not pin_name.startswith("Reference"):
                port_names.append(pin_name)
        
        return port_names
        
    except Exception as e:
        # Fallback to default port names if extraction fails
        print(f"Warning: Could not extract port names from layout: {e}")
        return ["P1", "P2"]

def run_em_simulation_task(task_data):
    """Run EM simulation with automatic data export"""
    try:
        import keysight.edatoolbox.multi_python as multi_python
        import empro
        import empro.toolkit.analysis as empro_analysis
        import keysight.edatoolbox.xxpro as xxpro
        import keysight.edatoolbox.ads as ads
        import math
        
        workspace_dir = task_data['workspace_dir']
        library_name = task_data['library_name']
        cell_name = task_data['cell_name']
        em_view_name = task_data['em_view_name']
        
        # Export configuration
        export_config = task_data.get('export_config', {})
        export_path = export_config.get('export_path', '')
        export_types = export_config.get('export_types', ['touchstone'])
        path_mode = export_config.get('path_mode', 'absolute')  # 'absolute' or 'relative'
        
        # Load workspace and project
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
        
        # Frequency plan
        frequencyPlanList = options.femFrequencyPlanList()
        frequencyPlanList.clear()
        
        plan = empro.simulation.FrequencyPlan()
        plan.type = 'Adaptive'
        plan.startFrequency = empro.core.Expression('0.1 GHz')
        plan.stopFrequency = empro.core.Expression('20 GHz')
        plan.numberOfFrequencyPoints = 200
        plan.samplePointsLimit = 200
        plan.pointsPerDecade = 5
        frequencyPlanList.append(plan)
        
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
        
        # Process and export results automatically
        export_results = {}
        
        if export_path and export_types:
            # Determine final export path
            if path_mode == 'relative':
                # Relative to library path
                lib_path = Path(workspace_dir) / library_name
                final_export_path = lib_path / export_path
            else:
                # Absolute path
                final_export_path = Path(export_path)
            
            final_export_path.mkdir(parents=True, exist_ok=True)
            
            # Get results using CircuitResults
            results = empro.analysis.CircuitResults(active_analysis)
            num_ports = results.numberOfPorts()
            
            # Export based on selected types
            if 'touchstone' in export_types:
                touchstone_file = final_export_path / f"{cell_name}.s{num_ports}p"
                results.write(str(touchstone_file), "touchstone", 6)
                export_results['touchstone'] = str(touchstone_file) if touchstone_file.exists() else None
            
            if 'dataset' in export_types:
                dataset_file = final_export_path / f"{cell_name}_results.ds"
                results.write(str(dataset_file), "ads_dataset", 8)
                export_results['dataset'] = str(dataset_file) if dataset_file.exists() else None
            
            if 'csv' in export_types:
                csv_file = final_export_path / f"{cell_name}_results.csv"
                export_s_parameters_csv(results, str(csv_file))
                export_results['csv'] = str(csv_file) if csv_file.exists() else None
        
        return {
            'success': True,
            'analysis_complete': True,
            'results_path': str(Path(workspace_dir) / 'results'),
            'export_results': export_results,
            'message': 'EM simulation completed with automatic data export'
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }

class UnitConverter:
    """Handle unit conversions for layout dimensions with comprehensive unit support"""
    
    # Comprehensive unit mapping including all ADS variations
    UNIT_ALIASES = {
        'um': ['um', 'micron', 'microns', 'µm', 'μm'],
        'mm': ['mm', 'millimeter', 'millimeters', 'millimetre', 'millimetres'],
        'meter': ['m', 'meter', 'meters', 'metre', 'metres'],
        'mil': ['mil', 'mils', 'thou', 'thous'],
        'inch': ['in', 'inch', 'inches']
    }
    
    # Conversion factors to micrometers (base unit)
    TO_UM = {
        'um': 1.0,
        'micron': 1.0,
        'microns': 1.0,
        'µm': 1.0,
        'μm': 1.0,
        'mm': 1000.0,
        'millimeter': 1000.0,
        'millimeters': 1000.0,
        'millimetre': 1000.0,
        'millimetres': 1000.0,
        'm': 1000000.0,
        'meter': 1000000.0,
        'meters': 1000000.0,
        'metre': 1000000.0,
        'metres': 1000000.0,
        'mil': 25.4,
        'mils': 25.4,
        'thou': 25.4,
        'thous': 25.4,
        'in': 25400.0,
        'inch': 25400.0,
        'inches': 25400.0
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
        
        # Try partial match (e.g., "micron" matches "microns")
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
        
        # Convert to micrometers first, then to target unit
        value_um = value * self.TO_UM.get(self.source_unit, 1000.0)
        target_factor = self.TO_UM.get(self.target_unit, 1000.0)
        
        if target_factor == 0:
            return value  # Avoid division by zero
        
        return value_um / target_factor

def get_technology_info(library):
    """Get technology information including units and available layers using correct ADS API"""
    try:
        # Check if library has technology
        if not library.has_tech:
            return {
                'units': 'mm',
                'dbu_per_unit': 10000,
                'layers': [{'layer_name': 'cond', 'layer_purpose': 'drawing', 'layer_number': 1, 'purpose_number': 0, 'process_role': 'conductor', 'is_physical': True, 'is_derived': False}],
                'num_layers': 1,
                'error': 'Library has no technology database'
            }
        
        # Get technology database using correct API
        tech_db = library.tech
        
        # Get units information - handle cases where schematic units might be None
        layout_units = tech_db.user_units.lower() if tech_db.user_units else 'mm'
        schematic_units = tech_db.user_units_sch.lower() if tech_db.user_units_sch else layout_units
        dbu_per_layout_unit = tech_db.dbu_per_uu if hasattr(tech_db, 'dbu_per_uu') else 1000
        dbu_per_schematic_unit = tech_db.dbu_per_uu_sch if hasattr(tech_db, 'dbu_per_uu_sch') else 1000
        
        # Get all layers including referenced ones
        layers = []
        
        # Get all layer numbers (including referenced)
        try:
            all_layer_numbers = tech_db.layer_numbers(local=False)
        except:
            all_layer_numbers = tech_db.layer_numbers()
        
        for layer_num in all_layer_numbers:
            try:
                layer = tech_db.layer(layer_num, local=False)
                if layer:
                    # Get layer purposes
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
                            # Fallback for purpose
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
                # Skip problematic layers
                continue
        
        # If no layers found, add default ones
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
            'dbu_per_schematic_unit': dbu_per_schematic_unit,
            'layers': layers,
            'num_layers': len(layers),
            'referenced_libraries': tech_db.referenced_lib_names if hasattr(tech_db, 'referenced_lib_names') else []
        }
    except Exception as e:
        # Fallback to standard configuration
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

def find_substrate_files(library_path):
    """Find .subst files in library path"""
    substrate_files = []
    
    if not library_path or not Path(library_path).exists():
        return substrate_files
    
    try:
        # Search for .subst files
        for subst_file in Path(library_path).rglob("*.subst"):
            substrate_files.append({
                'name': subst_file.stem,
                'path': str(subst_file),
                'relative_path': str(subst_file.relative_to(library_path))
            })
    except Exception as e:
        pass
    
    return substrate_files

# Touchstone parsing moved to GUI module for better separation of concerns

def export_s_parameters_csv(results, filename):
    """Export S-parameters to CSV file"""
    import csv
    import math
    
    num_ports = results.numberOfPorts()
    frequencies = list(results.frequencies())
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        
        # Header
        header = ['Frequency_Hz']
        for i in range(num_ports):
            for j in range(num_ports):
                header.extend([f"S{i+1}{j+1}_mag_db", f"S{i+1}{j+1}_phase_deg"])
        writer.writerow(header)
        
        # Data rows
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

def main():
    import keysight.edatoolbox.multi_python as multi_python
    """Main entry point for subprocess worker"""
    if len(sys.argv) != 2:
        print("Usage: python subprocess_worker.py <task_json_file>")
        sys.exit(1)
    
    try:
        # Parse task JSON from file
        task_file = sys.argv[1]
        with open(task_file, 'r', encoding='utf-8') as f:
            task_data = json.load(f)
        
        # Setup environment
        if not setup_ads_environment():
            result = {
                'success': False,
                'error': 'Failed to setup ADS environment'
            }
            print("JSON_RESULT:" + json.dumps(result))
            sys.exit(1)
        
        # Execute task
        task_type = task_data.get('task_type')

        
        
        # One ADS-bundled Python interpreter is used to launch the worker.
        # multi_python then switches product contexts internally so that
        # design work runs under ADS context and simulation work runs under
        # RFPro/EMPro context.
        if task_type == 'create_ads_design':
            with multi_python.ads_context() as ads_ctx:
                result = ads_ctx.call(
                    create_ads_design_task,
                    args=[task_data]
                )
            # result = create_ads_design_task(task_data)
        elif task_type == 'run_em_simulation':
            with multi_python.xxpro_context() as empro_ctx:
                result = empro_ctx.call(
                    run_em_simulation_task,
                    args=[task_data]
                )

            # result = run_em_simulation_task(task_data)
        else:
            result = {
                'success': False,
                'error': f'Unknown task type: {task_type}'
            }
        
        # Output result as JSON
        print("JSON_RESULT:" + json.dumps(result))
        
    except Exception as e:
        error_result = {
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }
        print("JSON_RESULT:" + json.dumps(error_result))
        sys.exit(1)

if __name__ == "__main__":
    main()
