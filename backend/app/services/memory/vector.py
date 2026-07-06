"""ChromaDB context store — schema embeddings + DBProfile semantic retrieval."""

from __future__ import annotations
import os
import re
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

from backend.app.config import settings
from backend.app.models.envelope import DBProfile

_CHROMA_PATH = os.path.join(settings.repo_root, "data", "chromadb")
_EMBED_MODEL = "all-MiniLM-L6-v2"  # ~22 MB, CPU-friendly

_client: chromadb.PersistentClient | None = None
_collection: chromadb.Collection | None = None


def _get_collection() -> chromadb.Collection:
    global _client, _collection
    if _collection is None:
        os.makedirs(_CHROMA_PATH, exist_ok=True)
        _client = chromadb.PersistentClient(path=_CHROMA_PATH)
        embed_fn = SentenceTransformerEmbeddingFunction(model_name=_EMBED_MODEL)
        _collection = _client.get_or_create_collection(
            name="idi_schema_context",
            embedding_function=embed_fn,
        )
    return _collection


def embed_db_profile(profile: DBProfile) -> None:
    """Embed each table's column list as a document."""
    col = _get_collection()
    docs, ids, metas = [], [], []
    for table in profile.tables:
        col_names = ", ".join(c.name for c in table.columns)
        doc = f"Table: {table.name}. Columns: {col_names}."
        if table.description:
            doc += f" Description: {table.description}"
        docs.append(doc)
        ids.append(f"{profile.db_name}::{table.name}")
        metas.append({"db": profile.db_name, "table": table.name})
    if docs:
        col.upsert(documents=docs, ids=ids, metadatas=metas)


_MAX_CHUNK_CHARS = 1000  # keeps each retrieved passage well under the embedder's 256-token window


def _chunk_text(text: str, max_chars: int = _MAX_CHUNK_CHARS) -> list[str]:
    """Split on paragraph boundaries, packing consecutive paragraphs up to max_chars.

    A single oversized paragraph is hard-sliced so no chunk ever exceeds max_chars —
    otherwise it would dominate a retrieval result with mostly-irrelevant text.
    """
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    current = ""
    for para in paragraphs:
        candidate = f"{current}\n\n{para}" if current else para
        if len(candidate) <= max_chars:
            current = candidate
            continue
        if current:
            chunks.append(current)
        if len(para) <= max_chars:
            current = para
        else:
            for i in range(0, len(para), max_chars):
                chunks.append(para[i : i + max_chars])
            current = ""
    if current:
        chunks.append(current)
    return chunks or [text]


def embed_text(doc_id: str, text: str, metadata: dict | None = None) -> None:
    """Embed a text document, chunked so retrieval returns focused passages instead
    of entire files (a whole multi-KB markdown doc as one "chunk" both blows past
    the embedder's truncation window and can single-handedly overflow the LLM's
    context on retrieval)."""
    col = _get_collection()
    # Clear any previous embedding of this document, whichever shape it was stored in
    # (a pre-chunking whole-doc id, or an earlier run's chunk set).
    col.delete(ids=[doc_id])
    col.delete(where={"source_id": doc_id})

    base_meta = metadata or {}
    chunks = _chunk_text(text)
    ids = [f"{doc_id}::chunk{i}" for i in range(len(chunks))]
    metas = [{**base_meta, "source_id": doc_id} for _ in chunks]
    col.upsert(documents=chunks, ids=ids, metadatas=metas)


def query_context(question: str, n_results: int = 5) -> list[str]:
    """Return the top-n most relevant schema passages for a question."""
    col = _get_collection()
    results = col.query(query_texts=[question], n_results=n_results)
    return results.get("documents", [[]])[0]
