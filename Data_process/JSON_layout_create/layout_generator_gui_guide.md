# Layout Generator GUI Guide

This directory contains historical GUI variants for creating and editing RFIC pixel-layout JSON templates.

## Recommended Entry

Use the stable launcher:

```bash
python layout_generator_main.py
```

The launcher selects the best available GUI variant in this order:

1. `layout_generator_gui_super_enhanced.py`
2. `legacy_variants/layout_generator_gui_enhanced.py`
3. `legacy_variants/layout_generator_gui.py`

## Output Schema

The GUI exports JSON files containing:

- `design_id`
- `metadata`
- `layout_matrices`
- `port_definitions`

These files are intended to be consumed by the ADS automation flow in `parallel_version/`.

## Variant Notes

- `layout_generator_gui_super_enhanced.py`: the most feature-complete historical variant
- `legacy_variants/layout_generator_gui_enhanced.py`: archived enhanced GUI with fill-ratio controls
- `legacy_variants/layout_generator_gui.py`: archived baseline GUI implementation

## Archive Boundary

Files under `legacy_variants/` are retained for recovery and comparison only.

New users should not start from those files directly.

## Dependencies

- Python 3.9+
- `numpy`
- `matplotlib`
- `tkinter`

## Public Repository Note

These GUI scripts are retained as historical utilities. They are useful for preparing JSON layout templates, but they are not the primary public entry point of the repository. New users should start with the root `README.md`, then continue with `docs/SETUP.md` and `docs/QUICKSTART.md`.
