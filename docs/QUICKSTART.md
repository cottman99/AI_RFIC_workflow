# Quickstart

This document gives the shortest practical path through the repository.

## Before You Start

Complete setup first:

- [SETUP.md](SETUP.md)

## Quickstart A: Validate ADS Batch Configuration

This is the best first command for a new user because it checks the config structure before creating any designs.

From the repository root:

```powershell
python .\parallel_version\batch_processor.py validate-config --config .\parallel_version\config_examples\batch_config_pdk.json
```

Before running it, edit:

- `parallel_version/config_examples/batch_config_pdk.json`

At minimum, set:

- `pdk_config.pdk_dir`
- `pdk_config.pdk_tech_dir`
- `substrate`

If the config validates, you have the repository and environment wired together correctly.

## Quickstart B: Run the Small Parallel ADS Flow

From the repository root:

```powershell
python .\parallel_version\batch_processor.py process-config --config .\parallel_version\config_examples\batch_config_pdk.json
```

This will:

1. create or open the target workspace
2. create the target library
3. create designs from JSON files in `config_examples/json_layout/`
4. run EM simulations
5. export results to the configured output directory

Recommended first-time behavior:

- keep `max_workers` small
- keep `batch_size` small
- use the sample `json_layout/` directory first

## Quickstart C: Build HDF5 From Simulation Results

After the ADS flow produces `.sNp` files, create an HDF5 dataset.

From the repository root:

```powershell
python .\Data_process\HDF5_create\create_hdf5.py --json_dir .\parallel_version\config_examples\json_layout --snp_dir .\parallel_version\batch_results --output_dir .\Data_process\HDF5_create\datasets
```

This groups compatible layouts and S-parameter files into HDF5 datasets.

## Quickstart D: Train A Model

After you have an HDF5 dataset, move to the ML environment and train a checkpoint.

From `Pytorch_Model/src/`:

```powershell
python train.py --hdf5_path "<path-to-your-dataset.h5>" --epochs 5 --batch_size 16 --checkpoint_name best_model_2ch_2port_16x16.pth
```

If you prefer to keep datasets under `Pytorch_Model/data/`, point `--hdf5_path` there explicitly.

## Quickstart E: Verify A Trained Model

From `Pytorch_Model/src/`:

```powershell
python tools\verify_model.py --hdf5_path "<path-to-your-dataset.h5>" --model_path ..\models\best_model_2ch_2port_16x16.pth --sample_index 0
```

## What Is Not Included By Default

The repository does not ship large runtime assets in Git history:

- ADS workspaces
- batch results
- HDF5 datasets
- trained model checkpoints

So a new user should expect to either:

1. generate data locally, or
2. add externally stored datasets/checkpoints later

## Recommended Reading After Quickstart

- [CONFIG_REFERENCE.md](CONFIG_REFERENCE.md)
- [WORKFLOW.md](WORKFLOW.md)
- [Pytorch_Model/README.md](../Pytorch_Model/README.md)
