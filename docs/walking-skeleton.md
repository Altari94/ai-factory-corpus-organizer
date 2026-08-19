# Walking Skeleton F0.4.3

`CorpusLoader` lädt mehrere Source-IDs über den F0.3-`CanonicalReadPort`.
Er verwendet ausschließlich den neuesten erfolgreichen Run mit kompatibler
Schema-Major-Version. Fehlgeschlagene oder inkompatible Quellen werden nicht
verarbeitet.

`TrivialEpisodeDetector` erzeugt zunächst genau eine Episode pro Canonical
`MESSAGE`. Start- und End-Unit sind dieselbe Canonical Unit. Das ist keine
semantische Entscheidung, sondern ein technischer Durchstich zur Prüfung des
vollständigen Datenflusses.

```text
CanonicalReadPort
    ↓
CorpusLoader (mehrere Quellen)
    ↓
TrivialEpisodeDetector
    ↓
Episode mit OrganizerRun- und Canonical-Provenienz
    ↓
SemanticWritePort
```
