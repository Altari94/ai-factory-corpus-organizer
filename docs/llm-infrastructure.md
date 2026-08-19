# LLM Processing Infrastructure F0.4.5

F0.4.5 definiert die technische Grenze für spätere semantische Entscheidungen.
Es wird noch kein echter Provider aufgerufen.

## Datenfluss

```text
ModelProfile
    ↓
ContextSelector (task-spezifisch)
    ↓
ChunkBuilder (konfiguriertes Tokenbudget)
    ↓
PromptBuilder (Prompt-ID + Version)
    ↓
LLMPort
    ↓
StructuredOutputValidator
    ↓
StructuredDecision + LLMExecutionTrace
```

## Grenzen

- Model Profiles enthalten alle Modell- und Tokenbudgets. Der Domain-Code setzt
  keine Providergrenzen voraus.
- Context Selection ist pro Aufgabe konfigurierbar. Die Canonical Unit IDs
  werden in Context, Chunks, Prompts, Decisions und Traces weitergeführt.
- Der Chunk Builder kennt nur Text, Zeichenbereiche und IDs. Er entscheidet nicht
  über Themen, Episoden oder Relationen. Lange Units werden an Whitespace-
  Grenzen fragmentiert und vollständig rekonstruierbar gehalten.
- Prompt-Versionen werden mit jedem `StructuredDecision` und jedem Trace
  gespeichert.
- `LLMPort` kennt nur `LLMRequest` und `LLMResponse`. Ein Provideradapter kann
  später ergänzt oder ausgetauscht werden.
- Ungültiges JSON, falsche Schemas oder unbekannte Canonical IDs erzeugen einen
  retryfähigen Validierungsfehler.

Der `InMemoryLLMAdapter` ist ausschließlich für Tests und deterministische
Entwicklung gedacht. Er führt keinen Netzwerkaufruf aus.
