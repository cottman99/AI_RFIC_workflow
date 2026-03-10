# ADS Multi-Python Mechanism

This document explains one of the most important implementation details in `AI_RFIC_workflow`:

- why ADS design tasks and EM simulation tasks run in different product contexts
- how `ads_context()` and `xxpro_context()` select different Python interpreters
- what the repository expects from the user

## Why This Exists

Keysight ADS and RFPro / EMPro do not behave like a single generic Python runtime.

In this repository, the workflow is split into two broad task classes:

- ADS database and layout tasks
- RFPro / EM simulation tasks

These two classes are executed through different Keysight product contexts, even though the outer workflow looks like one continuous automation pipeline.

## High-Level Execution Model

The runtime stack is:

1. a normal Python process launches the repository CLI
2. the CLI launches one ADS-bundled Python worker process
3. inside that worker, `keysight.edatoolbox.multi_python` spawns the correct product-specific subprocess for each task class

In the current implementation:

- ADS-side tasks use `multi_python.ads_context()`
- EM simulation tasks use `multi_python.xxpro_context()`

## Where This Happens In The Repository

Primary implementation points:

- `parallel_version/subprocess_cli_parallel.py`
- `parallel_version/subprocess_worker_parallel.py`
- `serial_version/subprocess_cli.py`
- `serial_version/subprocess_worker.py`

Task-to-context mapping in the parallel worker:

- ADS tasks:
  - `create_workspace_lib`
  - `create_design_only`
  - `create_ads_design`
  - `manage_workspace_conflict`
- xxPro tasks:
  - `run_em_simulation_only`
  - `run_em_simulation`

## How `ads_context()` Selects Its Interpreter

`keysight.edatoolbox.multi_python.ads_context()` accepts an optional directory argument:

```python
ads_context(python_ads_location=None)
```

If the location is not provided, Keysight's implementation calls:

- `keysight.edatoolbox.ads.get_python_ads_location()`

That function resolves the ADS installation root through:

- `HPEESOF_DIR`, if already set
- otherwise Keysight's ADS discovery logic

It then derives the ADS Python directory from the ADS installation root.

On Windows, that means the ADS interpreter is effectively:

```text
<ADS_INSTALL_DIR>\tools\python\python.exe
```

## How `xxpro_context()` Selects Its Interpreter

`keysight.edatoolbox.multi_python.xxpro_context()` also accepts an optional directory argument:

```python
xxpro_context(python_xxpro_location=None)
```

If the location is not provided, Keysight's implementation calls:

- `keysight.edatoolbox.xxpro.get_python_xxpro_location()`

That function first determines the xxPro installation location. In the common ADS-installed case, it does not require the user to point directly to the xxPro Python executable.

Instead, it:

1. resolves the ADS installation root
2. calls ADS `menv` to ask where the `fem` component is installed
3. derives the xxPro Python directory from the returned `fem` component location

On Windows, that typically means an interpreter like:

```text
<ADS_INSTALL_DIR>\fem\<version>\win32_64\bin\tools\win32\python\python.exe
```

## Important Practical Meaning

`ads_context()` and `xxpro_context()` do not merely change `sys.path`.

Keysight's `multi_python` implementation actually sets a different Python executable for each spawned subprocess.

Conceptually:

- ADS tasks execute under the ADS Python executable
- xxPro tasks execute under the xxPro / EMPro Python executable

This is why the mechanism should be understood as:

- one user-facing ADS worker entry point
- multiple product-specific subprocess interpreters underneath

not:

- one single Python process with all products mixed together

## What The Repository Expects From The User

In normal use, the user does not need to manually provide multiple product-specific Python executable paths.

The intended public interface is:

- `ADS_PYTHON`
- `ADS_INSTALL_DIR`

Why this is usually enough:

1. the repository uses `ADS_PYTHON` to launch the worker
2. the worker sets up the ADS environment, including `HPEESOF_DIR`
3. inside the worker, Keysight `multi_python` discovers the ADS-side and xxPro-side interpreters automatically

## Why The Repository Still Scans Multiple Candidate Executables

The repository CLI may scan several candidate interpreters under one ADS installation.

This is only a discovery convenience because a real ADS installation can expose more than one bundled interpreter path, for example:

- `tools/python/python.exe`
- a `fem/.../python/python.exe` path

This does not mean end users are expected to configure many interpreter variables by hand.

## When You Might Need More Than `ADS_PYTHON`

Advanced or unusual setups may require more explicit control, for example:

- multiple ADS installations on the same machine
- nonstandard xxPro installation layout
- custom environment management outside normal ADS installation structure

In those cases, a future enhancement could expose:

- explicit ADS Python directory override for `ads_context()`
- explicit xxPro Python directory override for `xxpro_context()`

The current repository does not expose those as public configuration fields.

## Relationship To Repository Environment Variables

Recommended user-facing variables:

- `ADS_PYTHON`
- `ADS_INSTALL_DIR`
- `PDK_DIR`
- `PDK_TECH_DIR`
- `SUBSTRATE`

Interpretation:

- `ADS_PYTHON` selects the worker entry interpreter
- `ADS_INSTALL_DIR` makes ADS/xxPro discovery more reliable
- `PDK_DIR`, `PDK_TECH_DIR`, and `SUBSTRATE` control the design technology side, not Python interpreter switching

## Mental Model For Maintainers

The most useful maintainer mental model is:

- outer normal Python for orchestration
- one ADS-bundled worker entry interpreter
- internal context switching through Keysight `multi_python`
- separate product-specific subprocess interpreters chosen by Keysight under the hood

## Related Files

- `docs/core/SETUP.md`
- `docs/core/CONFIG_REFERENCE.md`
- `docs/core/ARCHITECTURE.md`
- `parallel_version/subprocess_worker_parallel.py`
- `serial_version/subprocess_worker.py`
