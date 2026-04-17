from concurrent.futures import ThreadPoolExecutor

import bm25s
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import EventSummary
from app.services.embedding_store import EmbeddingStore

RRF_K = 60  # standard RRF smoothing constant reduces top-rank dominance
FETCH_K = 20  # fetch from each ranker


# takes a list of ranked lists and returns a list of the top k items
# by merging them based on the rank items are assigned in each list
def reciprocal_rank_fusion(ranked_lists: list[list[int]], top_k: int) -> list[int]:
    scores: dict[int, float] = {}
    for ranked in ranked_lists:
        for rank, doc_id in enumerate(ranked):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (RRF_K + rank)
    ordered = sorted(scores.items(), key=lambda pair: pair[1], reverse=True)
    return [doc_id for doc_id, _ in ordered[:top_k]]


class HybridSearch:
    def search(self, db: Session, query: str, k: int = 10) -> list[int]:
        if not query.strip():
            return []

        # Vector search is with ollama and keyword search is db,
        # so run them on two threads
        with ThreadPoolExecutor(max_workers=2) as pool:
            vector_future = pool.submit(EmbeddingStore().search, query, FETCH_K)
            keyword_future = pool.submit(self._keyword_search, db, query, FETCH_K)
            vector_ids = vector_future.result()
            keyword_ids = keyword_future.result()

        return reciprocal_rank_fusion([vector_ids, keyword_ids], top_k=k)

    def _keyword_search(self, db: Session, query: str, k: int) -> list[int]:
        rows = db.execute(
            select(EventSummary.id, EventSummary.summary)
        ).all()
        if not rows:
            return []

        doc_ids = [row[0] for row in rows]
        corpus_tokens = bm25s.tokenize([row[1] for row in rows], show_progress=False)

        retriever = bm25s.BM25(method="bm25l") # bm25l is better than okapi bm25 for longer text
        retriever.index(corpus_tokens, show_progress=False)

        query_tokens = bm25s.tokenize(query, show_progress=False)

        top_k = min(k, len(doc_ids))
        # retrieve() returns corpus indices (positions), not our doc_ids
        result_indices, result_scores = retriever.retrieve(
            query_tokens, k=top_k, show_progress=False
        )

        return [
            doc_ids[idx]
            for idx, score in zip(result_indices[0], result_scores[0])
            if score > 0
        ]
