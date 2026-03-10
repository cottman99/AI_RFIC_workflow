# Configuration Reference

This document explains the user-facing configuration points needed to run the repository.

## Environment Variables

Reference template:

- [`.env.example`](../.env.example)

Note:

- the repository does not parse `.env` automatically
- `.env.example` exists only as a user-facing template for shell or tooling integration

### `ADS_PYTHON`

Path to the Python interpreter shipped with ADS.

Example:

```text
C:\Path\To\ADS\tools\python\python.exe
```

Used for:

- importing `keysight.ads.de`
- importing `keysight.ads.emtools`
- running ADS-specific subprocess workers

Important:

- users normally provide only one `ADS_PYTHON`
- the repository does not require separate user-configured ADS Python paths for design and simulation phases
- phase switching is handled internally by `keysight.edatoolbox.multi_python`

### `ADS_INSTALL_DIR`

Path to the ADS installation root.

Example:

```text
C:\Path\To\ADS
```

Used for:

- ADS runtime discovery
- fallback ADS Python path construction
- locating alternative bundled interpreters under the same ADS installation when needed

## Internal Multi-Python Behavior

Inside the worker layer, the repository uses `keysight.edatoolbox.multi_python` to switch product contexts.

Current behavior:

- `ads_context()` is used for workspace/design/layout tasks
- `xxpro_context()` is used for RFPro / EM simulation tasks

This means the repository behaves like a multi-stage ADS workflow internally, even though the user-facing configuration usually only needs one `ADS_PYTHON`.

For a deeper explanation, see [ADS_MULTI_PYTHON.md](ADS_MULTI_PYTHON.md).

### `PDK_DIR`

Path to the main PDK library directory.

This is the design kit library, not the technology companion library.

### `PDK_TECH_DIR`

Path to the technology/reference library directory paired with the PDK.

This is typically the library that contains substrate and technology definitions used during layout and EM setup.

### `SUBSTRATE`

The substrate definition name expected by the selected PDK/reference library.

Example values depend on the kit you use. For the validated DemoKit example, the value was `demo`.

## `batch_config_pdk.json`

Primary sample file:

- [batch_config_pdk.json](../parallel_version/config_examples/batch_config_pdk.json)

### Path Resolution Rule

Important:

- relative paths in this config are resolved relative to the config file location
- users do not need to `cd` into `parallel_version/` just to make the bundled sample config work

## Top-Level Fields

### `workspace_dir`

Directory where the ADS workspace will be created or reused.

### `library_name`

Name of the target ADS library to create/use inside the workspace.

### `ref_library_name`

Expected name of the reference technology library.

For the DemoKit example, this is:

```text
DemoKit_Non_Linear_tech
```

If omitted in some flows, the repository can often infer a suitable value from `lib.defs`, but providing it explicitly is clearer for public use.

### `designs_dir`

Directory containing layout JSON files.

Each JSON file becomes one design task.

### `output_dir`

Directory where reports and exported results are written.

### `substrate`

Substrate definition name used when creating the design and EM view.

### `layer_mapping_file`

Path to the JSON file that maps logical layout layers to ADS technology layers.

## `pdk_config`

### `use_pdk`

When `true`, the flow uses a PDK-based setup.

### `pdk_dir`

Path to the main PDK directory.

### `pdk_tech_dir`

Path to the technology/reference library directory paired with the PDK.

## `export_config`

### `export_path`

Directory where exported simulation artifacts are written.

### `export_touchstone`

Whether to export `.sNp`.

### `export_dataset`

Whether to export ADS dataset files.

### `export_csv`

Whether to export CSV files.

## `execution_config`

### `max_workers`

Maximum number of parallel worker tasks.

Start with a small number for first-time validation.

### `batch_size`

How many tasks are launched per batch.

Also start small for first-time validation.

### `retry_failed`

Whether failed tasks should be retried automatically.

### `max_retries`

Maximum retry count per failed task.

## Related Files

- [frequency_config.json](../parallel_version/config_examples/frequency_config.json)
- [layer_mapping.json](../parallel_version/config_examples/layer_mapping.json)
- [WORKFLOW.md](WORKFLOW.md)
