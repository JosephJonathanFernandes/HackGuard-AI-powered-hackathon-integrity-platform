from concurrent.futures import ThreadPoolExecutor, as_completed
from fastapi import APIRouter, HTTPException

from hackguard.api.models.requests import AnalyzeRequest, BatchAnalyzeRequest, TeamEntry
from hackguard.api.models.responses import AnalysisResultResponse, BatchAnalysisResponse, TeamAnalysisResult
from hackguard.core.analyzer import RepoAnalyzer

router = APIRouter()

@router.post("/analyze", response_model=AnalysisResultResponse)
def analyze(req: AnalyzeRequest):
    """Analyzes a single repository and returns a risk score."""
    try:
        analyzer = RepoAnalyzer(
            repo_url=str(req.repo_url),
            hackathon_start=req.hackathon_start,
            hackathon_end=req.hackathon_end,
            github_token=req.github_token,
        )
        return analyzer.run_analysis()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


def _analyze_one_team(entry: TeamEntry, hackathon_start, hackathon_end, github_token) -> TeamAnalysisResult:
    """Worker function for batch analysis. Catches exceptions locally."""
    try:
        analyzer = RepoAnalyzer(
            repo_url=str(entry.repo_url),
            hackathon_start=hackathon_start,
            hackathon_end=hackathon_end,
            github_token=github_token,
        )
        result = analyzer.run_analysis()
        return TeamAnalysisResult(
            team_name=entry.team_name,
            **result.model_dump()
        )
    except Exception as e:
        return TeamAnalysisResult(
            team_name=entry.team_name,
            repo_url=str(entry.repo_url),
            error=str(e)
        )

@router.post("/teams/analyze-batch", response_model=BatchAnalysisResponse)
def analyze_batch(req: BatchAnalyzeRequest):
    """Analyzes multiple repositories in parallel."""
    if not req.teams:
        raise HTTPException(status_code=400, detail="No teams provided")

    results = []
    with ThreadPoolExecutor(max_workers=min(8, len(req.teams))) as pool:
        futures = {
            pool.submit(_analyze_one_team, entry, req.hackathon_start, req.hackathon_end, req.github_token): entry
            for entry in req.teams
        }
        for fut in as_completed(futures):
            results.append(fut.result())

    # Sort: successful analyses by risk score descending, failures at the end.
    results.sort(key=lambda r: (r.risk_score is None, -(r.risk_score or 0)))

    return BatchAnalysisResponse(count=len(results), teams=results)
