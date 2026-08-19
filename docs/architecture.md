# Architektur F0.4.0

Der Corpus Organizer ist ein eigenständiger Service. Seine fachliche
Anwendungslogik hängt nur vom `CanonicalReadPort` ab.

```text
F0.3 Canonical Source
        ↓
CanonicalReadPort
        ↓
CorpusReader / Domain-Core
        ↓
spätere Episode- und Semantic-Services
```

Der konkrete Speicheradapter wird erst außerhalb des Domain-Cores ergänzt.
F0.4.0 enthält bewusst nur einen InMemory-Adapter. Dadurch können Contract-Tests
ausgeführt werden, ohne Supabase zu benötigen.

Der Organizer kennt weder das ursprüngliche Dateiformat noch die Tabellen des
F0.3-Speichers. Markdown und JSON müssen vor dem Read Port bereits denselben
Canonical Contract liefern.

## Semantic Contract v1

`OrganizerRun` ist der Versions- und Provenienzrahmen für alle abgeleiteten
Objekte. Dazu gehören `Episode`, `Entity`, `Topic`, `EpisodeRelation` und
`Thread` sowie die Verknüpfungsobjekte `EpisodeEntity`, `EpisodeTopic`,
`TopicRelation` und `ThreadEpisode`.

Eine `Episode` verändert keinen Canonical-Text. Sie referenziert ein Dokument
und seine Start-/End-Units. Die Sequenznummer erhält die Chronologie. Topics,
Entities und Threads sind bewusst getrennte Konzepte: Episoden können mit
mehreren Topics und Entities verbunden werden; Topics können über
`parent_topic_id` hierarchisch verknüpft werden; Threads können Episoden aus
verschiedenen Dokumenten und damit Quellen verbinden.
