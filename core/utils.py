import hashlib
import re
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


def make_chunk_id(
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


def strip_triple_backticks(text: str) -> str:
    """
    Remove a surrounding fenced code block if the model wrapped the entire response,
    e.g. ```markdown\n...\n```  or ```\n...\n```.
    Only strips when the entire text is wrapped.
    """
    if not text:
        return text
    # pattern: optional leading whitespace, starting ``` with optional lang, capture inner, ending ```
    m = re.match(r"^\s*```(?:[\w+-]*)\s*\n(.*)\n```(?:\s*)$", text, flags=re.DOTALL)
    if m:
        return m.group(1).strip()
    return text.strip()


def is_all_ok(val_text: str) -> bool:
    """
    Normalize validator responses to decide whether it's ALL_OK.
    Accepts:
      - "ALL_OK"
      - "All_OK"
      - "all ok"
      - "Validation result:\nALL_OK"
      - trailing periods or whitespace
    """
    if not val_text:
        return False
    # remove "Validation result:" or similar prefixes
    txt = re.sub(r"^\s*Validation\s*result\s*:\s*", "", val_text, flags=re.I).strip()
    # keep only the core token words, uppercase and remove punctuation
    core = re.sub(r"[^A-Za-z0-9_]", "", txt).upper()
    return core in ("ALLOK", "ALL_OK", "OK")
