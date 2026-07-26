import time
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from hackguard.api.main import app
from hackguard.api.models.responses import AnalysisResultResponse

client = TestClient(app)

def test_cors_headers():
    response = client.options("/analyze", headers={
        "Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "POST",
    })
    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers

def test_analyze_invalid_url():
    # Should 400, not 500
    response = client.post("/analyze", json={
        "repo_url": "not-a-url",
        "hackathon_start": "2026-07-24T00:00:00Z",
        "hackathon_end": "2026-07-26T00:00:00Z"
    })
    assert response.status_code == 422 # Pydantic validation error

def test_analyze_happy_path():
    with patch("hackguard.api.routes.analysis.RepoAnalyzer") as MockAnalyzer:
        mock_instance = MockAnalyzer.return_value
        mock_instance.run_analysis.return_value = AnalysisResultResponse(
            repo_url="https://github.com/a/b",
            risk_score=10.0,
            verdict_band="LOW",
            signals=[],
            timeline=[],
            disclaimer="Disclaimer text"
        )
        
        response = client.post("/analyze", json={
            "repo_url": "https://github.com/a/b",
            "hackathon_start": "2026-07-24T00:00:00Z",
            "hackathon_end": "2026-07-26T00:00:00Z"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["risk_score"] == 10.0
        assert data["verdict_band"] == "LOW"

def test_batch_analyze_empty():
    response = client.post("/teams/analyze-batch", json={
        "teams": [],
        "hackathon_start": "2026-07-24T00:00:00Z",
        "hackathon_end": "2026-07-26T00:00:00Z"
    })
    assert response.status_code == 400
    assert response.json()["detail"] == "No teams provided"

def test_batch_analyze_mixed_and_sorting():
    with patch("hackguard.api.routes.analysis.RepoAnalyzer.run_analysis", autospec=True) as mock_run:
        def side_effect(self):
            url = self.repo_url
            if "fail" in url:
                raise RuntimeError("Failed to clone")
            score = 90.0 if "high" in url else 10.0
            
            return AnalysisResultResponse(
                repo_url=url,
                risk_score=score,
                verdict_band="HIGH" if score > 50 else "LOW",
                signals=[],
                timeline=[],
                disclaimer="Disclaimer"
            )
            
        mock_run.side_effect = side_effect
        
        response = client.post("/teams/analyze-batch", json={
            "teams": [
                {"team_name": "Team Low", "repo_url": "https://github.com/a/low"},
                {"team_name": "Team Fail", "repo_url": "https://github.com/a/fail"},
                {"team_name": "Team High", "repo_url": "https://github.com/a/high"},
            ],
            "hackathon_start": "2026-07-24T00:00:00Z",
            "hackathon_end": "2026-07-26T00:00:00Z"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 3
        
        # Check sort order: Success desc by risk score, then failures
        teams = data["teams"]
        assert teams[0]["team_name"] == "Team High"
        assert teams[0]["risk_score"] == 90.0
        
        assert teams[1]["team_name"] == "Team Low"
        assert teams[1]["risk_score"] == 10.0
        
        assert teams[2]["team_name"] == "Team Fail"
        assert teams[2]["error"] == "Failed to clone"
        assert teams[2]["risk_score"] is None

def test_batch_analyze_concurrency():
    # Test that the ThreadPoolExecutor actually parallelizes
    with patch("hackguard.api.routes.analysis.RepoAnalyzer.run_analysis", autospec=True) as mock_run:
        def slow_analysis(self):
            time.sleep(0.1) # 100ms per analysis
            return AnalysisResultResponse(
                repo_url=self.repo_url,
                risk_score=10.0,
                verdict_band="LOW",
                signals=[],
                timeline=[],
                disclaimer="Disclaimer text"
            )
            
        mock_run.side_effect = slow_analysis
        
        # 8 teams * 0.1s = 0.8s if serial.
        # Max workers is min(8, len(teams)), so 8 workers.
        # Parallel time should be ~0.1s.
        teams = [{"team_name": f"Team {i}", "repo_url": f"https://github.com/a/b{i}"} for i in range(8)]
        
        start_time = time.time()
        response = client.post("/teams/analyze-batch", json={
            "teams": teams,
            "hackathon_start": "2026-07-24T00:00:00Z",
            "hackathon_end": "2026-07-26T00:00:00Z"
        })
        end_time = time.time()
        
        assert response.status_code == 200
        assert response.json()["count"] == 8
        
        elapsed = end_time - start_time
        # Allow some overhead, but it definitely shouldn't take 0.8 seconds.
        assert elapsed < 0.5
