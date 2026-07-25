from pydantic import BaseModel
from typing import List, Any

class SignalResponse(BaseModel):
    name: str
    weight: float
    score: float
    evidence: str
    confidence: str

class TimelineEntry(BaseModel):
    time: str
    label: str
    files_changed: int
    insertions: int
    deletions: int
    inside_window: bool

class AnalysisResultResponse(BaseModel):
    repo_url: str
    risk_score: float
    verdict_band: str
    signals: List[SignalResponse]
    timeline: List[TimelineEntry]
    disclaimer: str

class TeamAnalysisResult(BaseModel):
    team_name: str
    repo_url: str
    risk_score: float | None = None
    verdict_band: str | None = None
    signals: List[SignalResponse] = []
    timeline: List[TimelineEntry] = []
    error: str | None = None
    disclaimer: str | None = None

class BatchAnalysisResponse(BaseModel):
    count: int
    teams: List[TeamAnalysisResult]
