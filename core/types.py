from dataclasses import dataclass


@dataclass
class Chunk:
    id: str
    repo: str
    file: str
    name: str
    code: str
    start: int
    end: int
    lang: str = "python"
    meta: dict = None
