from collections.abc import Sequence
from supabase import Client

from app.domain.embedding import SimilarityQuery, SimilarityResult, StoredEmbedding


class SupabaseVectorAdapter:
    """Supabase adapter; pgvector details stay outside the domain and ports."""

    def __init__(self, client: Client) -> None:
        self.client = client

    def save(self, embeddings: Sequence[StoredEmbedding]) -> None:
        if not embeddings:
            return
        self.client.table("embeddings").insert(
            [
                {
                    "embedding_id": str(item.embedding_id),
                    "organizer_run_id": str(item.organizer_run_id),
                    "canonical_unit_id": str(item.canonical_unit_id),
                    "embedding_profile_id": item.profile_id,
                    "model_version": item.model_version,
                    "dimensions": item.dimensions,
                    "embedding": item.vector,
                    "created_at": item.created_at.isoformat(),
                    "metadata": item.metadata,
                }
                for item in embeddings
            ]
        ).execute()

    def similarity_search(self, query: SimilarityQuery) -> list[SimilarityResult]:
        response = self.client.rpc(
            "match_canonical_embeddings",
            {
                "query_embedding": query.vector,
                "query_profile_id": query.profile_id,
                "match_threshold": query.threshold if query.threshold is not None else -1.0,
                "match_count": query.limit,
            },
        ).execute()
        return [SimilarityResult.model_validate(row) for row in response.data]

