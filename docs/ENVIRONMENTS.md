# Environments

This document describes the runtime model of `AI_RFIC_workflow` from a user-facing perspective.

## Overview

The repository uses two Python contexts:

1. a normal Python interpreter for orchestration
2. the ADS-installed Python interpreter for ADS-specific tasks
3. a separate normal Python interpreter for HDF5 / PyTorch work

In practice this means:

- ADS automation is launched from a standard Python environment on Windows
- ADS-specific work runs inside the ADS Python shipped by Keysight
- HDF5 and ML work should run in a separate environment with `torch`, `h5py`, and `scikit-rf`

## ADS Orchestration Environment

Recommended characteristics:

- Windows Python
- standard `venv`, Conda env, or system Python
- no repository-specific `pip` dependencies required for the CLI layer

Validated orchestration example:

- Python `3.13.2`

Typical setup:

```powershell
python -m venv .venv-ads
.\.venv-ads\Scripts\Activate.ps1
```

Required ADS variables:

```powershell
$env:ADS_PYTHON = "C:\Path\To\ADS\tools\python\python.exe"
$env:ADS_INSTALL_DIR = "C:\Path\To\ADS"
```

Optional PDK variables:

```powershell
$env:PDK_DIR = "C:\Path\To\PDK"
$env:PDK_TECH_DIR = "C:\Path\To\PDK_Tech"
$env:SUBSTRATE = "your_substrate_name"
```

## ADS Internal Python

`ADS_PYTHON` should point to the Python interpreter bundled with ADS.

Its job is to provide:

- `keysight.ads.de`
- `keysight.ads.emtools`
- workspace/layout/simulation execution inside the ADS runtime

Do not treat it as the main repository environment.

Do not install `requirements.txt` into it.

## HDF5 / PyTorch Environment

Recommended characteristics:

- separate environment from the ADS orchestration env
- install from `requirements.txt`

Validated ML example:

- Python `3.12.11`

Typical setup:

```powershell
python -m venv .venv-ml
.\.venv-ml\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Expected packages:

- `torch`
- `numpy`
- `matplotlib`
- `h5py`
- `scikit-rf`
- `tqdm`
- `pandas`

## Practical Rule

Use these rules unless you have a strong reason not to:

- use a standard Windows Python environment for `parallel_version/` orchestration
- use the ADS bundled Python only through `ADS_PYTHON`
- use a separate ML environment for `create_hdf5.py`, `train.py`, and `verify_model.py`

## Validation Evidence

Machine-specific validated examples remain documented in:

- [RUNTIME_VALIDATION_RESULTS.md](RUNTIME_VALIDATION_RESULTS.md)

That document is evidence of what worked on one validated machine, not a requirement that users copy those exact environment names or paths.
