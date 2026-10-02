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

## Ladeplanung ab v2.1.0

1. **Tag einordnen:** schwach, mittel oder stark anhand des erwarteten Tagesertrags. Die gemessene PV-Abweichung korrigiert die Prognose zeitabhängig. Ein Klassenwechsel wird erst nach 15 Minuten bestätigt; daraus entstehen keine Ladepausen.
2. **Bedarf je Speicher:** Geräteziel, eigener SoC und bei A die einzelnen Packs bestimmen den Restbedarf. Das zusätzliche frühe SoC-Ziel greift nur, wenn dieser Speicher darunter liegt. „Wechselhaft“ ist ein separates Zielprofil bei gemessener Prognoseunsicherheit, keine vierte Ertragsklasse.
3. **Früh genug beginnen:** Schwache Tage starten mit vorhandenem PV-Überschuss und ohne Mittagsspitzenkappung. Mittlere und starke Tage dürfen später beginnen, soweit die gemeinsame PV-Prognose beide Speicher einschließlich Reserve versorgen kann. Falls nötig wird zuerst der Start vorgezogen.
4. **Bevorzugte Leistung:** A und E verwenden unabhängig ihre eingestellte bevorzugte Ladegrenze. Eine höhere Grenze wird nur gewählt, wenn die Simulation damit die heutige Zielfüllung tatsächlich verbessert. Fehlender PV-Ertrag oder eine knappe Reserve allein erzeugen keine Maximalleistung.
5. **Nach Tagesfreigabe halten:** Keine 15-Minuten-Pausenslots und kein Zurücksetzen auf 0 W wegen Wolken, einer neuen Prognose oder dem Ende des Ladefensters. AstraMeter regelt die tatsächliche Leistung am Netzanschlusspunkt. Bei 100 % bleibt der Registerwert stehen; bei 100 → 99 % wird ohne Leistungserhöhung nachgeladen.

**Vor dem ersten Ladebeginn eines neuen mittleren oder starken Tages kann die Ladegrenze 0 W sein.** Nur so bleibt Platz für die spätere PV-Spitze. Nach der Tagesfreigabe bleibt sie positiv. Ein frühes SoC-Ziel kann die Tagesfreigabe vorziehen; sein Erreichen löst keine erneute Sperre aus. An schwachen Tagen bleibt eine vorhandene positive Grenze auch vor dem ersten Überschuss stehen. Eine Ladefreigabe wird gespeichert und übersteht einen HA-Neustart am selben Tag.

### Planungsparameter

| Einstellung | Wirkung |
|---|---|
| Prognosesicherheit | Verwendet nur den eingestellten Anteil jeder PV-Prognose, einmal für den gemeinsamen PV-Ertrag. |
| Wolkenreserve | Zieht die eingestellte AC-Energie einmal vom zukünftigen Überschuss ab, beginnend am Tagesende. |
| Planungswirkungsgrad | Rechnet AC-Überschuss in erwartete gespeicherte Energie um. |
| Knappheitsreserve | Erhöht den rechnerischen Restbedarf für die Entscheidung, ob ein später Start noch reicht. |
| Knappheits-Hysterese | Verlangt zusätzliche Reserve, bevor eine bestehende Knappheit endet. |
| Mittlerer Tag | Orientierungspunkt für den bevorzugten Start innerhalb der mittleren Ertragsklasse. |

Hausverbrauch und reservierte Leistung für Handbetrieb/Kalibrierung werden abgezogen. Die Ladeplanung berücksichtigt eine langsamere Endphase und zählt die verfügbare PV-Energie für A und E zusammen nur einmal. Das bisherige gemeinsame Feld „Minimale effiziente Ladeleistung“ entfällt; maßgeblich sind die bevorzugten Leistungen je Speicher.

Die Vollladung hat Vorrang vor der Mittagsspitzenkappung. Eine Prognose kann tatsächliches Wetter und Hausverbrauch nicht garantieren; die Planung wird laufend neu geprüft. Die Diagnose zeigt die verbleibende rechnerische Fehlmenge und die aktuelle Begründung je Speicher. Eine Freigabe ist eine **Leistungsgrenze**, keine erzwungene Ladung oder zugesicherte Istleistung.

Kalibrierung, Handbetrieb, manuelle Sperren, ungültige Daten und Gerätegrenzen haben weiterhin Vorrang. Die Regel zum Halten der Ladegrenze gilt für den normalen automatischen Fahrplan.

## Kalibrierung

Seit v2.0.1 ist die eingestellte Ruhezeit **vor** der Kalibrierladung ein Wunschwert: Bei leerem Speicher und ausreichend realem PV-Überschuss kann ein nutzbares Fenster früher beginnen. Die tatsächlich erreichte Dauer steht je Speicher in der Kalibrierungsansicht. Die Ruhezeit **nach** bestätigten 100 % bleibt für das Kalibrierergebnis erforderlich.

Seit v2.0.2 wird ein kurzfristiger PV-Einbruch bei der Kalibrierfensteranzeige für heute nicht mehr pauschal auf den gesamten restlichen Tag übertragen. Die Anzeige bewertet spätere 15-Minuten-Prognosen mit der zeitabhängigen Korrektur der Tagesplanung.

Ab v2.0.3 beginnt ein vorbereiteter Speicher bei mindestens 600 W frischer Einspeisung am zugeordneten Netzsensor. Die angestrebte Ruhezeit vor dem Laden und das prognostizierte Zeitfenster verhindern den Start nicht; der untere SoC für die Kalibrierung liegt bei 14 %. Ein kurzer Ertragseinbruch oder höchstens 400 W Ladeleistung beendet die Kalibrierladung nicht. Für diese Fälle und für knappe Prognosen erzeugt die Integration HA-Warnungen. Für zusätzliche Push-Nachrichten muss in den Integrationsoptionen ein Handy-Dienst wie `notify.mobile_app_mein_geraet` hinterlegt sein. Gerätegrenzen, Datenprüfungen und die obere Ruhezeit gelten weiterhin.

## Entwicklung

```sh
python -m compileall -q custom_components/speicher_ladelogik_ae tests
node --check custom_components/speicher_ladelogik_ae/frontend/speicher-ladelogik-ae-panel.js
node --test tests/test_ae_panel.mjs
```

Die Python-Verhaltenstests in `tests/test_*.py` laufen über den einfachen Runner der CI, einschließlich Tagesverläufen, Reservewirkung, unabhängigem Handbetrieb und Kalibrierung. Home Assistant und die echten Speicher müssen vor Aktivierung der Automatik in der eigenen Installation geprüft werden.
