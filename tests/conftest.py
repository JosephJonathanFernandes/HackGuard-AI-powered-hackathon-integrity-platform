import pytest
from datetime import datetime, timezone

@pytest.fixture
def hackathon_start():
    return datetime(2026, 7, 24, 0, 0, tzinfo=timezone.utc)

@pytest.fixture
def hackathon_end():
    return datetime(2026, 7, 26, 0, 0, tzinfo=timezone.utc)

@pytest.fixture
def mock_commits():
    return [
        {
            "hexsha": "aaaaaa",
            "dt": datetime(2026, 7, 25, 12, 0, tzinfo=timezone.utc),
            "author": "dev@example.com",
            "message": "Update README",
            "files_changed": 1,
            "insertions": 10,
            "deletions": 5,
        },
        {
            "hexsha": "bbbbbb",
            "dt": datetime(2026, 7, 23, 12, 0, tzinfo=timezone.utc),
            "author": "dev@example.com",
            "message": "Initial commit",
            "files_changed": 5,
            "insertions": 100,
            "deletions": 0,
        }
    ]
