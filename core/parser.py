import ast
from pathlib import Path

from core.types import Chunk
from core.utils import _make_chunk_id


class Parser:
    def __init__(self, repo_dir):
        self.repo_dir = repo_dir

    def extract_python_functions(self):
        print("repo_dir", self.repo_dir)
        path = Path(self.repo_dir)

        source = path.read_text()
        tree = ast.parse(source)

        funcs = []
        lines = source.splitlines()

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                start = node.lineno
                end = node.end_lineno

                code = "\n".join(lines[start - 1 : end])

                funcs.append(
                    {
                        "file": str(path),
                        "name": node.name,
                        "code": code,
                        "start": start,
                        "end": end,
                    }
                )

        return funcs

    def extract_chunks(self):
        funcs = self.extract_python_functions()

        chunks = []
        for func in funcs:
            chunks.append(
                Chunk(
                    id=_make_chunk_id(
                        self.repo_dir,
                        func["file"],
                        func["start"],
                        func["end"],
                        func["name"],
                    ),
                    repo=self.repo_dir,
                    file=func["file"],
                    name=func["name"],
                    code=func["code"],
                    start=func["start"],
                    end=func["end"],
                )
            )

        return chunks
