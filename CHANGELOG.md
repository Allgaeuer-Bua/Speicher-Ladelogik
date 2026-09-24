# Änderungsverlauf

## 1.2.0

- Die Änderungen der Vorabversion 1.1.1 einschließlich der getrennten Kalibrierergebnisse,
  optionaler paralleler Kalibrierung und stabiler 15-Minuten-Fahrplanslots sind enthalten.
- Anhaltende gemessene Netzeinspeisung kann bei unsicherer Tagesplanung eine
  morgendliche Ladung vorziehen. Ohne konfiguriertes vorzeitiges Ladeziel endet
  diese Absicherung bei 80 % je Speicher; ein starker Tag behält die
  Mittagsspitzenplanung, solange die kurzfristige Prognose trägt.
- Die redundante Mindestreserve entfällt. Das vorzeitige Ladeziel steht nun
  je Speicher direkt bei den Fahrplanfunktionen. Die Betriebsart steht am
  Ende der Steuerungsseite, Kalibrieraktionen direkt unter dem jeweiligen Speicher.
- In der Einrichtung werden die Modelle für alle drei Speicher einheitlich
  als Venus A, Venus D und Venus E angezeigt.
- In der Speicheransicht werden pro Gerät Wirkungsgrad mit Ladeleistung sowie
  Pack-Zelldrift im Verlauf angezeigt (heute, 7 und 30 Tage, soweit der
  Home-Assistant-Verlauf Daten enthält).

## 1.1.1-beta.3

- Die Kalibrierkarte zeigt je Speicher die AC-Energie des letzten erfolgreichen
  Laufs, ob der Messwert für die künftige Fensterplanung übernommen wurde, und
  die nach der oberen Ruhephase gespeicherte Zelldrift je verfügbarem Pack.
- Fehlende historische Driftwerte werden als fehlend gekennzeichnet. Die Drift
  am Ladebeginn und bei 100 % wird nicht als Top-Balancing-Erfolg interpretiert,
  weil sie bei unterschiedlichem SoC gemessen wurde.
- Zwei Kalibrierungen können optional parallel laufen, wenn der zweite Speicher
  bereits leer vorbereitet ist und beide Leistungen gemeinsam vom gemessenen
  PV-Überschuss gedeckt werden. Jeder Lauf behält seinen eigenen Zustand,
  Abschluss, Messwert und seine eigene Grenzwert-Rücksicherung.
- Neue Läufe speichern zusätzlich die Zelldrift bei 100 % vor und nach der
  oberen Ruhephase. Die Veränderung wird als Messwert angezeigt und nicht als
  Beweis für aktives Balancing gewertet.

## 1.1.1-beta.2

- Verlaufsdiagramme werden als durchgehende Linien dargestellt; der doppelte
  Leistungsgraph auf der Übersicht entfällt.
- Die Speicheransicht zeigt die tatsächliche Lade- und Entladegrenze getrennt.
- Die Steuerungsseite beginnt mit Kalibrierung und Handbetrieb.
- Bevorzugte, maximale automatische Lade- und maximale automatische
  Entladeleistung sind je Speicher getrennt einstellbar.
- Reicht die bevorzugte Ladeleistung nicht, wird die kleinste passende
  50-W-Zwischenstufe geplant, statt unmittelbar auf das Gerätemaximum zu gehen.
- Die Mindestreserve ist je Speicher einstellbar und kann einzelne Geräte beim
  frühen Sichern priorisieren.
- Das Mittagsfenster orientiert sich am lokalen Sonnenhöchststand. Vor- und
  Nachlauf sind getrennt einstellbar; Standard sind zwei Stunden vorher und
  vier Stunden nachher.

## 1.1.1-beta.1

- Vorabversion zum Praxistest; kein Merge in den stabilen `main`-Branch.
- Ein heute ausreichendes Kalibrierfenster wird unabhängig davon erkannt, ob
  der Speicher bereits 13 % erreicht hat, und während der Vorbereitung neu
  bewertet.
- Die benötigte Ladedauer wird sekundengenau statt auf den nächsten
  15-Minuten-Schritt aufgerundet geprüft.
- Testablauf nach Marstek-Empfehlung: bis 13 % entladen, 90 Minuten untere
  Ruhephase, mit der eingestellten Kalibrierleistung laden und anschließend
  90 Minuten obere Ruhephase. In beiden Ruhephasen sind Laden und Entladen
  gesperrt.

## 1.1.0

- Bis zu drei unabhängige Speicherinstanzen; Modelle A, D und E dürfen mehrfach
  vorkommen.
- Automatische Migration bestehender V1.0-Konfigurationen.
- Venus A: 1–6 Module zu je 2,08 kWh, maximal 12,48 kWh.
- Venus D: 1–6 Module zu je 2,56 kWh, maximal 15,36 kWh.
- Gelernte Kalibrierenergie wird nach dem ersten erfolgreichen Lauf verwendet.
- AC-Referenzenergie inklusive realer Verluste: Venus A 3,77 kWh bei zwei
  Modulen, Venus E 5,15 kWh.
- Der pauschale Aufschlag von 0,25 kWh entfällt.
- Laufende Kalibrierungen verlängern ihr Fenster bei ausreichendem gemessenem
  PV-Überschuss, statt allein wegen des Prognoseendes abzubrechen.
