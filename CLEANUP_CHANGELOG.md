# Cleanup Changelog

## [Unreleased]
### Added
- Initiated audit log with tool run outcomes for Phase 2 automated hygiene checks.

### Fixed
- Normalized plugin manifest parsing to expose `contributes_settings` metadata and avoid API crashes when listing plugin settings.
- Deleted generated Celery beat schedule artefact and duplicate lowercase Dockerfile; repository now relies on the canonical Dockerfile and regenerated state stays ignored.

### Pending
- Format black-flagged Python modules and resolve mypy module collision.
- Re-run detect-secrets and vulture once package installation is available.
