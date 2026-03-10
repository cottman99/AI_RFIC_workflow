#!/usr/bin/env python3
"""
ASCII-only Batch Processor for JSON Layout to EM Simulation

This version uses only ASCII characters to avoid Windows encoding issues.

Usage:
    python batch_processor_ascii.py --config batch_config.json
    python batch_processor_ascii.py --json-dir ./layouts --workspace ./batch_results
"""

import json
import os
import sys
import subprocess
import argparse
import logging
from pathlib import Path
import time
from typing import Dict, List, Any

class BatchProcessorASCII:
    """Batch processing engine with ASCII-only output"""
    
    def __init__(self):
        self.setup_logging()
        self.results = []
        self.failed_jobs = []
        
    def setup_logging(self):
        """Setup logging with ASCII-only output"""
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        
        # Setup logger
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.DEBUG)
        
        # Clear existing handlers
        logger.handlers.clear()
        
        # Console handler (INFO level)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        self.logger = logger
        
        # Log system info
        self.logger.info(f"Python version: {sys.version}")
        self.logger.info(f"Working directory: {os.getcwd()}")
        self.logger.info(f"Platform: {sys.platform}")
    
    def find_json_files(self, directory: str, pattern: str = "*.json") -> List[Path]:
        """Find all JSON files in directory matching pattern"""
        directory = Path(directory)
        if not directory.exists():
            self.logger.error(f"Directory not found: {directory}")
            return []
        
        json_files = list(directory.rglob(pattern))
        self.logger.info(f"Found {len(json_files)} JSON files in {directory}")
        return json_files
    
    def load_config(self, config_file: str) -> Dict[str, Any]:
        """Load batch processing configuration"""
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            self.logger.info(f"Loaded configuration from {config_file}")
            return config
        except Exception as e:
            self.logger.error(f"Failed to load config file: {e}")
            return self.get_default_config()
    
    def get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            "json_dir": "./test_layouts",
            "workspace_root": "./batch_workspace",
            "library_name": "Batch_EM_Lib",
            "use_pdk": True,
            "pdk_loc": "path/to/pdk",
            "pdk_tech_loc": "path/to/pdk_tech",
            "substrate": "demo",
            "layer_mapping": "./default_layer_mapping.json",
            "export_types": ["touchstone", "csv"],
            "export_path": "./batch_results",
            "max_workers": 1,
            "timeout": 3600,
            "retry_failed": True,
            "retry_count": 2
        }
    
    def create_job_config(self, json_file: Path, base_config: Dict[str, Any], job_index: int) -> Dict[str, Any]:
        """Create configuration for individual job"""
        cell_name = json_file.stem
        workspace_dir = Path(base_config["workspace_root"]) / f"job_{job_index:03d}_{cell_name}"
        
        return {
            "json_file": str(json_file),
            "workspace_dir": str(workspace_dir),
            "library_name": base_config["library_name"],
            "cell_name": cell_name,
            "use_pdk": base_config.get("use_pdk", True),
            "pdk_loc": base_config.get("pdk_loc", ""),
            "pdk_tech_loc": base_config.get("pdk_tech_loc", ""),
            "substrate": base_config.get("substrate", "demo"),
            "layer_mapping": base_config.get("layer_mapping", ""),
            "export_types": base_config.get("export_types", ["touchstone"]),
            "export_path": base_config["export_path"],
            "timeout": base_config.get("timeout", 3600)
        }
    
    def validate_job_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate job result and check for expected output files"""
        validation_result = {
            "valid": True,
            "issues": [],
            "export_files_count": 0,
            "export_files_size": 0,
            "validation_details": {}
        }
        
        if not result["success"]:
            validation_result["valid"] = False
            validation_result["issues"].append(f"Job failed: {result.get('error', 'Unknown error')}")
            return validation_result
        
        # Check export files
        export_files = result.get("export_files", {})
        if not export_files:
            validation_result["valid"] = False
            validation_result["issues"].append("No export files found")
            return validation_result
        
        # Validate each export type
        for export_type, files in export_files.items():
            if not files:
                validation_result["issues"].append(f"No {export_type} files found")
                continue
            
            valid_files = []
            for file_path in files:
                file_obj = Path(file_path)
                if file_obj.exists() and file_obj.stat().st_size > 0:
                    valid_files.append(file_path)
                    validation_result["export_files_count"] += 1
                    validation_result["export_files_size"] += file_obj.stat().st_size
                else:
                    validation_result["issues"].append(f"File missing or empty: {file_path}")
            
            validation_result["validation_details"][export_type] = {
                "expected_files": len(files),
                "valid_files": len(valid_files),
                "files": valid_files
            }
        
        # Overall validation
        if validation_result["export_files_count"] == 0:
            validation_result["valid"] = False
            validation_result["issues"].append("No valid export files found")
        
        return validation_result
    
    def run_single_job(self, job_config: Dict[str, Any]) -> Dict[str, Any]:
        """Run a single EM simulation job"""
        start_time = time.time()
        json_file = Path(job_config["json_file"])
        
        self.logger.info(f"Starting job: {json_file.name}")
        self.logger.debug(f"Job config: {job_config}")
        
        result = {
            "file": str(json_file),
            "cell_name": job_config["cell_name"],
            "success": False,
            "error": None,
            "error_details": None,
            "start_time": start_time,
            "end_time": None,
            "duration": None,
            "export_files": {},
            "workspace_dir": job_config["workspace_dir"],
            "export_path": job_config["export_path"],
            "validation": None
        }
        
        try:
            # Create workspace directory
            workspace_dir = Path(job_config["workspace_dir"])
            workspace_dir.mkdir(parents=True, exist_ok=True)
            
            # Create export directory (convert to absolute path)
            export_dir = Path(job_config["export_path"]).resolve()
            export_dir.mkdir(parents=True, exist_ok=True)
            
            # Build CLI command
            cmd = [
                sys.executable,
                str(Path(__file__).parent / "subprocess_cli.py"),
                "complete",
                "--json", job_config["json_file"],
                "--workspace", job_config["workspace_dir"],
                "--library", job_config["library_name"],
                "--cell", job_config["cell_name"]
            ]
            
            # Add optional parameters
            if job_config.get("substrate"):
                cmd.extend(["--substrate", job_config["substrate"]])
            
            if job_config.get("use_pdk"):
                cmd.append("--use-pdk")
                if job_config.get("pdk_loc"):
                    cmd.extend(["--pdk-loc", job_config["pdk_loc"]])
                if job_config.get("pdk_tech_loc"):
                    cmd.extend(["--pdk-tech-loc", job_config["pdk_tech_loc"]])
            
            if job_config.get("layer_mapping") and Path(job_config["layer_mapping"]).exists():
                cmd.extend(["--layer-mapping", job_config["layer_mapping"]])
            
            # Use export path as provided in job_config (from base_config)
            # Convert to absolute path to ensure consistent behavior
            export_path = str(export_dir)
            cmd.extend(["--export-path", export_path])
            
            # Add export types
            export_types = job_config.get("export_types", [])
            if "touchstone" in export_types:
                cmd.append("--export-touchstone")
            if "dataset" in export_types:
                cmd.append("--export-dataset")
            if "csv" in export_types:
                cmd.append("--export-csv")
            
            self.logger.debug(f"Running command: {' '.join(cmd)}")
            
            # Set encoding environment for subprocess
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            
            # Run subprocess with proper encoding
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=False,  # Use bytes to avoid encoding issues
                timeout=job_config["timeout"],
                env=env
            )
            
            # Decode with error handling
            try:
                stdout = process.stdout.decode('utf-8', errors='replace')
                stderr = process.stderr.decode('utf-8', errors='replace')
            except UnicodeDecodeError:
                stdout = process.stdout.decode('gbk', errors='replace')
                stderr = process.stderr.decode('gbk', errors='replace')
            
            self.logger.debug(f"Process return code: {process.returncode}")
            
            if process.returncode == 0:
                result["success"] = True
                
                # Try to find exported files (use absolute path)
                export_path = Path(job_config["export_path"]).resolve()
                if export_path.exists():
                    # Get job-specific design name pattern
                    job_name = Path(job_config["json_file"]).stem
                    design_pattern = f"{job_name}_*"
                    
                    for export_type in export_types:
                        pattern = f"*.{export_type}"
                        if export_type == "touchstone":
                            pattern = "*.s*p"
                        elif export_type == "dataset":
                            pattern = "*.ds"  # Fix: dataset files are .ds, not .dataset
                        
                        # Find all matching files
                        all_files = list(export_path.glob(pattern))
                        
                        # Filter files that belong to this job
                        job_files = []
                        for file_path in all_files:
                            file_name = file_path.name
                            # Check if file matches job pattern
                            if file_name.startswith(job_name + "_") or file_name.startswith(job_name + "."):
                                job_files.append(str(file_path))
                        
                        result["export_files"][export_type] = job_files
                        
                    self.logger.info(f"Exported files: {result['export_files']}")
                else:
                    self.logger.warning(f"Export path does not exist: {export_path}")
                
            else:
                result["error"] = stderr or stdout
                result["error_details"] = {
                    "return_code": process.returncode,
                    "stdout": stdout,
                    "stderr": stderr
                }
                self.logger.error(f"Process failed with return code {process.returncode}")
                self.logger.error(f"Error output: {result['error']}")
                
        except subprocess.TimeoutExpired:
            result["error"] = f"Job timeout after {job_config['timeout']} seconds"
            result["error_details"] = {"timeout": job_config["timeout"]}
            self.logger.error(f"Job timeout: {result['error']}")
        except Exception as e:
            result["error"] = str(e)
            result["error_details"] = {"exception": str(e)}
            self.logger.error(f"Error processing {json_file.name}: {e}")
        
        result["end_time"] = time.time()
        result["duration"] = result["end_time"] - result["start_time"]
        
        # Validate result
        result["validation"] = self.validate_job_result(result)
        
        if result["success"] and result["validation"]["valid"]:
            self.logger.info(f"SUCCESS: Completed: {json_file.name} ({result['duration']:.1f}s)")
            self.logger.info(f"  Validation: {result['validation']['export_files_count']} files, {result['validation']['export_files_size']} bytes")
        elif result["success"] and not result["validation"]["valid"]:
            self.logger.warning(f"PARTIAL: {json_file.name} completed but validation failed")
            for issue in result["validation"]["issues"]:
                self.logger.warning(f"  Issue: {issue}")
        else:
            self.logger.error(f"FAILED: {json_file.name} - {result['error']}")
        
        return result
    
    def run_batch_sequential(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Run batch jobs sequentially"""
        self.logger.info(f"Running {len(jobs)} jobs sequentially")
        results = []
        start_time = time.time()
        
        for idx, job in enumerate(jobs, 1):
            # Calculate progress
            progress_percent = (idx - 1) / len(jobs) * 100
            elapsed = time.time() - start_time
            avg_time_per_job = elapsed / (idx - 1) if idx > 1 else 0
            remaining_jobs = len(jobs) - idx + 1
            estimated_remaining = avg_time_per_job * remaining_jobs
            
            # Display progress
            self.logger.info(f"Processing job {idx}/{len(jobs)} ({progress_percent:.1f}%) - {job['cell_name']}")
            self.logger.info(f"  Progress: {idx-1} completed, {remaining_jobs} remaining")
            self.logger.info(f"  Elapsed: {elapsed:.1f}s, ETA: {estimated_remaining:.1f}s")
            
            # Run job
            result = self.run_single_job(job)
            results.append(result)
            
            # Update statistics
            success_count = sum(1 for r in results if r["success"])
            self.logger.info(f"  Current success rate: {success_count}/{len(results)} ({success_count/len(results)*100:.1f}%)")
            
            # Small delay between jobs
            time.sleep(2)
        
        # Final statistics
        total_time = time.time() - start_time
        success_count = sum(1 for r in results if r["success"])
        
        self.logger.info(f"Batch processing completed in {total_time:.1f}s")
        self.logger.info(f"Final results: {success_count}/{len(results)} successful ({success_count/len(results)*100:.1f}%)")
        
        return results
    
    def generate_validation_report(self, results: List[Dict[str, Any]], config: Dict[str, Any]) -> str:
        """Generate detailed validation report"""
        validated_jobs = [r for r in results if r.get('validation')]
        valid_jobs = [r for r in validated_jobs if r['validation']['valid']]
        invalid_jobs = [r for r in validated_jobs if not r['validation']['valid']]
        
        total_files = sum(r['validation']['export_files_count'] for r in validated_jobs)
        total_size = sum(r['validation']['export_files_size'] for r in validated_jobs)
        
        report = f"""
# Validation Report

## Validation Summary
- **Total jobs**: {len(results)}
- **Validated jobs**: {len(validated_jobs)}
- **Valid jobs**: {len(valid_jobs)}
- **Invalid jobs**: {len(invalid_jobs)}
- **Validation success rate**: {(len(valid_jobs)/len(validated_jobs)*100):.1f}%
- **Total export files**: {total_files}
- **Total data size**: {total_size} bytes

## Export Files by Type
"""
        
        # Aggregate export files by type
        export_stats = {}
        for result in validated_jobs:
            validation = result['validation']
            for export_type, details in validation['validation_details'].items():
                if export_type not in export_stats:
                    export_stats[export_type] = {
                        'total_files': 0,
                        'valid_files': 0,
                        'total_size': 0
                    }
                export_stats[export_type]['total_files'] += details['expected_files']
                export_stats[export_type]['valid_files'] += details['valid_files']
                
                # Calculate size
                for file_path in details['files']:
                    try:
                        file_size = Path(file_path).stat().st_size
                        export_stats[export_type]['total_size'] += file_size
                    except:
                        pass
        
        for export_type, stats in export_stats.items():
            success_rate = (stats['valid_files'] / stats['total_files'] * 100) if stats['total_files'] > 0 else 0
            report += f"- **{export_type.upper()}**: {stats['valid_files']}/{stats['total_files']} files ({success_rate:.1f}%), {stats['total_size']} bytes\n"
        
        # Add validation issues
        all_issues = []
        for result in invalid_jobs:
            validation = result['validation']
            for issue in validation['issues']:
                all_issues.append(f"{result['cell_name']}: {issue}")
        
        if all_issues:
            report += "\n## Validation Issues\n\n"
            for issue in all_issues[:20]:  # Limit to first 20 issues
                report += f"- {issue}\n"
            if len(all_issues) > 20:
                report += f"- ... and {len(all_issues) - 20} more issues\n"
        
        return report
    
    def generate_report(self, results: List[Dict[str, Any]], config: Dict[str, Any]) -> str:
        """Generate batch processing report"""
        success_count = sum(1 for r in results if r["success"])
        failed_count = len(results) - success_count
        total_duration = sum(r["duration"] for r in results if r["duration"])
        
        # Calculate statistics
        if results:
            durations = [r["duration"] for r in results if r["duration"]]
            avg_duration = sum(durations) / len(durations) if durations else 0
            min_duration = min(durations) if durations else 0
            max_duration = max(durations) if durations else 0
            
            successful_durations = [r["duration"] for r in results if r["success"] and r["duration"]]
            failed_durations = [r["duration"] for r in results if not r["success"] and r["duration"]]
            
            avg_success_duration = sum(successful_durations) / len(successful_durations) if successful_durations else 0
            avg_failed_duration = sum(failed_durations) / len(failed_durations) if failed_durations else 0
        else:
            avg_duration = min_duration = max_duration = 0
            avg_success_duration = avg_failed_duration = 0
        
        # Generate validation report
        validation_report = self.generate_validation_report(results, config)
        
        report = f"""
# Batch Processing Report

## Processing Summary
- **Total jobs**: {len(results)}
- **Successful**: {success_count}
- **Failed**: {failed_count}
- **Success rate**: {(success_count/len(results)*100):.1f}%
- **Total time**: {total_duration:.1f}s

## Performance Statistics
- **Average duration**: {avg_duration:.1f}s
- **Min duration**: {min_duration:.1f}s
- **Max duration**: {max_duration:.1f}s
- **Avg successful job**: {avg_success_duration:.1f}s
- **Avg failed job**: {avg_failed_duration:.1f}s

## Configuration
- **Workspace root**: {config['workspace_root']}
- **Library name**: {config['library_name']}
- **PDK mode**: {'Yes' if config.get('use_pdk') else 'No'}
- **Export types**: {', '.join(config.get('export_types', []))}
- **Export path**: {config.get('export_path', 'Not specified')}

## Detailed Results
"""
        
        for result in results:
            if result["success"]:
                if result.get('validation') and result['validation']['valid']:
                    status = "VALID"
                    status_symbol = "[V]"
                elif result.get('validation'):
                    status = "PARTIAL"
                    status_symbol = "[P]"
                else:
                    status = "SUCCESS"
                    status_symbol = "[S]"
            else:
                status = "FAILED"
                status_symbol = "[F]"
            
            report += f"- **{status_symbol} {status}**: {result['cell_name']} ({result['duration']:.1f}s)"
            if not result["success"]:
                error_msg = result.get('error', 'Unknown error')
                report += f" - {error_msg[:100]}{'...' if len(error_msg) > 100 else ''}"
            elif result.get('validation') and result['validation']['valid']:
                validation = result['validation']
                report += f" - {validation['export_files_count']} files, {validation['export_files_size']} bytes"
            report += "\n"
        
        # Add failed jobs section if any
        failed_jobs = [r for r in results if not r["success"]]
        if failed_jobs:
            report += "\n## Failed Jobs Analysis\n\n"
            for job in failed_jobs:
                report += f"### {job['cell_name']}\n"
                report += f"- **Error**: {job.get('error', 'Unknown error')}\n"
                report += f"- **Duration**: {job.get('duration', 0):.1f}s\n"
                report += f"- **Workspace**: {job.get('workspace_dir', 'N/A')}\n"
                report += f"- **Export path**: {job.get('export_path', 'N/A')}\n"
                
                if job.get('error_details'):
                    report += "- **Details**: \n"
                    for key, value in job['error_details'].items():
                        report += f"  - {key}: {value}\n"
                report += "\n"
        
        # Add export files summary
        all_export_files = {}
        for result in results:
            if result.get('export_files'):
                for export_type, files in result['export_files'].items():
                    if export_type not in all_export_files:
                        all_export_files[export_type] = []
                    all_export_files[export_type].extend(files)
        
        if all_export_files:
            report += "## Export Files Summary\n\n"
            for export_type, files in all_export_files.items():
                report += f"- **{export_type.upper()}**: {len(files)} files\n"
            report += "\n"
        
        # Add validation report
        report += "\n" + validation_report
        
        # Save report
        report_file = Path(config["workspace_root"]) / "batch_report.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        # Save validation report separately
        validation_file = Path(config["workspace_root"]) / "validation_report.md"
        with open(validation_file, 'w', encoding='utf-8') as f:
            f.write(validation_report)
        
        self.logger.info(f"Report saved to: {report_file}")
        self.logger.info(f"Validation report saved to: {validation_file}")
        return str(report_file)
    
    def process_directory(self, json_dir: str, pattern: str = "*.json", **kwargs) -> bool:
        """Process all JSON files in directory"""
        json_files = self.find_json_files(json_dir, pattern)
        if not json_files:
            return False
        
        config = self.get_default_config()
        config.update(kwargs)
        config["workspace_root"] = str(Path(json_dir) / "batch_workspace")
        
        return self.process_files(json_files, config)
    
    def process_files(self, json_files: List[Path], config: Dict[str, Any]) -> bool:
        """Process list of JSON files"""
        if not json_files:
            self.logger.error("No JSON files to process")
            return False
        
        # Create jobs
        jobs = []
        for idx, json_file in enumerate(json_files):
            job = self.create_job_config(json_file, config, idx)
            jobs.append(job)
        
        self.logger.info(f"Starting batch processing of {len(jobs)} files")
        
        # Run jobs sequentially
        results = self.run_batch_sequential(jobs)
        
        # Generate report
        report_file = self.generate_report(results, config)
        
        # Summary
        success_count = sum(1 for r in results if r["success"])
        self.logger.info(f"Batch processing complete: {success_count}/{len(results)} successful")
        self.logger.info(f"Report saved to: {report_file}")
        
        return success_count == len(results)

def create_parser() -> argparse.ArgumentParser:
    """Create argument parser"""
    parser = argparse.ArgumentParser(
        description="ASCII-only Batch processor for JSON Layout to EM Simulation"
    )
    
    parser.add_argument('--config', help='Batch configuration JSON file')
    parser.add_argument('--json-dir', help='Directory containing JSON files')
    parser.add_argument('--pattern', default='*.json', help='File pattern to match')
    parser.add_argument('--workspace', default='./batch_workspace', help='Root workspace directory')
    parser.add_argument('--library', default='Batch_EM_Lib', help='Library name')
    parser.add_argument('--substrate', default='demo', help='Substrate name')
    parser.add_argument('--use-pdk', action='store_true', help='Use PDK mode')
    parser.add_argument('--pdk-loc', help='PDK library location')
    parser.add_argument('--pdk-tech-loc', help='PDK tech location')
    parser.add_argument('--layer-mapping', help='Layer mapping JSON file')
    parser.add_argument('--export-types', nargs='+', default=['touchstone', 'csv'], 
                       choices=['touchstone', 'dataset', 'csv'], help='Export formats')
    parser.add_argument('--timeout', type=int, default=3600, help='Timeout per job in seconds')
    
    return parser

def main():
    """Main entry point"""
    parser = create_parser()
    args = parser.parse_args()
    
    if not args.config and not args.json_dir:
        parser.print_help()
        print("\nError: Either --config or --json-dir must be provided")
        return 1
    
    # Set encoding for Windows
    if os.name == 'nt':
        os.environ['PYTHONIOENCODING'] = 'utf-8'
    
    processor = BatchProcessorASCII()
    
    try:
        if args.config:
            config = processor.load_config(args.config)
            json_files = processor.find_json_files(config.get("json_dir", "."))
            success = processor.process_files(json_files, config)
        else:
            config_kwargs = {
                "workspace_root": args.workspace,
                "library_name": args.library,
                "substrate": args.substrate,
                "use_pdk": args.use_pdk,
                "pdk_loc": args.pdk_loc or '',
                "pdk_tech_loc": args.pdk_tech_loc or '',
                "layer_mapping": args.layer_mapping or '',
                "export_types": args.export_types,
                "timeout": args.timeout
            }
            success = processor.process_directory(args.json_dir, args.pattern, **config_kwargs)
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\nERROR: Batch processing cancelled by user")
        return 1
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
