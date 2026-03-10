# Reference Map

This document maps repository-level public documents to the deeper internal engineering references retained under `serial_version/docs/`.

## Purpose

The root `docs/` directory is intended for concise public-facing documentation.

The `serial_version/docs/` directory is retained as internal engineering reference material. It is useful for maintenance and recovery, but it is not the preferred first stop for GitHub readers.

## Public to Internal Mapping

### `docs/core/ARCHITECTURE.md`

Use this first for:

- repository-level structure
- subsystem overview
- public mainline understanding

Deep internal references:

- `serial_version/docs/01-main-architecture.md`
- `serial_version/docs/03-subprocess-architecture.md`
- `serial_version/docs/07-configuration-management.md`

### `docs/core/WORKFLOW.md`

Use this first for:

- end-to-end stage sequence
- handoff points between subsystems
- recommended execution order

Deep internal references:

- `serial_version/docs/01-main-architecture.md`
- `serial_version/docs/02-ads-api-integration.md`
- `serial_version/docs/08-visualization-results.md`

### `docs/core/GLOSSARY.md`

Use this first for:

- repository terminology normalization

Deep internal references:

- `serial_version/docs/04-json-layout-schema.md`
- `serial_version/docs/07-configuration-management.md`

### `docs/maintenance/PROJECT_HEALTH_REPORT.md`

Use this first for:

- publication readiness assessment
- repository risks and cleanup priorities

Related internal references:

- `serial_version/docs/06-error-handling.md`
- `serial_version/docs/07-configuration-management.md`

### `docs/maintenance/VALIDATION_PLAN.md`

Use this first for:

- next-phase environment validation planning
- staged runtime verification

Related internal references:

- `serial_version/docs/02-ads-api-integration.md`
- `serial_version/docs/03-subprocess-architecture.md`
- `serial_version/docs/06-error-handling.md`

## Recommended Reading Order

For a new maintainer:

1. `README.md`
2. `docs/core/ARCHITECTURE.md`
3. `docs/core/WORKFLOW.md`
4. `docs/maintenance/PROJECT_HEALTH_REPORT.md`
5. `docs/maintenance/VALIDATION_PLAN.md`
6. selected files from `serial_version/docs/` only when deeper implementation detail is required
