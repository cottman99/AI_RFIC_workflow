#!/usr/bin/env python3
"""
Validate S-parameter files and filter out incomplete ones.
"""

import os
import skrf as rf
import argparse
from pathlib import Path

def validate_snp_file(filepath):
    """Validate if a .s2p file is complete and readable."""
    try:
        network = rf.Network(filepath)
        # Check if file has actual data
        if len(network.f) == 0:
            return False, "No frequency data"
        if network.s.shape[0] == 0:
            return False, "No S-parameter data"
        return True, "Valid"
    except Exception as e:
        return False, str(e)

def main():
    parser = argparse.ArgumentParser(description='Validate S-parameter files')
    parser.add_argument('--snp_dir', required=True, help='Directory containing .s2p files')
    parser.add_argument('--output_dir', help='Directory to move valid files to')
    
    args = parser.parse_args()
    
    snp_dir = Path(args.snp_dir)
    
    if not snp_dir.exists():
        print(f"Directory {snp_dir} does not exist")
        return
    
    # Get all .s2p files
    snp_files = list(snp_dir.glob('*.s2p'))
    
    print(f"Found {len(snp_files)} .s2p files")
    
    valid_files = []
    invalid_files = []
    
    for filepath in snp_files:
        is_valid, message = validate_snp_file(filepath)
        
        if is_valid:
            valid_files.append(filepath)
            print(f"VALID: {filepath.name}: {message}")
        else:
            invalid_files.append(filepath)
            print(f"INVALID: {filepath.name}: {message}")
    
    print(f"\nSummary:")
    print(f"Valid files: {len(valid_files)}")
    print(f"Invalid files: {len(invalid_files)}")
    
    if invalid_files:
        print("\nInvalid files:")
        for f in invalid_files:
            print(f"  - {f.name}")

if __name__ == "__main__":
    main()