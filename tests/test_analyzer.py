import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

from hackguard.core.analyzer import RepoAnalyzer

@pytest.fixture
def mock_github_client():
    with patch("hackguard.core.analyzer.GithubClient") as MockClient:
        instance = MockClient.return_value
        instance.parse_repo_url.return_value = ("owner", "repo")
        instance.get_repo_metadata.return_value = {
            "created_at": "2026-07-25T12:00:00Z",
            "stargazers_count": 0,
            "forks_count": 0
        }
        yield instance

@pytest.fixture
def mock_git_client(mock_commit_in_window):
    with patch("hackguard.core.analyzer.GitClient") as MockClient:
        instance = MagicMock()
        instance.get_commit_stats.return_value = [mock_commit_in_window]
        MockClient.return_value.__enter__.return_value = instance
        yield instance

def test_analyzer_happy_path(mock_github_client, mock_git_client, hackathon_start, hackathon_end):
    analyzer = RepoAnalyzer("https://github.com/owner/repo", hackathon_start, hackathon_end)
    result = analyzer.run_analysis()
    
    assert result.repo_url == "https://github.com/owner/repo"
    assert "LOW" in result.verdict_band
    assert result.risk_score < 35.0
    assert len(result.signals) > 0

def test_analyzer_zero_commits(mock_github_client, mock_git_client, hackathon_start, hackathon_end):
    mock_git_client.get_commit_stats.return_value = []
    analyzer = RepoAnalyzer("https://github.com/owner/repo", hackathon_start, hackathon_end)
    with pytest.raises(RuntimeError, match="Repo has no commits"):
        analyzer.run_analysis()

def test_analyzer_github_api_failure(mock_github_client, mock_git_client, hackathon_start, hackathon_end):
    # API failure should degrade gracefully
    mock_github_client.get_repo_metadata.side_effect = RuntimeError("Rate limited")
    
    analyzer = RepoAnalyzer("https://github.com/owner/repo", hackathon_start, hackathon_end)
    result = analyzer.run_analysis()
    
    # We should have a signal for Repo Creation Date with weight 0
    repo_creation_signal = next(s for s in result.signals if s.name == "Repository creation date")
    assert repo_creation_signal.weight == 0.0
    assert repo_creation_signal.score == 0.0
    assert "skipped" in repo_creation_signal.evidence
    
    # The score should still compute gracefully from the remaining signals
    assert result.risk_score >= 0.0

def test_analyzer_timezone_handling(mock_github_client, mock_git_client):
    # Ensure dt objects without tzinfo are bumped to UTC safely
    analyzer = RepoAnalyzer(
        "https://github.com/owner/repo",
        datetime(2026, 7, 24),
        datetime(2026, 7, 26, tzinfo=timezone.utc)
    )
    assert analyzer.hackathon_start.tzinfo == timezone.utc
    assert analyzer.hackathon_end.tzinfo == timezone.utc

def test_analyzer_rejects_large_repo(mock_github_client, mock_git_client):
    # If the metadata returns a size > 1,000,000 KB, it should throw ValueError immediately
    mock_github_client.get_repo_metadata.return_value = {
        "created_at": "2026-07-20T12:00:00Z",
        "stargazers_count": 5,
        "forks_count": 1,
        "size": 1500000  # 1.5 GB
    }
    
    analyzer = RepoAnalyzer(
        "https://github.com/owner/repo",
        datetime(2026, 7, 24, tzinfo=timezone.utc),
        datetime(2026, 7, 26, tzinfo=timezone.utc)
    )
    
    with pytest.raises(ValueError, match="Repository is too large"):
        analyzer.run_analysis()

def test_weighted_score_math():
    from hackguard.api.models.responses import SignalResponse
    
    # Setup mock signals to verify risk_score math
    s1 = SignalResponse(name="s1", weight=0.5, score=100.0, evidence="", confidence="")
    s2 = SignalResponse(name="s2", weight=0.5, score=0.0, evidence="", confidence="")
    
    analyzer = RepoAnalyzer("url", datetime.now(), datetime.now())
    # We mock run_analysis internals to return our exact signals
    with patch("hackguard.core.analyzer.GithubClient") as MockGH, \
         patch("hackguard.core.analyzer.GitClient") as mock_git:
         
        MockGH.return_value.parse_repo_url.return_value = ("a", "b")
        mock_git.return_value.__enter__.return_value.get_commit_stats.return_value = [{"hexsha": "1", "dt": datetime.now(timezone.utc), "author": "dev", "message": "msg", "files_changed": 1, "insertions": 1, "deletions": 0}]
        
        # Override the signals list logic directly by patching the signal evaluations
        with patch("hackguard.core.analyzer.evaluate_first_commit", return_value=s1), \
             patch("hackguard.core.analyzer.evaluate_commit_distribution", return_value=s2), \
             patch("hackguard.core.analyzer.evaluate_repo_creation", return_value=SignalResponse(name="x", weight=0.0, score=0.0, evidence="", confidence="")), \
             patch("hackguard.core.analyzer.evaluate_large_dumps", return_value=SignalResponse(name="x", weight=0.0, score=0.0, evidence="", confidence="")), \
             patch("hackguard.core.analyzer.evaluate_commit_cadence", return_value=SignalResponse(name="x", weight=0.0, score=0.0, evidence="", confidence="")), \
             patch("hackguard.core.analyzer.evaluate_message_quality", return_value=SignalResponse(name="x", weight=0.0, score=0.0, evidence="", confidence="")), \
             patch("hackguard.core.analyzer.evaluate_author_spread", return_value=SignalResponse(name="x", weight=0.0, score=0.0, evidence="", confidence="")):
             
             result = analyzer.run_analysis()
             # sum(w*s)/total_w => (0.5*100 + 0.5*0) / 1.0 = 50.0
             assert result.risk_score == 50.0
