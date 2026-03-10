# Documentation Map

This repository keeps documentation in three layers so new users do not need to read every file in `docs/`.

## Core

These are the primary public-facing documents and should remain highly visible.

- [core/SETUP.md](core/SETUP.md): environment preparation and prerequisites
- [core/QUICKSTART.md](core/QUICKSTART.md): shortest practical path through the workflow
- [core/CONFIG_REFERENCE.md](core/CONFIG_REFERENCE.md): configuration fields and expected values
- [core/WORKFLOW.md](core/WORKFLOW.md): stage-by-stage operational flow
- [core/ARCHITECTURE.md](core/ARCHITECTURE.md): repository and subsystem structure
- [core/ADS_MULTI_PYTHON.md](core/ADS_MULTI_PYTHON.md): Keysight multi-context runtime mechanism
- [core/GLOSSARY.md](core/GLOSSARY.md): terminology normalization

## Reference

These documents are useful, but they are not required for first-time onboarding.

- [reference/ENVIRONMENTS.md](reference/ENVIRONMENTS.md): runtime environment model and interpreter roles
- [reference/MODEL_DATA_COMPATIBILITY.md](reference/MODEL_DATA_COMPATIBILITY.md): model/dataset schema relationships
- [reference/DATA_AND_MODEL_ASSETS.md](reference/DATA_AND_MODEL_ASSETS.md): treatment of large local assets

## Maintenance

These are maintainer-facing or release-governance documents. Keep them in-repo, but do not treat them as first-stop onboarding material.

- [maintenance/PROJECT_HEALTH_REPORT.md](maintenance/PROJECT_HEALTH_REPORT.md): deep repository audit snapshot
- [maintenance/GITHUB_RELEASE_CHECKLIST.md](maintenance/GITHUB_RELEASE_CHECKLIST.md): publication and release hygiene checklist
- [maintenance/REFERENCE_MAP.md](maintenance/REFERENCE_MAP.md): mapping from public docs to deeper legacy engineering references
- [maintenance/VALIDATION_PLAN.md](maintenance/VALIDATION_PLAN.md): planned validation sequence
- [maintenance/RUNTIME_VALIDATION_RESULTS.md](maintenance/RUNTIME_VALIDATION_RESULTS.md): machine-specific validation evidence
- [maintenance/RETRAIN_2CH_CHECKPOINT.md](maintenance/RETRAIN_2CH_CHECKPOINT.md): retraining record for the current 2-channel checkpoint

## Visibility Guidance

- `core/`: keep prominently linked from the root `README.md`
- `reference/`: keep discoverable, but not in the first reading path
- `maintenance/`: keep available for maintainers, but lower-visibility than the core docs

## Legacy Engineering Notes

Deeper historical implementation notes still exist under:

- `serial_version/docs/`

Those files are intentionally treated as internal engineering references rather than primary public documentation.
