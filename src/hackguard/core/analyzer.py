from datetime import datetime, timezone
from typing import Optional

from hackguard.core.github_client import GithubClient
from hackguard.core.git_client import GitClient
from hackguard.core.signals import (
    evaluate_repo_creation, evaluate_stars_forks, evaluate_first_commit,
    evaluate_commit_distribution, evaluate_large_dumps, evaluate_commit_cadence,
    evaluate_message_quality, evaluate_author_spread
)
from hackguard.api.models.responses import AnalysisResultResponse, TimelineEntry

DISCLAIMER = (
    "This is a risk score based on available evidence, not proof of "
    "misconduct. Timestamps and history can be altered by a determined "
    "participant. Use this to prioritize manual review, not to accuse."
)

class RepoAnalyzer:
    """Orchestrates the analysis of a repository."""

    def __init__(self, repo_url: str, hackathon_start: datetime, hackathon_end: datetime, github_token: Optional[str] = None):
        self.repo_url = str(repo_url)
        self.hackathon_start = self._ensure_tz(hackathon_start)
        self.hackathon_end = self._ensure_tz(hackathon_end)
        self.github_token = github_token

    @staticmethod
    def _ensure_tz(dt: datetime) -> datetime:
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt

    def run_analysis(self) -> AnalysisResultResponse:
        signals = []
        github_client = GithubClient(token=self.github_token)
        owner, name = github_client.parse_repo_url(self.repo_url)

        # 1. GitHub metadata
        try:
            meta = github_client.get_repo_metadata(owner, name)
            repo_created_at = datetime.fromisoformat(meta["created_at"].replace("Z", "+00:00"))
            signals.append(evaluate_repo_creation(repo_created_at, self.hackathon_start))
            
            stars = meta.get("stargazers_count", 0)
            forks = meta.get("forks_count", 0)
            stars_signal = evaluate_stars_forks(stars, forks)
            if stars_signal:
                signals.append(stars_signal)
        except Exception as e:
            signals.append(evaluate_repo_creation(datetime.now(), self.hackathon_start, error=str(e)))

        # 2. Local Git History
        with GitClient(self.repo_url) as git_client:
            commits = git_client.get_commit_stats()

            if not commits:
                raise RuntimeError("Repo has no commits")

            signals.append(evaluate_first_commit(commits, self.hackathon_start))
            signals.append(evaluate_commit_distribution(commits, self.hackathon_start, self.hackathon_end))
            signals.append(evaluate_large_dumps(commits, self.hackathon_start, self.hackathon_end))
            signals.append(evaluate_commit_cadence(commits, self.hackathon_start, self.hackathon_end))
            signals.append(evaluate_message_quality(commits))
            signals.append(evaluate_author_spread(commits))

            timeline = [
                TimelineEntry(
                    time=c["dt"].isoformat(),
                    label=c["message"][:60] or "(no message)",
                    files_changed=c["files_changed"],
                    insertions=c["insertions"],
                    deletions=c["deletions"],
                    inside_window=self.hackathon_start <= c["dt"] <= self.hackathon_end,
                )
                for c in commits
            ]

        # 3. Compile Score
        total_weight = sum(s.weight for s in signals) or 1
        risk_score = sum(s.weight * s.score for s in signals) / total_weight

        if risk_score >= 65:
            band = "HIGH — recommend manual review"
        elif risk_score >= 35:
            band = "MEDIUM — worth a closer look"
        else:
            band = "LOW — consistent with in-event development"

        return AnalysisResultResponse(
            repo_url=self.repo_url,
            risk_score=round(risk_score, 1),
            verdict_band=band,
            signals=signals,
            timeline=timeline,
            disclaimer=DISCLAIMER,
        )
