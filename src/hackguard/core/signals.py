import statistics
from datetime import datetime
from typing import List, Dict, Any
from hackguard.api.models.responses import SignalResponse

GENERIC_MESSAGES = {
    "update", "updates", "fix", "final", "final final", "wip",
    "initial commit", "changes", "commit", "test", "asdf", "misc",
}

def evaluate_repo_creation(repo_created_at: datetime, hackathon_start: datetime, error: str = None) -> SignalResponse:
    if error:
        return SignalResponse(
            name="Repository creation date",
            weight=0.0, score=0.0,
            evidence=f"GitHub API metadata unavailable ({error}) — skipped, relying on git history signals only.",
            confidence="n/a",
        )
    
    days_before = (hackathon_start - repo_created_at).total_seconds() / 86400
    if repo_created_at < hackathon_start:
        s_score = min(100.0, max(0.0, 40 + days_before * 2))
        evidence = (
            f"GitHub repo was created on {repo_created_at.date()}, "
            f"{days_before:.1f} day(s) before the declared hackathon start "
            f"({hackathon_start.date()})."
        )
    else:
        s_score = 5.0
        evidence = f"Repo created at {repo_created_at.date()}, on/after hackathon start — consistent with event timing."
        
    return SignalResponse(
        name="Repository creation date",
        weight=0.20, score=s_score, evidence=evidence,
        confidence="medium — GitHub's own timestamp, not user-editable, but a repo can be re-created from old code",
    )

def evaluate_stars_forks(stars: int, forks: int) -> SignalResponse | None:
    if stars > 0 or forks > 0:
        return SignalResponse(
            name="Pre-existing stars/forks",
            weight=0.10, score=float(min(100, (stars + forks) * 10)),
            evidence=f"Repo already has {stars} star(s) and {forks} fork(s), suggesting prior public visibility.",
            confidence="high — hard to fake engagement from other GitHub users",
        )
    return None

def evaluate_first_commit(commits: List[Dict[str, Any]], hackathon_start: datetime) -> SignalResponse:
    first_commit_dt = commits[-1]["dt"]
    days_before_first = (hackathon_start - first_commit_dt).total_seconds() / 86400
    if first_commit_dt < hackathon_start:
        s_score = min(100.0, max(0.0, 45 + days_before_first * 3))
        evidence = (
            f"First commit is timestamped {first_commit_dt.date()}, "
            f"{days_before_first:.1f} day(s) before the hackathon started."
        )
    else:
        s_score = 5.0
        evidence = f"First commit at {first_commit_dt.date()}, within/after the event window."
        
    return SignalResponse(
        name="First commit timestamp",
        weight=0.15, score=s_score, evidence=evidence,
        confidence="low — commit timestamps are trivially rewritable (`git commit --date`)",
    )

def evaluate_commit_distribution(commits: List[Dict[str, Any]], hackathon_start: datetime, hackathon_end: datetime) -> SignalResponse:
    in_window = [c for c in commits if hackathon_start <= c["dt"] <= hackathon_end]
    before_window = [c for c in commits if c["dt"] < hackathon_start]
    pct_before = 100.0 * len(before_window) / len(commits)
    
    return SignalResponse(
        name="Commit distribution vs. event window",
        weight=0.25, score=pct_before,
        evidence=(
            f"{len(before_window)}/{len(commits)} commits ({pct_before:.0f}%) fall before "
            f"the hackathon start; {len(in_window)} fall inside the official window."
        ),
        confidence="low — rewritable, same caveat as above",
    )

def evaluate_large_dumps(commits: List[Dict[str, Any]], hackathon_start: datetime, hackathon_end: datetime) -> SignalResponse:
    in_window = [c for c in commits if hackathon_start <= c["dt"] <= hackathon_end]
    total_insertions = sum(c["insertions"] for c in commits) or 1
    dump_commits = [c for c in in_window if c["insertions"] > 0.5 * total_insertions and c["files_changed"] > 15]
    
    if dump_commits:
        dc = dump_commits[0]
        return SignalResponse(
            name="Large code dump inside window",
            weight=0.20, score=85.0,
            evidence=(
                f"Commit {dc['hexsha']} at {dc['dt']} added {dc['insertions']} lines across "
                f"{dc['files_changed']} files in one shot — over half the project's total code, "
                f"in a single commit. Classic signature of pasting in pre-existing work."
            ),
            confidence="medium — could also be a legitimate initial scaffold import",
        )
    else:
        return SignalResponse(
            name="Large code dump inside window",
            weight=0.20, score=5.0,
            evidence="No single commit accounts for a disproportionate share of the codebase.",
            confidence="medium",
        )

def evaluate_commit_cadence(commits: List[Dict[str, Any]], hackathon_start: datetime, hackathon_end: datetime) -> SignalResponse:
    in_window = [c for c in commits if hackathon_start <= c["dt"] <= hackathon_end]
    
    if len(in_window) >= 2:
        gaps_hr = []
        for a, b in zip(in_window, in_window[1:]):
            gaps_hr.append(abs((b["dt"] - a["dt"]).total_seconds() / 3600))
        avg_gap = statistics.mean(gaps_hr)
        evidence = (
            f"{len(in_window)} commits inside the window, averaging one every {avg_gap:.1f}h — "
            f"{'a steady, incremental build-up' if avg_gap < 6 else 'sparse, bursty activity'}."
        )
        s_score = 10.0 if avg_gap < 6 else 40.0
    else:
        evidence = f"Only {len(in_window)} commit(s) inside the window — too little incremental history to show organic development."
        s_score = 70.0
        
    return SignalResponse(
        name="Commit cadence during event",
        weight=0.15, score=s_score, evidence=evidence,
        confidence="medium — a determined faker can script evenly-spaced fake commits",
    )

def evaluate_message_quality(commits: List[Dict[str, Any]]) -> SignalResponse:
    msgs = [c["message"].lower().strip() for c in commits]
    generic_ct = sum(1 for m in msgs if m in GENERIC_MESSAGES or len(m) < 4)
    pct_generic = 100.0 * generic_ct / len(msgs)
    
    return SignalResponse(
        name="Commit message quality",
        weight=0.05, score=min(60.0, pct_generic),
        evidence=f"{generic_ct}/{len(msgs)} commit messages are generic/low-content (e.g. 'wip', 'fix').",
        confidence="low — weak signal on its own",
    )

def evaluate_author_spread(commits: List[Dict[str, Any]]) -> SignalResponse:
    authors = set(c["author"] for c in commits)
    score = 85.0 if len(authors) == 1 else 5.0
    evidence = (
        f"Found {len(authors)} unique author(s)."
        f" {'A single author suggests lack of team collaboration.' if len(authors) == 1 else 'Multiple authors indicate collaborative work.'}"
    )
    return SignalResponse(
        name="Author spread",
        weight=0.05,
        score=score,
        evidence=evidence,
        confidence="medium"
    )
