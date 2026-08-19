-- F0.4.7a.10 persistence for episode memberships, decisions and provider traces.

create table if not exists public.episode_memberships (
    membership_id uuid primary key default gen_random_uuid(),
    organizer_run_id uuid not null references public.organizer_runs(organizer_run_id),
    episode_id uuid not null references public.episodes(episode_id),
    canonical_unit_id uuid not null references public.content_units(unit_id),
    sequence integer not null check (sequence >= 0),
    unique (organizer_run_id, episode_id, canonical_unit_id)
);

create table if not exists public.structured_decisions (
    decision_id uuid primary key,
    organizer_run_id uuid not null references public.organizer_runs(organizer_run_id),
    trace_id uuid not null,
    task text not null,
    prompt_id text not null,
    prompt_version text not null,
    model_profile_id text not null,
    canonical_unit_ids uuid[] not null,
    decision jsonb not null,
    created_at timestamptz not null default now()
);

create table if not exists public.llm_execution_traces (
    trace_id uuid primary key,
    organizer_run_id uuid not null references public.organizer_runs(organizer_run_id),
    task text not null,
    model_profile_id text not null,
    model_name text not null,
    prompt_id text not null,
    prompt_version text not null,
    request_id uuid not null,
    attempt integer not null check (attempt >= 1),
    canonical_unit_ids uuid[] not null,
    started_at timestamptz not null,
    finished_at timestamptz,
    status text not null check (status in ('STARTED', 'SUCCEEDED', 'RETRYABLE_FAILURE', 'FAILED')),
    input_tokens integer check (input_tokens >= 0),
    output_tokens integer check (output_tokens >= 0),
    latency_ms integer check (latency_ms >= 0),
    retry_count integer not null default 0 check (retry_count >= 0),
    estimated_cost_usd double precision check (estimated_cost_usd >= 0),
    raw_output text,
    structured_decision_id uuid,
    error text
);

create index if not exists episode_memberships_run_idx
    on public.episode_memberships (organizer_run_id, episode_id, sequence);
create index if not exists episode_memberships_unit_idx
    on public.episode_memberships (canonical_unit_id);
create index if not exists structured_decisions_run_idx
    on public.structured_decisions (organizer_run_id);
create index if not exists llm_execution_traces_run_idx
    on public.llm_execution_traces (organizer_run_id, started_at);

alter table public.episode_memberships enable row level security;
alter table public.structured_decisions enable row level security;
alter table public.llm_execution_traces enable row level security;
