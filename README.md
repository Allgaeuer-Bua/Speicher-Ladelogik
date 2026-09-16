# Speicher-Ladelogik

Intelligente Speicher-Ladesteuerung für Home Assistant mit zwei unabhängig
regelbaren Speichern und AstraMeter.

## V1.0 RC 6

Der Release Candidate ersetzt die bisherigen YAML-Helfer und
Steuerautomationen durch native Entitäten der Integration.

RC5 ergänzt ein eigenständiges, responsives Dashboard. Es wird von der
Integration automatisch mitinstalliert und erscheint nach dem Neustart als
**Speicher-Ladelogik** in der Home-Assistant-Seitenleiste. Zusätzliche Karten,
Themes oder eine manuelle YAML-Konfiguration sind dafür nicht erforderlich.

RC6 überarbeitet dieses Panel mit einem dauerhaft dunklen Design, einem
richtungsgenauen Energiefluss, deutschen Kalibrierphasen, gerundeten Messwerten
und einer verständlichen Diagnose der Schreibzugriffe.

### Funktionen

- Betriebsarten **Aus**, **Beobachten** und **Automatik**
- Fahrplan aus PV-Prognose, realem Ertrag, Hauslast und Netzbilanz
- PV-AC-Messung mit MPPT- und Bilanz-Fallback
- unabhängig belegbare Speicherplätze **Venus A** und **Venus E**; bei der
  Einrichtung können auch Entitäten anderer Venus-Modelle gewählt werden
- frei einstellbare bevorzugte Ladeleistung und Nennkapazität je Speicher
- minimale und maximale SoC-Grenze werden ausschließlich vom jeweiligen Gerät
  gelesen; die Integration erzeugt und schreibt keine zweite SoC-Grenze
- stabile Leistungsgrenzen: Register werden nur bei einer wirklichen Änderung
  geschrieben; die Feinregelung übernimmt AstraMeter
- verbindliche 15-Minuten-Entscheidungsslots verhindern ein erneutes Ein- und
  Ausschalten innerhalb desselben Prognoseintervalls; Sicherheitsstopps und
  Benutzereingriffe wirken weiterhin sofort
- die Planung veröffentlicht Spitzenfenster, Einspeiseziel, Vorziehen,
  Deckungsfaktor und die bis zur nächsten Viertelstunde fixierte Entscheidung
- kein künstliches Absenken des Registers oberhalb 90 % und kein 0-W-Schreiben
  beim Erreichen der oberen Gerätegrenze
- dauerhafter Handbetrieb getrennt je Speicher; der andere Speicher bleibt im
  automatischen Fahrplan. Eine bleibende HA-Meldung erinnert an den Handbetrieb
- Kalibrierwarteschlange und 500-W-Kalibrierung; Vorbereitung durch natürlichen
  Hausverbrauch bis 13 %, das BMS begrenzt anschließend an der unteren
  Gerätegrenze (für die Kalibrierung 12 %)
- die Entladevorbereitung beginnt auf ausdrücklichen Tastendruck sofort, ohne
  feste Uhrzeit und ohne PV-Leistungsschwelle
- der jeweils andere Speicher bleibt während der Vorbereitung bis 14 % gesperrt;
  bei mindestens 15 Sekunden Netzbezug wird er vorübergehend freigegeben und
  nach 15 Sekunden ohne Netzbezug wieder gesperrt
- ab 14 % bleibt der andere Speicher mit seiner vom Gerät gemeldeten maximalen
  Entladeleistung dauerhaft freigegeben
- drei nicht bestätigte Schreibvorgänge sperren nur den betroffenen Speicher;
  Home Assistant meldet die Sperre dauerhaft bis zur Quittierung
- momentaner Lade- und Entladewirkungsgrad sowie Verlustleistung je Speicher;
  auch kleine Leistungen werden erfasst, sofern AC- und DC-Richtung plausibel
  sind
- Zustände, Vormerkungen, Sicherungen und Einstellungen werden intern über
  Home Assistant gespeichert

Wetter wird in V1.0 nicht ein zweites Mal direkt bewertet: Die PV-Prognose
enthält den Wettereinfluss bereits. So wird dieselbe Wetterlage nicht doppelt
gewichtet.

### Wechsel von Beta 7

1. Vor dem Update die alten Automationen deaktiviert lassen.
2. RC6 über HACS installieren und Home Assistant neu starten.
3. Der erste RC-Start erfolgt absichtlich in **Beobachten**. Entitäten und Plan
   prüfen.
4. Danach `select.speicher_ladelogik_betriebsart` auf **Automatik** stellen.
   Diese Auswahl bleibt bei späteren Neustarts erhalten.
5. Alte `pv_ladelogik_*`-Helfer erst entfernen, wenn Planung, Handbetrieb und
   Kalibrierknöpfe im neuen Gerät geprüft wurden.

> Niemals die alte Registerautomation und die Integration gleichzeitig steuern
> lassen. Die Integration verweigert Automatik, solange eine bekannte alte
> Steuerautomation aktiv ist.

### Eigenständiges Dashboard

Das Dashboard wird zusammen mit der Integration ausgeliefert und automatisch
als Seitenleisten-Panel registriert. Es enthält die Ansichten **Übersicht**,
**Speicher**, **Steuerung** und **Diagnose**. Entitäten werden über ihre stabilen
Unique IDs aufgelöst, sodass das Panel auch nach einer Änderung der Entity-ID
funktioniert.

Das bisherige YAML-Dashboard bleibt im Verzeichnis [`dashboards/`](dashboards/)
als kompatible Alternative erhalten.

Projektseite und Fehlerberichte:

- <https://github.com/Allgaeuer-Bua/Speicher-Ladelogik>
- <https://github.com/Allgaeuer-Bua/Speicher-Ladelogik/issues>
