import pytest

from app.adapters.supabase_client import create_supabase_service_client
from app.config.settings import Settings


def test_supabase_service_client_requires_server_credentials() -> None:
    with pytest.raises(ValueError, match="SUPABASE_URL"):
        create_supabase_service_client(Settings())
