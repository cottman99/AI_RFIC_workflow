# Architecture

This document describes the public-facing repository architecture of `AI_RFIC_workflow`.

## System Purpose

The repository implements a layout-to-EM-to-ML pipeline for pixelized RFIC structures:

1. Generate pixel layout templates as JSON.
2. Convert JSON layouts into ADS geometry and RFPro EM views.
3. Run EM simulations and export S-parameter results.
4. Build HDF5 datasets from layouts and simulation outputs.
5. Train a CNN surrogate model to predict EM responses from layout tensors.

## Repository-Level Subsystems

### Layout Template Generation

Directory:

- `Data_process/JSON_layout_create/`

Responsibilities:

- Create and edit pixelized layout templates
- Manage multi-layer binary matrices
- Define ports on layout borders
- Export design descriptions as JSON
- Generate randomized layout variants for simulation data production

Recommended launcher:

- `Data_process/JSON_layout_create/layout_generator_main.py`

Repository role:

- this is the upstream producer of the layout JSON assets consumed by the ADS automation flow
- it is optional for first-time quickstart users only because sample JSON files are already included

### ADS / RFPro Automation

Primary execution line:

- `parallel_version/`

Legacy/reference implementation:

- `serial_version/`

Responsibilities:

- Detect ADS Python runtime
- Parse JSON layout files
- Convert matrices to ADS geometry
- Create workspace, library, cell, layout, and `rfpro_view`
- Configure EM frequency plans
- Run simulations and export results

### Dataset Construction

Directory:

- `Data_process/HDF5_create/`

Responsibilities:

- Match layout JSON files with `.sNp` simulation results
- Convert layouts into padded tensors
- Flatten complex S-parameters into real-valued vectors
- Build grouped HDF5 datasets

### Surrogate Modeling

Directory:

- `Pytorch_Model/`

Responsibilities:

- Load HDF5 datasets
- Define CNN architecture
- Train regression models
- Verify model predictions against simulation data

## Execution Model

The automation layer is intentionally split across runtimes:

- Normal Python runtime:
  - configuration parsing
  - orchestration
  - JSON preprocessing
- ADS Python runtime:
  - workspace creation
  - layout generation
  - EM view creation
  - simulation execution

This keeps ADS-specific dependencies isolated from the rest of the Python toolchain.

## ADS Multi-Python Mechanism

One of the most important implementation details is that the repository does not treat all ADS-related work as a single undifferentiated Python phase.

The runtime model is:

1. a normal Python process launches the CLI/orchestration layer
2. that layer launches an ADS-bundled Python interpreter as a worker process
3. inside the worker, `keysight.edatoolbox.multi_python` switches between product contexts

In the current implementation:

- design-oriented tasks run inside `multi_python.ads_context()`
- EM simulation tasks run inside `multi_python.xxpro_context()`

This is the mechanism that lets one worker process execute both:

- ADS database/layout operations
- RFPro / EMPro simulation operations

without requiring the user to manually launch different interpreters for each phase.

### What The User Usually Needs To Provide

In normal use, the user does not need to provide multiple ADS Python executable paths.

The public configuration expectation is:

- provide `ADS_PYTHON` as one valid ADS-bundled Python interpreter
- optionally provide `ADS_INSTALL_DIR` to improve runtime discovery

The repository then uses:

- `ADS_PYTHON` to start the worker process
- `multi_python.ads_context()` for ADS-side tasks
- `multi_python.xxpro_context()` for RFPro / EMPro-side tasks

### Why The Code Still Searches Multiple Candidate Paths

The code may search several candidate executables under an ADS install because Keysight installations can expose different bundled interpreters, for example:

- `tools/python/python.exe`
- a `fem/.../python/python.exe` path

This is a discovery convenience, not a requirement that users manually configure several interpreter paths.

### Mental Model

The most accurate mental model is:

- one user-facing ADS Python entry point
- multiple product contexts inside the worker

not:

- many separate user-managed ADS Python environments for each pipeline stage

For a dedicated explanation, see [ADS_MULTI_PYTHON.md](ADS_MULTI_PYTHON.md).

## Recommended Public Mainline

For GitHub publication, the recommended mainline is:

1. `Data_process/JSON_layout_create/`
2. `parallel_version/`
3. `Data_process/HDF5_create/`
4. `Pytorch_Model/`

`serial_version/` should be treated as legacy/reference material.

## Assets Outside Source Control

The following should remain local assets rather than tracked repository files:

- ADS / RFPro workspaces
- simulation outputs
- logs
- HDF5 datasets
- trained model weights

## External Dependencies

This repository cannot be validated end-to-end through `pip` alone. Runtime execution also depends on:

- Keysight ADS
- RFPro / ADS EM tooling
- valid licenses
- accessible PDK or reference technology libraries

## Internal Reference Sources

For deeper engineering detail, the most useful internal reference documents are:

- `serial_version/docs/01-main-architecture.md`
- `serial_version/docs/03-subprocess-architecture.md`
- `serial_version/docs/04-json-layout-schema.md`
- `serial_version/docs/07-configuration-management.md`

These are engineering reference materials, not polished public documentation.
