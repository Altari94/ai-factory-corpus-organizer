from collections.abc import Sequence

from openai import APIConnectionError, APITimeoutError, InternalServerError, OpenAI, RateLimitError

from app.domain.embedding import EmbeddingInput, EmbeddingOutput


class OpenAIEmbeddingAdapter:
    """OpenAI embedding adapter; vector persistence stays behind VectorStorePort."""

    def __init__(self, client: OpenAI, *, model: str, expected_dimensions: int | None = None) -> None:
        self.client = client
        self.model = model
        self.expected_dimensions = expected_dimensions

    def embed(self, profile_id: str, inputs: Sequence[EmbeddingInput]) -> list[EmbeddingOutput]:
        if not inputs:
            return []
        response = self.client.embeddings.create(
            model=self.model,
            input=[item.text for item in inputs],
        )
        vectors = sorted(response.data, key=lambda item: item.index)
        if len(vectors) != len(inputs):
            raise ValueError("OpenAI returned an unexpected embedding count")
        outputs = [
            EmbeddingOutput(
                canonical_unit_id=item.canonical_unit_id,
                profile_id=profile_id,
                model_version=response.model,
                vector=list(vector.embedding),
            )
            for item, vector in zip(inputs, vectors, strict=True)
        ]
        if self.expected_dimensions is not None and any(
            len(output.vector) != self.expected_dimensions for output in outputs
        ):
            raise ValueError("OpenAI embedding dimensions do not match the configured profile")
        return outputs
