from typing import List, Tuple
from openai import OpenAI
import os
from pathlib import Path
from dotenv import load_dotenv

from core.cloner import RepoCloner
from core.docgen import DocGenerator, LLMConfig
from core.embedder import Embedder
from core.indexer.faiss_indexer import FaissIndexer
from core.parser import Parser
from core.types import Chunk


load_dotenv()

client = OpenAI()


code_clone_dir = RepoCloner(
    "https://github.com/Prakash7895/Character-Recognition-using-Backpropagation.git",
)


chunks = []
for file in Path(code_clone_dir.clone_repo()).rglob("*.py"):
    print("file", file.name)
    chunks = Parser(file).extract_chunks()
    print(len(chunks))

id2chunk = {chunk.id: chunk for chunk in chunks}


embedder = Embedder()

vectors = embedder.embed_texts([func.code for func in chunks])
print(vectors.shape)

indexer = FaissIndexer(vectors.shape[1])


def get_similar_chunks(
    query: str, embedder: Embedder, indexer: FaissIndexer, id2chunk, k=5
):
    vec = embedder.embed_texts([query])[0]
    results = indexer.search(vec, k)
    return [(id2chunk[result["id"]], result["score"]) for result in results]


cfg = LLMConfig(model="gpt-3.5-turbo", temperature=0.0, max_tokens=500)

dg = DocGenerator(llm_client=client, config=cfg)


def write_markdown(chunk, md, output_dir="./documentations"):
    root = Path(output_dir)
    file_path = Path(chunk.file)
    out_file = root / file_path.name.replace(".py", ".md")
    out_file.parent.mkdir(parents=True, exist_ok=True)

    name = f"{chunk.name or'chunk_'}_{chunk.start}_{chunk.end}.md"
    (out_file.parent / name).write_text(md)


for chunk in chunks:
    related_chunks = get_similar_chunks(chunk.code, embedder, indexer, id2chunk)
    md = dg.generate_function_md(chunk, related_chunks)
    write_markdown(chunk, md)
