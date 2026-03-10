# Workflow

This document describes the intended operational workflow of the project.

## Stage 1: Create Layout Templates

Input:

- process metadata
- layer definitions
- pixelized metal patterns
- port locations

Tooling:

- `Data_process/JSON_layout_create/`

Output:

- one or more layout JSON files

Each layout JSON contains:

- metadata
- per-layer binary matrices
- port definitions

## Stage 2: Build ADS Designs

Input:

- layout JSON files
- layer mapping configuration
- workspace configuration
- PDK or reference technology configuration

Tooling:

- `parallel_version/subprocess_cli_parallel.py`
- `parallel_version/subprocess_worker_parallel.py`

Actions:

- detect ADS Python runtime
- create or open workspace and library
- create cell and layout view
- convert layout matrices to ADS geometry
- place ports using border definitions
- create `rfpro_view`

Output:

- ADS workspace objects
- generated layout and EM views

## Stage 3: Run EM Simulations

Input:

- created ADS design data
- frequency configuration
- export configuration

Actions:

- configure simulation options
- execute RFPro / ADS EM simulation
- export simulation outputs

Output:

- Touchstone `.sNp`
- optional CSV exports
- optional ADS dataset exports

## Stage 4: Build Machine Learning Dataset

Input:

- layout JSON files
- matching `.sNp` files

Tooling:

- `Data_process/HDF5_create/create_hdf5.py`

Actions:

- convert layout matrices to padded tensors
- interpolate S-parameters onto target frequencies
- flatten complex responses into real-valued vectors
- group compatible samples by port count and matrix size
- write HDF5 datasets

Output:

- HDF5 dataset files for training

## Stage 5: Train CNN Surrogate Model

Input:

- HDF5 dataset

Tooling:

- `Pytorch_Model/src/train.py`
- `Pytorch_Model/src/dataset.py`
- `Pytorch_Model/src/model.py`

Actions:

- load HDF5 tensors and metadata
- split into training and validation sets
- build CNN regressor
- train on layout tensors and S-parameter vectors
- save best-performing checkpoint

Output:

- trained `.pth` weights

## Stage 6: Verify Model Behavior

Input:

- HDF5 dataset
- trained model checkpoint

Tooling:

- `Pytorch_Model/src/tools/verify_model.py`

Optional experimental helper:

- `Pytorch_Model/src/tools/experimental_gui/verify_model_gui.py`

Actions:

- run inference on selected samples
- compare predicted and true S-parameter responses
- inspect plots and error metrics
- optionally use the experimental GUI wrapper for ad-hoc local inspection

Output:

- qualitative and quantitative validation results

## Recommended Public Execution Line

The recommended public execution line is:

1. `Data_process/JSON_layout_create/`
2. `parallel_version/`
3. `Data_process/HDF5_create/`
4. `Pytorch_Model/`

`serial_version/` should remain reference material only.

## Known Preconditions

End-to-end runtime validation requires:

- Windows-compatible ADS installation
- ADS Python runtime
- RFPro / EM tooling
- valid license access
- available PDK or reference technology libraries

## Known Repository Constraints

- simulation outputs are runtime artifacts and should not be committed
- training datasets and model weights should not be committed by default
- some historical files reflect the original development machine and require cleanup before publication
