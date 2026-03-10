# Model Verification Tools

This directory contains the model verification utilities for the PyTorch stage.

## Scripts

- `verify_model.py`: CLI verification and plotting
- `verify_model_gui.py`: GUI wrapper for interactive verification

Both tools now support:

- direct script execution
- module execution with `python -m`

## Recommended Usage

Run from `Pytorch_Model/src/`.

Direct execution:

```bash
python tools/verify_model.py --hdf5_path "<path-to-your-dataset.h5>" --model_path "../models/best_model_2ch_2port_16x16.pth" --sample_index 0
```

Module execution:

```bash
python -m tools.verify_model --hdf5_path "<path-to-your-dataset.h5>" --model_path "../models/best_model_2ch_2port_16x16.pth" --sample_index 0
```

## Legacy Compatibility Note

The old 1-channel checkpoint was renamed locally to:

```text
Pytorch_Model/models/best_model_legacy_1ch_2port_16x16_pre20260310.pth
```

It only matches the older 1-channel datasets such as:

```text
Data_process/JSON_layout_create/tmp/hdf5/small_set/dataset_2port_16x16.h5
Data_process/JSON_layout_create/tmp/hdf5/large_set/dataset_2port_16x16.h5
```

Do not use that legacy checkpoint with the current 2-channel dataset in `Pytorch_Model/data/`.
