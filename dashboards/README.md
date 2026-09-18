# YAML-Dashboard V1.0 (Alternative)

Das Dashboard ist für **Speicher-Ladelogik 1.0.0** ausgelegt und verwendet
ausschließlich Karten, die Home Assistant selbst mitbringt. Es sind keine
zusätzlichen HACS-Karten oder Themes erforderlich.

Ab RC5 installiert die Integration ein eigenständiges Dashboard automatisch in
der Home-Assistant-Seitenleiste. Diese YAML-Variante bleibt für Nutzer erhalten,
die lieber ein normales, frei bearbeitbares Home-Assistant-Dashboard verwenden.

## Installation

1. In Home Assistant **Einstellungen → Dashboards → Dashboard hinzufügen**
   öffnen und ein leeres Dashboard erstellen.
2. Das neue Dashboard öffnen, oben rechts **Bearbeiten** auswählen und über das
   Drei-Punkte-Menü den **Rohkonfigurationseditor** öffnen.
3. Den gesamten Inhalt aus
   `speicher_ladelogik_dashboard_v1.yaml` einfügen und speichern.
4. Wenn Home Assistant abweichende Entitäts-IDs erzeugt hat, die betroffenen
   IDs im Rohkonfigurationseditor ersetzen.

## Aufbau

- **Übersicht:** Systemstatus, Energiefluss, Speicher und Tagesplanung
- **Speicher:** Details, Gerätegrenzen, Wirkungsgrad und 24-Stunden-Verläufe
- **Steuerung:** Betriebsart, Handbetrieb, Kalibrierung und Planungsparameter
- **Diagnose:** Datenquellen, Registerzugriffe und Planungsdetails

## Referenz-Entitäten

Die Entitäten der Integration werden bei einer Standardinstallation automatisch
mit den im Dashboard verwendeten IDs angelegt. Die folgenden physischen
Quell-Entitäten gehören zur Referenzanlage und müssen bei einer anderen
Installation gegebenenfalls ersetzt werden:

- `sensor.hausleistung_gesamt`
- `sensor.stromzahler_leistung`
- `sensor.marstek_venus_a_soc_batterie`
- `sensor.marstek_venus_a_ac_leistung`
- `sensor.marstek_venus_e_soc`
- `sensor.marstek_venus_e_ac_leistung`
- die Lade-, Entlade- und SoC-Grenzen beider Geräte

## Sicherheit

Die Schaltflächen für Kalibrieraufträge und die Fehlerquittierung führen echte
Aktionen aus und besitzen deshalb eine Bestätigungsabfrage. Der Handbetrieb wird
auf der Steuerungsansicht deutlich eingeblendet, solange er aktiv ist.
