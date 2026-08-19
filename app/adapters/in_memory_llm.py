from collections.abc import Callable

from app.domain.llm import LLMRequest, LLMResponse


class InMemoryLLMAdapter:
    """Deterministic test adapter; never performs a network request."""

    def __init__(self, responder: Callable[[LLMRequest], str] | None = None) -> None:
        self.responder = responder or (lambda _request: "{}")
        self.requests: list[LLMRequest] = []

    def generate(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        output = self.responder(request)
        return LLMResponse(
            request_id=request.request_id,
            model_profile_id=request.profile.profile_id,
            model_name=request.profile.model_name,
            raw_output=output,
        )
