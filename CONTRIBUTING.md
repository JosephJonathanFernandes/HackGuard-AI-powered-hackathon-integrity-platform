# Contributing to HackGuard

We love your input! We want to make contributing to this project as easy and transparent as possible, whether it's:
- Reporting a bug
- Discussing the current state of the code
- Submitting a fix
- Proposing new features

## Development Setup

1. Fork the repo and create your branch from `main`.
2. Install dependencies: `pip install -r requirements.txt`.
3. Set your `PYTHONPATH`: `export PYTHONPATH=src` (or `set PYTHONPATH=src` on Windows).

## Code Style & Linting
- We use `black` for formatting and `ruff` (or `flake8`) for linting.
- Run `scripts/lint.sh` before committing to ensure style compliance.

## Testing
- We use `pytest`. All new features must include corresponding unit tests.
- Run tests via `pytest tests/`.

## Pull Requests
- Ensure all tests pass.
- Update documentation if you change API contracts or system architecture.
- Keep PRs focused on a single logical change.
