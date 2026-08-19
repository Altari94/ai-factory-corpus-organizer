# Golden Evaluation Corpus

`golden_corpus.v1.json` ist das versionierte Format für manuelle Ground Truth
vor dem ersten LLM-Einsatz. Es enthält acht aus dem lokalen Exportbestand
ausgewählte echte ChatGPT-Exporte.

Die Fälle decken unterschiedliche Grenzfälle ab: externe Recherche und
Fakten/Meinung, lange versionierte Konzeptarbeit, technische Unsicherheit,
Querverweise zwischen Anforderungen, Wissensarchitektur sowie multimodale und
personenbezogene Eingaben.

Der Status ist bewusst `DRAFT_GROUND_TRUTH`: Die acht Fälle erfüllen den
geforderten Umfang, die Annotationen sind versioniert und manuell als erste
Ground-Truth-Fassung markiert. Eine zweite Review-Runde bleibt als normale
Qualitätssicherung vor einem späteren LLM-Gate sinnvoll.

Die JSON-Datei enthält SHA-256-Referenzen statt Kopien der Originale. Dadurch
bleiben Rohdaten und Golden-Metadaten getrennt, und die Auswahl ist trotzdem
prüfbar.

## F0.4.17 Evaluation und Regression

`app/services/evaluation.py` misst Boundaries, Relations und Topic-Qualität
getrennt. Für `SAME_THREAD` gilt bewusst Precision vor Recall: Ein falscher
Merge blockiert die Regression, auch wenn dadurch weniger echte Fortsetzungen
gefunden werden.

Der aktuelle Golden Corpus ist noch `DRAFT_GROUND_TRUTH`. Vor einem echten
Model-/Prompt-Vergleich müssen für jeden ausgewählten Fall konkrete Unit-IDs
für Boundaries, Episode-Zuordnungen und Relationsentscheidungen manuell
ergänzt werden. Der Code erfindet diese Annotationen ausdrücklich nicht.
