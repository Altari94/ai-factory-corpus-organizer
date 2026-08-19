from collections.abc import Sequence

from app.domain.discovery import TopicCluster


class VersionedTopicNamer:
    """Provider-neutral naming contract; labels never identify clusters."""

    def __init__(self, prompt_version: str = "topic-naming-v1") -> None:
        self.prompt_version = prompt_version

    def name(self, cluster: TopicCluster, representative_texts: Sequence[str]) -> TopicCluster:
        label = " / ".join(text.split()[0] for text in representative_texts[:3] if text.split()) or "Unassigned"
        return cluster.model_copy(update={"label": label, "metadata": {**cluster.metadata, "prompt_version": self.prompt_version}})
