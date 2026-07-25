# HackGuard — MVP

Risk-scoring, not verdicts: analyzes a submitted GitHub repo against a declared
hackathon time window and surfaces evidence for judges to review — it never
accuses, it flags.

## What's in this MVP

- **Git Repository Analyzer** (`backend/analyzer.py`) — clones the repo, pulls
  GitHub metadata (creation date, stars/forks), walks full commit history, and
  scores 7 weighted signals: repo age, pre-existing stars/forks, first-commit
  timing, commit distribution vs. the event window, large single-commit code
  dumps, commit cadence realism, message quality, author spread.
- **FastAPI backend** (`backend/main.py`) — `/analyze` endpoint wrapping the
  analyzer.
- **Judge Dashboard** (`frontend/index.html`) — single static page, no build
  step. Enter a repo URL + hackathon window, get a risk score, per-signal
  evidence breakdown, and a commit timeline chart (red = before the window,
  green = inside it).

## Deliberately cut from this pass (see original pitch)

- PPT reuse detector (needs a seeded corpus of past decks to compare against —
  not buildable convincingly without real data)
- VS Code telemetry extension (real signal, but its own multi-day build + needs
  participant adoption)
- Cross-repo AST/embedding similarity search

## Running it

```bash
# backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# frontend
# just open frontend/index.html in a browser — it calls http://localhost:8000
```

Optional: pass a GitHub personal access token in the dashboard's token field
to avoid unauthenticated API rate limits (60 req/hr without one).

## Known weaknesses (be upfront about these when you demo)

- Git timestamps (`first commit`, `commit distribution`) are the *most
  spoofable* signals — a participant can rewrite history with
  `git commit --date`. They're intentionally weighted lower than harder-to-fake
  signals like existing stars/forks.
- No signal here can *prove* pre-existing work — see `disclaimer` field on
  every API response. The product's value is triage, not judgment.

## Suggested next build session

1. Test against 3–5 real repos with known-good and known-bad timing to tune
   signal weights.
2. Add a `/teams` batch endpoint + leaderboard view for the full judge
   dashboard (currently single-repo lookup only).
3. Sketch the PPT similarity checker as a separate service once you have a
   sample deck corpus to test against.
