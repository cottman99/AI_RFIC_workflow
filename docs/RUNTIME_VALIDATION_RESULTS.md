# Runtime Validation Results

Validation date: March 10, 2026

This document records what was actually validated after repository cleanup.

## Environment Used

ADS automation:

- outer Python: a local Windows orchestration environment validated with Python `3.13.2`
- ADS Python: the ADS 2026 Update1 bundled Python runtime
- ADS install root: a local ADS 2026 Update1 installation
- PDK: `DemoKit_Non_Linear`
- PDK tech library: `DemoKit_Non_Linear_tech`
- substrate: `demo`

ML workflow:

- Python: a local ML environment validated with Python `3.12.11`

## Validated Pipeline Stages

### ADS / EM Flow

Passed:

- ADS runtime detection
- JSON sample parsing
- workspace creation
- library creation
- layout and `rfpro_view` creation
- single-sample simulation
- 3-sample parallel batch simulation
- Touchstone export

### Dataset And ML Flow

Passed:

- HDF5 inspection
- HDF5 generation from real `.s2p` results
- 1-epoch training smoke test
- direct verification / inference script
- 5-epoch retraining of a new local 2-channel checkpoint on the 600-sample dataset

## Important Fixes Confirmed During Validation

### 1. Reference Library Inference

Problem:

- `create-design-only` could create a design whose substrate reference resolved to the target design library instead of the PDK tech library
- this caused RFPro EM loading to fail with substrate-read errors

Fix:

- `parallel_version/subprocess_cli_parallel.py` now infers the best reference library from workspace `lib.defs`

Result:

- default design creation and simulation now work without manually passing `--ref-library-name`

### 2. Batch Config BOM Compatibility

Problem:

- Windows-generated JSON config files with UTF-8 BOM failed in `batch_config.py`

Fix:

- `parallel_version/batch_config.py` now reads config and JSON assets with `utf-8-sig`

Result:

- both BOM and non-BOM config files validate successfully

### 3. Tool Script Import Reliability

Problem:

- `Pytorch_Model/src/tools/verify_model.py` failed when executed directly because `dataset` was not importable from that working mode

Fix:

- both verification tools now support direct execution and module execution

Result:

- `python verify_model.py ...` and `python -m tools.verify_model ...` both work

## Legacy Model Boundary

The former legacy checkpoint was renamed locally to:

```text
Pytorch_Model/models/best_model_legacy_1ch_2port_16x16_pre20260310.pth
```

It is not compatible with the current 2-channel datasets and should remain a local legacy artifact.

See:

- [MODEL_DATA_COMPATIBILITY.md](MODEL_DATA_COMPATIBILITY.md)

## Local Replacement Checkpoint

A new local replacement checkpoint was generated during validation:

- `Pytorch_Model/models/best_model_2ch_2port_16x16_20260310.pth`
- matching manifest:
  `Pytorch_Model/models/best_model_2ch_2port_16x16_20260310.json`

Training summary:

- dataset: `Pytorch_Model/data/dataset_2port_16x16.h5`
- samples: `600`
- input channels: `2`
- output dimension: `42`
- epochs: `5`
- batch size: `16`
- seed: `42`
- best validation loss: about `0.004049`

Single-sample verification:

- sample `0` MSE: about `0.003831`

This checkpoint is local-only because `Pytorch_Model/models/` is intentionally ignored by Git.

See:

- [RETRAIN_2CH_CHECKPOINT.md](RETRAIN_2CH_CHECKPOINT.md)
