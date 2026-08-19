from dataclasses import dataclass

from app.adapters.supabase_client import create_supabase_service_client
from app.adapters.supabase_llm_trace import SupabaseLLMTraceAdapter
from app.adapters.supabase_semantic import SupabaseSemanticAdapter
from app.config.settings import Settings


@dataclass(frozen=True)
class SupabaseSemanticAdapters:
    semantic: SupabaseSemanticAdapter
    traces: SupabaseLLMTraceAdapter


def build_supabase_semantic_adapters(settings: Settings) -> SupabaseSemanticAdapters:
    client = create_supabase_service_client(settings)
    return SupabaseSemanticAdapters(
        semantic=SupabaseSemanticAdapter(client),
        traces=SupabaseLLMTraceAdapter(client),
    )
