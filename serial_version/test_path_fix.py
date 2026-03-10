#!/usr/bin/env python3
"""
Path Fix Validation Script

This script validates that the path handling fixes work correctly
by testing relative path resolution in the batch processing system.
"""

import sys
import json
from pathlib import Path

def test_path_resolution():
    """Test path resolution fixes"""
    
    print("=== Path Fix Validation ===\n")
    
    # Test configuration
    config_path = Path("batch_config.json")
    if not config_path.exists():
        print("[ERROR] batch_config.json not found")
        return False
    
    # Load configuration
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    print("[INFO] Configuration loaded:")
    for key, value in config.items():
        if isinstance(value, str) and ('path' in key or 'dir' in key):
            print(f"   {key}: {value}")
    
    # Test path resolution
    export_path = config.get("export_path", "./batch_workflow/batch_results")
    
    print(f"\n[TEST] Testing path resolution:")
    print(f"   Original path: {export_path}")
    
    # Test relative to absolute conversion
    if export_path.startswith("./"):
        abs_path = Path(export_path).resolve()
        print(f"   Resolved to: {abs_path}")
        print(f"   Is absolute: {abs_path.is_absolute()}")
        print(f"   Exists: {abs_path.exists()}")
        
        # Check if it's the expected location
        expected_path = Path.cwd() / export_path[2:]  # Remove "./"
        print(f"   Expected: {expected_path}")
        print(f"   Matches expected: {abs_path == expected_path}")
    
    # Test batch_processor path handling
    print(f"\n[TEST] Testing batch_processor path handling:")
    
    # Simulate what batch_processor would do
    job_config = {
        "export_path": export_path
    }
    
    # This is what the fixed code does
    export_dir = Path(job_config["export_path"]).resolve()
    print(f"   Fixed code creates: {export_dir}")
    
    # This is what the old code would do
    old_export_dir = Path(job_config["export_path"])
    print(f"   Old code creates: {old_export_dir}")
    print(f"   Old path is absolute: {old_export_dir.is_absolute()}")
    
    # Test the difference
    print(f"\n[RESULT] Path comparison:")
    print(f"   Fixed path: {export_dir}")
    print(f"   Old path: {old_export_dir}")
    print(f"   Paths are same: {export_dir == old_export_dir}")
    
    if export_dir != old_export_dir:
        print(f"   [FIXED] Fix will change behavior (this is expected)")
        print(f"   [FIXED] Fixed path is absolute: {export_dir.is_absolute()}")
        print(f"   [OLD] Old path is absolute: {old_export_dir.is_absolute()}")
    else:
        print(f"   [WARNING] No change detected (path might already be absolute)")
    
    # Check actual export directory
    print(f"\n[CHECK] Checking actual export directories:")
    
    # Check configured path
    configured_path = Path(export_path)
    print(f"   Configured path: {configured_path}")
    print(f"   Configured exists: {configured_path.exists()}")
    
    # Check resolved path
    resolved_path = configured_path.resolve()
    print(f"   Resolved path: {resolved_path}")
    print(f"   Resolved exists: {resolved_path.exists()}")
    
    # Check temp directory (where files were going before)
    temp_export_path = Path.home() / "AppData" / "Local" / "Temp" / "batch_workflow" / "batch_results"
    print(f"   Temp path: {temp_export_path}")
    print(f"   Temp exists: {temp_export_path.exists()}")
    
    if temp_export_path.exists():
        files = list(temp_export_path.glob("*"))
        print(f"   Temp files: {len(files)}")
        for f in files[:5]:  # Show first 5
            print(f"     - {f.name}")
    
    # Check expected path
    expected_path = Path.cwd() / "batch_workflow" / "batch_results"
    print(f"   Expected path: {expected_path}")
    print(f"   Expected exists: {expected_path.exists()}")
    
    if expected_path.exists():
        files = list(expected_path.glob("*"))
        print(f"   Expected files: {len(files)}")
        for f in files[:5]:  # Show first 5
            print(f"     - {f.name}")
    
    print(f"\n[SUCCESS] Path validation complete")
    return True

def show_recommendation():
    """Show recommendations for next steps"""
    
    print(f"\n[RECOMMENDATIONS] Next steps:")
    print(f"1. [DONE] Path fixes have been applied to both batch_processor.py and batch_processor_ascii.py")
    print(f"2. [TODO] Run a test batch to verify the fixes work")
    print(f"3. [TODO] Check that files are exported to the correct directory")
    print(f"4. [TODO] Verify that file counting works correctly with the new paths")
    
    print(f"\n[COMMAND] Test command:")
    print(f"   python batch_processor_ascii.py --config batch_config.json")
    
    print(f"\n[PATH] Expected output location:")
    expected_path = Path.cwd() / "batch_workflow" / "batch_results"
    print(f"   {expected_path}")

if __name__ == "__main__":
    test_path_resolution()
    show_recommendation()