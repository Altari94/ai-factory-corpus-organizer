from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.adapters.semantic_factory import build_supabase_semantic_adapters
from app.config.settings import get_settings
from app.domain.catalogue import CatalogueTopic, CorpusCatalogue, CorpusStatistics
from app.services.catalogue_builder import CatalogueBuilder, CatalogueNotFoundError


router = APIRouter(prefix="/catalogue", tags=["catalogue"])


def get_catalogue_builder() -> CatalogueBuilder:
    return CatalogueBuilder(build_supabase_semantic_adapters(get_settings()).semantic)


def _catalogue_or_404(run_id: UUID, builder: CatalogueBuilder) -> CorpusCatalogue:
    try:
        return builder.build(run_id)
    except CatalogueNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/{organizer_run_id}", response_model=CorpusCatalogue)
def get_catalogue(
    organizer_run_id: UUID,
    builder: Annotated[CatalogueBuilder, Depends(get_catalogue_builder)],
) -> CorpusCatalogue:
    return _catalogue_or_404(organizer_run_id, builder)


@router.get("/{organizer_run_id}/topics", response_model=list[CatalogueTopic])
def get_catalogue_topics(
    organizer_run_id: UUID,
    builder: Annotated[CatalogueBuilder, Depends(get_catalogue_builder)],
) -> list[CatalogueTopic]:
    return _catalogue_or_404(organizer_run_id, builder).topics


@router.get("/{organizer_run_id}/statistics", response_model=CorpusStatistics)
def get_corpus_statistics(
    organizer_run_id: UUID,
    builder: Annotated[CatalogueBuilder, Depends(get_catalogue_builder)],
) -> CorpusStatistics:
    return _catalogue_or_404(organizer_run_id, builder).statistics
