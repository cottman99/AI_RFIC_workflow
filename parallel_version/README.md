# parallel_version

This is the recommended public execution line for the ADS / RFPro automation workflow.

## Role

`parallel_version/` is the best place for a new user to start if the goal is:

- create ADS workspaces and libraries
- build designs from layout JSON
- run EM simulations
- export batch results

Compared with `serial_version/`, this directory has the clearer public-facing execution model.

## Main Entry Points

### `batch_processor.py`

High-level batch entry point.

Useful commands:

```powershell
python .\parallel_version\batch_processor.py validate-config --config .\parallel_version\config_examples\batch_config_pdk.json
python .\parallel_version\batch_processor.py process-config --config .\parallel_version\config_examples\batch_config_pdk.json
```

### `subprocess_cli_parallel.py`

Lower-level CLI entry point for step-by-step control.

Main subcommands:

- `create-workspace-lib`
- `create-design-only`
- `run-simulation-only`
- `complete-workflow`

## Configuration

Start from:

- `config_examples/batch_config_pdk.json`
- `config_examples/frequency_config.json`
- `config_examples/layer_mapping.json`
- `config_examples/json_layout/`

Important behavior:

- relative paths in `batch_config_pdk.json` are resolved relative to the config file itself
- this makes the bundled sample config safer for new users

See [CONFIG_REFERENCE.md](../docs/core/CONFIG_REFERENCE.md).

## Prerequisites

- Windows
- Keysight ADS / RFPro installed
- valid license access
- accessible PDK or reference technology library
- `ADS_PYTHON` and `ADS_INSTALL_DIR` configured

## Recommended First Step

Run config validation before any real batch execution:

```powershell
python .\parallel_version\batch_processor.py validate-config --config .\parallel_version\config_examples\batch_config_pdk.json
```

Then continue with:

- [SETUP.md](../docs/core/SETUP.md)
- [QUICKSTART.md](../docs/core/QUICKSTART.md)
