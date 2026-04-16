import re

from rank_bm25 import BM25Okapi
from sqlalchemy import select

from app.database import SessionLocal
from app.models import EventSummary
from app.services.embedding_store import EmbeddingStore

RRF_K = 60  # standard RRF smoothing constant reduces top-rank dominance
FETCH_K = 20  # fetch from each ranker
TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())

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
    def search(self, query: str, k: int = 10) -> list[int]:
        if not query.strip():
            return []

        vector_ids = EmbeddingStore().search(query, k=FETCH_K)
        keyword_ids = self._keyword_search(query, k=FETCH_K)
        return reciprocal_rank_fusion([vector_ids, keyword_ids], top_k=k)

    def _keyword_search(self, query: str, k: int) -> list[int]:
        
        db = SessionLocal()
        try:
            rows = db.execute(
                select(EventSummary.id, EventSummary.summary)
            ).all()
        finally:
            db.close()

        if not rows:
            return []

        doc_ids = [row[0] for row in rows]
        tokenized_corpus = [tokenize(row[1]) for row in rows]
        # BM25Okapi requires a non-empty corpus; empty token lists per doc are fine
        bm25 = BM25Okapi(tokenized_corpus)

        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        scores = bm25.get_scores(query_tokens)
        # pair back with doc_ids, drop zero/negative scores, take top k
        ranked = sorted(
            ((doc_id, score) for doc_id, score in zip(doc_ids, scores) if score > 0),
            key=lambda pair: pair[1],
            reverse=True,
        )
        return [doc_id for doc_id, _ in ranked[:k]]
