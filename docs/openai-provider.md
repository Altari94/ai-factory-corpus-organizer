# OpenAI Provider Integration

Die produktive Provider-Schicht ist über zwei Adapter angebunden:

- `OpenAILLMAdapter` verwendet die OpenAI Responses API.
- `OpenAIEmbeddingAdapter` verwendet die OpenAI Embeddings API.

Beide Adapter liegen außerhalb von Domain und Ports. Ein Modellwechsel erfolgt
über `ModelProfile` beziehungsweise die Umgebungsvariablen, nicht durch eine
Änderung am Boundary Judge oder am Canonical Contract.

## Konfiguration

Die Werte gehören ausschließlich in die lokale `.env`:

```env
OPENAI_API_KEY=...
OPENAI_LLM_MODEL=gpt-5.2
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_TIMEOUT_SECONDS=60
OPENAI_MAX_RETRIES=2
OPENAI_RETRY_BASE_SECONDS=1
```

`OPENAI_API_KEY` wird beim Erzeugen des Clients zwingend geprüft. Die Datei
`.env` ist Git-ignoriert und darf niemals committed werden.

Die Laufzeitverdrahtung erfolgt über `build_openai_adapters(get_settings())`.
Sie erzeugt einen gemeinsamen OpenAI-Client sowie getrennte LLM- und
Embedding-Adapter. Der Boundary Judge erhält weiterhin nur den `LLMPort`; der
Vector Store bleibt unabhängig davon.

## Structured Output

Der LLM-Adapter fordert ein versionierungsunabhängiges JSON-Schema an. Für den
Boundary Judge sind ausschließlich `SAME_EPISODE`, `NEW_EPISODE` und
`UNCERTAIN` zulässig. Die bestehende `StructuredOutputValidator` prüft danach
zusätzlich Pydantic-Schema, Pflichtfelder und Canonical Unit IDs.

Ein Providerfehler wird nie als semantische Entscheidung interpretiert. Für
transiente Fehler nutzt der Adapter begrenzte Exponential-Retries. Nach dem
letzten Versuch wird ein `LLMProviderError` ausgelöst und der Boundary Judge
führt keine Episode-Entscheidung aus.

Der LLM-Trace enthält neben Tokenzahlen und Provider-Request-ID auch Latenz
und tatsächliche Retry-Anzahl. Eine `estimated_cost_usd`-Angabe bleibt
optional und muss über ein explizites Modellpreis-Profil konfiguriert werden;
der Domain-Code schätzt keine Preise anhand von Modellnamen.

## Nutzung und Kosten

Die Adapter sind implementiert und über Mock-Tests geprüft. Es wurde bewusst
noch kein echter Chat an die API gesendet. Ein Live-Test sollte zunächst mit
synthetischem oder anonymisiertem Text erfolgen.

Die Modelle und ihre aktuellen Eigenschaften sollten vor dem produktiven
Betrieb anhand der offiziellen OpenAI-Dokumentation geprüft werden. Für
Embedding-Vergleiche muss dasselbe Embedding-Profil verwendet werden; ältere
Profilversionen bleiben separat speicherbar.

## Anonymisierung

Vor der produktiven Provider-Nutzung wird ein eigener Anonymisierungsadapter
vor den LLM- und Embedding-Ports ergänzt. Er soll Namen, Kontaktdaten und
andere personenbezogene Angaben durch stabile Platzhalter ersetzen. Der
Canonical Originaltext bleibt dabei unverändert; geteilt wird nur die
bereinigte Provider-Repräsentation.

## F0.4.7a.10 Productive Persistence E2E

Der synthetische E2E-Lauf wurde mit den produktiven Adaptern durchgeführt:

```text
synthetische Canonical Units
  -> OpenAI Embeddings API
  -> Supabase embeddings / pgvector
  -> OpenAI Responses API mit gpt-5.6-luna
  -> strukturierte Boundary Decisions
  -> Episode Builder
  -> Supabase Episodes, Memberships, Decisions und Traces
```

Dabei wurden neun synthetische Units, neun Embeddings, drei Episoden und neun
Memberships persistiert. Beide Boundary-Entscheidungen waren `NEW_EPISODE`.
Die Supabase-RPC-Similarity-Suche lieferte Ergebnisse, und der Run wurde als
`SUCCEEDED` gespeichert. Ein zweiter synthetischer Lauf schrieb einen neuen
Organizer Run; die Ergebnisse des ersten Runs blieben unverändert erhalten.

Die Testdaten sind als `synthetic` und mit dem Gate `F0.4.7a.10` markiert.
