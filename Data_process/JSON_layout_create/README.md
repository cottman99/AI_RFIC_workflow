# JSON_layout_create

This directory contains tools for generating, editing, and exporting pixel-layout JSON templates.

## Recommended Entry Point

Start with:

- `layout_generator_main.py`

This launcher exists to give the repository a stable ASCII-named entry point.

## Current Recommended GUI Variant

The current recommended GUI target is the most feature-complete historical variant in this directory.

The launcher selects the preferred implementation automatically, so users do not need to invoke the Chinese-named GUI files directly.

## Outputs

The generator produces layout JSON files that contain:

- metadata
- per-layer binary matrices
- port definitions

These JSON files are the expected inputs for the ADS automation flow in `parallel_version/`.

## Directory Notes

- `JSON_layout_data/`: sample and historical layout JSON assets
- `tmp/`: local runtime artifacts, ignored by Git

## Testing Notes

The included `test_*.py` files reflect historical feature work and ad-hoc validation. They should not be treated as a formal public test suite.

## Next Step

After generating layout JSON files, continue with:

- [parallel_version/README.md](../../parallel_version/README.md)
