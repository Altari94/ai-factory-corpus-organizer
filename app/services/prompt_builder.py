from app.domain.llm import BuiltPrompt, ContextChunk, PromptDefinition


class PromptBuilder:
    """Renders versioned task instructions independently of any LLM adapter."""

    def build(self, definition: PromptDefinition, chunk: ContextChunk) -> BuiltPrompt:
        context = "\n".join(
            f"[{item.unit_id}] {item.text}" for item in chunk.items
        )
        return BuiltPrompt(
            prompt_id=definition.prompt_id,
            prompt_version=definition.version,
            task=definition.task,
            system=definition.system_template,
            user=definition.user_template.replace("{context}", context),
            source_unit_ids=chunk.source_unit_ids,
        )
