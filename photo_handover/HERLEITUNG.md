# Hasenheide 1 — Herleitung der Angaben

Belege für die Zuordnungen in `README.md`, `serien.csv` und `positionen.csv` sowie Abweichungen zwischen Labbook
(OneNote: Chronik je Versuch, Versuchsanordnung je Woche), EXIF der Bilder und Ablage. Bei Abweichungen gilt EXIF.

## Kameras

- **J4 = Ordner `100CANON`** (Hep_160_S2_R2, 10.12. V1): Der Bildausschnitt ist derselbe wie bei C1 an L1 (02.12. und
  11.12.); laut Chronik stand dort am 10.12. V1 nur J4. Einstellungen F14, 1/500 s wie in der Chronik; erstes Bild
  11:32:16, Chronik „Ledsa Jülich ein“ 11:32:18. Seriennummer 233024001950. Aufnahme in Bündeln von ~8 Bildern im Abstand 0,14 s etwa alle 3 s (2570 Bilder in 1272 s).
  Die Chronik nennt eine „Dreifachaufzeichnung mit verschiedener Blende“; in EXIF haben alle Bilder F14, 1/500 s.
- **J3 = Ordner `FZJ`** (09.12.): Auszug aus der J3-Tagesserie je Lauf; Intervall unregelmäßig (im Mittel je Serie
  3,4–4,0 s), Weißabgleich automatisch.

## Positionen

- Labbook-Schreibweise U = unten, O = oben; Paper und Grundriss L = lower, U = upper.
- **L1/L2:** Woche 1 nennt sie L1 (Flur) und L2 (F3), die Versuchsanordnung der Woche 2 und die Chronik 08.–10.12. L2
  und L3, die Chronik am 11.12. wieder „L1“ für C1 (aber „L3“ für N1). Die Koordinaten sind in beiden Wochen gleich.
  Über die Bildausschnitte belegt: C1 am 02.12. („L1“), C1 am 11.12. („L1“) und J4 am 10.12. („L2“) sehen dieselbe Szene,
  ebenso N1 in Woche 1 („L2“) und Woche 2 („L3“). Hier daher einheitlich L1/L2.
- Bisherige Auswertungen setzen die Kamera meist auf die Scheibe (x = 0): die H1-LEDSA-Dokumentation bei BCL, die
  BCL-Einzelauswertung und der FDS-Zwilling; die Stapel-Konfigurationen des LEDSA-Papers mischen x = 0 und Labbook-x
  (README, „Bezug zum LEDSA-Paper“). Die Labbook-Lage (x < 0) mit `pane_distance` ist genauer und hier maßgeblich.
  In älteren Auswertungsdateien ist die x-Koordinate von F1U/F1L teils vertauscht geführt (−0,232 gegen −0,058).
- Die LED-Streifen enden laut Labbook bei z = 0,055 m (BCL) bzw. 0,1 m (Jülich) und 2,535 m; Paper, FDS-Zwilling,
  Grundriss und die bisherigen Auswertungen nehmen vereinfacht 0–2,5 m.
- LED 1 lag in Woche 1 bei x/y = 4,15/3,45 m, in Woche 2 bei 4,162/3,464 m; LED 2–4 unverändert.

## Belegung und Belichtung je Tag (Labbook; EXIF-Abweichungen rechts)

| Zeitraum | C1 | C2 | C3 | N1 | S1 | weitere | EXIF ≠ Labbook |
|---|---|---|---|---|---|---|---|
| 01.12. (Vorversuch) | – | – | – | – | – | Ordner `C1` = M50 mit Seriennr. von C2, F6.3, 1/1600, Autofokus, Weißabgleich automatisch | – |
| 02.12. | F18 1/640 | F18 1/500 | F18 1/400 | F29 1/250 | F16 1/400 | – | – |
| 03.–04.12. | F18 1/640 | F18 1/500 | F18 1/500 | F29 1/320 | F16 1/400 | – | C3 am 04.12.: 1/400 |
| 08.12. | F3U, F18 1/320 | F1U, F16 1/400 | F2U, F18 1/500 | L3, F29 1/320 | – | J1–J3, J4 | C3: 1/400 |
| 09.12. | F2U, F18 1/320 | – | – | – | – | J1–J3 (J3 = `FZJ`, F16 1/160) | J3 bei Hep_160_S2_R1: 1/125 |
| 10.12. V1–V2 | F2U, F18 1/400 | F1U, F16 1/400 | F3U, F18 1/800 | L3, F29 1/320 | – | J1–J4 (J4 F14 1/500) | – |
| 10.12. V3–V4 | F2O, 1/400 | F1U, 1/400 | F3U, 1/800 | L3 | – | J nicht aktiv | – |
| 10.12. V5–V6 | F2O, 1/400 | F2U, F16 1/640 | – | – | – | J nicht aktiv | – |
| 11.12. (PUR) | L1, F18 1/500 | F1U, F18 1/400 | F2O, F18 1/500 | L3, F29 1/320 | – | – | N1: F20 statt F29 |

Positionen in Labbook-Schreibweise. ISO 100 und manueller Weißabgleich bei C1–C3, N1, S1; Fokus manuell ab 02.12. V2.
Aufnahmeintervall 5 s bei den BCL-Kameras.

## Zeitbasis

Ein Abgleich der Kamerauhren gegen die Messdaten-Zeit ist nicht dokumentiert. Stichproben (Labbook-Ereignisse „Kamera
aus/ein“ gegen letztes/erstes Bild) ergeben −2,5 bis −14 s; das schließt einen Uhrversatz von einigen Sekunden nicht aus,
belegt ihn aber auch nicht.

## Ablage: Bereinigung und Fehler in der Quelle

1. `Hep_160_S3_R1/3_LEDSA/251210_V_01_C2` ist eine bytegleiche Kopie des C2-Ordners von Hep_160_S2_R2 (341 Bilder,
   gleiche Namen und Größen, EXIF 10.12. 11:31–11:59 = Lauf Hep_160_S2_R2) und wurde nicht übernommen. Die echten
   C2-Bilder von Hep_160_S3_R1 sind nicht mehr auffindbar.
2. `Hep_160_S2_R2/3_LEDSA/N1/IMG_*.NEF` (369 Dateien) sind umbenannte Kopien der Originale in `N1/Original/` (Größe und
   Zeitstempel je Paar gleich, Stichproben bytegleich) und wurden nicht übernommen; alle 401 Originale und das Log
   `2025_12_16_11_08_53_IMG_rename_log.csv` (DSC → IMG) sind dabei.
