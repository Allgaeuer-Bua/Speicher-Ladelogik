# Änderungen

## 2.2.0

- Kalibrierung aus „Steuerung“ in einen eigenen Reiter mit sämtlichen Einstellungen, Vormerkungen, Aufträgen und Ergebnissen verschoben.
- Lokale Darstellungseinstellungen über das Palettensymbol: fünf Akzentfarben, unabhängige Speicherfarben, Hell/Dunkel/Automatisch, Kompakt/Komfortabel und normale/dezente/ausgeschaltete Animation. Browser-Speicherfehler beeinträchtigen die Bedienung nicht; Warnungs- und Fehlerfarben bleiben fest.
- Kompakter Gesamt-SoC, aufklappbare Pack- und Technikdetails, klarere Unterscheidung zwischen Ladefreigabe und tatsächlichem Energiefluss. Reduzierte Bewegung des Betriebssystems wird berücksichtigt.
- Diagnose: Beginn und Ende stehen untereinander. Konkrete Fehlermeldungen benennen ungültige SoC-Grenzen, Gesamt-/Pack-Sensoren und Stellbereiche. Keine zusätzliche pauschale Fehlermeldung für denselben Grenzfehler.
- Ladeplanung, insbesondere das Verhalten an schwachen Tagen, und bestehende Sicherheitsbedingungen bleiben unverändert.

## 2.1.2

- Dashboard vereinfacht: „SoC je Speicher“ sowie die Verlaufsgrafiken für SoC/Leistung, Wirkungsgrad und Zelldrift entfernt. Aktuelle Speicherwerte und Energiezählung bleiben erhalten; die Übersicht lädt keine Verlaufsdaten mehr.
- Ladegrenzen-Diagnose als übersichtliche Karte je Speicher: klare Begründung, bevorzugte Leistung, berechneter Wert, geltende Sollgrenze und Zeitplanung. Zusätzliche Details und der erste Freigabegrund sind aufklappbar.
- Kalibrierungsmeldungen überstehen HA-Neustarts: Bereits gemeldete Abschlüsse und Abbrüche werden nicht erneut als neues Ereignis gemeldet. Bestehende abgeschlossene Sitzungen werden beim Update berücksichtigt; echte neue Ereignisse bleiben sichtbar.
- Verhaltenstests für wiederholte Neustarts, neue Ereignisse und fehlgeschlagene Benachrichtigungen ergänzt. Bestehende Ladeplanung und Sicherheitsprüfungen bleiben erhalten.

## 2.1.1

- Starke Tage verwenden ausschließlich ihr eigenes frühes SoC-Ziel. Kurzfristige Prognoseabweichungen aktivieren nicht mehr das Wechselhaft-Profil. Eine tatsächlich gefährdete Vollladung darf den Start weiterhin vorziehen.
- Frische AC-Messwerte bestätigen den Datenempfang auch bei 0 W oder Entladung. Eine Ladefreigabe verlangt keine Mindest-Istleistung mehr.
- Optionaler Wechselrichterstatus (Charge, Discharge, Standby) je Speicher ergänzt die Diagnose. Die üblichen A/E-Entitäten sind vorbelegt; fehlende Statussensoren blockieren die Integration nicht.
- Veraltete AC-Messwerte erzeugen nach drei Minuten ohne frische Daten nur einen Hinweis pro Störung und Speicher. Frische Statuswerte verdecken keine veralteten AC-Werte. Hinweise werden nach Erholung entfernt; der Störungszustand übersteht einen Neustart.
- Die erste Tagesfreigabe speichert Zeitpunkt, Begründung, Tagesklasse, SoC-Ziel und Prognosefaktoren dauerhaft für diesen Tag. Die Diagnose zeigt den ursprünglichen Freigabegrund zusätzlich zur laufenden Entscheidung. Bereits vorhandene Freigaben werden ohne erfundenen Startgrund übernommen.

## 2.1.0

- Normalen Ladeplan durch eine Tagesfreigabe je Speicher ersetzt. Die alten 15-Minuten-Ladepausen, Leistungsaufteilung und konkurrierenden Freigabewege entfallen.
- Drei Ertragsklassen: schwach, mittel, stark. Eigene frühe SoC-Ziele je Speicher bleiben erhalten; „Wechselhaft“ dient als Zielprofil bei Prognoseunsicherheit. An schwachen Tagen keine Mittagsspitzenkappung.
- Bevorzugte Leistung hat Vorrang. Zuerst früher starten; höhere Leistung nur bei nachgewiesen besserer Zielfüllung. PV, Hausverbrauch, Verluste und Reserven werden gemeinsam bilanziert, Speicherbedarf und Freigabe getrennt bewertet.
- Nach der Tagesfreigabe bleiben positive Grenzen bei Wolken, Prognoseänderungen und am Abend stehen. Bei 100 % bleibt das Register erhalten; Nachladen bei 99 % erzeugt keine Leistungsspitze. Die Tagesfreigabe übersteht einen HA-Neustart.
- Vor dem ersten Ladebeginn eines neuen mittleren/starken Tages bleibt eine 0-W-Sperre möglich, damit die spätere Mittagsspitze aufgenommen werden kann. Frühe SoC-Ziele lösen nach ihrer Erfüllung keine erneute Sperre aus.
- Diagnose nennt die aktuelle eigene Entscheidung je Speicher. Handbetrieb der E überschreibt die Begründung für A nicht mehr. Die Oberfläche zeigt die tatsächliche Freigabe und wirksame Mittagsspitzenplanung; das ungenutzte gemeinsame Mindestleistungsfeld entfällt.
- Bestehende Einstellungen und Kalibrieraufträge bleiben erhalten. Kalibrierung, Handbetrieb und Sicherheitsprüfungen behalten Vorrang.

## 2.0.3

- Der Energiefluss zeigt Solar und Haus mit größerem Abstand, auch auf schmalen Bildschirmen.
- Bei Kalibrierung startet ein vorbereiteter Speicher ab 600 W frisch gemessener Netzeinspeisung; die angestrebte untere Ruhezeit und eine ausreichend lange Prognose sind keine Start- oder Abbruchbedingungen mehr. Die untere SoC-Grenze beträgt 14 %.
- Zu kurze Vorruhezeit, ein zu knappes Prognosefenster und weniger als 400 W Einspeisung lösen eine HA-Warnung und eine Push-Nachricht an den konfigurierten Handy-Dienst aus. Gemessene Ladeleistung bis 400 W wird nach fünf Minuten gemeldet, ohne deswegen zu pausieren. Geräteschutz und Prüfungen für ungültige Daten bleiben aktiv.

## 2.0.2

- Das Kalibrierfenster für heute nutzt die gleiche zeitabhängige PV-Prognosekorrektur wie die Tagesplanung. Ein vorübergehender Einbruch der aktuellen PV-Leistung verkürzt damit nicht pauschal alle späteren Prognoseabschnitte.
- Die Prognosesicherheit wird weiterhin einmal berücksichtigt; die Fensterberechnung für morgen bleibt unverändert.

## 2.0.1

- Kalibrierung: Ein laufender Auftrag kann mit „Heute“ oder „Morgen“ neu terminiert werden; ein bereits begonnenes PV-Fenster wird bei ausreichendem realem Überschuss nicht durch eine neue Prognose verworfen.
- Vor dem Laden ist die eingestellte untere Ruhezeit ein Wunschwert. Bei geeignetem PV-Fenster und ausreichendem aktuellem Überschuss kann früher geladen werden; die tatsächliche Dauer wird je Speicher gespeichert und angezeigt.
- Ein geringfügiger SoC-Rücksprung oder eine kurze, überprüfbare Messunterbrechung setzt die untere Ruhephase nicht unnötig zurück. Der letzte Pausengrund ist sichtbar.
- Die obere Ruhephase und die Prüfungen für Zellzustand, SoC, Live-Überschuss und Ladeleistung bleiben für ein erfolgreiches Kalibrierergebnis maßgeblich.

## 2.0.0

- Eigenständige Integration mit der Kennung `speicher_ladelogik_ae` für Venus A und Venus E. Das Repository enthält nur noch dieses Paket.
- Venus D und generische Mehrfachauswahl aus Konfiguration, HA-Entitäten und Dashboard entfernt; bis zu vier optionale MPPT-Sensoren für Venus A.
- Energiefluss mit zwei getrennten Speichern samt Leistung und SoC; Übersicht zeigt SoC je Speicher statt „Energie heute“.
- SoC-/Leistungsverlauf innerhalb der Speicherkarte unter den Packdaten; doppelte AC-Leistungskurve entfernt.
- Venus-A-Ladegrenze bleibt bei ausstehendem letztem SoC-Prozent erhalten, ohne den gehaltenen Registerwert als aktive Ladung zu zählen. Sicherheitsstopps behalten Vorrang.
- Neue Installation beginnt in **Beobachten**; Einstellungen und Kalibrierhistorie der alten Domain werden nicht automatisch migriert.
