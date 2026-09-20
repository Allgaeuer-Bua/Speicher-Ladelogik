# Änderungsverlauf

## 1.1.0

- Bis zu drei unabhängige Speicherinstanzen; Modelle A, D und E dürfen mehrfach
  vorkommen.
- Automatische Migration bestehender V1.0-Konfigurationen.
- Venus A: 1–6 Module zu je 2,08 kWh, maximal 12,48 kWh.
- Venus D: 1–6 Module zu je 2,56 kWh, maximal 15,36 kWh.
- Gelernte Kalibrierenergie wird nach dem ersten erfolgreichen Lauf verwendet.
- AC-Referenzenergie inklusive realer Verluste: Venus A 3,77 kWh bei zwei
  Modulen, Venus E 5,15 kWh.
- Der pauschale Aufschlag von 0,25 kWh entfällt.
- Laufende Kalibrierungen verlängern ihr Fenster bei ausreichendem gemessenem
  PV-Überschuss, statt allein wegen des Prognoseendes abzubrechen.
