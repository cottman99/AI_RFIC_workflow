# Model And Data Compatibility

This document records the current compatibility status of local HDF5 assets and model checkpoints.

## Verified Assets

| Asset | Samples | Layout shape | S-parameter shape | Notes |
| --- | ---: | --- | --- | --- |
| `Data_process/HDF5_create/hdf5_data/dataset_2port_16x16.h5` | 10 | `(10, 2, 18, 18)` | `(10, 42)` | 2-channel dataset |
| `Pytorch_Model/data/dataset_2port_16x16.h5` | 600 | `(600, 2, 18, 18)` | `(600, 42)` | 2-channel dataset |
| `Data_process/JSON_layout_create/tmp/hdf5/small_set/dataset_2port_16x16.h5` | 10 | `(10, 1, 18, 18)` | `(10, 42)` | 1-channel dataset |
| `Data_process/JSON_layout_create/tmp/hdf5/large_set/dataset_2port_16x16.h5` | 100 | `(100, 1, 18, 18)` | `(100, 42)` | 1-channel dataset |
| `Pytorch_Model/models/best_model_legacy_1ch_2port_16x16_pre20260310.pth` | n/a | expects `1` input channel | outputs `42` values | about `310,110,453` bytes |
| `Pytorch_Model/models/best_model_2ch_2port_16x16_20260310.pth` | n/a | expects `2` input channels | outputs `42` values | local replacement checkpoint |

## Key Finding

`best_model_legacy_1ch_2port_16x16_pre20260310.pth` is not compatible with the current 2-channel dataset stored in:

- `Pytorch_Model/data/dataset_2port_16x16.h5`
- `Data_process/HDF5_create/hdf5_data/dataset_2port_16x16.h5`

Observed mismatch:

- checkpoint first convolution expects `1` input channel
- current main HDF5 datasets provide `2` channels

This causes `load_state_dict()` or downstream verification to fail when the current code builds a 2-channel model.

## Evidence

Validated facts:

- `Pytorch_Model/data/dataset_2port_16x16.h5` has shape `(600, 2, 18, 18)`
- `Data_process/HDF5_create/hdf5_data/dataset_2port_16x16.h5` has shape `(10, 2, 18, 18)`
- `best_model_legacy_1ch_2port_16x16_pre20260310.pth` stores `feature_extractor.0.weight` with shape `(64, 1, 3, 3)`
- `best_model_legacy_1ch_2port_16x16_pre20260310.pth` stores `regressor.13.weight` with output dimension `42`
- `best_model_2ch_2port_16x16_20260310.pth` loads successfully with the current 2-channel model definition

In contrast, historical temporary HDF5 assets under:

- `Data_process/JSON_layout_create/tmp/hdf5/small_set/`
- `Data_process/JSON_layout_create/tmp/hdf5/large_set/`

are both 1-channel datasets and match the checkpoint's input-channel expectation.

## Likely Provenance

The most likely interpretation is:

1. `best_model_legacy_1ch_2port_16x16_pre20260310.pth` was trained on an earlier single-layer / single-channel dataset
2. the repository later evolved to 2-layer / 2-channel layout tensors
3. the tracked checkpoint was not retrained or renamed after that schema change

This is consistent with the repository state:

- historical JSON generator outputs in `JSON_layout_data/small_set` and `large_set` are single-layer
- current public example JSON in `parallel_version/config_examples/json_layout/` is 2-layer
- current training code dynamically uses dataset channel count, so the code is newer than the checkpoint

## Release Guidance

Do not publish `Pytorch_Model/models/best_model_legacy_1ch_2port_16x16_pre20260310.pth` as the canonical current model.

Use one of these options instead:

1. Retrain a new checkpoint on the current 2-channel dataset and publish that as the primary model.
2. Keep the current checkpoint only as a legacy artifact and rename it explicitly:
   `best_model_legacy_1ch_2port_16x16_pre20260310.pth`
3. Publish a matching 1-channel HDF5 dataset together with the legacy checkpoint and document the schema.

## Recommended Next Step

The cleanest public-state fix is:

- keep current code
- keep current 2-channel dataset schema
- retrain and republish a 2-channel checkpoint
