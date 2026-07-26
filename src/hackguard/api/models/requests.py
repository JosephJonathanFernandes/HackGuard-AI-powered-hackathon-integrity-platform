from datetime import datetime
from pydantic import BaseModel, HttpUrl, model_validator

class AnalyzeRequest(BaseModel):
    repo_url: HttpUrl
    hackathon_start: datetime
    hackathon_end: datetime
    github_token: str | None = None
    
    @model_validator(mode='after')
    def check_dates(self) -> 'AnalyzeRequest':
        if self.hackathon_start >= self.hackathon_end:
            raise ValueError('hackathon_start must be before hackathon_end')
        return self

class TeamEntry(BaseModel):
    team_name: str
    repo_url: HttpUrl

class BatchAnalyzeRequest(BaseModel):
    teams: list[TeamEntry]
    hackathon_start: datetime
    hackathon_end: datetime
    github_token: str | None = None

    @model_validator(mode='after')
    def check_dates(self) -> 'BatchAnalyzeRequest':
        if self.hackathon_start >= self.hackathon_end:
            raise ValueError('hackathon_start must be before hackathon_end')
        return self
