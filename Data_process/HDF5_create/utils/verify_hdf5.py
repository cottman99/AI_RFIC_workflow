#!/usr/bin/env python3
"""
Verify the contents of the created HDF5 file.
"""

import h5py
import numpy as np
import os
import argparse

def verify_hdf5(hdf5_path):
    """Verify the contents of the HDF5 file."""
    if not os.path.exists(hdf5_path):
        print(f"File {hdf5_path} does not exist")
        return
    
    try:
        with h5py.File(hdf5_path, 'r') as f:
            print(f"Successfully opened: {hdf5_path}")
            
            # List all groups and datasets
            def print_structure(name, obj):
                if isinstance(obj, h5py.Dataset):
                    print(f"Dataset: {name}, shape: {obj.shape}, dtype: {obj.dtype}")
                elif isinstance(obj, h5py.Group):
                    print(f"Group: {name}")
            
            print("\nFile structure:")
            f.visititems(print_structure)
            
            # Check metadata
            if 'metadata' in f:
                meta = f['metadata']
                print("\nMetadata:")
                for key in meta.keys():
                    print(f"  {key}: {meta[key][:]} (shape: {meta[key].shape})")
                
                # Print attributes
                print("\nMetadata attributes:")
                for key, value in meta.attrs.items():
                    print(f"  {key}: {value}")
            
            # Check data shapes
            if 'layouts' in f:
                layouts = f['layouts']
                print(f"\nLayouts dataset: shape={layouts.shape}, dtype={layouts.dtype}")
                
            if 's_params' in f:
                s_params = f['s_params']
                print(f"S-parameters dataset: shape={s_params.shape}, dtype={s_params.dtype}")
                
            print(f"\nTotal samples: {layouts.shape[0] if 'layouts' in f else 0}")
            
    except Exception as e:
        print(f"Error reading HDF5 file: {e}")


def main():
    parser = argparse.ArgumentParser(description="Verify the contents of the created HDF5 file.")
    parser.add_argument("hdf5_path", help="Path to the HDF5 file to verify")
    args = parser.parse_args()
    
    verify_hdf5(args.hdf5_path)

if __name__ == "__main__":
    main()