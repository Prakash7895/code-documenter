from typing import List, Tuple
from openai import OpenAI
import os
from pathlib import Path
from dotenv import load_dotenv

from core.cloner import RepoCloner
from core.embedder import Embedder
from core.indexer.faiss_indexer import FaissIndexer
from core.parser import Parser
from core.types import Chunk


load_dotenv()

client = OpenAI()


def generate_response(prompt):
    resp = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    return resp.choices[0].message.content


# resp = generate_response("What model are you? what is your name?")
# print(resp)


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
indexer.add(vectors, [func.id for func in chunks])
# indexer.save(code_clone_dir.clone_repo())


results = indexer.search(vectors[1])
print(results)


def get_similar_chunks(
    query: str, embedder: Embedder, indexer: FaissIndexer, id2chunk, k=5
):
    vec = embedder.embed_texts([query])[0]
    results = indexer.search(vec, k)
    return [(id2chunk[result["id"]], result["score"]) for result in results]


FUNCTION_PROMPT = """
You're an expert software engineer.
Generate clear, accurate documentation for the following function.

### Target Function
File: {file}
Function: {name}
Lines: {start}-{end}
Code: {code}

### Related Code (Context)
{context}

### Task
1. Explain what this function does.
2. Explain parameters & expected types.
3. Explain return values.
4. Explain how this fits into the file/module.
5. Write a short example usage.
6. Highlight any edge cases or surprising behaviors.

Return only Markdown.
"""


def generate_doc_for_chunk(chunk: Chunk, related_chunks: List[Tuple[Chunk, float]]):
    context_text = "\n\n".join(
        [f"#### {c.name} ({c.file})\n```\n{c.code}\n```" for c, score in related_chunks]
    )

    prompt = FUNCTION_PROMPT.format(
        file=chunk.file,
        name=chunk.name,
        start=chunk.start,
        end=chunk.end,
        code=chunk.code,
        context=context_text,
    )

    return generate_response(prompt)


def write_markdown(chunk, md, output_dir="./documentations"):
    root = Path(output_dir)
    file_path = Path(chunk.file)
    out_file = root / file_path.name.replace(".py", ".md")
    out_file.parent.mkdir(parents=True, exist_ok=True)

    name = f"{chunk.name or'chunk_'}_{chunk.start}_{chunk.end}.md"
    (out_file.parent / name).write_text(md)


for chunk in chunks:
    related_chunks = get_similar_chunks(chunk.code, embedder, indexer, id2chunk)
    md = generate_doc_for_chunk(chunk, related_chunks)
    write_markdown(chunk, md)
