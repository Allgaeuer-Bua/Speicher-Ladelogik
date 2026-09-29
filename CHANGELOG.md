# Änderungen

## 2.0.0

- Eigenständige Integration mit der Kennung `speicher_ladelogik_ae` für Venus A und Venus E. Das Repository enthält nur noch dieses Paket.
- Venus D und generische Mehrfachauswahl aus Konfiguration, HA-Entitäten und Dashboard entfernt; bis zu vier optionale MPPT-Sensoren für Venus A.
- Energiefluss mit zwei getrennten Speichern samt Leistung und SoC; Übersicht zeigt SoC je Speicher statt „Energie heute“.
- SoC-/Leistungsverlauf innerhalb der Speicherkarte unter den Packdaten; doppelte AC-Leistungskurve entfernt.
- Venus-A-Ladegrenze bleibt bei ausstehendem letztem SoC-Prozent erhalten, ohne den gehaltenen Registerwert als aktive Ladung zu zählen. Sicherheitsstopps behalten Vorrang.
- Neue Installation beginnt in **Beobachten**; Einstellungen und Kalibrierhistorie der alten Domain werden nicht automatisch migriert.
