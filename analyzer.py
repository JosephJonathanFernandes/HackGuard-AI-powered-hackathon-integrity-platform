"""
HackGuard Git Repository Analyzer
----------------------------------
Clones a GitHub repo, inspects its commit history against a declared
hackathon window, and produces a RISK SCORE (not a verdict) describing
how likely it is the project pre-dates the event — with the evidence
that fed into the score, so a human judge can make the actual call.
"""

import os
import re
import shutil
import statistics
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import requests
from git import Repo, GitCommandError

GITHUB_API = "https://api.github.com"

GENERIC_MESSAGES = {
    "update", "updates", "fix", "final", "final final", "wip",
    "initial commit", "changes", "commit", "test", "asdf", "misc",
}


@dataclass
class Signal:
    name: str
    weight: float          # 0-1, relative importance
    score: float            # 0-100, this signal's own risk contribution
    evidence: str            # human-readable explanation
    confidence: str = "medium"  # how spoofable / trustworthy this signal is


@dataclass
class AnalysisResult:
    repo_url: str
    risk_score: float
    verdict_band: str
    signals: list = field(default_factory=list)
    timeline: list = field(default_factory=list)
    disclaimer: str = (
        "This is a risk score based on available evidence, not proof of "
        "misconduct. Timestamps and history can be altered by a determined "
        "participant. Use this to prioritize manual review, not to accuse."
    )


def _parse_github_repo(url: str):
    m = re.search(r"github\.com[:/]+([^/]+)/([^/.]+)", url)
    if not m:
        raise ValueError("Could not parse a GitHub owner/repo from that URL")
    return m.group(1), m.group(2)


def _github_api_get(path: str, token: Optional[str] = None):
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    resp = requests.get(f"{GITHUB_API}{path}", headers=headers, timeout=15)
    if resp.status_code == 403:
        raise RuntimeError("GitHub API rate-limited — pass a token for higher limits")
    resp.raise_for_status()
    return resp.json()


def clone_repo(repo_url: str, workdir: str) -> Repo:
    try:
        return Repo.clone_from(repo_url, workdir)
    except GitCommandError as e:
        raise RuntimeError(f"Could not clone {repo_url}: {e}")


def _commit_stats(repo: Repo):
    """Walk full history, return list of dicts: hash, dt, author, msg, files_changed, insertions, deletions"""
    commits = []
    for c in repo.iter_commits("--all", reverse=True):
        stats = c.stats.total
        commits.append({
            "hexsha": c.hexsha[:8],
            "dt": datetime.fromtimestamp(c.committed_date, tz=timezone.utc),
            "author": c.author.email or c.author.name,
            "message": c.message.strip().splitlines()[0] if c.message else "",
            "files_changed": stats.get("files", 0),
            "insertions": stats.get("insertions", 0),
            "deletions": stats.get("deletions", 0),
        })
    return commits


def analyze_repo(
    repo_url: str,
    hackathon_start: datetime,
    hackathon_end: datetime,
    github_token: Optional[str] = None,
) -> AnalysisResult:
    if hackathon_start.tzinfo is None:
        hackathon_start = hackathon_start.replace(tzinfo=timezone.utc)
    if hackathon_end.tzinfo is None:
        hackathon_end = hackathon_end.replace(tzinfo=timezone.utc)

    owner, name = _parse_github_repo(repo_url)

    signals = []

    # --- 1. GitHub metadata (repo creation date, stars/forks pre-event) ---
    # Best-effort: GitHub's unauthenticated API is tightly rate-limited, so a
    # missing token (or a rate-limit hit) should degrade, not crash the analysis.
    try:
        meta = _github_api_get(f"/repos/{owner}/{name}", github_token)
        repo_created_at = datetime.fromisoformat(meta["created_at"].replace("Z", "+00:00"))
        stars = meta.get("stargazers_count", 0)
        forks = meta.get("forks_count", 0)

        days_before = (hackathon_start - repo_created_at).total_seconds() / 86400
        if repo_created_at < hackathon_start:
            s_score = min(100, max(0, 40 + days_before * 2))  # older repo => higher risk, caps at 100
            evidence = (
                f"GitHub repo '{owner}/{name}' was created on {repo_created_at.date()}, "
                f"{days_before:.1f} day(s) before the declared hackathon start "
                f"({hackathon_start.date()})."
            )
        else:
            s_score = 5
            evidence = f"Repo created at {repo_created_at.date()}, on/after hackathon start — consistent with event timing."
        signals.append(Signal(
            name="Repository creation date",
            weight=0.20, score=s_score, evidence=evidence,
            confidence="medium — GitHub's own timestamp, not user-editable, but a repo can be re-created from old code",
        ))

        if stars > 0 or forks > 0:
            signals.append(Signal(
                name="Pre-existing stars/forks",
                weight=0.10, score=min(100, (stars + forks) * 10),
                evidence=f"Repo already has {stars} star(s) and {forks} fork(s), suggesting prior public visibility.",
                confidence="high — hard to fake engagement from other GitHub users",
            ))
    except Exception as e:
        signals.append(Signal(
            name="Repository creation date",
            weight=0.0, score=0,
            evidence=f"GitHub API metadata unavailable ({e}) — skipped, relying on git history signals only.",
            confidence="n/a",
        ))

    # --- 2. Clone and walk commit history ---
    workdir = tempfile.mkdtemp(prefix="hackguard_")
    try:
        repo = clone_repo(repo_url, workdir)
        commits = _commit_stats(repo)

        if not commits:
            raise RuntimeError("Repo has no commits")

        first_commit_dt = commits[0]["dt"]
        days_before_first = (hackathon_start - first_commit_dt).total_seconds() / 86400
        if first_commit_dt < hackathon_start:
            s_score = min(100, max(0, 45 + days_before_first * 3))
            evidence = (
                f"First commit is timestamped {first_commit_dt.date()}, "
                f"{days_before_first:.1f} day(s) before the hackathon started."
            )
        else:
            s_score = 5
            evidence = f"First commit at {first_commit_dt.date()}, within/after the event window."
        signals.append(Signal(
            name="First commit timestamp",
            weight=0.15, score=s_score, evidence=evidence,
            confidence="low — commit timestamps are trivially rewritable (`git commit --date`)",
        ))

        # commits inside vs before the window
        in_window = [c for c in commits if hackathon_start <= c["dt"] <= hackathon_end]
        before_window = [c for c in commits if c["dt"] < hackathon_start]
        pct_before = 100 * len(before_window) / len(commits)
        signals.append(Signal(
            name="Commit distribution vs. event window",
            weight=0.15, score=pct_before,
            evidence=(
                f"{len(before_window)}/{len(commits)} commits ({pct_before:.0f}%) fall before "
                f"the hackathon start; {len(in_window)} fall inside the official window."
            ),
            confidence="low — rewritable, same caveat as above",
        ))

        # sudden large dump: any single commit with huge insertions relative to repo history
        total_insertions = sum(c["insertions"] for c in commits) or 1
        dump_commits = [c for c in in_window if c["insertions"] > 0.5 * total_insertions and c["files_changed"] > 15]
        if dump_commits:
            dc = dump_commits[0]
            signals.append(Signal(
                name="Large code dump inside window",
                weight=0.20, score=85,
                evidence=(
                    f"Commit {dc['hexsha']} at {dc['dt']} added {dc['insertions']} lines across "
                    f"{dc['files_changed']} files in one shot — over half the project's total code, "
                    f"in a single commit. Classic signature of pasting in pre-existing work."
                ),
                confidence="medium — could also be a legitimate initial scaffold import",
            ))
        else:
            signals.append(Signal(
                name="Large code dump inside window",
                weight=0.20, score=5,
                evidence="No single commit accounts for a disproportionate share of the codebase.",
                confidence="medium",
            ))

        # commit cadence realism during window
        if len(in_window) >= 2:
            gaps_hr = []
            for a, b in zip(in_window, in_window[1:]):
                gaps_hr.append((b["dt"] - a["dt"]).total_seconds() / 3600)
            avg_gap = statistics.mean(gaps_hr)
            evidence = (
                f"{len(in_window)} commits inside the window, averaging one every {avg_gap:.1f}h — "
                f"{'a steady, incremental build-up' if avg_gap < 6 else 'sparse, bursty activity'}."
            )
            s_score = 10 if avg_gap < 6 else 40
        else:
            evidence = f"Only {len(in_window)} commit(s) inside the window — too little incremental history to show organic development."
            s_score = 70
        signals.append(Signal(
            name="Commit cadence during event",
            weight=0.15, score=s_score, evidence=evidence,
            confidence="medium — a determined faker can script evenly-spaced fake commits",
        ))

        # generic / low-effort commit messages
        msgs = [c["message"].lower().strip() for c in commits]
        generic_ct = sum(1 for m in msgs if m in GENERIC_MESSAGES or len(m) < 4)
        pct_generic = 100 * generic_ct / len(msgs)
        signals.append(Signal(
            name="Commit message quality",
            weight=0.05, score=min(60, pct_generic),
            evidence=f"{generic_ct}/{len(msgs)} commit messages are generic/low-content (e.g. 'wip', 'fix').",
            confidence="low — weak signal on its own",
        ))

        # author count sanity check
        authors = set(c["author"] for c in commits)
        signals.append(Signal(
            name="Author identity spread",
            weight=0.05, score=5 if len(authors) >= 1 else 50,
            evidence=f"{len(authors)} distinct commit author identity/identities detected.",
            confidence="low — informational, not inherently risky",
        ))

        timeline = [
            {
                "time": c["dt"].isoformat(),
                "label": c["message"][:60] or "(no message)",
                "files_changed": c["files_changed"],
                "insertions": c["insertions"],
                "deletions": c["deletions"],
                "inside_window": hackathon_start <= c["dt"] <= hackathon_end,
            }
            for c in commits
        ]

    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    # --- weighted final score ---
    total_weight = sum(s.weight for s in signals) or 1
    risk_score = sum(s.weight * s.score for s in signals) / total_weight

    if risk_score >= 65:
        band = "HIGH — recommend manual review"
    elif risk_score >= 35:
        band = "MEDIUM — worth a closer look"
    else:
        band = "LOW — consistent with in-event development"

    return AnalysisResult(
        repo_url=repo_url,
        risk_score=round(risk_score, 1),
        verdict_band=band,
        signals=signals,
        timeline=timeline,
    )
