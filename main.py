from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from dataclasses import asdict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from analyzer import analyze_repo

app = FastAPI(title="HackGuard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    repo_url: str
    hackathon_start: datetime
    hackathon_end: datetime
    github_token: str | None = None


class TeamEntry(BaseModel):
    team_name: str
    repo_url: str


class BatchAnalyzeRequest(BaseModel):
    teams: list[TeamEntry]
    hackathon_start: datetime
    hackathon_end: datetime
    github_token: str | None = None


def _result_to_dict(result):
    return {
        "repo_url": result.repo_url,
        "risk_score": result.risk_score,
        "verdict_band": result.verdict_band,
        "disclaimer": result.disclaimer,
        "signals": [asdict(s) for s in result.signals],
        "timeline": result.timeline,
    }


@app.post("/analyze")
def analyze(req: AnalyzeRequest):
    try:
        result = analyze_repo(
            repo_url=req.repo_url,
            hackathon_start=req.hackathon_start,
            hackathon_end=req.hackathon_end,
            github_token=req.github_token,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return _result_to_dict(result)


def _analyze_one_team(entry: TeamEntry, hackathon_start, hackathon_end, github_token):
    """Runs in a worker thread; never raises — errors are captured per-team
    so one broken repo URL doesn't take down the whole batch."""
    try:
        result = analyze_repo(
            repo_url=entry.repo_url,
            hackathon_start=hackathon_start,
            hackathon_end=hackathon_end,
            github_token=github_token,
        )
        return {"team_name": entry.team_name, "error": None, **_result_to_dict(result)}
    except Exception as e:
        return {
            "team_name": entry.team_name,
            "repo_url": entry.repo_url,
            "error": str(e),
            "risk_score": None,
            "verdict_band": None,
            "signals": [],
            "timeline": [],
        }


@app.post("/teams/analyze-batch")
def analyze_batch(req: BatchAnalyzeRequest):
    if not req.teams:
        raise HTTPException(status_code=400, detail="No teams provided")

    results = []
    # Cloning is I/O-bound (network), so a small thread pool speeds up a
    # multi-team batch considerably without adding process complexity.
    with ThreadPoolExecutor(max_workers=min(8, len(req.teams))) as pool:
        futures = {
            pool.submit(_analyze_one_team, entry, req.hackathon_start, req.hackathon_end, req.github_token): entry
            for entry in req.teams
        }
        for fut in as_completed(futures):
            results.append(fut.result())

    # Sort: successful analyses by risk score descending, failures at the end.
    results.sort(key=lambda r: (r["risk_score"] is None, -(r["risk_score"] or 0)))

    return {"count": len(results), "teams": results}


@app.get("/health")
def health():
    return {"status": "ok"}
