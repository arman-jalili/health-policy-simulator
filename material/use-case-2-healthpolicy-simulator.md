# Use Case 2: HealthPolicy Simulator

## Zielbild des Use Cases

Ziel ist die Entwicklung eines transparenten KI-Agenten-Simulationssystems für das österreichische Gesundheits- und Sozialsystem, in dem autonome institutionelle KI-Agenten relevante Stakeholder repräsentieren, komplexe Fragestellungen eigenständig diskutieren, verhandeln und bewerten sowie nachvollziehbare Kompromisse und Handlungsempfehlungen erzeugen. Der Mensch erhält nicht nur ein Ergebnis, sondern einen vollständigen Einblick in die Argumentationswege, Konflikte, Verhandlungen und Konsensbildungsprozesse der beteiligten KI-Agenten.

Damit wird die KI vom reinen Analysewerkzeug zu einem strategischen Multi-Agenten-Simulator für politische, organisatorische und finanzielle Entscheidungen im Gesundheitswesen.

## Kernidee: Multi-Agenten-System für verhandlungsbasierte Entscheidungsunterstützung

Im Zentrum dieses Use Cases steht die Entwicklung eines KI-gestützten Multi-Agenten-Systems, das die wesentlichen Akteure des österreichischen Gesundheits- und Sozialsystems durch spezialisierte Agenten repräsentiert. Jeder Agent übernimmt die Rolle einer Institution oder Interessensgruppe und vertritt deren Ziele, Argumentationsmuster, Handlungsspielräume und strategische Interessen.

Das System soll nicht nur Informationen analysieren, sondern eigenständig Diskussionen, Debatten und Verhandlungen zwischen den beteiligten Akteuren durchführen.

Dadurch entsteht ein virtueller Verhandlungsraum, in dem gesundheitspolitische Fragestellungen aus unterschiedlichen Perspektiven betrachtet und mögliche Lösungswege entwickelt werden können.

## Institutionelle KI-Agenten

Jeder Agent repräsentiert einen relevanten Stakeholder des österreichischen Gesundheitswesens und entwickelt eigenständig Positionen auf Basis von Daten, historischen Entscheidungen, öffentlichen Stellungnahmen und institutionellen Zielen.

**Mögliche Agenten:**

1. Sozialversicherung
2. Gesundheitsministerium
3. Bundesländer
4. Ärztekammer
5. Vertragsärzt:innen
6. Wahlärzt:innen
7. Krankenanstalten
8. Pflegevertretungen
9. Patient:innenvertretungen
10. Gesetzgeber
11. Finanzministerium
12. Public-Health-Expert:innen
13. Wirtschaftskammer, Arbeiterkammer und Landwirtschaftskammer
14. Industrie (z. B. Pharma)

**Jeder Agent verfügt über:**

- eigene Zielsetzungen,
- definierte Interessen,
- Restriktionen,
- Budgetvorgaben,
- Entscheidungsprioritäten,
- historische Positionen,
- institutionelles Wissen.

Die Agenten sollen nicht einfach vorgefertigte Antworten liefern, sondern situationsabhängig argumentieren, auf Gegenargumente reagieren und ihre Position gegebenenfalls anpassen.

Die Einstellung der Agenten kann etwa aus dem Pressearchiv oder aus Meldungen der Presseagentur eruiert werden.

## Autonome Diskussionen und Verhandlungen

Ein wesentliches Merkmal des Systems ist die Fähigkeit der Agenten, eigenständig miteinander zu interagieren.

Je nach Fragestellung können die Agenten:

- diskutieren,
- debattieren,
- verhandeln,
- Gegenpositionen entwickeln,
- Koalitionen bilden,
- Kompromisse suchen,
- Alternativen ausarbeiten,
- Auswirkungen ihrer Vorschläge bewerten.

**Beispielfragestellung:**

> „Wie können die Gesundheitsausgaben bis 2035 um 10 % gesenkt werden, ohne die Versorgungsqualität wesentlich zu verschlechtern?"

**Möglicher Ablauf:**

1. Jeder Agent entwickelt zunächst seine Ausgangsposition.
2. Die Agenten präsentieren ihre Interessen und Argumente.
3. Andere Agenten reagieren darauf.
4. Konfliktpunkte werden identifiziert.
5. Kompromissvorschläge werden ausgearbeitet.
6. Die Vorschläge werden hinsichtlich Kosten, Akzeptanz und Umsetzbarkeit bewertet.
7. Die Agenten nähern sich schrittweise einer gemeinsamen Lösung an.

## Moderations-Agent

Optional kann ein eigener KI-Agent die Rolle eines neutralen Moderators übernehmen.

Dieser Moderator-Agent:

- übersetzt die Benutzerfrage in einen Verhandlungsauftrag,
- bestimmt die relevanten Akteure,
- definiert die Verhandlungsregeln,
- steuert die Diskussion,
- fordert Begründungen ein,
- erkennt Widersprüche,
- fasst Zwischenergebnisse zusammen,
- dokumentiert Konsenspunkte und Konflikte,
- beendet die Verhandlung bei Erreichen eines definierten Ergebnisses.

Der Moderator vertritt keine eigene Position, sondern sorgt für einen transparenten, strukturierten und nachvollziehbaren Verhandlungsprozess.

## Transparenz und Nachvollziehbarkeit als zentrales Designprinzip

Ein wesentliches Ziel dieses Use Cases ist, dass die Ergebnisse der Agenten nicht als „Black Box" erscheinen.

Der End-User muss jederzeit nachvollziehen können:

### Wer hat welche Position vertreten?

Für jeden Agenten soll sichtbar gemacht werden:

- ursprüngliche Position
- zentrale Argumente
- verwendete Datenquellen
- strategische Ziele
- Prioritäten

### Welche Diskussionen haben stattgefunden?

Das System soll einen transparenten Verhandlungsverlauf bereitstellen:

- Argumente und Gegenargumente
- Zustimmung und Ablehnung
- Konfliktpunkte
- Meinungsänderungen
- Kompromissvorschläge

Dies kann beispielsweise in Form eines Verhandlungsprotokolls oder einer Chat-Ansicht erfolgen.

### Welche Zwischenresultate wurden erzielt?

Während der Verhandlung sollen Zwischenergebnisse dokumentiert werden:

- Themen mit hoher Zustimmung
- offene Konfliktfelder
- alternative Lösungswege
- gescheiterte Vorschläge
- neu entstandene Optionen

### Worauf haben sich die Agenten geeinigt?

Am Ende erzeugt das System automatisch:

- Konsenspunkte
- Mehrheitspositionen
- Minderheitspositionen
- verbleibende Konflikte
- Handlungsempfehlungen

## Verhandlungsergebnis statt Einzelantwort

Der eigentliche Output des Systems soll nicht nur eine KI-generierte Antwort sein.

Der Output besteht aus:

| # | Bestandteil | Leitfrage |
|---|---|---|
| 1 | Zusammenfassung der Ausgangsfrage | Welche Fragestellung wurde untersucht? |
| 2 | Beteiligte Agenten | Welche Institutionen waren involviert? |
| 3 | Verhandlungsverlauf | Welche Argumente wurden ausgetauscht? |
| 4 | Konfliktanalyse | Wo lagen die größten Interessensunterschiede? |
| 5 | Kompromissvorschläge | Welche Lösungsansätze wurden entwickelt? |
| 6 | Konsensanalyse | Worauf konnten sich die Agenten einigen? |
| 7 | Offene Streitpunkte | Welche Differenzen bleiben bestehen? |
| 8 | Auswirkungen | Welche Folgen sind unter den jeweiligen Szenarien zu erwarten? |

## Spieltheoretischer Verhandlungsmodus

Zur Erhöhung der Realitätsnähe können die institutionellen Agenten spieltheoretische Strategien anwenden.

Die Agenten analysieren dabei:

- strategische Vorteile,
- Verhandlungsmacht,
- Koalitionsmöglichkeiten,
- gegenseitige Abhängigkeiten,
- Anreizsysteme,
- Risiken von Kooperation oder Blockade.

Dadurch entsteht nicht nur eine Meinungsaggregation, sondern eine realistische Simulation politischer und institutioneller Entscheidungsprozesse im Gesundheitswesen.

## Realistische Datengrundlage wählen

Die diskutierenden Agenten können auch auf Basis von Zahlen und Fakten argumentieren. Diese Argumente wiegen schwerer, müssen aber stichhaltig nachgewiesen werden. Die Zahlen dürfen sich auch nicht widersprechen und müssen mittels Tests bzw. Feedbackschleifen verifiziert werden. Dies kann etwa über einen eigenen Agenten „Experte" geschehen.

## Vorgaben

1. Institutionen dürfen nicht durch einzelne Personen aus der realen Welt vertreten werden. Es dürfen keine Meldungen von echten Personen zitiert oder dargestellt werden.
2. Transparent machen, wie die Standpunkte der KI-Agenten der einzelnen Player zustande kommen. Standpunkte kommen von Medienberichten und Pressestatements der Player — das soll nachvollziehbar gemacht werden.
3. Agenten sollen lernen, wie die Teil-Ergebnisse von Verhandlungen ausgehen, und diese in den nächsten Verhandlungsrunden beachten.
4. Aktuelle Ereignisse und Informationen sollen stärker berücksichtigt und gewichtet werden als historische Informationen.

## Konkretes Anwendungsszenario: Reduktion der Wartezeiten auf Facharzttermine

### Ausgangslage

In mehreren Regionen Österreichs steigen die Wartezeiten für Facharzttermine kontinuierlich an. Gleichzeitig stehen die Sozialversicherungsträger unter Kostendruck, während Ärzt:innen über zunehmende Arbeitsbelastung und Personalmangel berichten.

Folgende Fragestellung wird aufgeworfen:

> „Wie können die Wartezeiten auf Facharzttermine innerhalb von fünf Jahren um 20 % reduziert werden, ohne die Gesundheitsausgaben um mehr als 5 % zu erhöhen?"

### Beteiligte KI-Agenten

Für die Bearbeitung der Fragestellung werden mehrere institutionelle Agenten aktiviert:

- Gesundheitsministerium
- Sozialversicherung
- Ärztekammer
- Vertragsärzt:innen
- Krankenanstalten
- Pflegevertretung
- Bundesländer
- Patientenvertretung
- Finanzministerium

Jeder Agent verfügt über eigene Ziele und Bewertungskriterien.

### Beispielhafte Interessen

| Agent | Interessen |
|---|---|
| Sozialversicherung | Kostensteigerungen begrenzen; effiziente Leistungserbringung fördern |
| Ärztekammer | Attraktivität des Arztberufs erhalten; Qualität der Versorgung sicherstellen |
| Patientenvertretung | Schnellere Termine; hohe Behandlungsqualität |
| Bundesländer | Regionale Versorgung sicherstellen; politische Umsetzbarkeit gewährleisten |
| Finanzministerium | Budgetstabilität einhalten; zusätzliche Ausgaben begrenzen |

### Phase 1: Positionsbildung

Jeder Agent analysiert die Fragestellung zunächst eigenständig.

Beispielsweise könnte:

- die Ärztekammer mehr Kassenstellen fordern,
- die Sozialversicherung auf Telemedizin und digitale Triage setzen,
- die Patientenvertretung längere Öffnungszeiten verlangen,
- das Finanzministerium Investitionen nur bei nachweisbarer Wirkung unterstützen.

Diese Positionen werden inklusive der zugrunde liegenden Argumente und Quellen dokumentiert.

### Phase 2: Diskussion und Debatte

Die Agenten diskutieren ihre Vorschläge miteinander.

**Beispielhafter Dialog**

> **Ärztekammer-Agent:** Die Hauptursache der Wartezeiten ist der Mangel an Fachärztinnen und Fachärzten. Ohne zusätzliche Kassenstellen wird keine nachhaltige Verbesserung erreicht.
>
> **Sozialversicherungs-Agent:** Neue Stellen verursachen hohe laufende Kosten. Zunächst sollte geprüft werden, welche Leistungen telemedizinisch erbracht werden können.
>
> **Patientenvertretungs-Agent:** Eine reine Digitalisierung reicht nicht aus. Besonders ältere Menschen benötigen weiterhin persönliche Betreuung.
>
> **Bundesländer-Agent:** In ländlichen Regionen sind mobile Versorgungseinheiten möglicherweise effizienter als zusätzliche Standorte.

### Phase 3: Verhandlung

Anschließend beginnt eine strukturierte Verhandlung.

Der Moderator-Agent erkennt:

**Konsenspunkte**

- Wartezeiten müssen reduziert werden.
- Regionale Unterschiede sind zu berücksichtigen.
- Digitale Angebote können einen Beitrag leisten.

**Konfliktpunkte**

- Anzahl zusätzlicher Kassenstellen
- Höhe der notwendigen Investitionen
- Verhältnis zwischen Telemedizin und persönlicher Versorgung

Der Moderator fordert die Agenten auf, Kompromissvorschläge zu entwickeln.

### Phase 4: Kompromissfindung

Nach mehreren Verhandlungsrunden entsteht folgendes Maßnahmenpaket:

**Vereinbarte Maßnahmen**

1. Ausbau der Telemedizin für ausgewählte Leistungen
2. Schaffung zusätzlicher Kassenstellen in Mangelregionen
3. Einführung einer digitalen Facharzt-Triage
4. Erweiterte Kompetenzen für bestimmte Gesundheitsberufe
5. Monitoring der Wartezeiten durch ein nationales Dashboard

**Nicht umgesetzte Vorschläge**

- Flächendeckende Honorarkürzungen
- Verpflichtende Telemedizin für alle Patient:innen

Diese Vorschläge fanden keine ausreichende Unterstützung der Agenten.

### Phase 5: Transparente Ergebnisdarstellung

Der End-User erhält nun den gesamten Entscheidungsprozess inklusive des notwendigen Hintergrundwissens.

**Dashboard-Bestandteile**

- **Beteiligte Akteure**
  - Welche Agenten waren beteiligt?
  - Welche Ziele verfolgen die jeweiligen Agenten, welche Positionen haben sie eingenommen?
- **Verhandlungsverlauf**
  - Welche Argumente wurden vorgebracht?
  - Welche Gegenargumente gab es?
  - Welche Positionen haben sich verändert?
- **Konsensanalyse**

  Pro Thema sollen die Zustimmungen, Argumente und Positionen pro Akteur aufgezeigt werden bzw. wie sich diese im Laufe der Verhandlungssituation verändern.

- **Offene Konflikte**
  - Finanzierung neuer Stellen
  - Verteilung der Ressourcen zwischen Stadt und Land

### Erwartete Wirkung

Simulationsergebnisse:

- Wartezeitreduktion: 22 %
- Budgetsteigerung: 4,3 %
- Höhere Versorgungssicherheit in ländlichen Regionen
- Mittlere Umsetzbarkeit innerhalb von 3 bis 5 Jahren

### Nutzen des Szenarios

Dieses Beispiel zeigt den zentralen Mehrwert des Multi-Agenten-Ansatzes: Die KI liefert nicht nur eine einzelne Antwort, sondern simuliert einen realitätsnahen gesundheitspolitischen Entscheidungsprozess. Nutzer:innen sehen transparent,

- welche Institution welche Interessen vertreten hat,
- welche Argumente ausgetauscht wurden,
- wo Konflikte entstanden sind,
- welche Kompromisse gefunden wurden,
- und warum die finale Empfehlung zustande gekommen ist.

Dadurch entsteht ein digitaler Verhandlungs- und Konsensraum für komplexe Fragestellungen des österreichischen Gesundheitswesens. Dieser Ansatz kann auf Themen wie Honorarverhandlungen, Spitalsplanung, Pflegereformen, Primärversorgungseinheiten, Impfstrategien oder die Finanzierung neuer Gesundheitsleistungen übertragen werden.

## Datenquellen

- Pressearchiv des Dachverbandes
- Gesetzliche Grundlagen: SOZDOK

## Bewertungskriterien für die Fachjury

Der HealthPolicy Simulator soll unterschiedliche institutionelle Perspektiven auf gesundheitspolitische Fragestellungen realistisch abbilden. Die KI-Agenten sollen die jeweiligen Interessen, Ziele und Rahmenbedingungen der vertretenen Institutionen nachvollziehbar berücksichtigen und ihre Positionen auf geeignete Informationsquellen stützen.

Im Mittelpunkt steht eine dynamische Diskussion, in der die Agenten aufeinander reagieren, Gegenargumente aufgreifen und bestehende Zielkonflikte herausarbeiten. Ziel ist es, unterschiedliche Lösungsansätze zu prüfen, deren Vor- und Nachteile abzuwägen und nachvollziehbare Kompromissvorschläge zu entwickeln. Dabei sollen auch alternative Szenarien, mögliche Auswirkungen und verbleibende Konflikte berücksichtigt werden.

Ein wesentliches Element ist die Transparenz des gesamten Entscheidungsprozesses. Die verwendeten Quellen, zentralen Argumente, Annahmen und Änderungen von Positionen sollen nachvollziehbar dargestellt werden. Ergebnisse sollen verständlich aufbereitet sein und konkrete Entscheidungsgrundlagen liefern, ohne Unsicherheiten zu verschleiern oder einen Konsens künstlich zu erzwingen.

Die Verhandlung, die darin ausgetauschten Argumente sowie die bewerteten Interessen und Ziele zu den Fragestellungen sollen visuell verständlich dargestellt werden. Die Veränderung der Positionen im Rahmen der Verhandlung soll ebenfalls visualisiert werden.

Die Lösung soll anhand eines funktionsfähigen Prototyps demonstriert werden. Neben der fachlichen Qualität zählen auch die eigenständige technische Umsetzung, das Zusammenspiel der KI-Agenten und die Nutzung geeigneter Daten- und Wissensquellen. Überlegt auch, wie eure Lösung über den Prototyp hinaus weiterentwickelt und für einen praktischen Einsatz nutzbar gemacht werden könnte.

## Bewertungskriterien für die Finaljury

_(Noch offen.)_
