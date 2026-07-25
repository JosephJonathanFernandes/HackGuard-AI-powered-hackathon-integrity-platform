from datetime import datetime, timezone
from hackguard.core.signals import (
    evaluate_repo_creation,
    evaluate_first_commit,
    evaluate_stars_forks,
    evaluate_commit_distribution
)

def test_evaluate_repo_creation_before_start(hackathon_start):
    repo_created = datetime(2026, 7, 20, 0, 0, tzinfo=timezone.utc)
    signal = evaluate_repo_creation(repo_created, hackathon_start)
    assert signal.score > 5
    assert "4.0 day(s) before" in signal.evidence

def test_evaluate_stars_forks():
    signal = evaluate_stars_forks(5, 2)
    assert signal.score == 70
    assert signal.weight == 0.10

def test_evaluate_first_commit(mock_commits, hackathon_start):
    # first commit in mock_commits is 'bbbbbb' at index 1 (reverse chronological usually, but evaluate expects commits[0] to be first or handles it... wait, the logic uses commits[0]['dt'] - let's check what analyzer passed).
    # wait, analyzer.py had `for c in repo.iter_commits("--all", reverse=True):` so commits[0] is the FIRST commit chronologically.
    # So we should pass mock_commits sorted by date.
    sorted_commits = sorted(mock_commits, key=lambda x: x["dt"])
    signal = evaluate_first_commit(sorted_commits, hackathon_start)
    assert signal.score > 5

def test_evaluate_commit_distribution(mock_commits, hackathon_start, hackathon_end):
    signal = evaluate_commit_distribution(mock_commits, hackathon_start, hackathon_end)
    assert signal.score == 50.0  # 1 out of 2 commits is before the window
