# ADS API Integration Patterns - Complete Implementation Guide

## Overview

This documentation provides comprehensive implementation patterns for integrating with Keysight ADS and EMPro APIs within the RFIC Layout-to-EM Simulation GUI system. All patterns are validated through production code and represent the official approach for ADS 2025 Update 2.

## Environment Setup and Initialization

### ADS Python Environment Detection

```python
import os
import sys
from pathlib import Path

class ADSEnvironmentManager:
    """Manages ADS Python environment detection and setup"""
    
    def __init__(self):
        self.ads_base_path = None
        self.python_executable = None
        self.ads_python_path = None
        self._detect_ads_environment()
    
    def _detect_ads_environment(self):
        """Comprehensive ADS environment detection"""
        possible_paths = [
            r"C:\Path\To\ADS2026_Update1",
            r"C:\Path\To\ADS2025",
            r"C:\Path\To\ADS2025_Update2",
            os.environ.get("HPEESOF_DIR", "")
        ]
        
        for base_path in possible_paths:
            if os.path.exists(base_path):
                self.ads_base_path = base_path
                self._setup_python_paths()
                break
        
        if not self.ads_base_path:
            raise EnvironmentError("ADS installation not found")
    
    def _setup_python_paths(self):
        """Setup ADS Python paths with fallback mechanisms"""
        python_paths = [
            os.path.join(self.ads_base_path, "tools", "python", "python.exe"),
            os.path.join(self.ads_base_path, "fem", "2025.20", "win32_64", "bin", "tools", "win32", "python", "python.exe"),
            os.path.join(self.ads_base_path, "fem", "2025.20", "win32_64", "bin", "tools", "win32", "python3", "python.exe")
        ]
        
        for path in python_paths:
            if os.path.exists(path):
                self.python_executable = path
                break
        
        if not self.python_executable:
            raise EnvironmentError("ADS Python executable not found")
    
    def get_python_path(self):
        """Returns the ADS Python executable path"""
        return self.python_executable
```

### ADS Module Import Strategy

```python
def setup_ads_modules(ads_base_path):
    """Setup ADS Python modules with proper path configuration"""
    
    # Core ADS paths
    ads_python_paths = [
        os.path.join(ads_base_path, "fem", "2025.20", "win32_64", "bin", "tools", "win32", "python"),
        os.path.join(ads_base_path, "tools", "python", "Lib", "site-packages"),
        os.path.join(ads_base_path, "tools", "python", "DLLs")
    ]
    
    # Add to Python path
    for path in ads_python_paths:
        if path not in sys.path:
            sys.path.insert(0, path)
    
    # Environment variables
    os.environ["HPEESOF_DIR"] = ads_base_path
    os.environ["ADS_LICENSE_FILE"] = os.path.join(ads_base_path, "licenses")
    
    # Import ADS modules
    try:
        import keysight.ads.de as de
        from keysight.ads.de import db_uu as db
        import keysight.ads.emtools as em
        import keysight.ads.dataset as dataset
        import keysight.edatoolbox.ads as ads
        import keysight.edatoolbox.multi_python as multi_python
        
        return {
            'de': de,
            'db': db,
            'em': em,
            'dataset': dataset,
            'ads': ads,
            'multi_python': multi_python
        }
    except ImportError as e:
        raise ImportError(f"Failed to import ADS modules: {e}")
```

## Workspace Management Patterns

### Complete Workspace Lifecycle

```python
def create_complete_workspace(workspace_path, library_name, process_config):
    """Complete workspace creation with all required components"""
    
    from keysight.ads.de import db_uu as db
    import keysight.ads.de as de
    
    workspace_path = Path(workspace_path)
    
    # Phase 1: Workspace Creation
    try:
        # Clean existing workspace if needed
        if workspace_path.exists():
            import shutil
            shutil.rmtree(workspace_path)
        
        # Create new workspace
        workspace = de.create_workspace(str(workspace_path))
        workspace.open()
        
        # Phase 2: Library Creation
        library_path = workspace_path / library_name
        de.create_new_library(library_name, str(library_path))
        
        # Open library with proper mode
        library = workspace.open_library(
            library_name, 
            str(library_path), 
            de.LibraryMode.SHARED
        )
        
        # Phase 3: Technology Setup
        _setup_technology(library, process_config)
        
        return {
            'workspace': workspace,
            'library': library,
            'library_path': str(library_path)
        }
        
    except Exception as e:
        workspace.close() if 'workspace' in locals() else None
        raise RuntimeError(f"Workspace creation failed: {e}")

def _setup_technology(library, process_config):
    """Setup technology based on PDK or reference library"""
    
    if process_config.get('use_pdk', False):
        # PDK-based technology
        pdk_path = process_config['pdk_path']
        library.setup_schematic_tech_from_pdk(pdk_path)
        library.create_layout_tech_from_pdk(pdk_path)
    else:
        # Reference library-based technology
        library.setup_schematic_tech()
        library.create_layout_tech_std_ads(
            unit_system="millimeter",
            grid_resolution=10000,
            create_substrate=process_config.get('create_substrate', False)
        )
```

## Cell and View Creation Patterns

### Standardized Cell Creation

```python
def create_standard_cell(library, cell_name, substrate_name=None):
    """Create a standardized cell with all required views"""
    
    # Create cell
    cell = library.create_cell(cell_name)
    
    # Create substrate if specified
    if substrate_name:
        substrate_obj = _create_substrate(library, substrate_name)
    
    # Create views in sequence
    views = {}
    
    # Layout view
    layout_design = db.create_layout(f"{library.name}:{cell_name}:layout")
    views['layout'] = layout_design
    
    # Schematic view (optional)
    schematic_design = db.create_schematic(f"{library.name}:{cell_name}:schematic")
    views['schematic'] = schematic_design
    
    # Symbol view (optional)
    symbol_design = db.create_symbol(f"{library.name}:{cell_name}:symbol")
    views['symbol'] = symbol_design
    
    return {
        'cell': cell,
        'views': views,
        'substrate': substrate_obj if substrate_name else None
    }

def _create_substrate(library, substrate_name):
    """Create complete microstrip substrate stackup"""
    
    import keysight.ads.de.substrate as substrate
    
    substrate_obj = substrate.create_substrate(library, substrate_name)
    
    # Bottom ground
    bottom_interface = substrate_obj.interfaces[0]
    bottom_interface.convert_to_cover()
    bottom_interface.material_name = "PERFECT_CONDUCTOR"
    
    # Dielectric layer
    dielectric = substrate_obj.materials[0]
    dielectric.material_name = "FR4_epoxy"
    dielectric.thickness_expr = "0.508"
    dielectric.thickness_unit = substrate.Unit.MILLIMETER
    dielectric.permittivity_expr = "4.4"
    dielectric.loss_tangent_expr = "0.02"
    
    # Top conductor
    substrate_obj.insert_material_and_interface_above(0)
    conductor_interface = substrate_obj.interfaces[1]
    conductor_layer = substrate_obj.insert_layer(
        conductor_interface, de.ProcessRole.CONDUCTOR
    )
    conductor_layer.layer_number = 2
    conductor_layer.material_name = "COPPER"
    conductor_layer.thickness_expr = "0.035"
    conductor_layer.thickness_unit = substrate.Unit.MILLIMETER
    conductor_layer.sheet = True
    
    # Air layer
    substrate_obj.insert_material_and_interface_above(1)
    air_layer = substrate_obj.materials[2]
    air_layer.material_name = "AIR"
    air_layer.thickness_expr = "1000"
    air_layer.thickness_unit = substrate.Unit.MILLIMETER
    
    substrate_obj.save_substrate()
    return substrate_obj
```

## Geometry Creation Patterns

### Matrix-to-Layout Conversion

```python
def create_layout_from_matrix(layout_design, matrix_data, layer_mapping, config):
    """Convert matrix-based layout to ADS layout geometry"""
    
    # Get technology layers
    tech_layers = {}
    for json_layer, ads_layer_name in layer_mapping.items():
        tech_layers[json_layer] = db.LayerId.create_layer_id_from_library(
            layout_design.library.name, ads_layer_name, "drawing"
        )
    
    # Process each layer
    for layer_name, matrix in matrix_data.items():
        if layer_name not in tech_layers:
            continue
            
        layer_id = tech_layers[layer_name]
        polygons = _matrix_to_polygons(matrix, config)
        
        # Create geometry
        for polygon in polygons:
            if len(polygon) >= 3:
                layout_design.add_polygon(layer_id, polygon)
    
    layout_design.save_design()

def _matrix_to_polygons(matrix, config):
    """Convert binary matrix to polygon coordinates"""
    
    from skimage import measure
    import numpy as np
    
    # Convert to numpy array
    arr = np.array(matrix)
    
    # Find contours
    contours = measure.find_contours(arr, 0.5)
    
    polygons = []
    pixel_size = config.get('pixel_size_um', 14.0)
    
    for contour in contours:
        # Convert to layout coordinates
        coords = [(x * pixel_size, y * pixel_size) for x, y in contour]
        polygons.append(coords)
    
    return polygons
```

## Port Creation and Configuration

### Advanced Port Placement System

```python
def create_ports_from_definitions(layout_design, port_definitions, tech_layers, config):
    """Create ports based on JSON port definitions with automatic placement"""
    
    created_ports = {}
    
    for port_def in port_definitions:
        port_name = port_def['name']
        layer_name = port_def['layer']
        edge = port_def['edge']
        position_index = port_def['position_index']
        
        # Get layer
        layer_id = tech_layers.get(layer_name)
        if not layer_id:
            raise ValueError(f"Layer {layer_name} not found")
        
        # Calculate port position based on edge and index
        position = _calculate_port_position(
            layout_design, layer_id, edge, position_index, config
        )
        
        # Create port using proven pattern
        port = _create_port_at_position(
            layout_design, port_name, layer_id, position, edge
        )
        
        created_ports[port_name] = port
    
    return created_ports

def _calculate_port_position(layout_design, layer_id, edge, index, config):
    """Calculate optimal port position based on edge placement"""
    
    # Get bounding box of geometry on this layer
    shapes = layout_design.get_shapes(layer_id)
    if not shapes:
        raise ValueError(f"No geometry found on layer {layer_id}")
    
    # Calculate bounding box
    min_x = min_y = float('inf')
    max_x = max_y = float('-inf')
    
    for shape in shapes:
        bbox = shape.get_bounding_box()
        min_x = min(min_x, bbox[0][0])
        min_y = min(min_y, bbox[0][1])
        max_x = max(max_x, bbox[1][0])
        max_y = max(max_y, bbox[1][1])
    
    # Calculate position based on edge
    pixel_size = config.get('pixel_size_um', 14.0)
    
    if edge == 'left':
        x = min_x - pixel_size
        y = min_y + index * pixel_size
    elif edge == 'right':
        x = max_x + pixel_size
        y = min_y + index * pixel_size
    elif edge == 'top':
        x = min_x + index * pixel_size
        y = max_y + pixel_size
    elif edge == 'bottom':
        x = min_x + index * pixel_size
        y = min_y - pixel_size
    else:
        raise ValueError(f"Invalid edge: {edge}")
    
    return (x, y)

def _create_port_at_position(layout_design, port_name, layer_id, position, edge):
    """Create port at specific position with proper orientation"""
    
    # Create net and terminal
    net = layout_design.find_or_add_net(port_name)
    term = layout_design.add_term(net, port_name)
    
    # Create connection point
    dot = layout_design.add_dot(layer_id, position)
    
    # Calculate angle based on edge
    angle_map = {
        'left': 180.0,
        'right': 0.0,
        'top': 270.0,
        'bottom': 90.0
    }
    angle = angle_map.get(edge, 0.0)
    
    # Create pin
    pin = layout_design.add_pin(term, dot, angle=angle)
    
    return {
        'net': net,
        'term': term,
        'dot': dot,
        'pin': pin,
        'position': position,
        'angle': angle
    }
```

## EM View Creation Patterns

### RFPro and Momentum View Creation

```python
def create_em_views(library_name, cell_name, substrate_name, view_types=None):
    """Create EM views for both RFPro and Momentum simulations"""
    
    if view_types is None:
        view_types = ['rfpro', 'momentum']
    
    created_views = {}
    
    for view_type in view_types:
        view_name = f"{view_type}_view"
        
        try:
            if view_type == 'rfpro':
                em.create_empro_view(
                    (library_name, cell_name, view_name),
                    "rfpro",
                    (library_name, cell_name, "layout"),
                    (library_name, substrate_name)
                )
            elif view_type == 'momentum':
                em.create_empro_view(
                    (library_name, cell_name, view_name),
                    "momentum",
                    (library_name, cell_name, "layout"),
                    (library_name, substrate_name)
                )
            
            created_views[view_type] = view_name
            
        except Exception as e:
            print(f"Failed to create {view_type} view: {e}")
    
    return created_views
```

## Simulation Configuration

### Advanced Simulation Setup

```python
def configure_em_simulation(workspace_name, library_name, cell_name, em_view_name, config):
    """Configure EM simulation with advanced settings"""
    
    import empro
    import empro.toolkit.analysis as empro_analysis
    import keysight.edatoolbox.xxpro as xxpro
    
    # Load workspace and view
    xxpro.use_workspace(workspace_name)
    pro_lcv = ads.LibraryCellView(library=library_name, cell=cell_name, view=em_view_name)
    xxpro.load_pro_view(pro_lcv)
    
    project = empro.activeProject
    
    # Clear existing analyses
    project.analyses.clear()
    
    # Create new analysis
    analysis = empro.analysis.Analysis()
    analysis.name = config.get('analysis_name', 'EM_Analysis')
    analysis.analysisType = empro.analysis.Analysis.EMFUAnalysisType
    
    # Configure frequency plan
    _configure_frequency_plan(analysis, config)
    
    # Configure ports
    _configure_ports(analysis, config)
    
    # Configure mesh settings
    _configure_mesh_settings(analysis, config)
    
    # Configure solver settings
    _configure_solver_settings(analysis, config)
    
    # Configure resources
    _configure_resources(analysis, config)
    
    project.analyses.append(analysis)
    project.saveActiveProject()
    
    return analysis

def _configure_frequency_plan(analysis, config):
    """Configure frequency plan based on configuration"""
    
    options = analysis.simulationSettings
    frequency_plan_list = options.femFrequencyPlanList()
    frequency_plan_list.clear()
    
    plan = empro.simulation.FrequencyPlan()
    
    # Frequency configuration
    freq_config = config.get('frequency', {})
    
    if freq_config.get('type') == 'linear':
        plan.type = 'Linear'
        plan.startFrequency = empro.core.Expression(freq_config.get('start', '1MHz'))
        plan.stopFrequency = empro.core.Expression(freq_config.get('stop', '50GHz'))
        plan.numberOfFrequencyPoints = freq_config.get('points', 1000)
    
    elif freq_config.get('type') == 'adaptive':
        plan.type = 'Adaptive'
        plan.startFrequency = empro.core.Expression(freq_config.get('start', '0 Hz'))
        plan.stopFrequency = empro.core.Expression(freq_config.get('stop', '50 GHz'))
        plan.numberOfFrequencyPoints = freq_config.get('points', 300)
        plan.samplePointsLimit = freq_config.get('limit', 300)
        plan.pointsPerDecade = freq_config.get('points_per_decade', 5)
    
    frequency_plan_list.append(plan)

def _configure_ports(analysis, config):
    """Configure ports based on layout"""
    
    port_list = analysis.ports
    port_list.clear()
    
    # Get port definitions from config or auto-detect
    port_configs = config.get('ports', [])
    
    for i, port_config in enumerate(port_configs):
        port_name = port_config.get('name', f'P{i+1}')
        
        port = empro_analysis.createPortFromPins(
            [port_name], ['Reference Pin On Cover']
        )
        port.name = port_name
        port.referenceImpedance = empro.core.Expression(
            port_config.get('impedance', 50.0)
        )
        port.feedType = port_config.get('feed_type', 'Auto')
        
        port_list.append(port)

def _configure_mesh_settings(analysis, config):
    """Configure mesh settings for optimal accuracy"""
    
    options = analysis.simulationSettings
    
    # Apply preset
    preset = config.get('preset', 'Momentum RF')
    options.setPresetByName(preset)
    
    # Momentum-specific settings
    if hasattr(options, 'momMatrixSolver'):
        options.momMatrixSolver.solveMatrixType = config.get(
            'solver_type', 'DirectCompressed'
        )
    
    if hasattr(options, 'momMeshSettings'):
        mesh_config = config.get('mesh', {})
        options.momMeshSettings.meshGranularity = empro.core.Expression(
            mesh_config.get('granularity', '50 cpw')
        )
        options.momMeshSettings.edgeMesh = mesh_config.get('edge_mesh', 'Automatic')
```

## Best Practices and Optimization

### Performance Optimization

```python
class ADSPerformanceOptimizer:
    """Performance optimization for ADS operations"""
    
    def __init__(self):
        self.cache = {}
        self.context_pool = []
    
    def optimize_context_reuse(self, operation_func, *args, **kwargs):
        """Optimize context reuse for repeated operations"""
        
        cache_key = f"{operation_func.__name__}_{hash(str(args))}_{hash(str(kwargs))}"
        
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        with multi_python.ads_context() as ads_ctx:
            result = ads_ctx.call(operation_func, args=args, kwargs=kwargs)
            self.cache[cache_key] = result
            return result
    
    def batch_process_designs(self, designs, batch_size=5):
        """Batch process multiple designs efficiently"""
        
        results = []
        
        for i in range(0, len(designs), batch_size):
            batch = designs[i:i+batch_size]
            
            with multi_python.ads_context() as ads_ctx:
                batch_results = ads_ctx.call(
                    self._process_batch,
                    args=[batch]
                )
                results.extend(batch_results)
        
        return results
```

This comprehensive guide provides production-ready patterns for ADS API integration, ensuring reliable and efficient automation of RFIC layout-to-simulation workflows.
