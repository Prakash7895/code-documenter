import json
from pathlib import Path
import faiss
import numpy as np


class FaissIndexer:
    def __init__(self, dim: int, index_path: str = None):
        self.dim = dim
        self.index = faiss.IndexHNSWFlat(dim, 32)
        self.id_map = []
        self.index_path = index_path

    def add(self, vectors: np.ndarray, ids: list):
        self.index.add(
            vectors,
        )
        self.id_map.extend(ids)

    def search(self, vector: np.ndarray, k: int = 5):
        if vector.ndim == 1:
            vector = vector.reshape(1, -1)

        D, I = self.index.search(vector.astype("float32"), k)
        results = []
        for dist, idx in zip(D[0], I[0]):
            if idx < 0 or idx >= len(self.id_map):
                continue
            results.append({"id": self.id_map[idx], "score": float(dist)})
        return results

    def save(self, out_dir: str):
        p = Path(out_dir)
        p.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(p / "index.faiss"))
        (p / "id_map.json").write_text(json.dumps(self.id_map))

    def load(self, in_dir: str):
        p = Path(in_dir)
        self.index = faiss.read_index(str(p / "index.faiss"))
        self.id_map = json.loads((p / "id_map.json").read_text())
