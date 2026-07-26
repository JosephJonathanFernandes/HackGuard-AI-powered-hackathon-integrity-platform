import pytest
from datetime import datetime, timezone

@pytest.fixture
def hackathon_start():
    return datetime(2026, 7, 24, 0, 0, tzinfo=timezone.utc)

@pytest.fixture
def hackathon_end():
    return datetime(2026, 7, 26, 0, 0, tzinfo=timezone.utc)

@pytest.fixture
def mock_commit_in_window():
    return {
        "hexsha": "aaaaaa",
        "dt": datetime(2026, 7, 25, 12, 0, tzinfo=timezone.utc),
        "author": "dev@example.com",
        "message": "Update README",
        "files_changed": 1,
        "insertions": 10,
        "deletions": 5,
    }

@pytest.fixture
def mock_commit_before_window():
    return {
        "hexsha": "bbbbbb",
        "dt": datetime(2026, 7, 20, 12, 0, tzinfo=timezone.utc),
        "author": "dev@example.com",
        "message": "Initial commit",
        "files_changed": 5,
        "insertions": 100,
        "deletions": 0,
    }

@pytest.fixture
def mock_commit_large_dump():
    return {
        "hexsha": "cccccc",
        "dt": datetime(2026, 7, 24, 12, 0, tzinfo=timezone.utc),
        "author": "dev@example.com",
        "message": "Dump project files",
        "files_changed": 50,
        "insertions": 10000,
        "deletions": 0,
    }

@pytest.fixture
def mock_commit_boundary_start(hackathon_start):
    return {
        "hexsha": "dddddd",
        "dt": hackathon_start,
        "author": "dev@example.com",
        "message": "Boundary start",
        "files_changed": 1,
        "insertions": 1,
        "deletions": 0,
    }

@pytest.fixture
def mock_commit_boundary_end(hackathon_end):
    return {
        "hexsha": "eeeeee",
        "dt": hackathon_end,
        "author": "dev@example.com",
        "message": "Boundary end",
        "files_changed": 1,
        "insertions": 1,
        "deletions": 0,
    }
