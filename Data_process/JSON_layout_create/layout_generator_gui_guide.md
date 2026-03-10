# Layout Generator GUI Guide

This directory contains historical GUI variants for creating and editing RFIC pixel-layout JSON templates.

## Recommended Entry

Use the stable launcher:

```bash
python layout_generator_main.py
```

The launcher selects the best available GUI variant in this order:

1. `layout_generator_gui_super_enhanced.py`
2. `layout_generator_gui_enhanced.py`
3. `layout_generator_gui.py`

## Output Schema

The GUI exports JSON files containing:

- `design_id`
- `metadata`
- `layout_matrices`
- `port_definitions`

These files are intended to be consumed by the ADS automation flow in `parallel_version/`.

## Variant Notes

- `layout_generator_gui.py`: baseline GUI implementation
- `layout_generator_gui_enhanced.py`: adds fill-ratio controls and extended editing helpers
- `layout_generator_gui_super_enhanced.py`: the most feature-complete historical variant

## Dependencies

- Python 3.9+
- `numpy`
- `matplotlib`
- `tkinter`

## Public Repository Note

These GUI scripts are retained as historical utilities. They are useful for preparing JSON layout templates, but they are not the primary public entry point of the repository. New users should start with the root `README.md`, then continue with `docs/SETUP.md` and `docs/QUICKSTART.md`.
