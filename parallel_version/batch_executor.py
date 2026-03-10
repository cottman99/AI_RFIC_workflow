#!/usr/bin/env python3
"""
Batch Executor for ADS Parallel Processing System

This module handles parallel execution of tasks using process pools,
with proper error handling and progress monitoring.

Author: ADS Python API Guide
Date: 2025
"""

import subprocess
import logging
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from concurrent.futures import ProcessPoolExecutor, as_completed, Future
from dataclasses import dataclass
import json
import sys
import traceback

from batch_config import ConfigManager, BatchConfig

@dataclass
class TaskResult:
    """Result of a single task execution"""
    task_id: str
    task_type: str  # 'design' or 'simulation'
    success: bool
    result: Dict[str, Any]
    error: Optional[str] = None
    execution_time: float = 0.0
    retry_count: int = 0

@dataclass
class BatchResult:
    """Result of a batch execution"""
    total_tasks: int
    successful_tasks: int
    failed_tasks: int
    task_results: List[TaskResult]
    execution_time: float
    error_summary: Dict[str, int]

class BatchExecutor:
    """Execute batch tasks in parallel with proper error handling"""
    
    def __init__(self, config: BatchConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.config_manager = ConfigManager()
        self.config_manager.config = config
        
    def execute_batch_workflow(self, tasks: List[Dict[str, Any]]) -> BatchResult:
        """Execute complete batch workflow: workspace → designs → simulation"""
        start_time = time.time()
        
        self.logger.info(f"Starting batch workflow with {len(tasks)} tasks")
        
        # Phase 1: Create workspace and library
        workspace_success = self._create_workspace_library()
        if not workspace_success:
            return BatchResult(
                total_tasks=len(tasks),
                successful_tasks=0,
                failed_tasks=len(tasks),
                task_results=[],
                execution_time=time.time() - start_time,
                error_summary={"workspace_creation_failed": len(tasks)}
            )
        
        # Phase 2: Create designs in parallel
        design_results = self._execute_design_creation(tasks)
        
        # Phase 3: Run simulations for successful designs
        successful_designs = [r for r in design_results if r.success]
        simulation_results = self._execute_simulation_tasks(successful_designs)
        
        # Combine results
        all_results = design_results + simulation_results
        
        # Calculate statistics
        successful_tasks = len([r for r in all_results if r.success])
        failed_tasks = len(all_results) - successful_tasks
        
        error_summary = self._analyze_errors(all_results)
        
        total_time = time.time() - start_time
        
        self.logger.info(f"Batch workflow completed in {total_time:.2f}s")
        self.logger.info(f"Successful: {successful_tasks}, Failed: {failed_tasks}")
        
        return BatchResult(
            total_tasks=len(all_results),
            successful_tasks=successful_tasks,
            failed_tasks=failed_tasks,
            task_results=all_results,
            execution_time=total_time,
            error_summary=error_summary
        )
    
    def _create_workspace_library(self) -> bool:
        """Create workspace and library"""
        self.logger.info("Phase 1: Creating workspace and library")
        
        try:
            args = self.config_manager.generate_cli_args('create-workspace-lib')
            
            # Log the command being sent to subprocess_cli_parallel.py
            cmd_str = ' '.join(args)
            self.logger.info(f"Command sent to subprocess_cli_parallel.py: {cmd_str}")
            
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            
            if result.returncode == 0:
                self.logger.info("[OK] Workspace and library created successfully")
                return True
            else:
                self.logger.error(f"[FAIL] Workspace creation failed: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"[FAIL] Workspace creation exception: {e}")
            return False
    
    def _execute_design_creation(self, tasks: List[Dict[str, Any]]) -> List[TaskResult]:
        """Execute design creation tasks in parallel"""
        self.logger.info(f"Phase 2: Creating {len(tasks)} designs in parallel")
        
        # Group tasks into batches
        batch_size = self.config.execution_config.batch_size
        task_batches = [tasks[i:i + batch_size] for i in range(0, len(tasks), batch_size)]
        
        all_results = []
        
        for batch_idx, batch in enumerate(task_batches):
            self.logger.info(f"Processing design batch {batch_idx + 1}/{len(task_batches)}")
            
            batch_results = self._execute_task_batch(
                batch,
                self._create_design_task,
                f"design_batch_{batch_idx}"
            )
            
            all_results.extend(batch_results)
            
            # Report batch progress
            successful = len([r for r in batch_results if r.success])
            self.logger.info(f"Batch {batch_idx + 1}: {successful}/{len(batch)} designs created successfully")
        
        return all_results
    
    def _execute_simulation_tasks(self, design_results: List[TaskResult]) -> List[TaskResult]:
        """Execute simulation tasks for successfully created designs"""
        self.logger.info(f"Phase 3: Running simulations for {len(design_results)} designs")
        
        # Convert design results to simulation tasks
        sim_tasks = []
        for design_result in design_results:
            sim_task = {
                'cell_name': design_result.task_id,
                'design_result': design_result.result
            }
            sim_tasks.append(sim_task)
        
        # Group into batches
        batch_size = self.config.execution_config.batch_size
        task_batches = [sim_tasks[i:i + batch_size] for i in range(0, len(sim_tasks), batch_size)]
        
        all_results = []
        
        for batch_idx, batch in enumerate(task_batches):
            self.logger.info(f"Processing simulation batch {batch_idx + 1}/{len(task_batches)}")
            
            batch_results = self._execute_task_batch(
                batch,
                self._run_simulation_task,
                f"simulation_batch_{batch_idx}"
            )
            
            all_results.extend(batch_results)
            
            # Report batch progress
            successful = len([r for r in batch_results if r.success])
            self.logger.info(f"Batch {batch_idx + 1}: {successful}/{len(batch)} simulations completed successfully")
        
        return all_results
    
    def _execute_task_batch(self, tasks: List[Dict[str, Any]], 
                           task_func, batch_name: str) -> List[TaskResult]:
        """Execute a batch of tasks in parallel"""
        
        results = []
        
        # Use simpler approach - log commands before and after execution
        self.logger.info(f"Starting parallel execution of {len(tasks)} tasks in {batch_name}")
        
        # Log all commands before execution
        for i, task in enumerate(tasks):
            task_id = task.get('cell_name', f'task_{i}')
            self.logger.info(f"Task {task_id}: Queued for execution")
        
        with ProcessPoolExecutor(max_workers=self.config.execution_config.max_workers) as executor:
            # Submit all tasks and track their submission
            futures = []
            for i, task in enumerate(tasks):
                task_id = task.get('cell_name', f'task_{i}')
                self.logger.info(f"Task {task_id}: Submitting to process pool")
                future = executor.submit(task_func, task)
                futures.append((task, task_id, future))
                self.logger.info(f"Task {task_id}: Submitted successfully")
            
            # Process results as they complete and log progress
            completed_count = 0
            for future in as_completed([f for _, _, f in futures]):
                completed_count += 1
                self.logger.info(f"Progress: {completed_count}/{len(tasks)} tasks completed")
                
                try:
                    task_result = future.result()
                    results.append(task_result)
                    
                    # Log individual task result with details
                    if task_result.success:
                        self.logger.info(f"[OK] {task_result.task_id} completed successfully in {task_result.execution_time:.2f}s")
                    else:
                        self.logger.error(f"[FAIL] {task_result.task_id} failed: {task_result.error}")
                        
                except Exception as e:
                    # Handle task execution failure
                    task_id = "unknown"
                    error_result = TaskResult(
                        task_id=task_id,
                        task_type="unknown",
                        success=False,
                        result={},
                        error=str(e),
                        execution_time=0.0
                    )
                    results.append(error_result)
                    self.logger.error(f"[FAIL] {task_id} execution failed: {e}")
        
        self.logger.info(f"Batch {batch_name} completed: {len(results)}/{len(tasks)} tasks processed")
        return results
    
    def _create_design_task(self, task: Dict[str, Any]) -> TaskResult:
        """Execute a single design creation task"""
        # Configure logging for worker process
        import logging
        import sys
        from pathlib import Path
        
        # Setup logging to match main process
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler('batch_processor.log', mode='a', encoding='utf-8')
            ]
        )
        
        # Get logger for this module
        logger = logging.getLogger('batch_executor')
        
        start_time = time.time()
        task_id = f"design_{task['cell_name']}"
        
        # Log task start
        logger.info(f"Starting design creation task for {task_id}")
        logger.info(f"JSON file: {task['json_file']}")
        
        try:
            # Build CLI arguments
            args = self.config_manager.generate_cli_args(
                'create-design-only',
                cell_name=task_id,
                json_file=task['json_file']
            )
            
            # Log the command being sent to subprocess_cli_parallel.py
            cmd_str = ' '.join(args)
            logger.info(f"COMMAND_SENT_TO_SUBPROCESS_CLI: {cmd_str}")
            logger.info(f"Executing design creation for {task_id}...")
            
            # Execute subprocess
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            
            execution_time = time.time() - start_time
            
            # Log command completion
            logger.info(f"Command completed for {task_id}: returncode={result.returncode}, time={execution_time:.2f}s")
            
            if result.returncode == 0:
                logger.info(f"SUCCESS: Design {task_id} created successfully")
                if result.stdout:
                    logger.debug(f"STDOUT: {result.stdout[:200]}...")  # Log first 200 chars
                return TaskResult(
                    task_id=task_id,
                    task_type='design',
                    success=True,
                    result={
                        'stdout': result.stdout,
                        'cell_name': task['cell_name'],
                        'json_file': task['json_file']
                    },
                    execution_time=execution_time
                )
            else:
                error_msg = result.stderr or "Unknown error"
                logger.error(f"FAILED: Design {task_id} creation failed: {error_msg}")
                return TaskResult(
                    task_id=task_id,
                    task_type='design',
                    success=False,
                    result={},
                    error=error_msg,
                    execution_time=execution_time
                )
                
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"EXCEPTION: Design {task_id} creation failed with exception: {e}")
            return TaskResult(
                task_id=task_id,
                task_type='design',
                success=False,
                result={},
                error=str(e),
                execution_time=execution_time
            )
    
    def _run_simulation_task(self, task: Dict[str, Any]) -> TaskResult:
        """Execute single simulation task"""
        # Configure logging for worker process
        import logging
        import sys
        
        # Setup logging to match main process
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler('batch_processor.log', mode='a', encoding='utf-8')
            ]
        )
        
        # Get logger for this module
        logger = logging.getLogger('batch_executor')
        
        task_id = f"simulation_{task['cell_name']}"
        start_time = time.time()
        
        try:
            logger.info(f"Starting simulation task for {task_id}")
            
            # Generate command
            cmd_args = self.config_manager.generate_cli_args('run-simulation-only', **task)
            cmd_str = " ".join(cmd_args)
            logger.info(f"COMMAND_SENT_TO_SUBPROCESS_CLI: {cmd_str}")
            
            # Execute command
            logger.info(f"Executing EM simulation for {task_id}...")
            process = subprocess.Popen(
                cmd_args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = process.communicate()
            execution_time = time.time() - start_time
            
            if process.returncode != 0:
                error_msg = stderr.strip() or stdout.strip() or "No error message available"
                logger.error(f"FAILED: EM simulation {task_id} failed: {error_msg}")
                return TaskResult(
                    task_id=task_id,
                    task_type='simulation',
                    success=False,
                    result={},
                    error=error_msg,
                    execution_time=execution_time
                )
            
            # Parse export results from stdout
            export_results = self._parse_export_results(stdout)
            logger.info(f"SUCCESS: EM simulation {task_id} completed with {len(export_results)} exports")
            
            return TaskResult(
                task_id=task_id,
                task_type='simulation',
                success=True,
                result={
                    "output": stdout,
                    "export_results": export_results
                },
                error=None,
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Task execution error: {str(e)}\n{traceback.format_exc()}"
            logger.error(f"FAILED: Task execution error for {task_id}: {error_msg}")
            return TaskResult(
                task_id=task_id,
                task_type='simulation',
                success=False,
                result={},
                error=error_msg,
                execution_time=execution_time
            )
    
    def _parse_export_results(self, stdout: str) -> Dict[str, str]:
        """Parse export results from CLI output"""
        export_results = {}
        
        try:
            lines = stdout.strip().split('\n')
            in_export_section = False
            
            for line in lines:
                # Look for "Exported files:" with or without logging prefix
                if 'Exported files:' in line:
                    in_export_section = True
                    continue
                elif in_export_section and '- ' in line and ': ' in line:
                    # Parse file export line: "2025-08-08 16:11:50,425 - INFO -   - touchstone: C:\path\to\file.s2p"
                    # Extract the part after "- INFO -   "
                    if ' - INFO -   - ' in line:
                        export_line = line.split(' - INFO -   - ')[1]
                    elif ' - WARNING -   - ' in line:
                        export_line = line.split(' - WARNING -   - ')[1]
                    elif ' - ERROR -   - ' in line:
                        export_line = line.split(' - ERROR -   - ')[1]
                    elif line.strip().startswith('- '):
                        # Fallback: just strip the line
                        export_line = line.strip()[2:]
                    else:
                        continue
                    
                    # Parse "touchstone: /path/to/file.s2p"
                    parts = export_line.split(': ', 1)
                    if len(parts) == 2:
                        export_type = parts[0].strip()
                        file_path = parts[1].strip()
                        export_results[export_type] = file_path
                elif in_export_section and not line.strip():
                    # Empty line ends the export section
                    break
                        
        except Exception as e:
            self.logger.warning(f"Failed to parse export results: {e}")
        
        return export_results
    
    def _analyze_errors(self, results: List[TaskResult]) -> Dict[str, int]:
        """Analyze error patterns in results"""
        error_summary = {}
        
        for result in results:
            if not result.success and result.error:
                # Categorize errors
                error_msg = result.error.lower()
                
                if 'workspace' in error_msg:
                    key = 'workspace_error'
                elif 'library' in error_msg:
                    key = 'library_error'
                elif 'design' in error_msg:
                    key = 'design_error'
                elif 'simulation' in error_msg:
                    key = 'simulation_error'
                elif 'file not found' in error_msg:
                    key = 'file_not_found'
                elif 'permission' in error_msg:
                    key = 'permission_error'
                else:
                    key = 'other_error'
                
                error_summary[key] = error_summary.get(key, 0) + 1
        
        return error_summary
    
    def execute_single_task(self, task_type: str, task_data: Dict[str, Any]) -> TaskResult:
        """Execute a single task with retry logic"""
        max_retries = self.config.execution_config.max_retries if self.config.execution_config.retry_failed else 0
        
        for attempt in range(max_retries + 1):
            try:
                if task_type == 'design':
                    result = self._create_design_task(task_data)
                elif task_type == 'simulation':
                    result = self._run_simulation_task(task_data)
                else:
                    raise ValueError(f"Unknown task type: {task_type}")
                
                # If successful or no retries left, return result
                if result.success or attempt == max_retries:
                    result.retry_count = attempt
                    return result
                    
                # Wait before retry
                if attempt < max_retries:
                    wait_time = 2 ** attempt  # Exponential backoff
                    self.logger.info(f"Retrying {task_data.get('cell_name', 'unknown')} in {wait_time}s...")
                    time.sleep(wait_time)
                    
            except Exception as e:
                if attempt == max_retries:
                    return TaskResult(
                        task_id=f"{task_type}_{task_data.get('cell_name', 'unknown')}",
                        task_type=task_type,
                        success=False,
                        result={},
                        error=str(e),
                        retry_count=attempt
                    )
                
                # Wait before retry
                wait_time = 2 ** attempt
                self.logger.warning(f"Task failed, retrying in {wait_time}s: {e}")
                time.sleep(wait_time)
        
        # Should never reach here
        return TaskResult(
            task_id=f"{task_type}_{task_data.get('cell_name', 'unknown')}",
            task_type=task_type,
            success=False,
            result={},
            error="Max retries exceeded",
            retry_count=max_retries
        )

def monitor_progress(executor: BatchExecutor, tasks: List[Dict[str, Any]]) -> None:
    """Monitor and display progress of batch execution"""
    print(f"Starting batch execution of {len(tasks)} tasks...")
    
    # This would typically be called from a separate thread or process
    # For now, it's a placeholder for future progress monitoring functionality
    pass

if __name__ == "__main__":
    # Test the executor
    import argparse
    
    parser = argparse.ArgumentParser(description="Batch Executor Test")
    parser.add_argument('--config', type=str, required=True, help='Configuration file')
    parser.add_argument('--test-task', action='store_true', help='Run single test task')
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    try:
        config_manager = ConfigManager()
        config = config_manager.load_config(args.config)
        
        executor = BatchExecutor(config)
        
        if args.test_task:
            # Run a simple test
            test_task = {
                'cell_name': 'test_design',
                'json_file': './test.json'
            }
            
            result = executor.execute_single_task('design', test_task)
            print(f"Test task result: {result.success}")
            
        else:
            # Scan for tasks and execute
            tasks = config_manager.scan_json_files()
            if tasks:
                batch_result = executor.execute_batch_workflow(tasks)
                print(f"Batch execution completed: {batch_result.successful_tasks}/{batch_result.total_tasks} successful")
            else:
                print("No tasks found to execute")
                
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
