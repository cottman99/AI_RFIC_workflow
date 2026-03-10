#!/usr/bin/env python3
"""
Batch Processor - Main CLI Interface for ADS Parallel Processing System

This module provides the main command-line interface for the batch processing system,
orchestrating the complete workflow from configuration to results.

Author: ADS Python API Guide
Date: 2025
"""

import argparse
import logging
import sys
import signal
import time
from pathlib import Path
from typing import Dict, List, Any, Optional

from batch_config import ConfigManager, BatchConfig
from batch_executor import BatchExecutor
from result_aggregator import ResultAggregator, BatchReport

class BatchProcessor:
    """Main batch processor orchestrating the complete workflow"""
    
    def __init__(self):
        self.config_manager = ConfigManager()
        self.config: Optional[BatchConfig] = None
        self.executor: Optional[BatchExecutor] = None
        self.aggregator: Optional[ResultAggregator] = None
        self.logger = self._setup_logging()
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _setup_logging(self) -> logging.Logger:
        """Setup comprehensive logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler('batch_processor.log')
            ]
        )
        return logging.getLogger(__name__)
    
    def _signal_handler(self, signum, frame):
        """Handle interrupt signals gracefully"""
        self.logger.info(f"Received signal {signum}, shutting down gracefully...")
        sys.exit(0)
    
    def process_config_file(self, config_file: str) -> int:
        """Process batch execution using configuration file"""
        
        try:
            # Load configuration
            self.logger.info(f"Loading configuration from: {config_file}")
            self.config = self.config_manager.load_config(config_file)
            
            # Initialize components
            self.executor = BatchExecutor(self.config)
            self.aggregator = ResultAggregator(self.config)
            
            # Validate environment
            if not self._validate_environment():
                return 1
            
            # Scan for tasks
            tasks = self.config_manager.scan_json_files()
            if not tasks:
                self.logger.error("No valid JSON files found in designs directory")
                return 1
            
            self.logger.info(f"Found {len(tasks)} tasks to process")
            
            # Display execution plan
            self._display_execution_plan(tasks)
            
            # Execute batch workflow
            batch_result = self.executor.execute_batch_workflow(tasks)
            
            # Process results
            report = self.aggregator.process_batch_results(batch_result)
            
            # Display summary
            self._display_results_summary(report)
            
            # Save reports
            saved_files = self.aggregator.save_report(report, self.config.output_dir)
            self.logger.info(f"Reports saved to: {saved_files}")
            
            # Return appropriate exit code
            return 0 if batch_result.failed_tasks == 0 else 1
            
        except Exception as e:
            self.logger.error(f"Batch processing failed: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return 1
    
    def _validate_environment(self) -> bool:
        """Validate execution environment"""
        self.logger.info("Validating execution environment...")
        
        # Check if CLI script exists
        cli_script = Path(__file__).parent / "subprocess_cli_parallel.py"
        if not cli_script.exists():
            self.logger.error(f"CLI script not found: {cli_script}")
            return False
        
        # Check designs directory
        designs_dir = Path(self.config.designs_dir)
        if not designs_dir.exists():
            self.logger.error(f"Designs directory not found: {designs_dir}")
            return False
        
        # Check output directory
        output_dir = Path(self.config.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Check PDK directories if enabled
        if self.config.pdk_config.use_pdk:
            pdk_dir = Path(self.config.pdk_config.pdk_dir)
            if not pdk_dir.exists():
                self.logger.warning(f"PDK directory not found: {pdk_dir}")
                # Don't fail, just warn
            
            pdk_tech_dir = Path(self.config.pdk_config.pdk_tech_dir)
            if not pdk_tech_dir.exists():
                self.logger.warning(f"PDK tech directory not found: {pdk_tech_dir}")
                # Don't fail, just warn
        
        self.logger.info("Environment validation completed")
        return True
    
    def _display_execution_plan(self, tasks: List[Dict[str, Any]]):
        """Display execution plan to user"""
        print("\n" + "="*60)
        print("BATCH EXECUTION PLAN")
        print("="*60)
        print(f"Configuration: {self.config.workspace_dir}")
        print(f"Library: {self.config.library_name}")
        print(f"Designs Directory: {self.config.designs_dir}")
        print(f"Output Directory: {self.config.output_dir}")
        print(f"Total Tasks: {len(tasks)}")
        print(f"Max Workers: {self.config.execution_config.max_workers}")
        print(f"Batch Size: {self.config.execution_config.batch_size}")
        print(f"Retry Failed: {self.config.execution_config.retry_failed}")
        print("\nTask Breakdown:")
        
        # Group by process type
        processes = {}
        for task in tasks:
            process = task.get('process', 'Unknown')
            if process not in processes:
                processes[process] = []
            processes[process].append(task)
        
        for process, task_list in processes.items():
            print(f"  {process}: {len(task_list)} tasks")
        
        print("\nExecution Phases:")
        print("  1. Create workspace and library")
        print("  2. Create designs (parallel)")
        print("  3. Run simulations (parallel)")
        print("  4. Generate reports")
        print("="*60 + "\n")
        
        # Ask for confirmation
        try:
            response = input("Proceed with execution? [Y/n]: ").strip().lower()
            if response and response not in ['y', 'yes']:
                print("Execution cancelled by user")
                sys.exit(0)
        except KeyboardInterrupt:
            print("\nExecution cancelled by user")
            sys.exit(0)
    
    def _display_results_summary(self, report: BatchReport):
        """Display results summary"""
        print("\n" + "="*60)
        print("BATCH EXECUTION RESULTS")
        print("="*60)
        
        summary = self.aggregator.generate_quick_summary(report)
        print(summary)
        
        # Display task breakdown
        print(f"\nTask Statistics:")
        print(f"  Design Tasks: {report.task_statistics['design_tasks']['successful']}/{report.task_statistics['design_tasks']['total']} successful")
        print(f"  Simulation Tasks: {report.task_statistics['simulation_tasks']['successful']}/{report.task_statistics['simulation_tasks']['total']} successful")
        
        # Display export summary
        print(f"\nExport Summary:")
        print(f"  Total Files: {report.export_summary['total_files_exported']}")
        print(f"  Existing Files: {report.export_summary['existing_files']}")
        print(f"  Missing Files: {report.export_summary['missing_files']}")
        
        # Display error summary if any
        if report.error_analysis['total_errors'] > 0:
            print(f"\nError Summary:")
            print(f"  Total Errors: {report.error_analysis['total_errors']}")
            for category, count in report.error_analysis['error_categories'].items():
                print(f"  {category}: {count}")
        
        print("="*60 + "\n")
    
    def validate_config(self, config_file: str) -> int:
        """Validate configuration file without execution"""
        
        try:
            print(f"Validating configuration file: {config_file}")
            
            # Load configuration
            self.config = self.config_manager.load_config(config_file)
            
            # Validate paths
            print("\nConfiguration Validation:")
            print(f"[OK] Configuration file: Valid JSON")
            print(f"[OK] Workspace directory: {self.config.workspace_dir}")
            print(f"[OK] Library name: {self.config.library_name}")
            print(f"[OK] Designs directory: {self.config.designs_dir}")
            print(f"[OK] Output directory: {self.config.output_dir}")
            print(f"[OK] Max workers: {self.config.execution_config.max_workers}")
            print(f"[OK] Batch size: {self.config.execution_config.batch_size}")
            
            # Check designs directory
            designs_dir = Path(self.config.designs_dir)
            if designs_dir.exists():
                json_files = list(designs_dir.glob("*.json"))
                print(f"[OK] Designs directory exists with {len(json_files)} JSON files")
            else:
                print(f"[WARN] Designs directory does not exist: {designs_dir}")
            
            # Check PDK configuration
            if self.config.pdk_config.use_pdk:
                pdk_dir = Path(self.config.pdk_config.pdk_dir)
                if pdk_dir.exists():
                    print(f"[OK] PDK directory exists: {pdk_dir}")
                else:
                    print(f"[WARN] PDK directory not found: {pdk_dir}")
            
            print("\nConfiguration validation completed successfully!")
            return 0
            
        except Exception as e:
            print(f"Configuration validation failed: {e}")
            return 1
    
    def create_config_template(self, output_file: str) -> int:
        """Create configuration template file"""
        
        try:
            from batch_config import save_default_config
            save_default_config(output_file)
            print(f"Configuration template created: {output_file}")
            return 0
            
        except Exception as e:
            print(f"Failed to create configuration template: {e}")
            return 1
    
    def scan_tasks(self, config_file: str) -> int:
        """Scan and display available tasks without execution"""
        
        try:
            # Load configuration
            self.config = self.config_manager.load_config(config_file)
            
            # Scan for tasks
            tasks = self.config_manager.scan_json_files()
            
            if not tasks:
                print("No valid JSON files found")
                return 1
            
            print(f"\nFound {len(tasks)} tasks in {self.config.designs_dir}:")
            print("="*60)
            
            for i, task in enumerate(tasks, 1):
                print(f"{i:2d}. {task['cell_name']}")
                print(f"    Design ID: {task['design_id']}")
                print(f"    Process: {task['process']}")
                print(f"    File: {task['json_file']}")
                print(f"    Size: {task['file_size']} bytes")
                print()
            
            return 0
            
        except Exception as e:
            print(f"Task scanning failed: {e}")
            return 1

def create_parser():
    """Create command line argument parser"""
    parser = argparse.ArgumentParser(
        description="ADS Batch Processor - Parallel Design and Simulation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process batch using configuration file
  python batch_processor.py process-config --config batch_config.json
  
  # Validate configuration file
  python batch_processor.py validate-config --config batch_config.json
  
  # Create configuration template
  python batch_processor.py create-config --output batch_config.json
  
  # Scan available tasks
  python batch_processor.py scan-tasks --config batch_config.json
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Process configuration command
    process_parser = subparsers.add_parser('process-config', 
                                         help='Process batch using configuration file')
    process_parser.add_argument('--config', type=str, required=True,
                              help='Configuration file path')
    
    # Validate configuration command
    validate_parser = subparsers.add_parser('validate-config',
                                          help='Validate configuration file')
    validate_parser.add_argument('--config', type=str, required=True,
                                help='Configuration file path')
    
    # Create config template command
    create_parser = subparsers.add_parser('create-config',
                                        help='Create configuration template')
    create_parser.add_argument('--output', type=str, required=True,
                             help='Output configuration file path')
    
    # Scan tasks command
    scan_parser = subparsers.add_parser('scan-tasks',
                                      help='Scan and display available tasks')
    scan_parser.add_argument('--config', type=str, required=True,
                           help='Configuration file path')
    
    return parser

def main():
    """Main entry point"""
    parser = create_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    processor = BatchProcessor()
    
    try:
        if args.command == 'process-config':
            return processor.process_config_file(args.config)
        elif args.command == 'validate-config':
            return processor.validate_config(args.config)
        elif args.command == 'create-config':
            return processor.create_config_template(args.output)
        elif args.command == 'scan-tasks':
            return processor.scan_tasks(args.config)
        else:
            print(f"Unknown command: {args.command}")
            return 1
            
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback
        print(traceback.format_exc())
        return 1

if __name__ == "__main__":
    sys.exit(main())