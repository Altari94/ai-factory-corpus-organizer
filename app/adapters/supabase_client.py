from supabase import Client, create_client

from app.config.settings import Settings


def create_supabase_service_client(settings: Settings) -> Client:
    """Create the server-side Supabase client without exposing credentials."""

    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required")
    return create_client(settings.supabase_url, settings.supabase_service_role_key)
