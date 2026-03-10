# GitHub Release Checklist

Use this checklist to turn the current research repository into a clean public repository.

## 1. Repository Cleanup

- remove or ignore all `tmp/`, `__pycache__/`, logs, and runtime simulation artifacts
- keep large `.h5` datasets and `.pth` checkpoints out of normal Git history
- decide whether any tiny example dataset should remain in-repo

## 2. Mainline Scope

- keep `parallel_version/` as the public execution line
- keep `serial_version/` as legacy/reference only
- keep one primary layout-generator entry point
- remove or archive redundant legacy helpers

## 3. Environment Decoupling

- keep ADS paths configurable through environment variables
- keep PDK paths configurable through templates or config files
- document that ADS automation and PyTorch training currently use different Python environments

## 4. Documentation

- keep the root `README.md` accurate
- keep `docs/ARCHITECTURE.md` and `docs/WORKFLOW.md` aligned with code
- keep `docs/ENVIRONMENTS.md` aligned with validated interpreters
- keep `docs/RUNTIME_VALIDATION_RESULTS.md` aligned with real validation evidence

## 5. Data And Model Assets

- decide which datasets, if any, are public examples
- decide whether model artifacts will be published through Releases, object storage, or Git LFS
- rename legacy checkpoints clearly if they do not match the current dataset schema

## 6. Blocking Item Before Public Model Release

- keep the legacy 1-channel checkpoint clearly separated from the current 2-channel model line

Current finding:

- `best_model_legacy_1ch_2port_16x16_pre20260310.pth` expects 1 input channel
- the validated replacement is `best_model_2ch_2port_16x16_20260310.pth`
- current main HDF5 datasets are 2-channel

Acceptable release outcomes:

1. retrain a new 2-channel checkpoint and publish that
2. publish the renamed legacy checkpoint only as a legacy 1-channel artifact with matching dataset documentation
3. do not publish any checkpoint yet

## 7. Validation Expectations

Before calling the repository public-ready, make sure the following still pass:

- single-sample ADS workflow
- small parallel batch workflow
- HDF5 generation from real `.s2p`
- training smoke test
- model verification script
