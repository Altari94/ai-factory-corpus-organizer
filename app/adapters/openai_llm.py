import time
from time import perf_counter
from collections.abc import Callable

from openai import APIConnectionError, APITimeoutError, InternalServerError, OpenAI, RateLimitError

from app.ports.llm import LLMProviderError
from app.domain.llm import ContextTask, LLMRequest, LLMResponse


class OpenAILLMAdapter:
    """OpenAI Responses API adapter; the domain only sees the LLMPort contract."""

    def __init__(
        self,
        client: OpenAI,
        *,
        max_retries: int = 2,
        retry_base_seconds: float = 1.0,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.client = client
        self.max_retries = max(0, max_retries)
        self.retry_base_seconds = max(0.0, retry_base_seconds)
        self.sleep = sleep

    def generate(self, request: LLMRequest) -> LLMResponse:
        schema = _schema_for(request.prompt.task)
        last_error: Exception | None = None
        started = perf_counter()
        for attempt in range(self.max_retries + 1):
            try:
                response = self.client.responses.create(
                    model=request.profile.model_name,
                    input=[
                        {"role": "system", "content": request.prompt.system},
                        {"role": "user", "content": request.prompt.user},
                    ],
                    text={
                        "format": {
                            "type": "json_schema",
                            "name": f"{request.prompt.task.value.lower()}_decision",
                            "strict": True,
                            "schema": schema,
                        }
                    },
                )
                raw_output = getattr(response, "output_text", "") or ""
                if not raw_output:
                    raise LLMProviderError("OpenAI returned no structured output")
                usage = getattr(response, "usage", None)
                return LLMResponse(
                    request_id=request.request_id,
                    model_profile_id=request.profile.profile_id,
                    model_name=request.profile.model_name,
                    raw_output=raw_output,
                    input_tokens=getattr(usage, "input_tokens", None),
                    output_tokens=getattr(usage, "output_tokens", None),
                    provider_request_id=getattr(response, "id", None),
                    latency_ms=round((perf_counter() - started) * 1000),
                    retry_count=attempt,
                )
            except LLMProviderError as error:
                last_error = error
            except (APIConnectionError, APITimeoutError, InternalServerError, RateLimitError) as error:
                last_error = error
            if attempt < self.max_retries:
                self.sleep(self.retry_base_seconds * (2**attempt))

        message = f"OpenAI provider failed after {self.max_retries + 1} attempt(s)"
        if last_error:
            message = f"{message}: {type(last_error).__name__}"
        raise LLMProviderError(message) from last_error


def _schema_for(task: ContextTask) -> dict[str, object]:
    if task == ContextTask.BOUNDARY_JUDGE:
        return {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "decision_type": {"type": "string", "enum": ["BOUNDARY"]},
                "left_unit_id": {"type": "string", "format": "uuid"},
                "right_unit_id": {"type": "string", "format": "uuid"},
                "boundary": {
                    "type": "string",
                    "enum": ["SAME_EPISODE", "NEW_EPISODE", "UNCERTAIN"],
                },
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            },
            "required": [
                "decision_type",
                "left_unit_id",
                "right_unit_id",
                "boundary",
                "confidence",
            ],
        }
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "decision_type": {"type": "string", "enum": ["RELATION"]},
            "from_unit_id": {"type": "string", "format": "uuid"},
            "to_unit_id": {"type": "string", "format": "uuid"},
            "relation_type": {"type": "string", "minLength": 1},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        },
        "required": [
            "decision_type",
            "from_unit_id",
            "to_unit_id",
            "relation_type",
            "confidence",
        ],
    }
