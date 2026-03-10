# Data And Model Assets

This repository produces two classes of heavy runtime assets that should not be committed to normal Git history:

- EM simulation outputs and intermediate ADS workspace artifacts
- HDF5 datasets and trained model checkpoints

## Current Policy

- keep source code, configuration templates, and documentation in Git
- keep large datasets and checkpoints outside tracked history
- publish large assets through GitHub Releases, object storage, or Git LFS if needed

Typical local storage locations:

- `Pytorch_Model/models/`
- `Pytorch_Model/data/`
- `Data_process/HDF5_create/hdf5_data/`

## Naming Guidance

- HDF5 datasets: `dataset_<port_count>port_<height>x<width>.h5`
- model checkpoints: `best_model_<dataset_id>.pth`

## Important Status Note

The current local assets are not all schema-compatible with each other.

In particular:

- `Pytorch_Model/models/best_model_legacy_1ch_2port_16x16_pre20260310.pth` is the renamed local legacy 1-channel checkpoint
- `Pytorch_Model/models/best_model_2ch_2port_16x16_20260310.pth` is the validated local 2-channel replacement checkpoint
- the main tracked HDF5 datasets under `Pytorch_Model/data/` and `Data_process/HDF5_create/hdf5_data/` are 2-channel

Compatibility details are documented in:

- [MODEL_DATA_COMPATIBILITY.md](MODEL_DATA_COMPATIBILITY.md)

## Publication Guidance

- do not publish the renamed legacy checkpoint as the canonical current model
- prefer publishing versioned dataset / checkpoint pairs
- treat simulation output directories strictly as runtime artifacts
