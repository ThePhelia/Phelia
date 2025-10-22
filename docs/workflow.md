# Workflow

## Branching

- Use `feature/*` for new functionality.
- Use `fix/*` for bug fixes.
- Use `cleanup/*` for structural or hygiene changes.
- Keep branches short-lived; rebase frequently on `main`.

## Definition of Done for pull requests

- Linters (`pre-commit run --all-files`) pass locally.
- At least one smoke test per live service succeeds (`pytest tests/smoke`).
- Relevant docs (`README.md`, `docs/architecture.md`, `docs/workflow.md`) updated when behaviour or process shifts.
- No secrets, API keys, or credentials committed.
- For cleanup PRs, confirm no runtime behaviour changes.

## Commits

- Prefer small, descriptive commits (e.g. `chore(tree): move compose assets`).
- Avoid catch-all messages such as "misc fixes".
- Reference issues in the body when applicable.

## Tooling

- Install pre-commit hooks locally:
  ```bash
  pip install pre-commit
  pre-commit install
  ```
- Hooks currently run `black --check --diff` and `ruff`.
- Run smoke tests via:
  ```bash
  pip install -r apps/api/requirements.txt -r services/metadata-proxy/requirements.txt
  pytest tests/smoke
  ```
- For docker smoke coverage, use `./scripts/dev_smoke.sh` (requires Docker and docker compose).
