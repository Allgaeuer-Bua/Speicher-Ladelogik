# Änderungsverlauf

## 1.1.1-beta.1

- Vorabversion zum Praxistest; kein Merge in den stabilen `main`-Branch.
- Ein heute ausreichendes Kalibrierfenster wird unabhängig davon erkannt, ob
  der Speicher bereits 13 % erreicht hat, und während der Vorbereitung neu
  bewertet.
- Die benötigte Ladedauer wird sekundengenau statt auf den nächsten
  15-Minuten-Schritt aufgerundet geprüft.
- Testablauf nach Marstek-Empfehlung: bis 13 % entladen, 90 Minuten untere
  Ruhephase, mit der eingestellten Kalibrierleistung laden und anschließend
  90 Minuten obere Ruhephase. In beiden Ruhephasen sind Laden und Entladen
  gesperrt.

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
