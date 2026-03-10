# Retrain 2-Channel Checkpoint

This document records the local retraining run performed on March 10, 2026 to replace the renamed legacy 1-channel checkpoint `best_model_legacy_1ch_2port_16x16_pre20260310.pth`.

## Input Dataset

```text
Pytorch_Model/data/dataset_2port_16x16.h5
```

Dataset properties:

- samples: `600`
- layout tensor shape: `(600, 2, 18, 18)`
- output tensor shape: `(600, 42)`
- port count: `2`
- base matrix shape: `16 x 16`

## Command Used

Working directory:

```text
Pytorch_Model/src
```

Interpreter:

```text
Dedicated ML environment validated with Python 3.12.11
```

Command:

```bash
python train.py \
  --hdf5_path ../data/dataset_2port_16x16.h5 \
  --epochs 5 \
  --batch_size 16 \
  --learning_rate 1e-3 \
  --output_dir ../models \
  --checkpoint_name best_model_2ch_2port_16x16_20260310.pth \
  --seed 42
```

## Output Files

Local-only outputs:

- `Pytorch_Model/models/best_model_2ch_2port_16x16_20260310.pth`
- `Pytorch_Model/models/best_model_2ch_2port_16x16_20260310.json`
- `Pytorch_Model/models/best_model_2ch_2port_16x16_20260310_sample0.png`

These files are intentionally not tracked by Git because `Pytorch_Model/models/` is ignored.

## Result Summary

Training trace:

- epoch 1: train `0.101738`, val `0.006626`
- epoch 2: train `0.015528`, val `0.004049`
- epoch 3: train `0.009218`, val `0.009545`
- epoch 4: train `0.006637`, val `0.010563`
- epoch 5: train `0.004458`, val `0.009193`

Best validation loss:

```text
0.004049051116453484
```

Single-sample verification on sample `0`:

```text
MSE = 0.003831
```

## Release Guidance

If you later want to publish a model artifact, this retrained 2-channel checkpoint is the correct starting point, not the renamed legacy checkpoint `best_model_legacy_1ch_2port_16x16_pre20260310.pth`.

Before public release, consider:

1. retraining for more epochs with a tracked experiment log
2. exporting a versioned manifest together with the checkpoint
3. keeping the legacy checkpoint name explicit so the schema difference stays obvious
