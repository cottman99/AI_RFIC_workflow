# Validation Plan

This document defines the recommended validation order for the repository after cleanup. It is intentionally staged from low risk to high risk.

## Scope

This plan is for the next phase, when the ADS / RFPro environment is ready.

It does not assume that full EM simulation should be run immediately. The goal is to validate the pipeline incrementally and isolate failures early.

## Validation Order

### 1. Repository-Level Sanity Checks

Goal:

- confirm that the cleaned repository still has valid entry points
- confirm that configuration files resolve correctly

Checks:

- Python syntax check for edited scripts
- config file presence and path normalization
- sample JSON readability

Suggested targets:

- `parallel_version/subprocess_cli_parallel.py`
- `parallel_version/batch_processor.py`
- `Data_process/HDF5_create/create_hdf5.py`
- `Pytorch_Model/src/train.py`

### 2. ADS Runtime Detection

Goal:

- verify that ADS runtime discovery works with the cleaned configuration model

Preconditions:

- `ADS_PYTHON` or `ADS_INSTALL_DIR` set, or ADS installed in a known location

Checks:

- CLI can detect ADS Python
- subprocess handoff works
- failure messages are readable when detection fails

Suggested entry points:

- `parallel_version/subprocess_cli_parallel.py`
- `serial_version/subprocess_cli.py`

### 3. JSON Input Validation

Goal:

- verify that selected sample layouts are structurally valid

Checks:

- metadata fields exist
- matrix dimensions match `base_matrix_shape`
- port layers exist in layout matrices
- layer mapping file resolves

Suggested sample source:

- `parallel_version/config_examples/json_layout/`

### 4. Workspace Creation

Goal:

- verify that a clean workspace and library can be created without running a full simulation

Checks:

- workspace creation succeeds
- library creation succeeds
- PDK or reference technology setup is accepted

Suggested command family:

- `create-workspace-lib`

### 5. Design Creation

Goal:

- verify that a JSON layout can be converted into ADS geometry and ports

Checks:

- layout view exists
- geometry generation succeeds
- port placement succeeds
- `rfpro_view` creation succeeds or fails with a clear message

Suggested command family:

- `create-design-only`

### 6. Single Simulation Dry Run

Goal:

- validate EM execution path on a single design before any batch run

Checks:

- frequency plan loads
- simulation starts
- export directory is written correctly
- Touchstone output exists

Suggested command family:

- `run-simulation-only`

### 7. Single End-to-End Batch

Goal:

- validate the full public mainline with the smallest possible sample set

Checks:

- one or a few JSON inputs
- one batch config
- correct output file inventory
- readable report generation

Suggested entry point:

- `parallel_version/batch_processor.py`

### 8. Dataset Construction

Goal:

- verify that exported `.sNp` files can be matched and converted into HDF5

Checks:

- valid sample pairing
- HDF5 metadata correctness
- expected tensor dimensions

Suggested entry point:

- `Data_process/HDF5_create/create_hdf5.py`

### 9. Model Training Smoke Test

Goal:

- confirm that the ML stage still starts correctly on the cleaned repository

Checks:

- dataset load succeeds
- model builds correctly
- one short training run completes
- checkpoint save path works

Suggested entry point:

- `Pytorch_Model/src/train.py`

## Recommended First Real Validation Session

When the environment is ready, the first real validation session should be:

1. ADS runtime detection
2. one sample JSON validation
3. one workspace creation
4. one design creation
5. one simulation-only run

Only after these succeed should batch execution and ML stages be validated.

## Known Risk Areas

- ADS installation discovery
- PDK path correctness
- RFPro view creation
- export path handling
- historical encoding assumptions in console output
- historical JSON files outside curated example directories

