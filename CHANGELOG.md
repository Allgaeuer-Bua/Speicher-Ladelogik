# Änderungsverlauf

## 1.2.4

- Eine schwache Messung am frühen Morgen reduziert die restliche Tagesprognose
  nicht mehr schlagartig. Die Korrektur gewinnt erst mit mehr Messdaten Gewicht
  und klingt für spätere Prognoseintervalle ab. Rohprognose, Korrekturfaktor und
  dessen Messgrundlage sind in den Planungsattributen sichtbar.
- Wechsel der Tagesklasse benötigen einen Abstand zum Grenzwert und 15 Minuten
  Bestätigung. Vorzeitige SoC-Ziele gelten bis zum Beginn des Mittagsfensters.
- Ein vorzeitiges SoC-Ziel verwendet zuerst die bevorzugte Ladeleistung des
  jeweiligen Speichers. Nur wenn diese für das Ziel vor dem Mittagsfenster nicht
  reicht, steigt die Grenze bis zur eingestellten Maximalleistung.
- Nach einem Sicherheitsstopp wegen ungültiger Daten darf ein wieder gültiger
  Plan noch im laufenden 15-Minuten-Slot neu entscheiden. Der Sicherheitsstopp
  selbst setzt die Ladegrenze weiterhin sofort auf null.

## 1.2.3

- Niedrigere positive Ladegrenzen werden spätestens im folgenden 15-Minuten-Slot
  übernommen. Ein zuvor erhöhter Wert bleibt nicht mehr unbegrenzt hängen.
- Die Planung prüft zuerst einen früheren Beginn mit bevorzugter Leistung.
  Falls höhere Leistung benötigt wird, werden unnötige Erhöhungen anderer
  Speicher wieder entfernt. Die konservative Lade-Endphase bleibt berücksichtigt.
  Unter Diagnose ist die Entstehung jeder automatischen Ladegrenze mit Zeitpunkt,
  Restbedarf, Fenster und simulierter Fehlmenge nachvollziehbar.
- Vorzeitige SoC-Ziele je Tagesklasse erreichen nun tatsächlich den Planer;
  ausdrücklich eingestellte 0 % bleiben erhalten. Tagesgrenzen, Planungswirkungsgrad,
  Wolkenreserve und Mindestplanleistung verwenden die angebotenen Einstellbereiche.
  Ungeordnete Tagesgrenzen werden beim Ändern mit einer Erklärung abgelehnt.
- Ausgeschaltete Mittagsspitzenkappung begrenzt die Planung nicht mehr auf das
  Mittagsfenster. Tagesklassen und das verfügbare PV-Fenster bleiben berücksichtigt.
- Kalibrierung zählt die eigene Ladeleistung nicht nochmals als verfügbaren
  PV-Überschuss; auch zwei parallele Läufe teilen sich dieselbe Energiebilanz.
- Ruhezeiten vor und nach der Kalibrierladung sind unabhängig von 0 bis 240 Minuten
  einstellbar (5-Minuten-Schritte, Standard jeweils 90 Minuten). Änderungen gelten
  auch für laufende Ruhephasen. Die untere Restzeit fließt in den frühesten
  Ladebeginn ein; die obere Ruhephase benötigt kein PV-Fenster.
- Dashboard und eine gemeinsame Home-Assistant-Mitteilung zeigen alle laufenden
  und vorgemerkten Kalibrieraufträge mit den konfigurierten Speichernamen.
  Ruheende, möglicher Ladebeginn sowie geschätztes Lade- und Ruheende bleiben
  unterscheidbar. Interne Speicherplatzbuchstaben erscheinen nicht als Modellname.
- Pro Speicher wird eine geschätzte Lade-/Entladezeit bis zur jeweiligen SoC-Grenze
  mit Uhrzeit angezeigt. Grundlage ist die geglättete gemessene AC-Leistung;
  kurze Packwechsel werden überbrückt, Stillstand oder veraltete Werte zeigen
  keine vermeintlich sichere Ankunftszeit. Kalibrierenergie enthält Verluste bereits.
- Die Rückgabe von Lade- und Entladegrenzen ist auch für den internen Speicherplatz
  D eindeutig. Beim Wechsel zu Aus/Beobachten werden Kalibrier- und normale
  Sicherungswerte vollständig zurückgegeben; ausstehende Rückgaben bleiben bei
  Fehlern und Neustarts erhalten. Bestehende Freigabe- und Schreibfehlerprüfungen
  gelten weiter.
- Gesamt-SoC verwendet die tatsächlichen Modulkapazitäten. Diagrammgrenzen und
  Bezeichnungen folgen dem physischen Modell. W/kW werden in Live-Anzeige und
  Verlauf einheitlich umgerechnet.
- Energie aus Verlaufsdaten wird nicht über unbekannte Messintervalle
  hochgerechnet. Unvollständige Tageswerte sind markiert; Diagrammlinien bleiben
  wie gewünscht durchgehend.
- Python-Regressionstests laufen zusätzlich bei jedem Pull Request. Die geprüften
  Fälle umfassen Leistungsauswahl, Slotwechsel, parallele Kalibrierung, Rückgabe
  nach Schreibfehler/Neustart, Restzeiten, Sensorattribute und Dashboarddaten.


## 1.2.2

- Vorzeitiges Ladeziel je Speicher für schwache, wechselhafte, mittlere und starke
  Tage getrennt einstellbar. Vorhandene Ziele werden je Klasse übernommen.
  Bei 0 % greift auch die Vormittagsabsicherung für diesen Speicher nicht ein;
  der normale PV-Fahrplan bleibt aktiv. Die gerade verwendete Klasse und die
  Ziele sind in der Tagesplanung sichtbar.
- Ein aktiver Ladeslot zeigt seinen ursprünglichen Startgrund auch dann noch,
  wenn der Sollwert für den Rest des 15-Minuten-Slots gehalten wird.
- In der Speicheransicht Leistung in kW mit Lade-/Entladevorzeichen und
  Nulllinie, Wirkungsgrad separat sowie Pack-Zelldrift darunter. Längere
  Zeiträume fassen Messwerte zusammen und erhalten Leistungsspitzen.
- Die Modellauswahl in den gemeinsamen Datenquellen ist kompakt; in der unteren
  Ruhephase zeigt die Kalibrierung den frühestmöglichen Ladebeginn an.
- Die Tagesplanung vergleicht bisher gemessene und prognostizierte PV-Energie.

## 1.2.1

- Wirkungsgrad und AC-Leistung zeigen Laden und Entladen als getrennte
  Kurven. Ein Wirkungsgrad von 0 % im Leerlauf erscheint nicht als Messung.
- Bei 7- und 30-Tage-Verläufen enthält der Tooltip auch das Datum.

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
