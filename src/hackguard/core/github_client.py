import requests
import re
from typing import Optional, Tuple, Dict, Any

class GithubClient:
    """Client for interacting with the GitHub API."""
    
    BASE_URL = "https://api.github.com"
    
    def __init__(self, token: Optional[str] = None):
        self.token = token
        self.headers = {"Accept": "application/vnd.github+json"}
        if self.token:
            self.headers["Authorization"] = f"Bearer {self.token}"

    @staticmethod
    def parse_repo_url(url: str) -> Tuple[str, str]:
        """Extracts owner and repo name from a GitHub URL."""
        m = re.search(r"github\.com[:/]+([^/]+)/([^/.]+)", str(url))
        if not m:
            raise ValueError(f"Could not parse a GitHub owner/repo from URL: {url}")
        return m.group(1), m.group(2)

    def get_repo_metadata(self, owner: str, repo_name: str) -> Dict[str, Any]:
        """Fetches repository metadata from the GitHub API."""
        url = f"{self.BASE_URL}/repos/{owner}/{repo_name}"
        resp = requests.get(url, headers=self.headers, timeout=15)
        
        if resp.status_code == 403:
            raise RuntimeError("GitHub API rate-limited — pass a token for higher limits")
        resp.raise_for_status()
        
        return resp.json()
