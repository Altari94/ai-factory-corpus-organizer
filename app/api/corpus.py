from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.adapters.supabase_canonical import SupabaseCanonicalReadAdapter
from app.adapters.semantic_factory import build_supabase_semantic_adapters
from app.config.settings import get_settings
from app.domain.corpus_read import CorpusCatalogue, CorpusSlice, EpisodeView, TopicDetail, TopicNode
from app.domain.integrity import IntegrityReport
from app.services.integrity import OrganizerIntegrityService
from app.services.corpus_read import CorpusReadService


router = APIRouter(prefix="/semantic-runs", tags=["corpus read contract"])


def get_reader() -> CorpusReadService:
    settings = get_settings()
    adapters = build_supabase_semantic_adapters(settings)
    return CorpusReadService(adapters.semantic, SupabaseCanonicalReadAdapter(adapters.semantic.client))


@router.get("/{run_id}/corpus/topics", response_model=list[TopicNode])
def list_topics(run_id: UUID, reader: Annotated[CorpusReadService, Depends(get_reader)]):
    return reader.list_topics(run_id)


@router.get("/{run_id}/corpus/topics/{topic_id}", response_model=TopicDetail)
def get_topic(run_id: UUID, topic_id: UUID, reader: Annotated[CorpusReadService, Depends(get_reader)]):
    result = reader.get_topic(run_id, topic_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Topic not found")
    return result


@router.get("/{run_id}/corpus/topics/{topic_id}/children", response_model=list[TopicNode])
def get_topic_children(run_id: UUID, topic_id: UUID, reader: Annotated[CorpusReadService, Depends(get_reader)]):
    return reader.get_topic_children(run_id, topic_id)


@router.get("/{run_id}/corpus/topics/{topic_id}/episodes", response_model=list[EpisodeView])
def get_topic_episodes(run_id: UUID, topic_id: UUID, reader: Annotated[CorpusReadService, Depends(get_reader)]):
    return reader.get_topic_episodes(run_id, topic_id)


@router.get("/{run_id}/corpus/topics/{topic_id}/slice", response_model=CorpusSlice)
def get_corpus_slice(run_id: UUID, topic_id: UUID, include_descendants: bool = True, reader: Annotated[CorpusReadService, Depends(get_reader)] = None):
    return reader.get_corpus_slice(run_id, topic_id, include_descendants)


@router.get("/{run_id}/corpus/catalogue", response_model=CorpusCatalogue)
def get_corpus_catalogue(run_id: UUID, reader: Annotated[CorpusReadService, Depends(get_reader)]):
    return reader.get_catalogue(run_id)


@router.get("/{run_id}/integrity", response_model=IntegrityReport)
def get_integrity(run_id: UUID, reader: Annotated[CorpusReadService, Depends(get_reader)]):
    return OrganizerIntegrityService(reader.semantic_reader, reader.canonical_reader).validate(run_id)
