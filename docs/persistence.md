# Semantic Persistence

## Ports

Die Organizer-Domain spricht nur mit `SemanticReadPort` und
`SemanticWritePort`. Diese Ports verwenden ausschließlich die Pydantic-Domain-
Modelle. Supabase-Clienttypen kommen nur im Adapter `app/adapters/` vor.

## Adapter

- `InMemorySemanticAdapter`: lokale Entwicklung und Contract Tests
- `SupabaseSemanticAdapter`: Persistenz in den F0.4-Derived-Tabellen

Beide Adapter speichern `OrganizerRun` und alle Derived Objects run-scoped.
Historische Runs werden nicht überschrieben oder gelöscht.

## Migration

Die Migration legt `organizer_runs`, `episodes`, `entities`, `topics`,
`episode_relations`, `threads` und die Linktabellen an. Foreign Keys schützen
Run-, Episode-, Topic- und Canonical-Referenzen. RLS ist auf allen Tabellen
aktiviert; es gibt bewusst keine öffentlichen Policies, weil der aktuelle
Adapter serverseitig mit dem privilegierten Schlüssel arbeitet.

Die Security Advisors melden deshalb erwartungsgemäß `rls_enabled_no_policy` als
Info-Hinweis. Das ist kein offener anonymer Zugriff: Es existiert gerade keine
Policy für `anon` oder `authenticated`. Die Foreign-Key-Indizes sind in der
Basis- und Folge-Migration enthalten.
