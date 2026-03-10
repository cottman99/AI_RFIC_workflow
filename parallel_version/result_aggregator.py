#!/usr/bin/env python3
"""
Result Aggregator for ADS Parallel Processing System

This module handles collection, validation, and reporting of batch execution results.

Author: ADS Python API Guide
Date: 2025
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import csv
from dataclasses import dataclass, asdict
import sys

from batch_config import BatchConfig
from batch_executor import BatchResult, TaskResult

@dataclass
class FileInventory:
    """Information about exported files"""
    task_id: str
    file_type: str
    file_path: str
    file_size: int
    exists: bool
    export_timestamp: str

@dataclass
class BatchReport:
    """Comprehensive batch execution report"""
    execution_summary: Dict[str, Any]
    task_statistics: Dict[str, Any]
    file_inventory: List[FileInventory]
    error_analysis: Dict[str, Any]
    performance_metrics: Dict[str, Any]
    export_summary: Dict[str, Any]

class ResultAggregator:
    """Aggregate and analyze batch execution results"""
    
    def __init__(self, config: BatchConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
    def process_batch_results(self, batch_result: BatchResult) -> BatchReport:
        """Process raw batch results into comprehensive report"""
        
        self.logger.info("Processing batch execution results")
        
        # Process file inventory
        file_inventory = self._build_file_inventory(batch_result.task_results)
        
        # Generate execution summary
        execution_summary = self._generate_execution_summary(batch_result)
        
        # Calculate task statistics
        task_statistics = self._calculate_task_statistics(batch_result)
        
        # Analyze errors
        error_analysis = self._analyze_errors(batch_result)
        
        # Calculate performance metrics
        performance_metrics = self._calculate_performance_metrics(batch_result)
        
        # Generate export summary
        export_summary = self._generate_export_summary(file_inventory)
        
        report = BatchReport(
            execution_summary=execution_summary,
            task_statistics=task_statistics,
            file_inventory=file_inventory,
            error_analysis=error_analysis,
            performance_metrics=performance_metrics,
            export_summary=export_summary
        )
        
        self.logger.info("Results processing completed")
        return report
    
    def _build_file_inventory(self, task_results: List[TaskResult]) -> List[FileInventory]:
        """Build inventory of all exported files"""
        inventory = []
        
        for result in task_results:
            if result.success:
                export_results = result.result.get('export_results', {})
                
                for export_type, file_path in export_results.items():
                    if file_path:
                        file_path_obj = Path(file_path)
                        exists = file_path_obj.exists()
                        file_size = file_path_obj.stat().st_size if exists else 0
                        
                        inventory_item = FileInventory(
                            task_id=result.task_id,
                            file_type=export_type,
                            file_path=file_path,
                            file_size=file_size,
                            exists=exists,
                            export_timestamp=datetime.now().isoformat()
                        )
                        
                        inventory.append(inventory_item)
        
        return inventory
    
    def _generate_execution_summary(self, batch_result: BatchResult) -> Dict[str, Any]:
        """Generate execution summary"""
        return {
            'total_tasks': batch_result.total_tasks,
            'successful_tasks': batch_result.successful_tasks,
            'failed_tasks': batch_result.failed_tasks,
            'success_rate': (batch_result.successful_tasks / batch_result.total_tasks * 100) if batch_result.total_tasks > 0 else 0,
            'total_execution_time': batch_result.execution_time,
            'average_task_time': (batch_result.execution_time / batch_result.total_tasks) if batch_result.total_tasks > 0 else 0,
            'execution_timestamp': datetime.now().isoformat(),
            'workspace_dir': self.config.workspace_dir,
            'library_name': self.config.library_name
        }
    
    def _calculate_task_statistics(self, batch_result: BatchResult) -> Dict[str, Any]:
        """Calculate detailed task statistics"""
        
        # Separate design and simulation tasks - based on task_type field
        simulation_tasks = [r for r in batch_result.task_results if hasattr(r, 'task_type') and r.task_type == 'simulation']
        design_tasks = [r for r in batch_result.task_results if hasattr(r, 'task_type') and r.task_type == 'design']
        
        # Fallback: if task_type is not available, use result content
        if not simulation_tasks and not design_tasks:
            simulation_tasks = [r for r in batch_result.task_results if 'export_results' in r.result]
            design_tasks = [r for r in batch_result.task_results if 'export_results' not in r.result and 
                           'cell_name' in r.result and 'json_file' in r.result]
        
        # Calculate statistics
        stats = {
            'design_tasks': {
                'total': len(design_tasks),
                'successful': len([r for r in design_tasks if r.success]),
                'failed': len([r for r in design_tasks if not r.success]),
                'average_time': sum(r.execution_time for r in design_tasks) / len(design_tasks) if design_tasks else 0
            },
            'simulation_tasks': {
                'total': len(simulation_tasks),
                'successful': len([r for r in simulation_tasks if r.success]),
                'failed': len([r for r in simulation_tasks if not r.success]),
                'average_time': sum(r.execution_time for r in simulation_tasks) / len(simulation_tasks) if simulation_tasks else 0
            },
            'retry_statistics': {
                'tasks_retried': len([r for r in batch_result.task_results if r.retry_count > 0]),
                'total_retries': sum(r.retry_count for r in batch_result.task_results),
                'max_retries': max(r.retry_count for r in batch_result.task_results) if batch_result.task_results else 0
            }
        }
        
        return stats
    
    def _analyze_errors(self, batch_result: BatchResult) -> Dict[str, Any]:
        """Analyze error patterns and causes"""
        
        failed_tasks = [r for r in batch_result.task_results if not r.success]
        
        error_analysis = {
            'total_errors': len(failed_tasks),
            'error_categories': batch_result.error_summary.copy(),
            'failed_task_details': []
        }
        
        # Categorize failed tasks
        for task in failed_tasks:
            error_info = {
                'task_id': task.task_id,
                'error_message': task.error,
                'execution_time': task.execution_time,
                'retry_count': task.retry_count,
                'error_category': self._categorize_error(task.error)
            }
            error_analysis['failed_task_details'].append(error_info)
        
        # Calculate error rates by category
        total_tasks = batch_result.total_tasks
        if total_tasks > 0:
            error_analysis['error_rates'] = {
                category: (count / total_tasks * 100)
                for category, count in batch_result.error_summary.items()
            }
        else:
            error_analysis['error_rates'] = {}
        
        return error_analysis
    
    def _categorize_error(self, error_msg: Optional[str]) -> str:
        """Categorize error message"""
        if not error_msg:
            return 'unknown_error'
        
        error_msg = error_msg.lower()
        
        if 'workspace' in error_msg:
            return 'workspace_error'
        elif 'library' in error_msg:
            return 'library_error'
        elif 'design' in error_msg:
            return 'design_error'
        elif 'simulation' in error_msg:
            return 'simulation_error'
        elif 'file not found' in error_msg:
            return 'file_not_found'
        elif 'permission' in error_msg or 'access denied' in error_msg:
            return 'permission_error'
        elif 'timeout' in error_msg:
            return 'timeout_error'
        elif 'memory' in error_msg or 'out of memory' in error_msg:
            return 'memory_error'
        else:
            return 'other_error'
    
    def _calculate_performance_metrics(self, batch_result: BatchResult) -> Dict[str, Any]:
        """Calculate performance metrics"""
        
        if not batch_result.task_results:
            return {
                'total_execution_time': 0,
                'average_task_time': 0,
                'fastest_task_time': 0,
                'slowest_task_time': 0,
                'parallel_efficiency': 0
            }
        
        execution_times = [r.execution_time for r in batch_result.task_results]
        
        # Theoretical sequential execution time
        sequential_time = sum(execution_times)
        
        # Actual parallel execution time
        parallel_time = batch_result.execution_time
        
        # Parallel efficiency
        efficiency = (sequential_time / (parallel_time * self.config.execution_config.max_workers)) * 100 if parallel_time > 0 else 0
        
        return {
            'total_execution_time': parallel_time,
            'average_task_time': sum(execution_times) / len(execution_times),
            'fastest_task_time': min(execution_times),
            'slowest_task_time': max(execution_times),
            'theoretical_sequential_time': sequential_time,
            'parallel_efficiency': min(efficiency, 100.0),  # Cap at 100%
            'throughput_tasks_per_hour': (len(batch_result.task_results) / parallel_time) * 3600 if parallel_time > 0 else 0
        }
    
    def _generate_export_summary(self, file_inventory: List[FileInventory]) -> Dict[str, Any]:
        """Generate export file summary"""
        
        # Group by file type
        files_by_type = {}
        for item in file_inventory:
            file_type = item.file_type
            if file_type not in files_by_type:
                files_by_type[file_type] = []
            files_by_type[file_type].append(item)
        
        # Calculate statistics
        export_summary = {
            'total_files_exported': len(file_inventory),
            'existing_files': len([i for i in file_inventory if i.exists]),
            'missing_files': len([i for i in file_inventory if not i.exists]),
            'total_file_size': sum(i.file_size for i in file_inventory),
            'files_by_type': {}
        }
        
        for file_type, files in files_by_type.items():
            export_summary['files_by_type'][file_type] = {
                'count': len(files),
                'existing': len([f for f in files if f.exists]),
                'missing': len([f for f in files if not f.exists]),
                'total_size': sum(f.file_size for f in files),
                'average_size': sum(f.file_size for f in files) / len(files) if files else 0
            }
        
        return export_summary
    
    def save_report(self, report: BatchReport, output_dir: str) -> Dict[str, str]:
        """Save comprehensive report to files"""
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        saved_files = {}
        
        # Save JSON report
        json_file = output_path / f"batch_report_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(asdict(report), f, indent=2, default=str)
        saved_files['json_report'] = str(json_file)
        
        # Save CSV summary
        csv_file = output_path / f"batch_summary_{timestamp}.csv"
        self._save_csv_summary(report, csv_file)
        saved_files['csv_summary'] = str(csv_file)
        
        # Save detailed task results
        task_csv_file = output_path / f"task_details_{timestamp}.csv"
        self._save_task_details(report, task_csv_file)
        saved_files['task_details'] = str(task_csv_file)
        
        # Save file inventory
        inventory_csv_file = output_path / f"file_inventory_{timestamp}.csv"
        self._save_file_inventory(report, inventory_csv_file)
        saved_files['file_inventory'] = str(inventory_csv_file)
        
        # Save human-readable text report
        text_file = output_path / f"batch_report_{timestamp}.txt"
        self._save_text_report(report, text_file)
        saved_files['text_report'] = str(text_file)
        
        self.logger.info(f"Report saved to: {output_path}")
        return saved_files
    
    def _save_csv_summary(self, report: BatchReport, csv_file: Path):
        """Save CSV summary report"""
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Execution summary
            writer.writerow(['Metric', 'Value'])
            writer.writerow(['Total Tasks', report.execution_summary['total_tasks']])
            writer.writerow(['Successful Tasks', report.execution_summary['successful_tasks']])
            writer.writerow(['Failed Tasks', report.execution_summary['failed_tasks']])
            writer.writerow(['Success Rate (%)', f"{report.execution_summary['success_rate']:.2f}"])
            writer.writerow(['Total Execution Time (s)', f"{report.execution_summary['total_execution_time']:.2f}"])
            writer.writerow(['Average Task Time (s)', f"{report.execution_summary['average_task_time']:.2f}"])
            writer.writerow([])
            
            # Task statistics
            writer.writerow(['Design Tasks', report.task_statistics['design_tasks']['total']])
            writer.writerow(['Design Tasks Successful', report.task_statistics['design_tasks']['successful']])
            writer.writerow(['Simulation Tasks', report.task_statistics['simulation_tasks']['total']])
            writer.writerow(['Simulation Tasks Successful', report.task_statistics['simulation_tasks']['successful']])
            writer.writerow([])
            
            # Export summary
            writer.writerow(['Total Files Exported', report.export_summary['total_files_exported']])
            writer.writerow(['Existing Files', report.export_summary['existing_files']])
            writer.writerow(['Missing Files', report.export_summary['missing_files']])
            writer.writerow(['Total File Size (bytes)', report.export_summary['total_file_size']])
    
    def _save_task_details(self, report: BatchReport, csv_file: Path):
        """Save detailed task results to CSV"""
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            writer.writerow(['Task ID', 'Success', 'Execution Time (s)', 'Retry Count', 'Error Message'])
            
            # Note: We need to reconstruct task results from the available data
            # This is a simplified version
            for error_detail in report.error_analysis.get('failed_task_details', []):
                writer.writerow([
                    error_detail['task_id'],
                    False,
                    error_detail['execution_time'],
                    error_detail['retry_count'],
                    error_detail['error_message']
                ])
    
    def _save_file_inventory(self, report: BatchReport, csv_file: Path):
        """Save file inventory to CSV"""
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            writer.writerow(['Task ID', 'File Type', 'File Path', 'File Size (bytes)', 'Exists', 'Export Timestamp'])
            
            for item in report.file_inventory:
                writer.writerow([
                    item.task_id,
                    item.file_type,
                    item.file_path,
                    item.file_size,
                    item.exists,
                    item.export_timestamp
                ])
    
    def _save_text_report(self, report: BatchReport, text_file: Path):
        """Save human-readable text report"""
        with open(text_file, 'w', encoding='utf-8') as f:
            f.write("BATCH EXECUTION REPORT\n")
            f.write("=" * 50 + "\n\n")
            
            f.write(f"Generated: {report.execution_summary['execution_timestamp']}\n")
            f.write(f"Workspace: {report.execution_summary['workspace_dir']}\n")
            f.write(f"Library: {report.execution_summary['library_name']}\n\n")
            
            f.write("EXECUTION SUMMARY\n")
            f.write("-" * 30 + "\n")
            f.write(f"Total Tasks: {report.execution_summary['total_tasks']}\n")
            f.write(f"Successful: {report.execution_summary['successful_tasks']}\n")
            f.write(f"Failed: {report.execution_summary['failed_tasks']}\n")
            f.write(f"Success Rate: {report.execution_summary['success_rate']:.2f}%\n")
            f.write(f"Total Time: {report.execution_summary['total_execution_time']:.2f}s\n")
            f.write(f"Average Task Time: {report.execution_summary['average_task_time']:.2f}s\n\n")
            
            f.write("PERFORMANCE METRICS\n")
            f.write("-" * 30 + "\n")
            f.write(f"Parallel Efficiency: {report.performance_metrics['parallel_efficiency']:.2f}%\n")
            f.write(f"Throughput: {report.performance_metrics['throughput_tasks_per_hour']:.2f} tasks/hour\n")
            f.write(f"Fastest Task: {report.performance_metrics['fastest_task_time']:.2f}s\n")
            f.write(f"Slowest Task: {report.performance_metrics['slowest_task_time']:.2f}s\n\n")
            
            f.write("EXPORT SUMMARY\n")
            f.write("-" * 30 + "\n")
            f.write(f"Total Files: {report.export_summary['total_files_exported']}\n")
            f.write(f"Existing Files: {report.export_summary['existing_files']}\n")
            f.write(f"Missing Files: {report.export_summary['missing_files']}\n")
            f.write(f"Total Size: {report.export_summary['total_file_size']} bytes\n\n")
            
            if report.error_analysis['total_errors'] > 0:
                f.write("ERROR ANALYSIS\n")
                f.write("-" * 30 + "\n")
                f.write(f"Total Errors: {report.error_analysis['total_errors']}\n")
                for category, count in report.error_analysis['error_categories'].items():
                    f.write(f"  {category}: {count}\n")
                f.write("\n")
    
    def generate_quick_summary(self, report: BatchReport) -> str:
        """Generate quick summary for console output"""
        
        summary_lines = [
            "BATCH EXECUTION SUMMARY",
            "=" * 40,
            f"Total Tasks: {report.execution_summary['total_tasks']}",
            f"Successful: {report.execution_summary['successful_tasks']}",
            f"Failed: {report.execution_summary['failed_tasks']}",
            f"Success Rate: {report.execution_summary['success_rate']:.1f}%",
            f"Total Time: {report.execution_summary['total_execution_time']:.1f}s",
            f"Files Exported: {report.export_summary['total_files_exported']}",
            f"Parallel Efficiency: {report.performance_metrics['parallel_efficiency']:.1f}%",
            "=" * 40
        ]
        
        return "\n".join(summary_lines)

if __name__ == "__main__":
    # Test the result aggregator
    import argparse
    
    parser = argparse.ArgumentParser(description="Result Aggregator Test")
    parser.add_argument('--config', type=str, required=True, help='Configuration file')
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    try:
        from batch_config import ConfigManager
        
        config_manager = ConfigManager()
        config = config_manager.load_config(args.config)
        
        # Create a dummy batch result for testing
        from batch_executor import TaskResult
        
        dummy_results = [
            TaskResult(
                task_id="test_design_1",
                success=True,
                result={"export_results": {"touchstone": "/path/to/test1.s1p"}},
                execution_time=10.5
            ),
            TaskResult(
                task_id="test_design_2",
                success=False,
                result={},
                error="Test error message",
                execution_time=5.2
            )
        ]
        
        dummy_batch_result = BatchResult(
            total_tasks=2,
            successful_tasks=1,
            failed_tasks=1,
            task_results=dummy_results,
            execution_time=15.7,
            error_summary={"test_error": 1}
        )
        
        aggregator = ResultAggregator(config)
        report = aggregator.process_batch_results(dummy_batch_result)
        
        print("Generated test report:")
        print(aggregator.generate_quick_summary(report))
        
        # Save report
        saved_files = aggregator.save_report(report, "./test_output")
        print(f"Report saved to: {saved_files}")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)