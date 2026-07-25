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

    return {
        "repo_url": result.repo_url,
        "risk_score": result.risk_score,
        "verdict_band": result.verdict_band,
        "disclaimer": result.disclaimer,
        "signals": [asdict(s) for s in result.signals],
        "timeline": result.timeline,
    }


@app.get("/health")
def health():
    return {"status": "ok"}
