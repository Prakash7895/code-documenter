from typing import List
from sentence_transformers import SentenceTransformer


class Embedder:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        vecs = self.model.encode(texts, show_progress_bar=True, convert_to_numpy=True)
        return vecs.astype("float32")
