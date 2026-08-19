-- F0.4.6 Embedding persistence. pgvector is an adapter concern.
create extension if not exists vector with schema extensions;

create table if not exists public.embeddings (
    embedding_id uuid primary key default gen_random_uuid(),
    organizer_run_id uuid not null references public.organizer_runs(organizer_run_id),
    canonical_unit_id uuid not null references public.content_units(unit_id),
    embedding_profile_id text not null,
    model_version text not null,
    dimensions integer not null check (dimensions > 0),
    embedding extensions.vector not null,
    created_at timestamptz not null default now(),
    metadata jsonb not null default '{}'::jsonb
);

create index if not exists embeddings_run_idx on public.embeddings (organizer_run_id);
create index if not exists embeddings_unit_idx on public.embeddings (canonical_unit_id);
create index if not exists embeddings_profile_version_idx
    on public.embeddings (embedding_profile_id, model_version);

alter table public.embeddings enable row level security;

create or replace function public.match_canonical_embeddings (
    query_embedding extensions.vector,
    query_profile_id text,
    match_threshold float,
    match_count int
)
returns table (
    embedding_id uuid,
    canonical_unit_id uuid,
    profile_id text,
    model_version text,
    similarity float
)
language sql stable
as $$
    select
        e.embedding_id,
        e.canonical_unit_id,
        e.embedding_profile_id as profile_id,
        e.model_version,
        1 - (e.embedding <=> query_embedding) as similarity
    from public.embeddings e
    where e.embedding_profile_id = query_profile_id
      and 1 - (e.embedding <=> query_embedding) >= match_threshold
    order by e.embedding <=> query_embedding asc
    limit least(match_count, 200);
$$;

revoke execute on function public.match_canonical_embeddings(extensions.vector, text, float, int)
    from anon, authenticated;

