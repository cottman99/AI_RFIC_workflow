# Configuration Management and PDK Integration

## Overview

The configuration management system provides comprehensive support for both PDK-based and reference library-based technology configurations. This system ensures seamless integration with industry-standard PDKs while maintaining flexibility for custom technology implementations.

## Configuration Architecture

### Hierarchical Configuration System

```
┌─────────────────────────────────────────────────────────────┐
│                    Configuration Layers                      │
├─────────────────────────────────────────────────────────────┤
│  🔧 Global Config        │  📁 Project Config               │
│  ├── ADS Paths          │  ├── Technology Selection        │
│  ├── Default Parameters │  ├── PDK Configuration          │
│  └── Logging Settings   │  └── Layer Mappings             │
├─────────────────────────────────────────────────────────────┤
│  🏭 PDK Layer          │  📊 Runtime Config               │
│  ├── Technology Files   │  ├── Current Session            │
│  ├── Model Libraries    │  ├── User Preferences           │
│  └── Design Rules       │  └── Temporary Settings         │
└─────────────────────────────────────────────────────────────┘
```

## Configuration File Structure

### Global Configuration Schema

```json
{
  "ads_configuration": {
    "base_path": "C:\\Program Files\\Keysight\\ADS2025_Update2",
    "python_paths": [
      "tools\\python\\python.exe",
      "fem\\2025.20\\win32_64\\bin\\tools\\win32\\python\\python.exe"
    ],
    "license_file": "licenses\\ads_license.lic"
  },
  "default_parameters": {
    "frequency_range": ["1MHz", "50GHz"],
    "frequency_points": 1000,
    "solver_type": "momentum",
    "mesh_density": "50 cpw",
    "max_memory": "2GB",
    "max_threads": 4
  },
  "logging": {
    "level": "INFO",
    "file_rotation": true,
    "max_file_size": "10MB",
    "retention_days": 30
  },
  "paths": {
    "workspace_root": "C:\\Path\\To\\Workspaces",
    "pdk_root": "C:\\Path\\To\\PDKs",
    "results_root": "C:\\Path\\To\\Results",
    "temp_directory": "%TEMP%\\ADS_GUI"
  }
}
```

## PDK Integration Architecture

### PDK Detection and Management

```python
class PDKManager:
    """Comprehensive PDK management with auto-detection"""
    
    def __init__(self, config_manager):
        self.config = config_manager
        self.detected_pdks = {}
        self.active_pdk = None
        self._initialize_pdk_detection()
    
    def _initialize_pdk_detection(self):
        """Initialize PDK detection system"""
        
        pdk_search_paths = [
            "C:\\Path\\To\\Keysight\\PDKs",
            "C:\\Path\\To\\Installed\\PDKs",
            "D:\\Path\\To\\PDKs",
            self.config.get('pdk_root', 'C:\\Path\\To\\PDKs')
        ]
        
        for base_path in pdk_search_paths:
            self._scan_pdk_directory(base_path)
    
    def _scan_pdk_directory(self, base_path):
        """Scan directory for PDK installations"""
        
        if not os.path.exists(base_path):
            return
        
        for item in os.listdir(base_path):
            pdk_path = os.path.join(base_path, item)
            
            if os.path.isdir(pdk_path):
                pdk_info = self._analyze_pdk(pdk_path)
                if pdk_info:
                    self.detected_pdks[pdk_info['name']] = pdk_info
    
    def _analyze_pdk(self, pdk_path):
        """Analyze PDK structure and capabilities"""
        
        # Check for PDK structure
        required_files = [
            'eesof_lib.cfg',
            'technology.tf',
            'substrate.xml'
        ]
        
        pdk_info = {
            'name': os.path.basename(pdk_path),
            'path': pdk_path,
            'version': self._get_pdk_version(pdk_path),
            'process_node': self._extract_process_node(pdk_path),
            'layers': self._extract_layer_info(pdk_path),
            'models': self._get_available_models(pdk_path),
            'compatibility': self._check_ads_compatibility(pdk_path)
        }
        
        # Validate PDK completeness
        missing_files = [f for f in required_files 
                        if not os.path.exists(os.path.join(pdk_path, f))]
        
        if missing_files:
            pdk_info['incomplete'] = True
            pdk_info['missing_files'] = missing_files
        
        return pdk_info
    
    def _get_pdk_version(self, pdk_path):
        """Extract PDK version from configuration files"""
        
        version_file = os.path.join(pdk_path, 'version.txt')
        if os.path.exists(version_file):
            with open(version_file, 'r') as f:
                return f.read().strip()
        
        # Try to extract from eesof_lib.cfg
        cfg_file = os.path.join(pdk_path, 'eesof_lib.cfg')
        if os.path.exists(cfg_file):
            with open(cfg_file, 'r') as f:
                for line in f:
                    if 'VERSION' in line.upper():
                        return line.split('=')[1].strip()
        
        return "Unknown"
    
    def _extract_process_node(self, pdk_path):
        """Extract process node information"""
        
        # Common naming patterns
        name = os.path.basename(pdk_path).lower()
        
        patterns = [
            (r'(\d+)nm', lambda m: f"{m.group(1)}nm"),
            (r'(\d+)um', lambda m: f"{m.group(1)}µm"),
            (r'([\d.]+)um', lambda m: f"{m.group(1)}µm")
        ]
        
        for pattern, formatter in patterns:
            match = re.search(pattern, name)
            if match:
                return formatter(match)
        
        return "Process node unknown"
    
    def _extract_layer_info(self, pdk_path):
        """Extract layer information from technology files"""
        
        layer_info = []
        
        # Parse technology.tf file
        tech_file = os.path.join(pdk_path, 'technology.tf')
        if os.path.exists(tech_file):
            layer_info.extend(self._parse_technology_file(tech_file))
        
        # Parse substrate.xml file
        substrate_file = os.path.join(pdk_path, 'substrate.xml')
        if os.path.exists(substrate_file):
            layer_info.extend(self._parse_substrate_file(substrate_file))
        
        return layer_info
    
    def _parse_technology_file(self, tech_file):
        """Parse technology.tf file for layer information"""
        
        layers = []
        
        with open(tech_file, 'r') as f:
            content = f.read()
            
            # Extract layer definitions
            layer_pattern = r'LAYER\s+(\w+)\s+.*MATERIAL\s+(\w+)\s+.*THICKNESS\s+([\d.]+)'
            matches = re.findall(layer_pattern, content, re.IGNORECASE)
            
            for name, material, thickness in matches:
                layers.append({
                    'name': name,
                    'material': material,
                    'thickness_um': float(thickness),
                    'type': 'conductor' if 'metal' in name.lower() else 'dielectric'
                })
        
        return layers
```

## Technology Configuration

### Microstrip Technology Setup

```python
class MicrostripTechnology:
    """Microstrip technology configuration"""
    
    def __init__(self, process_node="65nm"):
        self.process_node = process_node
        self.layer_stack = self._create_microstrip_stack()
        self.design_rules = self._create_design_rules()
    
    def _create_microstrip_stack(self):
        """Create standard microstrip layer stack"""
        
        return [
            {
                'name': 'GROUND',
                'type': 'ground_plane',
                'material': 'PERFECT_CONDUCTOR',
                'thickness_um': 0.0,
                'conductivity': 1e10
            },
            {
                'name': 'SUBSTRATE',
                'type': 'dielectric',
                'material': 'FR4_epoxy',
                'thickness_um': 508.0,
                'permittivity': 4.4,
                'loss_tangent': 0.02
            },
            {
                'name': 'METAL1',
                'type': 'conductor',
                'material': 'COPPER',
                'thickness_um': 35.0,
                'conductivity': 5.8e7,
                'sheet_resistance': 0.0
            },
            {
                'name': 'AIR',
                'type': 'dielectric',
                'material': 'AIR',
                'thickness_um': 10000.0,
                'permittivity': 1.0,
                'loss_tangent': 0.0
            }
        ]
    
    def _create_design_rules(self):
        """Create microstrip design rules"""
        
        return {
            'min_line_width_um': 14.0,
            'min_line_spacing_um': 14.0,
            'min_via_size_um': 10.0,
            'min_via_spacing_um': 20.0,
            'max_current_density_A_um2': 1e-6,
            'frequency_limits': {
                'min': 1e6,
                'max': 50e9
            }
        }
```

### Stripline Technology Setup

```python
class StriplineTechnology:
    """Stripline technology configuration"""
    
    def __init__(self, process_node="65nm"):
        self.process_node = process_node
        self.layer_stack = self._create_stripline_stack()
    
    def _create_stripline_stack(self):
        """Create standard stripline layer stack"""
        
        return [
            {
                'name': 'GROUND_TOP',
                'type': 'ground_plane',
                'material': 'PERFECT_CONDUCTOR',
                'thickness_um': 0.0
            },
            {
                'name': 'DIELECTRIC_TOP',
                'type': 'dielectric',
                'material': 'FR4_epoxy',
                'thickness_um': 254.0,
                'permittivity': 4.4,
                'loss_tangent': 0.02
            },
            {
                'name': 'METAL1',
                'type': 'conductor',
                'material': 'COPPER',
                'thickness_um': 35.0,
                'conductivity': 5.8e7
            },
            {
                'name': 'DIELECTRIC_BOTTOM',
                'type': 'dielectric',
                'material': 'FR4_epoxy',
                'thickness_um': 254.0,
                'permittivity': 4.4,
                'loss_tangent': 0.02
            },
            {
                'name': 'GROUND_BOTTOM',
                'type': 'ground_plane',
                'material': 'PERFECT_CONDUCTOR',
                'thickness_um': 0.0
            }
        ]
```

## Layer Mapping System

### Dynamic Layer Mapping

```python
class LayerMappingManager:
    """Dynamic layer mapping between JSON and ADS layers"""
    
    def __init__(self, pdk_manager):
        self.pdk_manager = pdk_manager
        self.mapping_rules = self._load_mapping_rules()
        self.user_mappings = {}
    
    def create_layer_mapping(self, json_layers, technology_type='microstrip'):
        """Create layer mapping based on technology type"""
        
        if self.pdk_manager.active_pdk:
            return self._create_pdk_mapping(json_layers)
        else:
            return self._create_reference_mapping(json_layers, technology_type)
    
    def _create_pdk_mapping(self, json_layers):
        """Create mapping using PDK layer information"""
        
        pdk_layers = self.pdk_manager.active_pdk.get('layers', [])
        
        mapping = {}
        
        for json_layer in json_layers:
            # Find best matching PDK layer
            ads_layer = self._find_best_pdk_match(json_layer, pdk_layers)
            mapping[json_layer] = ads_layer
        
        return mapping
    
    def _create_reference_mapping(self, json_layers, technology_type):
        """Create mapping using reference technology"""
        
        reference_mappings = {
            'microstrip': {
                'METAL1': 'cond',
                'METAL2': 'cond2',
                'GROUND': 'gnd',
                'SUBSTRATE': 'sub'
            },
            'stripline': {
                'METAL1': 'cond',
                'GROUND_TOP': 'gnd',
                'GROUND_BOTTOM': 'gnd',
                'DIELECTRIC': 'sub'
            }
        }
        
        reference_map = reference_mappings.get(technology_type, {})
        
        mapping = {}
        for json_layer in json_layers:
            ads_layer = reference_map.get(json_layer, json_layer.upper())
            mapping[json_layer] = ads_layer
        
        return mapping
    
    def _find_best_pdk_match(self, json_layer, pdk_layers):
        """Find best matching PDK layer"""
        
        # Exact name match
        for layer in pdk_layers:
            if layer['name'].upper() == json_layer.upper():
                return layer['name']
        
        # Partial name match
        for layer in pdk_layers:
            if json_layer.upper() in layer['name'].upper():
                return layer['name']
        
        # Material-based matching
        material_map = {
            'METAL': [l['name'] for l in pdk_layers if l['type'] == 'conductor'],
            'GROUND': [l['name'] for l in pdk_layers if l['type'] == 'ground_plane'],
            'SUBSTRATE': [l['name'] for l in pdk_layers if l['type'] == 'dielectric']
        }
        
        for prefix, candidates in material_map.items():
            if json_layer.upper().startswith(prefix):
                return candidates[0] if candidates else json_layer
        
        return json_layer
```

## Configuration Persistence

### User Configuration Management

```python
class UserConfiguration:
    """Persistent user configuration management"""
    
    def __init__(self, config_file=None):
        self.config_file = config_file or self._get_default_config_path()
        self.config_data = self._load_config()
    
    def _get_default_config_path(self):
        """Get default configuration file path"""
        
        config_dir = Path.home() / '.rfic_gui'
        config_dir.mkdir(exist_ok=True)
        return config_dir / 'config.json'
    
    def _load_config(self):
        """Load configuration from file"""
        
        if not os.path.exists(self.config_file):
            return self._create_default_config()
        
        try:
            with open(self.config_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading config: {e}")
            return self._create_default_config()
    
    def _create_default_config(self):
        """Create default configuration"""
        
        default_config = {
            "recent_projects": [],
            "window_geometry": {
                "width": 1000,
                "height": 700,
                "x": 100,
                "y": 100
            },
            "default_paths": {
                "workspace": "C:\\Path\\To\\Workspaces",
                "pdk": "C:\\Path\\To\\PDKs",
                "results": "C:\\Path\\To\\Results"
            },
            "ui_preferences": {
                "theme": "default",
                "font_size": 10,
                "show_tooltips": True,
                "auto_save": True
            },
            "simulation_defaults": {
                "frequency_start": "1MHz",
                "frequency_stop": "50GHz",
                "frequency_points": 1000,
                "solver_type": "momentum"
            }
        }
        
        self.save_config(default_config)
        return default_config
    
    def save_config(self, config_data=None):
        """Save configuration to file"""
        
        if config_data:
            self.config_data.update(config_data)
        
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config_data, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def add_recent_project(self, project_path):
        """Add project to recent projects list"""
        
        recent = self.config_data.get('recent_projects', [])
        
        # Remove if already exists
        if project_path in recent:
            recent.remove(project_path)
        
        # Add to beginning
        recent.insert(0, project_path)
        
        # Keep only last 10
        recent = recent[:10]
        
        self.config_data['recent_projects'] = recent
        self.save_config()
```

## Best Practices

### Configuration Validation

```python
class ConfigurationValidator:
    """Validate configuration integrity"""
    
    def validate_configuration(self, config):
        """Validate complete configuration"""
        
        validation_results = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Validate paths
        self._validate_paths(config, validation_results)
        
        # Validate PDK settings
        self._validate_pdk_settings(config, validation_results)
        
        # Validate simulation parameters
        self._validate_simulation_params(config, validation_results)
        
        return validation_results
    
    def _validate_paths(self, config, results):
        """Validate all configured paths"""
        
        path_configs = [
            ('ads_configuration.base_path', 'ADS installation'),
            ('paths.workspace', 'Workspace directory'),
            ('paths.pdk', 'PDK directory'),
            ('paths.results', 'Results directory')
        ]
        
        for path_key, description in path_configs:
            path = self._get_nested_value(config, path_key)
            if path and not os.path.exists(path):
                results['warnings'].append(f"{description} path does not exist: {path}")
```

This comprehensive configuration management system provides robust, scalable support for both PDK-based and reference technology implementations with full validation and persistence capabilities.
