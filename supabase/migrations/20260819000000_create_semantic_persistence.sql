-- F0.4.2 Semantic Persistence
-- Run after the F0.3 canonical-source migrations in the same Supabase project.
-- These tables are server-side derived data; no public Data API policies are
-- created. RLS remains enabled as defense in depth.

create table if not exists public.organizer_runs (
    organizer_run_id uuid primary key default gen_random_uuid(),
    corpus_id uuid not null,
    code_version text not null,
    algorithm_version text not null,
    semantic_schema_version text not null,
    started_at timestamptz not null default now(),
    finished_at timestamptz,
    status text not null check (status in ('RUNNING', 'SUCCEEDED', 'FAILED')),
    configuration jsonb not null default '{}'::jsonb,
    error text
);

create table if not exists public.episodes (
    episode_id uuid primary key default gen_random_uuid(),
    organizer_run_id uuid not null references public.organizer_runs(organizer_run_id),
    document_id uuid not null references public.canonical_documents(document_id),
    start_unit_id uuid not null references public.content_units(unit_id),
    end_unit_id uuid not null references public.content_units(unit_id),
    sequence integer not null check (sequence >= 0),
    confidence double precision check (confidence between 0 and 1),
    status text not null check (status in ('PROPOSED', 'CONFIRMED', 'REJECTED'))
);

create table if not exists public.entities (
    entity_id uuid primary key default gen_random_uuid(),
    organizer_run_id uuid not null references public.organizer_runs(organizer_run_id),
    canonical_name text not null,
    entity_type text
);

create table if not exists public.topics (
    topic_id uuid primary key default gen_random_uuid(),
    organizer_run_id uuid not null references public.organizer_runs(organizer_run_id),
    label text not null,
    parent_topic_id uuid
);

alter table public.topics
    drop constraint if exists topics_parent_topic_id_fkey;
alter table public.topics
    add constraint topics_parent_topic_id_fkey
    foreign key (parent_topic_id) references public.topics(topic_id);

create table if not exists public.episode_relations (
    relation_id uuid primary key default gen_random_uuid(),
    organizer_run_id uuid not null references public.organizer_runs(organizer_run_id),
    from_episode_id uuid not null references public.episodes(episode_id),
    to_episode_id uuid not null references public.episodes(episode_id),
    relation_type text not null,
    confidence double precision check (confidence between 0 and 1)
);

create table if not exists public.threads (
    thread_id uuid primary key default gen_random_uuid(),
    organizer_run_id uuid not null references public.organizer_runs(organizer_run_id),
    label text not null,
    description text
);

create table if not exists public.episode_entities (
    link_id uuid primary key default gen_random_uuid(),
    organizer_run_id uuid not null references public.organizer_runs(organizer_run_id),
    episode_id uuid not null references public.episodes(episode_id),
    entity_id uuid not null references public.entities(entity_id),
    unique (organizer_run_id, episode_id, entity_id)
);

create table if not exists public.episode_topics (
    link_id uuid primary key default gen_random_uuid(),
    organizer_run_id uuid not null references public.organizer_runs(organizer_run_id),
    episode_id uuid not null references public.episodes(episode_id),
    topic_id uuid not null references public.topics(topic_id),
    unique (organizer_run_id, episode_id, topic_id)
);

create table if not exists public.topic_relations (
    relation_id uuid primary key default gen_random_uuid(),
    organizer_run_id uuid not null references public.organizer_runs(organizer_run_id),
    parent_topic_id uuid not null references public.topics(topic_id),
    child_topic_id uuid not null references public.topics(topic_id),
    relation_type text not null default 'PARENT_OF',
    unique (organizer_run_id, parent_topic_id, child_topic_id)
);

create table if not exists public.thread_episodes (
    link_id uuid primary key default gen_random_uuid(),
    organizer_run_id uuid not null references public.organizer_runs(organizer_run_id),
    thread_id uuid not null references public.threads(thread_id),
    episode_id uuid not null references public.episodes(episode_id),
    sequence integer not null check (sequence >= 0),
    unique (organizer_run_id, thread_id, episode_id)
);

create index if not exists episodes_run_sequence_idx
    on public.episodes (organizer_run_id, sequence);
create index if not exists episodes_document_idx
    on public.episodes (document_id);
create index if not exists episodes_start_unit_idx
    on public.episodes (start_unit_id);
create index if not exists episodes_end_unit_idx
    on public.episodes (end_unit_id);
create index if not exists entities_run_idx
    on public.entities (organizer_run_id);
create index if not exists topics_run_idx
    on public.topics (organizer_run_id);
create index if not exists topics_parent_idx
    on public.topics (parent_topic_id);
create index if not exists episode_relations_run_idx
    on public.episode_relations (organizer_run_id);
create index if not exists episode_relations_from_idx
    on public.episode_relations (from_episode_id);
create index if not exists episode_relations_to_idx
    on public.episode_relations (to_episode_id);
create index if not exists episode_entities_run_idx
    on public.episode_entities (organizer_run_id, episode_id);
create index if not exists episode_entities_entity_idx
    on public.episode_entities (entity_id);
create index if not exists episode_topics_run_idx
    on public.episode_topics (organizer_run_id, episode_id);
create index if not exists episode_topics_topic_idx
    on public.episode_topics (topic_id);
create index if not exists topic_relations_parent_idx
    on public.topic_relations (parent_topic_id);
create index if not exists topic_relations_child_idx
    on public.topic_relations (child_topic_id);
create index if not exists thread_episodes_run_sequence_idx
    on public.thread_episodes (organizer_run_id, thread_id, sequence);
create index if not exists thread_episodes_episode_idx
    on public.thread_episodes (episode_id);

alter table public.organizer_runs enable row level security;
alter table public.episodes enable row level security;
alter table public.entities enable row level security;
alter table public.topics enable row level security;
alter table public.episode_relations enable row level security;
alter table public.threads enable row level security;
alter table public.episode_entities enable row level security;
alter table public.episode_topics enable row level security;
alter table public.topic_relations enable row level security;
alter table public.thread_episodes enable row level security;

comment on table public.organizer_runs is 'F0.4 derived processing runs; server-side access only';
comment on table public.episodes is 'F0.4 derived episodes; canonical text remains in F0.3';
