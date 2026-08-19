# AI Factory Corpus Organizer

Der Corpus Organizer ist der eigenständige F0.4-Service der AI Factory. Er
bereitet den Canonical Corpus für spätere semantische Verarbeitung auf.

## Aktueller Umfang: F0.4.0–F0.4.5

F0.4.0 enthält ausschließlich das Service-Grundgerüst und die Anbindung an den
stabilen Canonical Read Port aus F0.3:

- lokaler FastAPI-Startpunkt (`GET /health`)
- eigener Python-Service mit virtueller Umgebung
- `CanonicalReadPort` als einzige fachliche Leseschnittstelle
- InMemory-Canonical-Adapter für Tests und lokale Entwicklung
- Domain-Core ohne Supabase- und OpenAI-Abhängigkeit
- versionierter Semantic Contract v1 für Organizer Runs und Derived Objects
- `SemanticReadPort` und `SemanticWritePort`
- InMemory- und Supabase-Adapter
- reproduzierbare Supabase-Migration mit Foreign Keys und RLS
- Walking Skeleton für mehrere Canonical Sources
- Trivial Episode Detector ohne KI
- versioniertes Golden-Corpus-Format
- Model Profiles, Context Selection und Chunk Builder
- versionierte Prompt Builder
- provider-neutraler `LLMPort` mit InMemory-Testadapter
- strukturierte Output-Validierung und Execution Traces

Noch nicht enthalten sind intelligente Episodenerkennung, Embeddings, LLMs oder
semantische Entscheidungen. Die aktuelle Episodenerkennung ist bewusst nur der
Trivial Episode Detector: eine Canonical MESSAGE wird zu einer Episode.

Die Modelle in `app/domain/semantic.py` definieren nur die Sprache der späteren
semantischen Ergebnisse. Jedes Derived Object trägt eine
`organizer_run_id`. Dadurch bleiben alte Runs erhalten und Ergebnisse aus
unterschiedlichen Code-, Algorithmus- oder Schema-Versionen vergleichbar.

## Starten

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Danach ist der Health-Endpoint unter <http://127.0.0.1:8000/health> erreichbar.

## Tests

```bash
pytest
```

## Architektur

```text
app/
├── domain/    # fachliche Canonical-Contract-Modelle
├── ports/     # abstrakte Ein-/Ausgangsschnittstellen
├── services/  # Organizer-Anwendungslogik
├── adapters/  # InMemory-Adapter; externe Adapter später hier
├── api/       # HTTP-Schnittstellen
└── config/    # Laufzeitkonfiguration
```

Der Organizer kennt weder die Supabase-Tabellen (`content_units` usw.) noch das
ursprüngliche Dateiformat. Ein späterer Adapter liest F0.3 und übersetzt dessen
Contract in den `CanonicalReadPort`.
