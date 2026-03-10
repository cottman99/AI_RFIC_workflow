# HDF5 Utilities

This directory contains secondary inspection helpers for the HDF5 dataset stage.

## Included Scripts

- `verify_hdf5.py`: inspect file structure, datasets, and metadata inside an HDF5 file
- `validate_snp_files.py`: scan `.s2p` files and report invalid or incomplete files

## Repository Position

These scripts are useful for troubleshooting and dataset hygiene, but they are not part of the primary public workflow.

The main HDF5 entry point remains:

- `../create_hdf5.py`
