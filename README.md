# Speicher-Ladelogik

Intelligente Speicher-Ladesteuerung für Home Assistant mit Venus A, Venus E und AstraMeter.

## V1.0 Beta 2

Die Integrations-Beta ist ausschließlich zur sicheren Datenprüfung gedacht:

- Einrichtung über **Einstellungen → Geräte & Dienste**
- freie Zuordnung der bestehenden Home-Assistant-Entitäten
- Aktualisierung alle 30 Sekunden und unmittelbar bei Zustandsänderungen
- Diagnose der gemeinsamen Daten sowie der Daten von Venus A und Venus E
- PV-AC-Messung mit MPPT-Fallback
- optionale Nicht-laden-Helfer für A und E\n- keine Schreibzugriffe auf Lade- oder Entladegrenzen

Die bisherige V2.2.1-Automation kann während dieses Tests unverändert weiterlaufen.

> **Nicht gleichzeitig steuern:** Erst eine spätere Beta übernimmt die Registersteuerung. Die alte Automation wird erst unmittelbar vor diesem kontrollierten Umschalttest deaktiviert.

## Entwicklung

Die bisherige YAML-/Python-Script-Version bleibt vorerst als Referenz im Repository. Die neue Integration befindet sich unter:

```text
custom_components/speicher_ladelogik/
```

Projektseite und Fehlerberichte:

- <https://github.com/Allgaeuer-Bua/Speicher-Ladelogik>
- <https://github.com/Allgaeuer-Bua/Speicher-Ladelogik/issues>
