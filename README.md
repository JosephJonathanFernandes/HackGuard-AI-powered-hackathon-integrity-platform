# HackGuard

HackGuard is a robust, modular risk-scoring engine designed to assist hackathon judges by identifying potential pre-existing work in submitted GitHub repositories. 

> **Important**: HackGuard provides risk scores, not verdicts. It surfaces evidence for judges to review. It never accuses; it flags.

## The Problem
Hackathons are built on the honor code. Unfortunately, some participants submit pre-existing work. HackGuard solves this by evaluating a repository's metadata and commit history against the declared event window, helping organizers triage submissions fairly and efficiently.

## Architecture & Tech Stack
Built with modularity and extensibility in mind, HackGuard adheres to SOLID principles and GitGuardian security standards:
- **FastAPI**: High-performance backend.
- **Pydantic**: Strict data validation and settings management.
- **GitPython & GitHub REST API**: Core engines for local git history parsing and remote metadata fetching.
- **Vanilla JS/HTML/CSS**: Lightweight, zero-build-step frontend dashboard using Chart.js.

For a deep dive into the system design, see [ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Getting Started

### Prerequisites
- Python 3.10+
- Git

### Installation
```bash
# Clone the repository
git clone https://github.com/your-org/HackGuard.git
cd HackGuard

# Set up environment variables
cp .env.example .env
# Edit .env with your GITHUB_TOKEN to avoid rate limits

# Install dependencies
pip install -r requirements.txt
```

### Usage
Start the backend server:
```bash
# Run using uvicorn and load from the src module
set PYTHONPATH=src
uvicorn hackguard.api.main:app --reload --port 8000
```
*(On Linux/macOS, use `export PYTHONPATH=src`)*

Then, simply open `frontend/index.html` in your browser.

## Security
We take security seriously. Hardcoded secrets are strictly forbidden. Please refer to our [SECURITY.md](SECURITY.md) for reporting vulnerabilities.

## Contributing
We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on code style, testing, and pull requests.
