# Legacy Helpers

This directory contains Windows-specific compatibility helpers and historical one-off support scripts from the older `serial_version/` workflow.

These files are retained for maintenance and recovery purposes only.

They are not part of the recommended public execution path.

## Contents

- `batch_processor_ascii.py`: ASCII-only variant of the old batch processor
- `fix_encoding.py`: one-off text cleanup helper for historical files
- `run_batch.ps1`: PowerShell wrapper around the ASCII batch processor
- `run_batch_windows.bat`: Windows batch wrapper around the ASCII batch processor
- `run_with_encoding_fix.bat`: old launcher for running the legacy batch processor with UTF-8 console settings
- `test_path_fix.py`: one-off validation script for an older path-resolution fix

## Expected Context

These helpers assume they live under:

- `serial_version/legacy_helpers/`

and may reference files in the parent `serial_version/` directory.

## Public Repository Guidance

New users should ignore this directory and start from:

- `../README.md`
- `../../docs/core/QUICKSTART.md`
