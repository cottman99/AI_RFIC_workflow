# AI_RFIC_workflow

`AI_RFIC_workflow` is a research workflow for pixelized RFIC layout automation on top of Keysight ADS / RFPro.

It covers the full chain:

1. generate or edit pixel-layout JSON templates
2. create ADS workspaces, libraries, cells, layout views, and `rfpro_view`
3. run EM simulations and export Touchstone / CSV / ADS datasets
4. convert layout and EM results into HDF5 datasets
5. train a PyTorch CNN surrogate model that predicts EM responses directly from layout tensors

The repository is publishable and the main technical flow has been runtime-validated, but it still reflects a research workflow rather than a polished end-user product.

## License Model

This repository uses a mixed noncommercial license model:

- source code and scripts: PolyForm Noncommercial 1.0.0
- documentation and non-software materials: CC BY-NC 4.0

This means the repository is source-available for public research and other noncommercial use, but it is not an OSI-approved open source repository.

See:

- [LICENSE](LICENSE)

## Start Here

If you are new to the repository, read these in order:

1. [SETUP.md](docs/core/SETUP.md)
2. [QUICKSTART.md](docs/core/QUICKSTART.md)
3. [CONFIG_REFERENCE.md](docs/core/CONFIG_REFERENCE.md)
4. [WORKFLOW.md](docs/core/WORKFLOW.md)
5. [ARCHITECTURE.md](docs/core/ARCHITECTURE.md)
6. [ADS_MULTI_PYTHON.md](docs/core/ADS_MULTI_PYTHON.md)

Full documentation map:

- [docs/README.md](docs/README.md)

## Repository Structure

```text
AI_RFIC_workflow/
|- Data_process/
|  |- JSON_layout_create/   # layout JSON generation and editing
|  `- HDF5_create/          # JSON + sNp -> HDF5
|- parallel_version/        # recommended public execution line
|- serial_version/          # legacy/reference implementation
|- Pytorch_Model/           # CNN training and verification
`- docs/                    # public documentation
```

## Recommended Mainline

The recommended public execution line is:

1. `Data_process/JSON_layout_create/`
2. `parallel_version/`
3. `Data_process/HDF5_create/`
4. `Pytorch_Model/`

`serial_version/` should be treated as legacy/reference material only.

## Runtime Model

This repository uses two different Python contexts.

### 1. ADS Automation Host

Use a normal Windows Python interpreter for the outer CLI/orchestration layer.

- This can be a standard `venv`, Conda environment, or system Python.
- It does not need `torch` or `scikit-rf`.
- It launches the ADS-installed Python for ADS-specific work.

Required environment variables:

```powershell
$env:ADS_PYTHON = "C:\Path\To\ADS\tools\python\python.exe"
$env:ADS_INSTALL_DIR = "C:\Path\To\ADS"
```

You can also start from:

- [`.env.example`](.env.example)

Optional but commonly needed:

```powershell
$env:PDK_DIR = "C:\Path\To\PDK"
$env:PDK_TECH_DIR = "C:\Path\To\PDK_Tech"
$env:SUBSTRATE = "your_substrate_name"
```

### 2. HDF5 / PyTorch Host

Use a separate Python environment for HDF5 creation, training, and verification.

Install packages with:

```bash
pip install -r requirements.txt
```

Important:

- do not install repository ML dependencies into the ADS internal Python runtime
- ADS-internal Python is only for Keysight modules invoked by the automation layer
- `requirements.txt` is for the HDF5 / ML environment

See [ENVIRONMENTS.md](docs/reference/ENVIRONMENTS.md).

## What Has Been Validated

Validated on March 10, 2026:

- `parallel_version/` single-sample workflow: passed
- `parallel_version/` 3-sample parallel batch workflow: passed
- `Data_process/HDF5_create/create_hdf5.py`: passed on real generated `.s2p` files
- `Pytorch_Model/src/train.py`: passed with smoke and retraining runs
- `Pytorch_Model/src/tools/verify_model.py`: passed with a current 2-channel checkpoint

Validation evidence and compatibility notes:

- [RUNTIME_VALIDATION_RESULTS.md](docs/maintenance/RUNTIME_VALIDATION_RESULTS.md)
- [MODEL_DATA_COMPATIBILITY.md](docs/reference/MODEL_DATA_COMPATIBILITY.md)
- [RETRAIN_2CH_CHECKPOINT.md](docs/maintenance/RETRAIN_2CH_CHECKPOINT.md)

## Key Constraints

- end-to-end execution requires Windows, Keysight ADS / RFPro, valid licenses, and an accessible PDK or reference technology library
- large HDF5 datasets and model checkpoints are intentionally not tracked by Git
- a historical 1-channel checkpoint exists only as a local legacy artifact and should not be treated as the canonical current model

## Additional Documentation

- [Documentation Map](docs/README.md)
- [Glossary](docs/core/GLOSSARY.md)
- [Data And Model Assets](docs/reference/DATA_AND_MODEL_ASSETS.md)
- [Runtime Validation Results](docs/maintenance/RUNTIME_VALIDATION_RESULTS.md)
