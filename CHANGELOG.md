# Änderungen

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
