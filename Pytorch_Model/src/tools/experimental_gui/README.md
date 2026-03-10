# Experimental GUI Verifier

This directory contains a historical Tkinter-based GUI wrapper for model verification.

## Status

- retained for convenience and experimentation
- not part of the validated public mainline
- lower priority than the CLI verifier

## Recommended Public Verifier

Use the CLI tool first:

```bash
python tools/verify_model.py --hdf5_path "<path-to-your-dataset.h5>" --model_path "../models/best_model_2ch_2port_16x16.pth" --sample_index 0
```

## Experimental GUI Entry

From `Pytorch_Model/src/`:

```bash
python tools/experimental_gui/verify_model_gui.py
```

## Notes

The GUI helper is intentionally kept out of the main onboarding path because the CLI verifier is simpler to maintain and easier to document for public users.
