"""Retrieval seam: narrow the misconception taxonomy to top-k candidates.

Two implementations behind one ``Retriever`` interface:

- ``InContextRetriever`` — returns the whole taxonomy (optionally capped). Correct
  when the taxonomy is small enough to fit in the prompt (the fixture: 6 items;
  CLAUDE.md explicitly allows in-context for small taxonomies).
- ``EmbeddingRetriever`` — the locked production path (sentence-transformers +
  Chroma). Embeds every misconception name once, then retrieves the top-k most
  similar to the item. This is what scales to real Eedi (~2.5k misconceptions).

**Integrity:** retrieval is *blind to the gold label* — candidates are chosen by
similarity to the question/answer only. ``recall@k`` (see eval/metrics.py) then
measures how often the gold misconception actually survives into the top-k, i.e.
the ceiling the diagnoser can reach.

``build_retriever`` selects the implementation by taxonomy size / config, so the
same call works on the fixture and on real Eedi.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from .. import config
from ..models import DiagnosisItem


@runtime_checkable
class Retriever(Protocol):
    def candidates(self, item: DiagnosisItem, k: int | None = None) -> list[tuple[str, str]]:
        """Return up to k (misconception_id, name) pairs relevant to the item."""
        ...


def _query_text(item: DiagnosisItem) -> str:
    """The signal we retrieve against: the question + the chosen wrong answer."""
    return f"{item.question_text}\nStudent chose: {item.chosen_answer_text}"


class InContextRetriever:
    """Return the full taxonomy (capped to k). No narrowing, no model, no network."""

    def __init__(self, mapping: dict[str, str]):
        self._items = list(mapping.items())

    def candidates(self, item: DiagnosisItem, k: int | None = None) -> list[tuple[str, str]]:
        if k is None or k >= len(self._items):
            return list(self._items)
        return self._items[:k]


class EmbeddingRetriever:
    """sentence-transformers embeddings + Chroma vector store, top-k by cosine.

    We embed with sentence-transformers and hand the vectors to Chroma directly
    (so Chroma never needs to download its own ONNX model). Heavy imports are
    deferred to construction time so the offline/in-context path never needs them.
    """

    def __init__(
        self,
        mapping: dict[str, str],
        *,
        model_name: str | None = None,
        collection_name: str = "misconceptions",
        persist_dir=None,
    ):
        from chromadb import Client, PersistentClient
        from chromadb.config import Settings
        from sentence_transformers import SentenceTransformer

        self.model_name = model_name or config.EMBED_MODEL
        self._model = SentenceTransformer(self.model_name)

        ids = list(mapping.keys())
        names = [mapping[i] for i in ids]
        embeddings = self._model.encode(
            names, normalize_embeddings=True, show_progress_bar=False
        ).tolist()

        if persist_dir is not None:
            client = PersistentClient(path=str(persist_dir))
        else:
            client = Client(Settings(anonymized_telemetry=False))
        # fresh collection each build so a changed taxonomy never serves stale rows
        try:
            client.delete_collection(collection_name)
        except Exception:
            pass
        self._col = client.create_collection(
            collection_name, metadata={"hnsw:space": "cosine"}
        )
        self._col.add(ids=ids, embeddings=embeddings, documents=names)
        self._mapping = dict(mapping)

    def candidates(self, item: DiagnosisItem, k: int | None = None) -> list[tuple[str, str]]:
        k = k or config.RETRIEVAL_K
        q = self._model.encode(
            [_query_text(item)], normalize_embeddings=True, show_progress_bar=False
        ).tolist()
        res = self._col.query(query_embeddings=q, n_results=min(k, len(self._mapping)))
        ids = res["ids"][0]
        return [(cid, self._mapping.get(cid, "")) for cid in ids]


def build_retriever(
    mapping: dict[str, str],
    *,
    kind: str | None = None,
    persist_dir=None,
) -> Retriever:
    """Pick a retriever. 'auto' -> in-context for small taxonomies, else embeddings."""
    kind = kind or config.RETRIEVER
    if kind == "auto":
        kind = "incontext" if len(mapping) <= config.RETRIEVAL_INCONTEXT_MAX else "embedding"
    if kind == "incontext":
        return InContextRetriever(mapping)
    if kind == "embedding":
        return EmbeddingRetriever(mapping, persist_dir=persist_dir)
    raise ValueError(f"unknown retriever kind: {kind!r}")
