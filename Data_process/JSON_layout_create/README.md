# JSON_layout_create

This directory contains tools for generating, editing, and exporting pixel-layout JSON templates.

## Why This Directory Matters

This directory is the upstream sample-generation layer of the repository.

Its role is to create the layout JSON files that the rest of the workflow depends on:

- `parallel_version/` consumes these JSON files to build ADS layouts and RFPro EM views
- `Data_process/HDF5_create/` later matches the same JSON files with exported `.sNp` results

So these scripts are not just convenience utilities. They are the source of the layout templates used by the ADS automation and ML dataset pipeline.

## Recommended Entry Point

Start with:

- `layout_generator_main.py`

This launcher exists to give the repository a stable ASCII-named entry point.

## Current Recommended GUI Variant

The current recommended GUI target is:

- `layout_generator_gui_super_enhanced.py`

The launcher falls back to:

- `legacy_variants/layout_generator_gui_enhanced.py`
- `legacy_variants/layout_generator_gui.py`

Users should prefer the stable launcher instead of importing variant-specific GUI scripts directly.

## Outputs

The generator produces layout JSON files that contain:

- metadata
- per-layer binary matrices
- port definitions

These JSON files are the expected inputs for the ADS automation flow in `parallel_version/`.

The current primary GUI also supports:

- interactive layer and port editing
- random layout generation
- batch generation of randomized variants
- geometric augmentation such as rotation and flips
- batch import and batch export of JSON files

## Directory Notes

- `JSON_layout_data/`: sample and historical layout JSON assets
- `legacy_variants/`: archived baseline and enhanced GUI variants
- `tmp/`: local runtime artifacts, ignored by Git

## Testing Notes

The included `test_*.py` files reflect historical feature work and ad-hoc validation. They should not be treated as a formal public test suite.

## Next Step

After generating layout JSON files, continue with:

- [parallel_version/README.md](../../parallel_version/README.md)

For first-time validation only, you may skip this stage and use the sample JSON files already shipped under `parallel_version/config_examples/json_layout/`.
