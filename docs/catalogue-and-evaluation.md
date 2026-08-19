# F0.4.16–F0.4.18 Catalogue, Evaluation und E2E-Gate

## Catalogue

Der Catalogue ist eine dynamische Read-Projektion auf genau einen
`organizer_run_id`. Er wird nicht als zusätzliche Tabelle gespeichert und ist
dadurch keine konkurrierende Source of Truth. Pro Topic liefert er Label,
Beschreibung, Parent, Episoden-, Dokument-, Entity- und Thread-Bezüge sowie
die Zahl angrenzender Relationen.

Swagger stellt bereit:

- `GET /catalogue/{organizer_run_id}`
- `GET /catalogue/{organizer_run_id}/topics`
- `GET /catalogue/{organizer_run_id}/statistics`

## Evaluation und Regression

Boundary-, Relation- und Topic-Metriken sind getrennt. Das Regression Gate
vergleicht versionierte Snapshots. Für `SAME_THREAD` ist ein Precision-Rückgang
standardmäßig nicht zulässig; falsche Thread-Merges sind kritischer als
getrennt gebliebene Fortsetzungen.

## E2E-Abnahme echter Quellen

`scripts/validate_real_corpus_e2e.py` verarbeitet keine Rohdateien. Es prüft
einen bereits erzeugten Organizer Run gegen explizit übergebene Source IDs:
Run-Status, mehrere Quellen, Episode- und Evidence-Provenienz, Topics und
chronologisch eindeutige Thread-Memberships. Die Auswahl echter Chats bleibt
eine bewusste Operatorentscheidung.
