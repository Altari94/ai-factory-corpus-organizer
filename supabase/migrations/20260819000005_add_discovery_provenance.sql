-- F0.4.15a semantic judge and discovery provenance.
-- Existing derived rows remain valid; new fields are additive.

alter table public.topics add column if not exists description text;
alter table public.episode_relations add column if not exists evidence_unit_ids uuid[] not null default '{}';
alter table public.episode_entities add column if not exists evidence_unit_ids uuid[] not null default '{}';

comment on column public.episode_relations.evidence_unit_ids is 'Canonical Unit IDs supporting the relation decision';
comment on column public.episode_entities.evidence_unit_ids is 'Canonical Unit IDs supporting the entity mention';

alter table public.topics enable row level security;
alter table public.episode_relations enable row level security;
alter table public.episode_entities enable row level security;
