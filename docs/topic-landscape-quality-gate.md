# F0.4 Topic Landscape Quality Gate

Die versionierte Ground-Truth-Datei `evaluation/golden_corpus.v1.json` enthält
die manuellen Prüffälle für die erste Landschaftsprüfung. Sie deckt unter
anderem Palworld Server Mod, persönliches Palworld, AI Factory, Second Brain,
Bachelorarbeit und Schweden/Reise ab.

Die Prüfung bewertet Navigation statt einer perfekten Ontologie:

- offensichtlich getrennte Domänen dürfen nicht regelmäßig verschmelzen;
- verwandte Palworld-Episoden müssen auffindbar bleiben;
- Untertopics dürfen fehlen, Singleton und `Unassigned` sind erlaubt;
- eine Episode darf mehreren Topics zugeordnet sein;
- Topic-Labels und Run-Versionen müssen reproduzierbar bleiben.

Die Datei bleibt bewusst als `DRAFT_GROUND_TRUTH` markiert, bis die manuelle
fachliche Annotation abgeschlossen ist. Automatische Metriken ersetzen diese
Product-Owner-Prüfung nicht.
