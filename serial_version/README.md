# serial_version

This directory is a legacy/reference implementation of the ADS automation workflow.

## What It Is

`serial_version/` preserves earlier single-process and GUI-oriented implementations of the project.

It remains useful for:

- recovering historical design decisions
- comparing older CLI/GUI behavior
- mining internal engineering documentation
- accessing archived compatibility helpers under `legacy_helpers/`

## What It Is Not

It is not the recommended public starting point for a new user.

For normal repository use, prefer:

- [parallel_version/README.md](../parallel_version/README.md)

## Why It Is Legacy

Compared with `parallel_version/`, this directory contains more historical compatibility material and less clearly bounded public workflow structure.

## Most Useful Content

- `subprocess_cli.py`
- `subprocess_worker.py`
- `batch_processor.py`
- `docs/`

Historical compatibility wrappers and one-off maintenance scripts live under:

- `legacy_helpers/`

For deeper internal reference, start with:

- [serial_version/docs/README.md](docs/README.md)
