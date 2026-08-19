from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.adapters.in_memory_semantic import InMemorySemanticAdapter
from app.adapters.supabase_semantic import SupabaseSemanticAdapter
from app.domain.semantic import Episode, OrganizerRun, OrganizerRunStatus


class FakeResponse:
    def __init__(self, data: list[dict]):
        self.data = data


class FakeTable:
    def __init__(self, database: dict[str, list[dict]], name: str):
        self.database = database
        self.name = name
        self.operation = "select"
        self.payload = None
        self.filters: list[tuple[str, object]] = []
        self.limit_value: int | None = None

    def insert(self, payload):
        self.operation = "insert"
        self.payload = payload
        return self

    def update(self, payload):
        self.operation = "update"
        self.payload = payload
        return self

    def select(self, _columns):
        self.operation = "select"
        return self

    def eq(self, key, value):
        self.filters.append((key, value))
        return self

    def limit(self, value):
        self.limit_value = value
        return self

    def execute(self):
        rows = self.database.setdefault(self.name, [])
        if self.operation == "insert":
            values = self.payload if isinstance(self.payload, list) else [self.payload]
            rows.extend(values)
            return FakeResponse(values)
        if self.operation == "update":
            for row in rows:
                if all(str(row.get(key)) == str(value) for key, value in self.filters):
                    row.update(self.payload)
            return FakeResponse([])
        result = [
            row for row in rows if all(str(row.get(key)) == str(value) for key, value in self.filters)
        ]
        if self.limit_value is not None:
            result = result[: self.limit_value]
        return FakeResponse(result)


class FakeClient:
    def __init__(self):
        self.database: dict[str, list[dict]] = {}

    def table(self, name: str) -> FakeTable:
        return FakeTable(self.database, name)


def make_fixture() -> tuple[OrganizerRun, Episode]:
    run = OrganizerRun(
        organizer_run_id=uuid4(),
        corpus_id=UUID("e4bc5ac3-86d5-4b29-bf53-d100df30a1ab"),
        code_version="contract-test",
        algorithm_version="1.0.0",
        semantic_schema_version="1.0.0",
        started_at=datetime.now(timezone.utc),
    )
    episode = Episode(
        organizer_run_id=run.organizer_run_id,
        episode_id=uuid4(),
        document_id=uuid4(),
        start_unit_id=uuid4(),
        end_unit_id=uuid4(),
        sequence=0,
    )
    return run, episode


def exercise_contract(adapter) -> None:
    run, episode = make_fixture()
    adapter.create_run(run)
    adapter.write_episodes([episode])
    adapter.complete_run(run.organizer_run_id, datetime.now(timezone.utc))

    stored_run = adapter.get_run(run.organizer_run_id)
    assert stored_run is not None
    assert stored_run.status == OrganizerRunStatus.SUCCEEDED
    assert adapter.get_episodes(run.organizer_run_id) == [episode]


def test_in_memory_and_supabase_adapters_share_the_same_contract() -> None:
    exercise_contract(InMemorySemanticAdapter())
    exercise_contract(SupabaseSemanticAdapter(FakeClient()))
