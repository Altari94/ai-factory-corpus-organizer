# F0.4.8–F0.4.15 Discovery Layers

Die Discovery-Schicht baut ausschließlich auf Derived Data auf. Sie verändert
keine Canonical Units und ersetzt keine Originalprovenienz.

## Entity Discovery

`EntityMention` trennt die erkannte Entity von ihrem Evidence-Kontext. Eine
Entity kann in vielen Episoden und Topics vorkommen. Der aktuelle
`HeuristicEntityExtractor` ist ein deterministischer Baseline-Adapter; ein
LLM-Extractor kann später denselben Port verwenden. Kategorien sind nicht
vorgegeben.

## Retrieval und Relations

`InMemoryEpisodeRetriever` liefert konfigurierbares Top-K-Retrieval mit Score,
Embedding-Profil und Modellversion. Retrieval allein erzeugt keine Relation.
Erst ein Relation Judge darf `SAME_THREAD`, `RELATED`, `UNRELATED` oder
`UNCERTAIN` entscheiden. `RelationContextSelector` hält den Kontext lokal und
die Relation-Persistence nutzt ein eigenes Derived Object.

## Graph

`SemanticGraphProjector` erzeugt einen reinen `CorpusGraph` aus Episoden,
Entities, Topics und Relations. Der Graph kennt weder PostgreSQL noch eine
Graphdatenbank. Eine spätere Neo4j-Projektion kann denselben Contract nutzen.

## Topics und Threads

`SimilarityClusterer` bildet zunächst unüberwachte Connected Components.
Singletons bleiben gültig. Cluster-ID und Label sind getrennt; Naming erfolgt
erst nach dem Clustering. `RepresentativeContextSelector` begrenzt große
Cluster-Kontexte. `RecursiveClusterer` hält Parent/Child-Information und
konfigurierbare Stop-Tiefe. `ThreadReconstructor` sortiert verbundene Episoden
chronologisch und hält Threads getrennt von Topics.

Alle Ergebnisse werden als Derived Data über den Organizer Run versioniert.

## Productive Semantic Judges

`ProductiveSemanticJudges` verbindet Relation Judging, Topic Naming und
Cluster-Coherence mit dem providerneutralen `LLMPort`. Die OpenAI-Variante
verwendet strikt validierte Structured Outputs; ungültige Antworten werden
begrenzt erneut versucht und nicht als Entscheidung übernommen. Jede gültige
Entscheidung erhält Prompt-, Modell-, Request-, Token- und Laufzeitprovenienz.

`DiscoveryPersistenceService` schreibt anschließend den vollständigen
run-scoped Derived-Datensatz über `SemanticWritePort`. Die Reihenfolge folgt
den Foreign Keys: Run, Episoden, Entities/Topics, Links, Relationen, Threads.
Damit bleiben alte Runs erhalten und InMemory- sowie Supabase-Adapter nutzen
denselben Schreibvertrag.
