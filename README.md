# Speicher-Ladelogik A/E

Eine Home-Assistant-Integration für **eine Marstek Venus A und eine Venus E** mit PV-Ladeplanung, Kalibrierung und einem eigenen Dashboard. Venus D und weitere Speicherbelegungen werden in dieser Variante nicht angeboten.

## Installation

1. In Home Assistant die bisherige Integration **Speicher-Ladelogik** auf **Beobachten** stellen und ihre bisherigen Automationen zur Ladegrenze deaktivieren.
2. Die alte Integration unter *Einstellungen → Geräte & Dienste* entfernen und Home Assistant neu starten. Wenn die alte Version manuell installiert wurde, `custom_components/speicher_ladelogik` ebenfalls entfernen.
3. Dieses Repository als benutzerdefiniertes **Integrations**-Repository in HACS hinzufügen und **Speicher-Ladelogik A/E** installieren. Alternativ `custom_components/speicher_ladelogik_ae` nach `/config/custom_components/` kopieren. Home Assistant neu starten.
4. Unter *Einstellungen → Geräte & Dienste → Integration hinzufügen* **Speicher-Ladelogik A/E** auswählen. Gemeinsame PV-, Netz-, Hauslast- und Prognosesensoren sowie danach Venus A und Venus E zuordnen. Für Venus A können bis zu vier MPPT-Leistungssensoren gewählt werden.
5. Das Dashboard prüfen. Die Integration startet im Modus **Beobachten**. Die Betriebsart **Automatik** erst einschalten, wenn die Sensoren gültig sind und keine andere Automation die Ladegrenzen derselben Geräte schreibt.

Die neue Kennung lautet `speicher_ladelogik_ae`. Einstellungen, Kalibrierhistorie und Verlaufsdaten der alten Integration werden nicht automatisch übernommen. Die alten HA-Entitäten können nach dem Entfernen als verwaist erscheinen; sie sind kein Bestandteil des neuen Pakets.

## Dashboard

- **Übersicht:** Solar, Netz, Haus, Venus A und Venus E mit eigener Leistung und SoC; darunter Tagesplanung und SoC-Verlauf je Speicher. Die alte Karte „Energie heute“ entfällt.
- **Speicher:** Je Speicher Status, Packdaten, SoC-/Leistungsverlauf unter den Packdaten sowie Wirkungsgrad und Zelldrift.
- **Steuerung:** Kalibrierung, Handbetrieb, Fahrplanfunktionen und Leistungsgrenzen; Betriebsart am Ende.
- **Diagnose:** Datenverfügbarkeit, Planung und Schreibergebnisse.

Die Planungs- und Kalibrierfunktionen aus 1.2.5 bleiben für A und E verfügbar. Bei der Venus A bleibt die Ladegrenze auch für das letzte SoC-Prozent gesetzt, sofern kein Sicherheitsstopp vorliegt; eine gehaltene Grenze zählt nicht als aktiver Ladeslot.

## Entwicklung

```sh
python -m compileall -q custom_components/speicher_ladelogik_ae tests
node --check custom_components/speicher_ladelogik_ae/frontend/speicher-ladelogik-ae-panel.js
node --test tests/test_ae_panel.mjs
```

Die Tests in `tests/test_ae_integration.py` laufen über den einfachen Runner der CI. Home Assistant und die echten Speicher müssen vor Aktivierung der Automatik in der eigenen Installation geprüft werden.
