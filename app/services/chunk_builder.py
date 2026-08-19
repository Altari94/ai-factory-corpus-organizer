import re
from collections.abc import Callable
from uuid import uuid4

from app.domain.llm import ChunkItem, ContextChunk, ContextUnit, ModelProfile, SelectedContext


class ChunkBuilder:
    """Builds size-bounded chunks without interpreting the content."""

    def __init__(self, token_counter: Callable[[str], int] | None = None) -> None:
        self.token_counter = token_counter or (lambda text: len(text.split()))

    def build(self, context: SelectedContext, profile: ModelProfile) -> list[ContextChunk]:
        chunks: list[ContextChunk] = []
        current: list[ChunkItem] = []
        current_tokens = 0

        for unit in context.units:
            fragments = self._split_unit(unit, profile.chunk_max_tokens)
            for fragment in fragments:
                fragment_tokens = self.token_counter(fragment.text)
                if current and current_tokens + fragment_tokens > profile.chunk_max_tokens:
                    chunks.append(self._make_chunk(len(chunks), current, current_tokens))
                    current = []
                    current_tokens = 0
                current.append(fragment)
                current_tokens += fragment_tokens
                if current_tokens >= profile.chunk_target_tokens:
                    chunks.append(self._make_chunk(len(chunks), current, current_tokens))
                    current = []
                    current_tokens = 0

        if current:
            chunks.append(self._make_chunk(len(chunks), current, current_tokens))
        return chunks

    def _split_unit(self, unit: ContextUnit, max_tokens: int) -> list[ChunkItem]:
        if self.token_counter(unit.text) <= max_tokens:
            return [ChunkItem(unit_id=unit.unit_id, text=unit.text, char_start=0, char_end=len(unit.text))]

        fragments: list[ChunkItem] = []
        current_start = 0
        last_word_end = 0
        current_text = ""
        word_spans = list(re.finditer(r"\S+", unit.text))
        for match in word_spans:
            candidate = unit.text[current_start : match.end()]
            if current_text and self.token_counter(candidate) > max_tokens:
                fragments.append(ChunkItem(unit_id=unit.unit_id, text=current_text, char_start=current_start, char_end=last_word_end))
                current_start = last_word_end
            last_word_end = match.end()
            current_text = unit.text[current_start:last_word_end]
        if word_spans:
            fragments.append(ChunkItem(unit_id=unit.unit_id, text=unit.text[current_start:], char_start=current_start, char_end=len(unit.text)))
        return fragments

    @staticmethod
    def _make_chunk(index: int, items: list[ChunkItem], tokens: int) -> ContextChunk:
        return ContextChunk(
            chunk_id=uuid4(),
            chunk_index=index,
            items=list(items),
            input_tokens=tokens,
            source_unit_ids=list(dict.fromkeys(item.unit_id for item in items)),
        )
