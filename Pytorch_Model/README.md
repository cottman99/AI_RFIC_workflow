# Pytorch_Model

This directory contains the CNN surrogate-model stage of the project.

## Scope

Files here cover:

- loading HDF5 layout / S-parameter datasets
- building a CNN regressor
- training a checkpoint
- verifying predictions against stored samples

Main entry points:

- `src/train.py`
- `src/tools/verify_model.py`

Optional experimental helper:

- `src/tools/experimental_gui/verify_model_gui.py`

## Recommended Python Environment

Use a dedicated ML environment that installs:

```bash
pip install -r ../requirements.txt
```

Recommended characteristics:

- separate from the ADS orchestration environment
- regular Python environment such as `venv` or Conda
- includes `torch`, `h5py`, and `scikit-rf`

See:

- [ENVIRONMENTS.md](../docs/reference/ENVIRONMENTS.md)

## Quick Start

From `Pytorch_Model/src/`:

```bash
python train.py --hdf5_path "<path-to-your-dataset.h5>" --epochs 50 --batch_size 4 --checkpoint_name "best_model_2ch_2port_16x16.pth"
```

Direct verification:

```bash
python tools/verify_model.py --hdf5_path "<path-to-your-dataset.h5>" --model_path "../models/best_model_2ch_2port_16x16.pth" --sample_index 0
```

Module-mode verification:

```bash
python -m tools.verify_model --hdf5_path "<path-to-your-dataset.h5>" --model_path "../models/best_model_2ch_2port_16x16.pth" --sample_index 0
```

## Compatibility Status

Legacy local checkpoint:

```text
Pytorch_Model/models/best_model_legacy_1ch_2port_16x16_pre20260310.pth
```

Current state:

- it expects `1` input channel
- the main current dataset `Pytorch_Model/data/dataset_2port_16x16.h5` provides `2` channels

So this checkpoint should be treated as a legacy artifact only.

## Local Replacement Checkpoint

A validated 2-channel checkpoint was retrained on March 10, 2026:

```text
Pytorch_Model/models/best_model_2ch_2port_16x16_20260310.pth
```

Matching local manifest:

```text
Pytorch_Model/models/best_model_2ch_2port_16x16_20260310.json
```

These files are local-only because `Pytorch_Model/models/` is ignored by Git.

The training script now defaults to a non-legacy output name:

```text
best_model_2ch_2port_16x16.pth
```

For public documentation and first-time user examples, prefer the generic name above.
Use the date-stamped filename only when referring to the specific local validation artifact.

See:

- [MODEL_DATA_COMPATIBILITY.md](../docs/reference/MODEL_DATA_COMPATIBILITY.md)
- [RETRAIN_2CH_CHECKPOINT.md](../docs/maintenance/RETRAIN_2CH_CHECKPOINT.md)
- [ENVIRONMENTS.md](../docs/reference/ENVIRONMENTS.md)

## Smoke-Test Status

Validated on March 10, 2026:

- HDF5 loading: passed
- 1-epoch training run on a generated 3-sample dataset: passed
- 5-epoch retraining on the 600-sample 2-channel dataset: passed
- verification script with the retrained 2-channel checkpoint: passed
