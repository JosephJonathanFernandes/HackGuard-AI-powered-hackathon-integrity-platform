# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Added
- Modularized architecture (`src/`, `tests/`, `docs/`, `config/`).
- GitHub Actions CI pipeline for automated testing and linting.
- Secure environment configuration via `pydantic-settings` and `.env`.
- Unit tests using `pytest`.
- Developer scripts (`lint.sh`).

### Changed
- Refactored monolithic `analyzer.py` into distinct `git_client`, `github_client`, and `signals` modules.
- Upgraded `README.md` to professional open-source standards.
- Removed hardcoded constants and enforced strict separation of concerns.

## [1.0.0] - MVP Release
### Added
- Initial single-repository risk scoring engine.
- Web dashboard with visualization (Chart.js) and batch analysis leaderboard.
- FastAPI backend with basic multithreading for batch analysis.
