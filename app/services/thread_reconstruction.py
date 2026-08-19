from collections import defaultdict
from collections.abc import Sequence
from uuid import UUID, uuid5

from app.domain.discovery import LogicalThread, ThreadComponent
from app.domain.semantic import EpisodeRelation


class ThreadReconstructor:
    def reconstruct(self, relations: Sequence[EpisodeRelation], episode_sequences: dict[UUID, tuple[UUID, int]]) -> list[LogicalThread]:
        adjacency: dict[UUID, set[UUID]] = defaultdict(set)
        for relation in relations:
            if relation.relation_type == "SAME_THREAD":
                adjacency[relation.from_episode_id].add(relation.to_episode_id)
                adjacency[relation.to_episode_id].add(relation.from_episode_id)
        visited: set[UUID] = set()
        threads: list[LogicalThread] = []
        for episode_id in sorted(adjacency, key=str):
            if episode_id in visited:
                continue
            stack = [episode_id]
            component: list[UUID] = []
            while stack:
                current = stack.pop()
                if current in visited:
                    continue
                visited.add(current)
                component.append(current)
                stack.extend(adjacency[current] - visited)
            ordered = sorted(component, key=lambda item: episode_sequences.get(item, (UUID(int=0), 0))[1])
            thread_id = uuid5(UUID(int=0), f"thread:{','.join(str(item) for item in ordered)}")
            threads.append(LogicalThread(thread_id=thread_id, components=[ThreadComponent(episode_id=item, sequence=index) for index, item in enumerate(ordered)]))
        return threads
