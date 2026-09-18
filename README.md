# Speicher-Ladelogik

**Speicher-Ladelogik** ist eine native Home-Assistant-Integration zur
prognose- und überschussabhängigen Steuerung von bis zu drei AC-gekoppelten
Marstek-Speichern. Sie koordiniert die Modelle **Venus A**, **Venus D** und
**Venus E** unabhängig voneinander und stellt Planung, Bedienung und Diagnose
in einem eigenen Dashboard bereit.

Die Integration kommuniziert nicht direkt mit Wechselrichtern, Stromzählern
oder Speichern. Sie verwendet vorhandene Home-Assistant-Entitäten. Dadurch
können Messwerte aus unterschiedlichen Integrationen und von verschiedenen
Anbietern verwendet werden, sofern Bedeutung, Einheit und Vorzeichen passen.

> **Aktuelle Version:** 1.0.1  
> **Erforderliche Home-Assistant-Version:** 2026.9.1 oder neuer

## Wofür ist die Integration gedacht?

Speicher-Ladelogik entscheidet anhand von PV-Prognose, tatsächlicher
PV-Erzeugung, Hausverbrauch, Netzbilanz und Ladezuständen:

- wann ein Speicher geladen werden soll,
- wie viel Ladeleistung freigegeben wird,
- welcher Speicher welchen Anteil übernimmt,
- wann Energie für später reserviert werden sollte,
- wann eine Mittagsspitze abgefangen werden kann,
- und ob ein geplantes Kalibrierfenster ausreicht.

Die Planung arbeitet in verbindlichen 15-Minuten-Slots. Sicherheitsstopps,
manuelle Eingriffe und ungültige Sensordaten wirken trotzdem sofort. Kleine
Messwertschwankungen führen dadurch nicht ständig zu neuen Schaltentscheidungen.

## Unterstützte Speicher

Es können ein bis drei Speicher eingerichtet werden – jeweils maximal ein
Gerät der folgenden Modelle:

| Modell | Besonderheiten |
| --- | --- |
| Venus A | Pack-SoC und Pack-Zelldrift, bis zu vier optionale MPPT-Sensoren |
| Venus D | Pack-SoC und Pack-Zelldrift, bis zu vier optionale MPPT-Sensoren |
| Venus E | Zellspannungsdifferenz und Gerätedaten ohne Pack-Auswahl |

Nicht eingerichtete Modelle erscheinen weder in der Planung noch im Dashboard.
Jeder Speicher besitzt eigene Leistungsgrenzen, Kapazität, Fahrplanfreigabe,
Handsteuerung, Kalibrierung und Fehlerbehandlung.

## Was wird benötigt?

### Home Assistant

- Home Assistant **2026.9.1** oder neuer
- [HACS](https://www.hacs.xyz/) für die komfortable Installation
- Recorder-/Verlaufsdaten für die Diagramme im Dashboard
- bereits in Home Assistant vorhandene Mess- und Steuerentitäten

### Gemeinsame Datenquellen

Bei der Einrichtung werden die passenden Entitäten ausgewählt:

- aktuelle Leistung am Netzanschlusspunkt,
- aktuelle Hausleistung,
- gemittelte Hausleistung,
- heutige PV-Energie,
- aktuelle PV-AC-Leistung oder geeignete MPPT-Leistungssensoren,
- 15-Minuten-PV-Prognosen für heute und morgen.

Die Prognosequelle ist nicht fest vorgegeben. Verwendet werden können
beispielsweise Open-Meteo-Sensoren oder andere Quellen, die passende
15-Minuten-Energiewerte in Home Assistant bereitstellen.

### Daten und Stellglieder je Speicher

Für jeden ausgewählten Speicher werden mindestens benötigt:

- SoC-Sensor,
- AC-Leistungssensor,
- beschreibbare maximale Ladeleistung,
- beschreibbare maximale Entladeleistung,
- Schalter für die automatische Zielwertregelung,
- Schalter zum Aktivieren der externen Leistungsregelung.

Für vollständige Diagnose-, Wirkungsgrad- und Kalibrierfunktionen werden
zusätzlich die angebotenen Gerätewerte ausgewählt, beispielsweise
DC-Batterieleistung, SoC-Grenzen, Zellspannung, Zelltemperatur, Zelldrift und
bei Venus A/D die vorhandenen Pack-Sensoren.

## Funktionen

### Planung und Regelung

- Betriebsarten **Aus**, **Beobachten** und **Automatik**
- Fahrplan aus PV-Prognose, realem Ertrag, Hauslast und Netzbilanz
- PV-AC-Messung mit MPPT- und Bilanz-Fallback
- getrennte Planung für jeden konfigurierten Speicher
- frei einstellbare bevorzugte Ladeleistung und Nennkapazität
- Mittagsspitzenkappung mit planbarem Einspeiseziel
- Berücksichtigung von Prognosegüte, Reserve und verfügbarem Tagesfenster
- stabile Leistungsgrenzen ohne unnötige Wiederholung identischer Schreibwerte
- keine künstliche Reduzierung allein aufgrund eines SoC oberhalb von 90 %

### Speichersteuerung

- dauerhafter Handbetrieb je Speicher
- automatische Steuerung der übrigen Speicher bleibt dabei erhalten
- minimale und maximale SoC-Grenzen werden vom jeweiligen Gerät gelesen
- ein Fehler sperrt nur den betroffenen Speicher
- drei nicht bestätigte Schreibvorgänge führen zu einer Sicherheitssperre
- Sperren und Schreibfehler können nach Prüfung quittiert werden
- Einstellungen, Vormerkungen und Sicherungszustände bleiben nach Neustarts
  erhalten

### Kalibrierung

- getrennte Kalibrieranforderung je Speicher
- Warteschlange für mehrere Speicher
- einstellbare Kalibrierleistung von **400 bis 1.500 W**
- Berechnung des verfügbaren Fensters und der benötigten Dauer für heute und
  morgen
- Entladevorbereitung durch den natürlichen Hausverbrauch
- Schutz vor gegenseitigem Laden oder Entladen mehrerer Speicher
- automatische Wiederherstellung der vorherigen Leistungsgrenzen

### Überwachung und Benachrichtigungen

- momentaner Lade- und Entladewirkungsgrad
- berechnete Verlustleistung je Speicher
- farbliche Zelldrift-Bewertung:
  - bis 20 mV: grün
  - über 20 bis unter 50 mV: gelb
  - ab 50 mV: rot
- dauerhafte Home-Assistant-Mitteilungen bei relevanten Problemen
- optional zusätzliche Nachricht über einen frei wählbaren
  `notify.mobile_app_*`-Dienst

## Eigenständiges Dashboard

Das Dashboard wird mit der Integration installiert und automatisch als
**Speicher-Ladelogik** in der Home-Assistant-Seitenleiste registriert.
Zusätzliche Karten, Themes oder eine manuelle YAML-Konfiguration sind nicht
erforderlich.

Es enthält vier Ansichten:

- **Übersicht:** Systemstatus, Tagesplanung, gemeinsamer Energiefluss,
  Tagesenergie sowie Leistungs- und SoC-Verläufe
- **Speicher:** Detailwerte, Tagesenergien, SoC-/Leistungsverlauf, Packdaten und
  optionale MPPT-Werte
- **Steuerung:** Betriebsart, Planungseinstellungen, Handbetrieb, Kalibrierung
  und Kalibrierfenster
- **Diagnose:** Datenquellen, Warnungen, Schreibzugriffe und fehlende Entitäten

Messwerte und Diagrammlegenden sind anklickbar und öffnen die zugehörige
Home-Assistant-Entität. Das mitgelieferte YAML-Dashboard im Verzeichnis
[`dashboards/`](dashboards/) bleibt als Alternative verfügbar.

## Installation über HACS

1. In HACS den Bereich **Integrationen** öffnen.
2. Falls das Repository noch nicht gelistet ist, unter
   **Benutzerdefinierte Repositories** hinzufügen:
   `https://github.com/Allgaeuer-Bua/Speicher-Ladelogik`
3. **Speicher-Ladelogik** herunterladen.
4. Home Assistant neu starten.
5. Unter **Einstellungen → Geräte & Dienste → Integration hinzufügen**
   nach **Speicher-Ladelogik** suchen.

## Einrichtung

1. Vorhandene Automationen deaktivieren, die dieselben Lade- oder
   Entladeleistungsgrenzen schreiben.
2. Gemeinsame Messwerte und Prognosesensoren auswählen.
3. Die vorhandenen Modelle Venus A, D und/oder E auswählen.
4. Für jeden Speicher die Messwerte und Stellglieder zuordnen.
5. Optional einen Handy-Benachrichtigungsdienst eintragen.
6. Nach Abschluss Entitäten, Vorzeichen und Planung im Modus
   **Beobachten** prüfen.
7. Erst danach die Betriebsart auf **Automatik** stellen.

Die gewählte Betriebsart bleibt bei einem Neustart erhalten.

## Betriebsarten

| Betriebsart | Verhalten |
| --- | --- |
| Aus | Keine automatische Planung oder Regelung |
| Beobachten | Planung und Diagnose laufen, ohne automatische Leistungssteuerung |
| Automatik | Planung und Leistungsgrenzen werden automatisch umgesetzt |

Ein einzelner Speicher kann zusätzlich in den Handbetrieb versetzt werden,
während die übrigen Speicher weiter automatisch geplant werden.

## Wichtige Hinweise

> Die Integration und eine alte Registerautomation dürfen niemals gleichzeitig
> dieselben Speicherwerte schreiben.

Beim ersten Start beginnt die Integration absichtlich im sicheren Modus
**Beobachten**. Vor dem Umschalten auf **Automatik** sollten insbesondere
Netzrichtung, Speicher-Leistungsvorzeichen, SoC-Werte und Stellglieder geprüft
werden.

Das Wetter wird nicht ein zweites Mal direkt bewertet. Der Wettereinfluss ist
bereits Bestandteil der PV-Prognose und würde sonst doppelt gewichtet.

Speicher-Ladelogik ist für die genannten Marstek-Venus-Modelle und deren
Entitäten ausgelegt. Sie ist kein universeller Treiber für beliebige
Batteriesysteme und ersetzt weder die Geräteintegration noch die
Schutzfunktionen des BMS.

## Aktualisierung

Nach einem Update über HACS Home Assistant neu starten. Änderungen und
Fehlerbehebungen sind auf der
[Release-Seite](https://github.com/Allgaeuer-Bua/Speicher-Ladelogik/releases)
aufgeführt.

## Projekt und Fehlerberichte

- [GitHub-Projekt](https://github.com/Allgaeuer-Bua/Speicher-Ladelogik)
- [Fehler oder Funktionswunsch melden](https://github.com/Allgaeuer-Bua/Speicher-Ladelogik/issues)
