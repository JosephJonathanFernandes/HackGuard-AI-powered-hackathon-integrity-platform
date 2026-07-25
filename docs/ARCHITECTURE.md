# Architecture

HackGuard follows a clear, layered architecture ensuring separation of concerns:

## System Components

1. **Presentation Layer (FastAPI)**
   - Located in `src/hackguard/api`.
   - Responsible for HTTP routing, request/response validation (via Pydantic), and error handling.
   - Entry point: `main.py` -> `routes/analysis.py`.

2. **Core Domain Logic**
   - Located in `src/hackguard/core`.
   - `analyzer.py`: Orchestrates the retrieval of data and the execution of signal checks.
   - `signals.py`: Pure functions that take git/github metadata and output normalized `SignalResponse` objects. Easy to test and extend.

3. **External Clients**
   - `github_client.py`: Abstracts GitHub API interactions, handling rate limits.
   - `git_client.py`: Handles cloning, git history traversal, and cleanup via a context manager.

## Data Flow
1. Client submits a single repo or batch of repos via REST API.
2. The router validates the payload and invokes `RepoAnalyzer`.
3. `RepoAnalyzer` uses `GithubClient` to fetch metadata and `GitClient` to clone the repository to a temporary directory.
4. Extracted metrics are fed into `signals.py` to generate individual risk scores.
5. The analyzer aggregates scores based on predefined weights and calculates a final risk band.
6. The `GitClient` context manager automatically cleans up the temporary repository.
7. The result is returned to the client as JSON.
