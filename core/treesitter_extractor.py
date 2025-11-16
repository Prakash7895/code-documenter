from pathlib import Path
from typing import Dict, List, Optional

from tree_sitter import Language, Node, Parser

from core.types import Chunk
from core.utils import make_chunk_id


Path("build/my-languages.so")

EXT_LANG = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".json": "json",
}

NODE_TYPES = {
    "python": {"function_definition", "class_definition"},
    "javascript": {
        "function_declaration",
        "method_definition",
        "function_expression",
        "arrow_function",
        "class_declaration",
    },
    "typescript": {
        "function_declaration",
        "method_definition",
        "function_expression",
        "arrow_function",
        "class_declaration",
    },
    "tsx": {
        "function_declaration",
        "method_definition",
        "function_expression",
        "arrow_function",
        "class_declaration",
    },
    "json": {"object", "array"},
}

DEFAULT_MAX_CHARS = 20000


class TreeSitterExtractor:
    def __init__(self, so_path: Optional[str] = "build/my-languages.so") -> None:
        self.so_path = Path(so_path)
        if not self.so_path.exists():
            raise FileNotFoundError(
                f"Tree-sitter shared lib not found at {self.so_path}"
            )

        self.lang_cache = {}
        for lang in set[str](EXT_LANG.values()):
            try:
                self.lang_cache[lang] = Language(str(self.so_path), lang)
            except Exception as e:
                print(
                    f"[TreeSitterExtractor] Warning: could not load language '{lang}' from {self.so_path}: {e}"
                )
        self._parser = Parser()

    def _get_language_for_extension(self, ext: str):
        return EXT_LANG.get(ext.lower())

    def _set_parser_language(self, lang_name: str):
        lang = self.lang_cache.get(lang_name)
        if not lang:
            raise RuntimeError(
                f"Language '{lang_name}' not available in compiled library."
            )
        self._parser.set_language(lang)

    @staticmethod
    def _node_text(node, src_bytes: bytes) -> str:
        return src_bytes[node.start_byte : node.end_byte].decode(
            "utf-8", errors="ignore"
        )

    def get_node_name(self, node: Node, lang_name: str, src):
        # Python function/class
        if lang_name == "python":
            for child in node.children:
                if child.type == "identifier":
                    return self._node_text(child, src)
            return None

        # JS/TS function declaration: function foo() {}
        if node.type == "function_declaration":
            ident = node.child_by_field_name("name")
            if ident:
                return self._node_text(ident, src)

        # JS/TS class declaration: class Foo {}
        if node.type == "class_declaration":
            ident = node.child_by_field_name("name")
            if ident:
                return self._node_text(ident, src)

        # JS/TS method: findAll() {}
        if node.type == "method_definition":
            for child in node.children:
                if child.type in ("property_identifier", "identifier"):
                    return self._node_text(child, src)

        # JS/TS arrow function: const foo = () => {}
        parent = node.parent
        if parent and parent.type == "variable_declarator":
            ident = parent.child_by_field_name("name")
            if ident:
                return self._node_text(ident, src)

        # default
        return None

    def extract_from_file(
        self, file_path: str, max_chars: int = DEFAULT_MAX_CHARS
    ) -> List[Dict]:
        p = Path(file_path)
        ext = p.suffix.lower()

        lang_name = self._get_language_for_extension(ext)

        if not lang_name:
            return []
        if lang_name not in self.lang_cache:
            print(
                f"[TreeSitterExtractor] Language '{lang_name}' not loaded; skipping {file_path}"
            )
            return []

        src_bytes = p.read_bytes()
        self._set_parser_language(lang_name)
        tree = self._parser.parse(src_bytes)
        root = tree.root_node

        results = []

        if lang_name == "json":
            code = src_bytes.decode("utf-8", errors="ignore")
            results.append(
                {
                    "file": str(p),
                    "name": Path(p).name,
                    "code": code[:max_chars]
                    + ("" if len(code) <= max_chars else "\n\n/* ...TRUNCATED... */"),
                    "start": 1,
                    "end": code.count("\n") + 1,
                    "lang": lang_name,
                }
            )
            return results

        stack = [root]
        seen_spans = set()
        node_types = NODE_TYPES.get(lang_name, set())

        while stack:
            node = stack.pop()
            if node.type in node_types:
                name = self.get_node_name(node, lang_name, src_bytes) or "<anon>"

                start_byte, end_byte = node.start_byte, node.end_byte
                span_key = (start_byte, end_byte)
                if span_key not in seen_spans:
                    seen_spans.add(span_key)
                    code = src_bytes[start_byte:end_byte].decode(
                        "utf-8", errors="ignore"
                    )

                    if len(code) > max_chars:
                        head = code[: (max_chars // 2)]
                        tail = code[-(max_chars // 2) :]
                        code = head + "\n\n/* ...TRUNCATED... */\n\n" + tail

                    start_line = node.start_point[0] + 1
                    end_line = node.end_point[0] + 1
                    results.append(
                        {
                            "file": str(p),
                            "name": name,
                            "code": code,
                            "start": start_line,
                            "end": end_line,
                            "lang": lang_name,
                        }
                    )
            for c in reversed(node.children):
                stack.append(c)

        return results

    def extract_from_repo(
        self, repo_root: str, include_exts: Optional[List[str]] = None
    ):
        root = Path(repo_root)
        exts = include_exts or list(EXT_LANG.keys())
        results = []
        for ext in exts:
            for f in root.rglob(f"*{ext}"):
                try:
                    results.extend(self.extract_from_file(str(f)))
                except Exception as e:
                    print(f"[TreeSitterExtractor] Error parsing {f}: {e}")
        return results

    def extract_chunks(self, repo_root: str, include_exts: Optional[List[str]] = None):
        funcs = self.extract_from_repo(repo_root, include_exts)

        chunks = []
        for func in funcs:
            chunks.append(
                Chunk(
                    id=make_chunk_id(
                        repo_root,
                        func["file"],
                        func["start"],
                        func["end"],
                        func["name"],
                    ),
                    repo=repo_root,
                    file=func["file"],
                    name=func["name"],
                    code=func["code"],
                    start=func["start"],
                    end=func["end"],
                    lang=func["lang"],
                )
            )

        return chunks
