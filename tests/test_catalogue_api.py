from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

from app.adapters.in_memory_semantic import InMemorySemanticAdapter
from app.api.catalogue import get_catalogue_builder
from app.domain.semantic import Episode, OrganizerRun, Topic
from app.main import app
from app.services.catalogue_builder import CatalogueBuilder


def test_catalogue_api_is_available_in_swagger_and_returns_statistics() -> None:
    store = InMemorySemanticAdapter()
    run = OrganizerRun(organizer_run_id=uuid4(), corpus_id=uuid4(), code_version="test", algorithm_version="test", semantic_schema_version="1.0", started_at=datetime.now(timezone.utc))
    store.create_run(run)
    store.write_episodes([Episode(organizer_run_id=run.organizer_run_id, episode_id=uuid4(), document_id=uuid4(), start_unit_id=uuid4(), end_unit_id=uuid4(), sequence=0)])
    store.write_topics([Topic(organizer_run_id=run.organizer_run_id, topic_id=uuid4(), label="Topic")])
    app.dependency_overrides[get_catalogue_builder] = lambda: CatalogueBuilder(store)
    try:
        client = TestClient(app)
        response = client.get(f"/catalogue/{run.organizer_run_id}/statistics")
        assert response.status_code == 200
        assert response.json()["episode_count"] == 1
        assert client.get("/openapi.json").status_code == 200
    finally:
        app.dependency_overrides.clear()
