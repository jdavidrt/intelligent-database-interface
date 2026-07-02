"""ChromaDB context store — schema embeddings + DBProfile semantic retrieval."""

from __future__ import annotations
import os
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


def embed_text(doc_id: str, text: str, metadata: dict | None = None) -> None:
    """Embed an arbitrary text document (e.g., soundwave context markdown)."""
    col = _get_collection()
    col.upsert(documents=[text], ids=[doc_id], metadatas=[metadata or {}])


def query_context(question: str, n_results: int = 5) -> list[str]:
    """Return the top-n most relevant schema passages for a question."""
    col = _get_collection()
    results = col.query(query_texts=[question], n_results=n_results)
    return results.get("documents", [[]])[0]
