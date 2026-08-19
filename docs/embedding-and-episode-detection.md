# F0.4.6–F0.4.7: Embeddings und Episodenerkennung

## Embedding Infrastructure

`EmbeddingPort` erzeugt Embeddings aus Canonical Units. `VectorStorePort`
speichert und durchsucht sie. Der Domain-Core kennt dabei nur IDs, Profile,
Modellversionen und Zahlenvektoren; weder Supabase noch pgvector sind Teil des
Domain-Modells.

Die InMemory-Implementierungen dienen als deterministische Testadapter. Der
Supabase-Adapter schreibt in `embeddings` und nutzt die RPC-Funktion
`match_canonical_embeddings` für Cosine-Similarity Search. Die Kombination aus
`embedding_profile_id` und `model_version` erlaubt mehrere alte und neue
Embedding-Stände parallel. Embeddings sind ausschließlich ein Suchsignal; sie
klassifizieren keine Inhalte.

Die Migration aktiviert pgvector im Schema `extensions`, legt Foreign Keys auf
Organizer Run und Canonical Unit an und aktiviert RLS. Es gibt absichtlich noch
keine fachlichen Client-Policies: der Zugriff ist für den serverseitigen
Adapter vorgesehen. Die Vector-Spalte ist in v1 dimensionsflexibel, damit
verschiedene Profile gespeichert werden können. Für ein stabiles Profil kann
später ein dimensionsgebundener HNSW-Index ergänzt werden.
Die RPC-Funktion setzt außerdem einen festen PostgreSQL-`search_path`, damit
ihre Namensauflösung nicht von der jeweiligen Sitzung abhängt.

## Episode Detection

Der Ablauf ist:

```text
Canonical MESSAGE Units
        ↓
BoundaryCandidateDetector
        ↓
BoundaryContextBuilder
        ↓
LLM Boundary Judge (Port, optional)
        ↓
EpisodeBuilder
```

Der Candidate Detector betrachtet benachbarte Units desselben Dokuments und
berechnet nachvollziehbare Signale: Sprecherwechsel, lexikalische Verschiebung
und Sequenzlücke. Nur Candidates oberhalb des konfigurierten Thresholds werden
weitergegeben. Unauffällige Stellen benötigen dadurch keinen LLM-Aufruf.

Der Context Builder behält die beiden Candidate-IDs und baut ein begrenztes
Modellfenster. Beide Candidate-Units müssen gemeinsam in einem Chunk liegen;
andernfalls wird die Boundary-Entscheidung sicher abgelehnt statt mit
unvollständigem Kontext ausgeführt.

Der Boundary Judge validiert ausschließlich strukturierten Output:

```json
{
  "decision_type": "BOUNDARY",
  "left_unit_id": "...",
  "right_unit_id": "...",
  "boundary": "SAME_EPISODE | NEW_EPISODE | UNCERTAIN",
  "confidence": 0.0
}
```

Promptversion, Modellprofil, Canonical IDs, Versuch und Ergebnis werden im
Execution Trace festgehalten. Der Episode Builder verarbeitet bestätigte
`NEW_EPISODE`-Grenzen, bewahrt Reihenfolge und Provenienz und erzeugt für jede
MESSAGE Unit genau eine Episode Membership. `SAME_EPISODE` und `UNCERTAIN`
erzeugen keine neue Grenze.
