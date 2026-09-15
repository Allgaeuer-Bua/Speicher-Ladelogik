# Speicher-Ladelogik

Intelligente Speicher-Ladesteuerung für Home Assistant mit Venus A, Venus E und AstraMeter.

## V1.0 Beta 7

Beta 7 übernimmt erstmals optional die kontrollierte Registersteuerung:

- Einrichtung über **Einstellungen → Geräte & Dienste**
- freie Zuordnung der bestehenden Home-Assistant-Entitäten
- Aktualisierung alle 30 Sekunden und unmittelbar bei Zustandsänderungen
- Diagnose der gemeinsamen Daten sowie der Daten von Venus A und Venus E
- PV-AC-Messung mit MPPT-Fallback
- vollständige Fahrplan- und Kalibrierberechnung im Schattenmodus
- automatischer Vergleich ausgewählter Ergebnisse mit der bisherigen V2.2.1
- automatische Kompatibilität mit den bisherigen `pv_ladelogik_*`- und
  `pv_kalibrierung_*`-Entity-IDs
- liest bestehende V2.2.1-Sitzungen, Sicherungen und Vormerkungen ohne Migration
- vorgeschlagene Stellbefehle bleiben im Beobachtungsmodus Diagnosewerte
- eigener Schalter **Registersteuerung**; standardmäßig und nach jedem
  Home-Assistant-/Integrationsneustart ausgeschaltet
- Schreiben ausschließlich auf die vier bei der Einrichtung gewählten Lade-
  und Entladegrenzen, mit Wertebereichsprüfung und Rückbestätigung
- drei fehlgeschlagene Schreibbestätigungen sperren nur den betroffenen Speicher
- bei ausgefallener Planung werden ausschließlich die Ladegrenzen auf 0 W gesetzt
- Ziel-Latch mit 2 Prozentpunkten Hysterese gegen 99/100-%-Pendeln
- zustandsbasierte Sollwertstabilisierung: ein sinnvoller Registerwert bleibt
  bis zu einer echten Fahrplan-, Ziel- oder Sicherheitsänderung erhalten
- Ziel-Latch und stabiler Fahrplanwert bleiben über einen HA-Neustart erhalten;
  gespeichert wird ausschließlich bei einer tatsächlichen Zustandsänderung
- getrennte Anzeige von rohem und stabilem Fahrplanwert sowie Haltegrund
- während der Kalibrierentladung bleibt der andere Speicher bis 14 % gesperrt;
  danach wird seine maximale Entladeleistung einmalig und ohne SoC-Flattern
  freigegeben
- kennzeichnet erwartete Abweichungen zur V2.2.1 im Planvergleich
- optionale Nicht-laden-Helfer für A und E
- bestehende V2.2.1-Helfer und das bisherige Dashboard werden während der
  kontrollierten Umstellung weitergeführt

### Kontrollierte Umschaltung

1. Beta 7 installieren und Home Assistant neu starten. Die Registersteuerung
   bleibt aus.
2. Eine aktuelle, fehlerfreie Planung abwarten.
3. Die bisherige **PV-Ladelogik AstraMeter Regelung** und den
   **PV-Ladelogik V2 Planungswächter** deaktivieren.
4. Erst danach am Gerät **Registersteuerung** einschalten.

> **Nie beide Steuerungen gleichzeitig aktivieren.** Zum Rückwechsel zuerst die
> Registersteuerung der Integration ausschalten und anschließend die beiden
> bisherigen Automationen wieder aktivieren.

## Entwicklung

Die bisherige YAML-/Python-Script-Version bleibt vorerst als Referenz im Repository. Die neue Integration befindet sich unter:

```text
custom_components/speicher_ladelogik/
```

Projektseite und Fehlerberichte:

- <https://github.com/Allgaeuer-Bua/Speicher-Ladelogik>
- <https://github.com/Allgaeuer-Bua/Speicher-Ladelogik/issues>
