import hashlib
from typing import Optional
from urllib.parse import urlparse
import os


def get_repo_name(repo_url):
    """Extract repository name from URL."""
    # Remove .git extension if present
    repo_url = repo_url.rstrip("/")
    if repo_url.endswith(".git"):
        repo_url = repo_url[:-4]

    # Extract the last part of the path
    parsed = urlparse(repo_url)
    repo_name = os.path.basename(parsed.path)
    return repo_name


def _make_chunk_id(
    repo: str, file_path: str, start: int, end: int, name: Optional[str] = None
) -> str:
    """
    Create a stable unique id for a chunk. Uses repo + file path + start/end + optional name.
    Hashing ensures ids are filesystem/DB safe and reasonably short.
    """
    base = f"{repo}||{file_path}||{start}||{end}||{name or ''}"
    # stable shorter hash
    h = hashlib.sha1(base.encode("utf-8")).hexdigest()[:16]
    return f"chunk-{h}"
