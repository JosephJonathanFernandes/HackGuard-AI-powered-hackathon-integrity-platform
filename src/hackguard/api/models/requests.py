from datetime import datetime
from pydantic import BaseModel, HttpUrl

class AnalyzeRequest(BaseModel):
    repo_url: HttpUrl
    hackathon_start: datetime
    hackathon_end: datetime
    github_token: str | None = None

class TeamEntry(BaseModel):
    team_name: str
    repo_url: HttpUrl

class BatchAnalyzeRequest(BaseModel):
    teams: list[TeamEntry]
    hackathon_start: datetime
    hackathon_end: datetime
    github_token: str | None = None
