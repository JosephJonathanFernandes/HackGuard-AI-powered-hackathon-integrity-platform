import tempfile
import shutil
from datetime import datetime, timezone
from typing import List, Dict, Any
from git import Repo, GitCommandError

class GitClient:
    """Client for performing git operations locally."""
    
    def __init__(self, repo_url: str):
        self.repo_url = str(repo_url)
        self.workdir = tempfile.mkdtemp(prefix="hackguard_")
        self.repo = None

    def clone(self) -> None:
        """Clones the repository to a temporary directory."""
        try:
            self.repo = Repo.clone_from(self.repo_url, self.workdir)
        except GitCommandError as e:
            raise RuntimeError(f"Could not clone {self.repo_url}: {e}")

    def get_commit_stats(self) -> List[Dict[str, Any]]:
        """Walks the full history and returns stats per commit."""
        if not self.repo:
            raise RuntimeError("Repository not cloned yet.")
            
        commits = []
        for c in self.repo.iter_commits("--all", reverse=True):
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

    def cleanup(self) -> None:
        """Removes the temporary directory."""
        if self.repo:
            self.repo.close()
        shutil.rmtree(self.workdir, ignore_errors=True)

    def __enter__(self):
        try:
            self.clone()
        except Exception:
            self.cleanup()
            raise
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
