#!/usr/bin/env python3
"""
Batch Configuration Manager for ADS Parallel Processing System

This module handles configuration loading, validation, and task generation
for the parallel processing system.

Author: ADS Python API Guide
Date: 2025
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
import sys

@dataclass
class ExecutionConfig:
    """Configuration for parallel execution"""
    max_workers: int = 4
    batch_size: int = 10
    retry_failed: bool = True
    max_retries: int = 3
    
@dataclass
class PDKConfig:
    """PDK configuration settings"""
    use_pdk: bool = True
    pdk_dir: str = ""
    pdk_tech_dir: str = ""
    
@dataclass
class FrequencyPlanConfig:
    """单个频率计划配置"""
    compute_type: str = 'Simulated'
    sweep_type: str = 'Adaptive'
    near_field_type: str = 'NoNearFields'
    far_field_type: str = 'NoFarFields'
    start_frequency: str = '0 Hz'
    stop_frequency: str = '10 GHz'
    number_of_points: int = 201
    sample_points_limit: int = 300
    points_per_decade: int = 5

@dataclass
class FrequencyConfig:
    """频率配置集合"""
    global_frequency_plan_type: str = 'Interpolating_AllFields'
    near_fields_save_for: str = 'AsDefinedByFrequencyPlans'
    far_fields_save_for: str = 'AsDefinedByFrequencyPlans'
    far_field_angular_resolution: str = '5 deg'
    adaptive_fp_max_samples: int = 200
    adaptive_fp_save_fields_for: str = 'AllFrequencies'
    frequency_plans: List[FrequencyPlanConfig] = field(default_factory=list)

@dataclass
class ExportConfig:
    """Export configuration settings"""
    export_path: str = "./batch_results"
    export_touchstone: bool = True
    export_dataset: bool = True
    export_csv: bool = True
    
@dataclass
class BatchConfig:
    """Main batch configuration"""
    workspace_dir: str = "./batch_workspace"
    library_name: str = "Batch_Lib"
    ref_library_name: str = "DemoKit_Non_Linear_tech"
    designs_dir: str = "./json_designs"
    output_dir: str = "./batch_results"
    substrate: str = "microstrip_substrate"
    layer_mapping_file: str = "./layer_mapping.json"
    
    pdk_config: PDKConfig = field(default_factory=PDKConfig)
    frequency_config: FrequencyConfig = field(default_factory=FrequencyConfig)
    export_config: ExportConfig = field(default_factory=ExportConfig)
    execution_config: ExecutionConfig = field(default_factory=ExecutionConfig)

class ConfigManager:
    """Configuration manager for batch processing"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.config: Optional[BatchConfig] = None
        self.config_dir: Optional[Path] = None

    def _resolve_path(self, path_value: str) -> str:
        """Resolve config paths relative to the config file location."""
        if not path_value:
            return ""

        path = Path(path_value)
        if path.is_absolute():
            return str(path)

        if self.config_dir is not None:
            return str((self.config_dir / path).resolve())

        return str(path.resolve())
        
    def load_config(self, config_file: str) -> BatchConfig:
        """Load configuration from JSON file"""
        config_path = Path(config_file).resolve()
        self.config_dir = config_path.parent
        
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_file}")
        
        try:
            with open(config_path, 'r', encoding='utf-8-sig') as f:
                config_data = json.load(f)
            
            self.logger.info(f"Loaded configuration from: {config_file}")
            
            # Convert to configuration objects
            self.config = self._parse_config(config_data)
            
            # Validate configuration
            self._validate_config()
            
            return self.config
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in configuration file: {e}")
        except Exception as e:
            raise RuntimeError(f"Failed to load configuration: {e}")
    
    def _parse_config(self, config_data: Dict[str, Any]) -> BatchConfig:
        """Parse raw configuration data into structured objects"""
        
        # Parse execution config
        exec_data = config_data.get('execution_config', {})
        execution_config = ExecutionConfig(
            max_workers=exec_data.get('max_workers', 4),
            batch_size=exec_data.get('batch_size', 10),
            retry_failed=exec_data.get('retry_failed', True),
            max_retries=exec_data.get('max_retries', 3)
        )
        
        # Parse PDK config
        pdk_data = config_data.get('pdk_config', {})
        pdk_config = PDKConfig(
            use_pdk=pdk_data.get('use_pdk', True),
            pdk_dir=self._resolve_path(pdk_data.get('pdk_dir', '')),
            pdk_tech_dir=self._resolve_path(pdk_data.get('pdk_tech_dir', ''))
        )
        
        # Parse export config
        export_data = config_data.get('export_config', {})
        export_config = ExportConfig(
            export_path=self._resolve_path(export_data.get('export_path', './batch_results')),
            export_touchstone=export_data.get('export_touchstone', True),
            export_dataset=export_data.get('export_dataset', True),
            export_csv=export_data.get('export_csv', True)
        )
        
        # Load frequency config from external file if specified
        frequency_config = {}
        if freq_config_file := config_data.get('frequency_config_file'):
            try:
                freq_config_path = Path(self._resolve_path(freq_config_file))
                if not freq_config_path.exists():
                    self.logger.error(f"Frequency configuration file not found: {freq_config_file}")
                    raise FileNotFoundError(f"Frequency configuration file not found: {freq_config_file}")
                
                with freq_config_path.open('r', encoding='utf-8-sig') as f:
                    frequency_config = json.load(f)
                self.logger.info(f"Loaded frequency configuration from: {freq_config_file}")
            except Exception as e:
                self.logger.error(f"Failed to load frequency config from {freq_config_file}: {e}")
                raise
        else:
            # Fall back to embedded frequency config for backward compatibility
            frequency_config = config_data.get('frequency_config', {})
            self.logger.info("Using embedded frequency configuration")
        
        # Parse frequency plans
        frequency_plans = []
        for plan_data in frequency_config.get('frequency_plans', []):
            plan = FrequencyPlanConfig(
                compute_type=plan_data.get('compute_type', 'Simulated'),
                sweep_type=plan_data.get('sweep_type', 'Adaptive'),
                near_field_type=plan_data.get('near_field_type', 'NoNearFields'),
                far_field_type=plan_data.get('far_field_type', 'NoFarFields'),
                start_frequency=plan_data.get('start_frequency', '0 Hz'),
                stop_frequency=plan_data.get('stop_frequency', '10 GHz'),
                number_of_points=plan_data.get('number_of_points', 201),
                sample_points_limit=plan_data.get('sample_points_limit', 300),
                points_per_decade=plan_data.get('points_per_decade', 5)
            )
            frequency_plans.append(plan)
        
        frequency_config_obj = FrequencyConfig(
            global_frequency_plan_type=frequency_config.get('global_frequency_plan_type', 'Interpolating_AllFields'),
            near_fields_save_for=frequency_config.get('near_fields_save_for', 'AsDefinedByFrequencyPlans'),
            far_fields_save_for=frequency_config.get('far_fields_save_for', 'AsDefinedByFrequencyPlans'),
            far_field_angular_resolution=frequency_config.get('far_field_angular_resolution', '5 deg'),
            adaptive_fp_max_samples=frequency_config.get('adaptive_fp_max_samples', 200),
            adaptive_fp_save_fields_for=frequency_config.get('adaptive_fp_save_fields_for', 'AllFrequencies'),
            frequency_plans=frequency_plans
        )
        
        # Parse main config
        batch_config = BatchConfig(
            workspace_dir=self._resolve_path(config_data.get('workspace_dir', './batch_workspace')),
            library_name=config_data.get('library_name', 'Batch_Lib'),
            ref_library_name=config_data.get('ref_library_name', 'DemoKit_Non_Linear_tech'),
            designs_dir=self._resolve_path(config_data.get('designs_dir', './json_designs')),
            output_dir=self._resolve_path(config_data.get('output_dir', './batch_results')),
            substrate=config_data.get('substrate', 'microstrip_substrate'),
            layer_mapping_file=self._resolve_path(config_data.get('layer_mapping_file', './layer_mapping.json')),
            pdk_config=pdk_config,
            frequency_config=frequency_config_obj,
            export_config=export_config,
            execution_config=execution_config
        )
        
        return batch_config
    
    def _validate_config(self):
        """Validate configuration parameters"""
        if not self.config:
            raise ValueError("No configuration loaded")
        
        # Validate paths
        designs_dir = Path(self.config.designs_dir)
        if not designs_dir.exists():
            self.logger.warning(f"Designs directory does not exist: {designs_dir}")
        
        # Validate execution parameters
        if self.config.execution_config.max_workers < 1:
            raise ValueError("max_workers must be at least 1")
        
        if self.config.execution_config.batch_size < 1:
            raise ValueError("batch_size must be at least 1")
        
        # Validate PDK configuration if enabled
        if self.config.pdk_config.use_pdk:
            if not self.config.pdk_config.pdk_dir:
                raise ValueError("pdk_dir is required when use_pdk is True")
            
            pdk_path = Path(self.config.pdk_config.pdk_dir)
            if not pdk_path.exists():
                self.logger.warning(f"PDK directory does not exist: {pdk_path}")
        
        self.logger.info("Configuration validation passed")
    
    def get_workspace_config(self) -> Dict[str, Any]:
        """Get workspace creation configuration"""
        return {
            'workspace_dir': str(Path(self.config.workspace_dir).absolute()),
            'library_name': self.config.library_name,
            'use_pdk': self.config.pdk_config.use_pdk,
            'pdk_dir': str(Path(self.config.pdk_config.pdk_dir).absolute()) if self.config.pdk_config.pdk_dir else '',
            'pdk_tech_dir': str(Path(self.config.pdk_config.pdk_tech_dir).absolute()) if self.config.pdk_config.pdk_tech_dir else ''
        }
    
    def get_design_task_config(self, json_file: str, cell_name: str) -> Dict[str, Any]:
        """Get design creation task configuration"""
        return {
            'workspace_dir': str(Path(self.config.workspace_dir).absolute()),
            'library_name': self.config.library_name,
            'cell_name': cell_name,
            'ref_library_name': self.config.ref_library_name,
            'substrate_name': self.config.substrate
        }
    
    def get_simulation_task_config(self, cell_name: str) -> Dict[str, Any]:
        """Get simulation task configuration"""
        return {
            'workspace_dir': str(Path(self.config.workspace_dir).absolute()),
            'library_name': self.config.library_name,
            'cell_name': cell_name,
            'em_view_name': 'rfpro_view',
            'frequency_config': self._get_frequency_config_dict(),
            'export_config': {
                'export_path': str(Path(self.config.export_config.export_path).absolute()),
                'export_types': self._get_export_types(),
                'path_mode': 'absolute'
            }
        }
    
    def _get_frequency_config_dict(self) -> Dict[str, Any]:
        """Convert frequency configuration to dictionary for task execution"""
        freq_config = self.config.frequency_config
        
        # Convert frequency plans to dictionaries
        frequency_plans = []
        for plan in freq_config.frequency_plans:
            plan_dict = {
                'compute_type': plan.compute_type,
                'sweep_type': plan.sweep_type,
                'near_field_type': plan.near_field_type,
                'far_field_type': plan.far_field_type,
                'start_frequency': plan.start_frequency,
                'stop_frequency': plan.stop_frequency,
                'number_of_points': plan.number_of_points,
                'sample_points_limit': plan.sample_points_limit,
                'points_per_decade': plan.points_per_decade
            }
            frequency_plans.append(plan_dict)
        
        return {
            'global_frequency_plan_type': freq_config.global_frequency_plan_type,
            'near_fields_save_for': freq_config.near_fields_save_for,
            'far_fields_save_for': freq_config.far_fields_save_for,
            'far_field_angular_resolution': freq_config.far_field_angular_resolution,
            'adaptive_fp_max_samples': freq_config.adaptive_fp_max_samples,
            'adaptive_fp_save_fields_for': freq_config.adaptive_fp_save_fields_for,
            'frequency_plans': frequency_plans
        }
    
    def _get_export_types(self) -> List[str]:
        """Get list of export types based on configuration"""
        export_types = []
        if self.config.export_config.export_touchstone:
            export_types.append('touchstone')
        if self.config.export_config.export_dataset:
            export_types.append('dataset')
        if self.config.export_config.export_csv:
            export_types.append('csv')
        return export_types
    
    def load_layer_mapping(self) -> Dict[str, Dict[str, str]]:
        """Load layer mapping from JSON file"""
        layer_mapping_file = Path(self.config.layer_mapping_file)
        
        if not layer_mapping_file.exists():
            self.logger.warning(f"Layer mapping file not found: {layer_mapping_file}")
            return self._get_default_layer_mapping()
        
        try:
            with open(layer_mapping_file, 'r', encoding='utf-8-sig') as f:
                layer_mapping = json.load(f)
            
            self.logger.info(f"Loaded layer mapping from: {layer_mapping_file}")
            return layer_mapping
            
        except Exception as e:
            self.logger.warning(f"Failed to load layer mapping: {e}")
            return self._get_default_layer_mapping()
    
    def _get_default_layer_mapping(self) -> Dict[str, Dict[str, str]]:
        """Get default layer mapping"""
        return {
            'L1': {'layer_name': 'cond', 'layer_purpose': 'drawing'},
            'L2': {'layer_name': 'via', 'layer_purpose': 'drawing'},
            'GND': {'layer_name': 'ground', 'layer_purpose': 'drawing'}
        }
    
    def scan_json_files(self) -> List[Dict[str, Any]]:
        """Scan designs directory for JSON files and generate tasks"""
        designs_dir = Path(self.config.designs_dir)
        
        if not designs_dir.exists():
            self.logger.error(f"Designs directory does not exist: {designs_dir}")
            return []
        
        json_files = list(designs_dir.glob("*.json"))
        
        if not json_files:
            self.logger.warning(f"No JSON files found in: {designs_dir}")
            return []
        
        tasks = []
        for json_file in json_files:
            try:
                # Generate cell name from file name
                cell_name = json_file.stem
                # Remove 'design_' prefix if present
                if cell_name.startswith('design_'):
                    cell_name = cell_name[len('design_'):]
                
                # Read JSON to get basic info
                with open(json_file, 'r', encoding='utf-8-sig') as f:
                    json_data = json.load(f)
                
                design_id = json_data.get('design_id', cell_name)
                metadata = json_data.get('metadata', {})
                
                task = {
                    'json_file': str(json_file.absolute()),
                    'cell_name': cell_name,
                    'design_id': design_id,
                    'process': metadata.get('process', 'Unknown'),
                    'description': metadata.get('description', 'No description'),
                    'file_size': json_file.stat().st_size
                }
                
                tasks.append(task)
                
            except Exception as e:
                self.logger.error(f"Failed to process JSON file {json_file}: {e}")
                continue
        
        self.logger.info(f"Found {len(tasks)} valid JSON files")
        return tasks
    
    def generate_cli_args(self, command: str, **kwargs) -> List[str]:
        """Generate CLI arguments for subprocess calls"""
        args = [sys.executable, str(Path(__file__).parent / "subprocess_cli_parallel.py"), command]
        
        # Add common arguments
        args.extend(['--workspace-dir', str(Path(self.config.workspace_dir).absolute())])
        args.extend(['--library-name', self.config.library_name])
        
        # Add command-specific arguments
        if command == 'create-workspace-lib':
            if self.config.pdk_config.use_pdk:
                args.append('--use-pdk')
                if self.config.pdk_config.pdk_dir:
                    args.extend(['--pdk-dir', str(Path(self.config.pdk_config.pdk_dir).absolute())])
                if self.config.pdk_config.pdk_tech_dir:
                    args.extend(['--pdk-tech-dir', str(Path(self.config.pdk_config.pdk_tech_dir).absolute())])
        
        elif command == 'create-design-only':
            args.extend(['--cell-name', kwargs.get('cell_name', '')])
            args.extend(['--json-file', kwargs.get('json_file', '')])
            args.extend(['--substrate', self.config.substrate])
            args.extend(['--ref-library-name', self.config.ref_library_name])
            
            layer_mapping_file = Path(self.config.layer_mapping_file)
            if layer_mapping_file.exists():
                args.extend(['--layer-mapping', str(layer_mapping_file.absolute())])
        
        elif command == 'run-simulation-only':
            args.extend(['--cell-name', kwargs.get('cell_name', '')])
            
            export_path = Path(self.config.export_config.export_path)
            if export_path.exists() or export_path.parent.exists():
                args.extend(['--export-path', str(export_path.absolute())])
            
            if self.config.export_config.export_touchstone:
                args.append('--export-touchstone')
            if self.config.export_config.export_dataset:
                args.append('--export-dataset')
            if self.config.export_config.export_csv:
                args.append('--export-csv')
            
            # Add frequency configuration as JSON string
            import json
            frequency_config_dict = self._get_frequency_config_dict()
            if frequency_config_dict and frequency_config_dict.get('frequency_plans'):
                # Generate the JSON string
                json_string = json.dumps(frequency_config_dict)
                # Add the JSON string as a single argument - subprocess.run will handle it correctly
                args.extend(['--frequency-config', json_string])
        
        return args

def create_default_config() -> Dict[str, Any]:
    """Create default configuration template"""
    return {
        "workspace_dir": "./batch_workspace",
        "library_name": "Batch_Lib",
        "ref_library_name": "DemoKit_Non_Linear_tech",
        "designs_dir": "./json_designs",
        "output_dir": "./batch_results",
        "pdk_config": {
            "use_pdk": True,
            "pdk_dir": "path/to/pdk",
            "pdk_tech_dir": "path/to/tech"
        },
        "substrate": "microstrip_substrate",
        "layer_mapping_file": "./layer_mapping.json",
        "export_config": {
            "export_path": "./batch_results",
            "export_touchstone": True,
            "export_dataset": True,
            "export_csv": True
        },
        "execution_config": {
            "max_workers": 4,
            "batch_size": 10,
            "retry_failed": True,
            "max_retries": 3
        }
    }

def save_default_config(config_file: str):
    """Save default configuration to file"""
    config_data = create_default_config()
    
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config_data, f, indent=2)
    
    print(f"Default configuration saved to: {config_file}")

if __name__ == "__main__":
    # Test configuration loading
    import argparse
    
    parser = argparse.ArgumentParser(description="Batch Configuration Manager")
    parser.add_argument('--config', type=str, help='Configuration file path')
    parser.add_argument('--create-default', type=str, help='Create default configuration file')
    
    args = parser.parse_args()
    
    if args.create_default:
        save_default_config(args.create_default)
        sys.exit(0)
    
    if args.config:
        try:
            manager = ConfigManager()
            config = manager.load_config(args.config)
            print("Configuration loaded successfully:")
            print(f"  Workspace: {config.workspace_dir}")
            print(f"  Library: {config.library_name}")
            print(f"  Max Workers: {config.execution_config.max_workers}")
            print(f"  Batch Size: {config.execution_config.batch_size}")
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)
    else:
        parser.print_help()
