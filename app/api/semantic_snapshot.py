from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.adapters.semantic_factory import build_supabase_semantic_adapters
from app.config.settings import get_settings
from app.domain.semantic_snapshot import SemanticSnapshot
from app.services.semantic_snapshot import SemanticSnapshotBuilder, SemanticSnapshotNotFoundError


router = APIRouter(prefix="/semantic-runs", tags=["semantic contract"])


def get_snapshot_builder() -> SemanticSnapshotBuilder:
    return SemanticSnapshotBuilder(build_supabase_semantic_adapters(get_settings()).semantic)


@router.get("/{organizer_run_id}/snapshot", response_model=SemanticSnapshot)
def get_snapshot(
    organizer_run_id: UUID,
    builder: Annotated[SemanticSnapshotBuilder, Depends(get_snapshot_builder)],
) -> SemanticSnapshot:
    try:
        return builder.build(organizer_run_id)
    except SemanticSnapshotNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

