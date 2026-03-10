# Setup

This document explains how to prepare a usable environment for `AI_RFIC_workflow`.

## Supported Platform

Current validated platform:

- Windows
- Keysight ADS / RFPro available locally
- valid ADS / RFPro license
- accessible PDK or reference technology library

The repository is not currently documented as a Linux or macOS workflow.

## Environment Overview

The repository intentionally splits work across two Python contexts:

1. an ADS orchestration environment
2. an HDF5 / PyTorch environment

This separation is important.

- The ADS orchestration environment launches ADS and its internal Python.
- The HDF5 / PyTorch environment carries `torch`, `h5py`, `scikit-rf`, plotting, and training tools.
- You should not try to turn the ADS internal Python into a full ML environment.

## A. ADS Orchestration Environment

Use any standard Windows Python environment for the outer CLI layer.

Validated example versions:

- standard Python `3.13.2` for orchestration
- ADS internal Python provided by ADS itself

You can create a local venv like this:

```powershell
python -m venv .venv-ads
.\.venv-ads\Scripts\Activate.ps1
python --version
```

The outer orchestration layer primarily uses the Python standard library plus repository code, so no extra `pip` packages are required for the ADS CLI path.

### Required ADS Variables

Set these before running ADS-related commands:

```powershell
$env:ADS_PYTHON = "C:\Path\To\ADS\tools\python\python.exe"
$env:ADS_INSTALL_DIR = "C:\Path\To\ADS"
```

If you prefer to keep a reusable local template, start from:

- [`.env.example`](../.env.example)

Important:

- the repository does not automatically load `.env`
- this file is a configuration template, not a built-in environment loader
- you still need to export variables in your shell or load them with your own tooling

Optional but usually needed for real PDK-based flows:

```powershell
$env:PDK_DIR = "C:\Path\To\PDK"
$env:PDK_TECH_DIR = "C:\Path\To\PDK_Tech"
$env:SUBSTRATE = "your_substrate_name"
```

### ADS Internal Python

`ADS_PYTHON` should point to the Python interpreter shipped with ADS, for example:

```text
C:\Path\To\ADS\tools\python\python.exe
```

Do not install `requirements.txt` into that interpreter.

Its role is:

- import `keysight.ads.de`
- import `keysight.ads.emtools`
- execute workspace/design/simulation tasks inside the ADS environment

Important clarification:

- you do not normally need to configure multiple ADS Python paths by hand
- the repository starts one ADS worker interpreter and then switches between ADS and RFPro / EMPro execution contexts internally
- this context switching is implemented with `keysight.edatoolbox.multi_python`

See [ADS_MULTI_PYTHON.md](ADS_MULTI_PYTHON.md) for the detailed mechanism.

## B. HDF5 / PyTorch Environment

Use a separate Python environment for:

- HDF5 creation
- HDF5 inspection
- model training
- model verification

Validated example version:

- Python `3.12.11`

Create a venv:

```powershell
python -m venv .venv-ml
.\.venv-ml\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Or a Conda environment:

```powershell
conda create -n rfic-ai python=3.12
conda activate rfic-ai
pip install -r requirements.txt
```

Packages expected in this environment:

- `numpy`
- `matplotlib`
- `h5py`
- `scikit-rf`
- `tqdm`
- `pandas`
- `torch`

## PDK And Config Preparation

For the ADS batch flow, start from:

- [batch_config_pdk.json](../parallel_version/config_examples/batch_config_pdk.json)
- [frequency_config.json](../parallel_version/config_examples/frequency_config.json)
- [layer_mapping.json](../parallel_version/config_examples/layer_mapping.json)

Important behavior:

- relative paths in the batch config are now resolved relative to the config file location
- this means users can run the CLI from the repository root without breaking the sample config layout

See [CONFIG_REFERENCE.md](CONFIG_REFERENCE.md).

## Sanity Checks

ADS-side sanity check:

```powershell
& $env:ADS_PYTHON -c "import keysight.ads.de, keysight.ads.emtools; print('ADS Python OK')"
```

ML-side sanity check:

```powershell
python -c "import torch, h5py, skrf; print('ML Python OK')"
```

## Next Step

After setup, continue with:

- [QUICKSTART.md](QUICKSTART.md)
