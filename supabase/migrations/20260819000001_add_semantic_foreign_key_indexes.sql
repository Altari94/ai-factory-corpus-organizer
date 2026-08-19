-- Follow-up indexes for all F0.4 semantic foreign-key columns.
-- Kept separate so existing installations can apply it without recreation.

create index if not exists episodes_document_idx on public.episodes (document_id);
create index if not exists episodes_start_unit_idx on public.episodes (start_unit_id);
create index if not exists episodes_end_unit_idx on public.episodes (end_unit_id);
create index if not exists entities_run_idx on public.entities (organizer_run_id);
create index if not exists topics_run_idx on public.topics (organizer_run_id);
create index if not exists topics_parent_idx on public.topics (parent_topic_id);
create index if not exists episode_relations_run_idx on public.episode_relations (organizer_run_id);
create index if not exists episode_relations_from_idx on public.episode_relations (from_episode_id);
create index if not exists episode_relations_to_idx on public.episode_relations (to_episode_id);
create index if not exists episode_entities_entity_idx on public.episode_entities (entity_id);
create index if not exists episode_entities_episode_idx on public.episode_entities (episode_id);
create index if not exists episode_topics_topic_idx on public.episode_topics (topic_id);
create index if not exists episode_topics_episode_idx on public.episode_topics (episode_id);
create index if not exists topic_relations_parent_idx on public.topic_relations (parent_topic_id);
create index if not exists topic_relations_child_idx on public.topic_relations (child_topic_id);
create index if not exists thread_episodes_episode_idx on public.thread_episodes (episode_id);
create index if not exists thread_episodes_thread_idx on public.thread_episodes (thread_id);
