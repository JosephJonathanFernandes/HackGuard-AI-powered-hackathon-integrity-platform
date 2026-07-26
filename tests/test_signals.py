from datetime import datetime, timezone
import pytest

from hackguard.core.signals import (
    evaluate_repo_creation, evaluate_stars_forks, evaluate_first_commit,
    evaluate_commit_distribution, evaluate_large_dumps, evaluate_commit_cadence,
    evaluate_message_quality, evaluate_author_spread
)

def test_evaluate_repo_creation(hackathon_start):
    # Before window
    repo_created = datetime(2026, 7, 20, 0, 0, tzinfo=timezone.utc)
    signal = evaluate_repo_creation(repo_created, hackathon_start)
    assert signal.score > 5
    assert signal.weight == 0.20
    assert "4.0 day(s) before" in signal.evidence

    # After window
    repo_created_after = datetime(2026, 7, 25, 0, 0, tzinfo=timezone.utc)
    signal_after = evaluate_repo_creation(repo_created_after, hackathon_start)
    assert signal_after.score == 5.0

    # With API Error
    signal_err = evaluate_repo_creation(datetime.now(), hackathon_start, error="API Limit")
    assert signal_err.score == 0.0
    assert signal_err.weight == 0.0
    assert "skipped" in signal_err.evidence

def test_evaluate_stars_forks():
    assert evaluate_stars_forks(0, 0) is None
    signal = evaluate_stars_forks(1, 1)
    assert signal.score == 20.0
    assert signal.weight == 0.10

def test_evaluate_first_commit(mock_commit_before_window, mock_commit_in_window, hackathon_start):
    # Sort commits ascending
    commits = [mock_commit_before_window, mock_commit_in_window]
    signal = evaluate_first_commit(commits, hackathon_start)
    assert signal.score > 5
    assert "4.0 day(s) before" in signal.evidence

def test_evaluate_commit_distribution_and_boundary(
    mock_commit_before_window, mock_commit_in_window, 
    mock_commit_boundary_start, mock_commit_boundary_end,
    hackathon_start, hackathon_end
):
    # 4 commits total: 1 before, 3 inside (including boundaries)
    commits = [mock_commit_before_window, mock_commit_boundary_start, mock_commit_in_window, mock_commit_boundary_end]
    signal = evaluate_commit_distribution(commits, hackathon_start, hackathon_end)
    # Only 1 is before hackathon start (25%)
    assert signal.score == 25.0
    assert "1/4 commits" in signal.evidence

def test_evaluate_large_dumps(mock_commit_in_window, mock_commit_large_dump, hackathon_start, hackathon_end):
    commits = [mock_commit_in_window, mock_commit_large_dump]
    signal = evaluate_large_dumps(commits, hackathon_start, hackathon_end)
    assert signal.score == 85.0
    assert "one shot" in signal.evidence

    # No large dump
    commits_safe = [mock_commit_in_window, mock_commit_in_window]
    signal_safe = evaluate_large_dumps(commits_safe, hackathon_start, hackathon_end)
    assert signal_safe.score == 5.0

def test_evaluate_commit_cadence(mock_commit_in_window, hackathon_start, hackathon_end):
    # 1 commit (division by zero edge case)
    commits = [mock_commit_in_window]
    signal = evaluate_commit_cadence(commits, hackathon_start, hackathon_end)
    assert signal.score == 70.0
    assert "Only 1 commit" in signal.evidence

    # 2 commits, close together (good cadence)
    commit2 = dict(mock_commit_in_window)
    commit2["dt"] = mock_commit_in_window["dt"] + __import__("datetime").timedelta(hours=2)
    commits2 = [mock_commit_in_window, commit2]
    signal2 = evaluate_commit_cadence(commits2, hackathon_start, hackathon_end)
    assert signal2.score == 10.0

def test_evaluate_message_quality(mock_commit_in_window):
    commit_bad = dict(mock_commit_in_window)
    commit_bad["message"] = "wip"
    signal = evaluate_message_quality([mock_commit_in_window, commit_bad])
    # 1 out of 2 is bad -> 50%
    assert signal.score == 50.0

def test_evaluate_author_spread(mock_commit_in_window):
    signal = evaluate_author_spread([mock_commit_in_window])
    assert signal.score == 5.0
