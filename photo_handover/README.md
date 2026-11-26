# Hasenheide 1 — LEDSA-Fotos

Rohbilder der kamerabasierten LED-Extinktionsmessung (LEDSA) aus der Brandversuchskampagne **Hasenheide 1**
(02.–11.12.2025, dazu ein Vorversuch am 01.12.2025) im Versuchsobjekt Hasenheide (Leipzig-Mölkau). Bereitgestellt von
BCL (Kontakt: Manuel Osburg) an Kristian Börger zur weiteren Verwendung für gemeinsame Veröffentlichungen.

**Inhalt:** 43627 RAW-Bilder in 100 Serien aus 31 Läufen (25032 CR3, 10293 NEF, 5732 ARW, 2570 CR2),
dazu im Ordner `FZJ` je Bild ein JPG. Originaldateien, unbearbeitet, aus
`W:\Versuche\2025\25-G-0161 - Hasenheide\06_Versuchsdoku\1_Measurements\<Lauf>\3_LEDSA\`.

**Nicht enthalten:** die Jülich-Tagesserien J1–J3 (liegen Kristian Börger bereits vor; aus J3 ist nur der Auszug `FZJ`
dabei), abgebrochene Serien und Videos. Die Läufe Ethyl_295_oil_open_R2 und
Ethyl_295_zero_open_R2 haben keine LEDSA-Aufnahmen.

## Dateien

| Datei | Inhalt |
|---|---|
| `<Lauf>/3_LEDSA/<Serienordner>/` | Bilder |
| `serien.csv` | je Serie: Lauf, Zündzeit, Kamera, Position, Bildzahl, erstes/letztes Bild, Beginn/Ende relativ zur Zündung, Intervall (Median ganzer Sekunden und Mittel), Belichtung, Lücken > 30 s, Bemerkung |
| `positionen.csv` | Kamerapositionen je Versuchswoche (x/y/z laut Labbook, `pane_distance`; dazu x in Paper/FDS) |
| `led_streifen.csv` | LED-Streifen (Lage, Höhe laut Labbook und in Paper/FDS, Farbe) |
| `configs/<Lauf>/<Serienordner>/` | LEDSA-0.13.0-Vorlage (`config.ini`, `config_analysis.ini`) je Serie; Kantenindizes nach der LED-Suche eintragen |
| `LEDSA_Floorplan.pdf`, `LEDSA_Section.pdf` | Grundriss und Schnitt mit Kameras und LED-Streifen |
| `HERLEITUNG.md` | Belege für Zuordnungen und Abweichungen zwischen Labbook, EXIF und Ablage |
| `dateiliste.tsv`, `SHA256SUMS.txt` | Pfad, Größe, Änderungszeit und SHA-256 jeder Bilddatei |

## Namen

- **Lauf:** `Ethyl_<Wanne>_<Nebel>_<Tür>_R<n>` (Ethanol, 500 g; Nebel `glycol` = Glykolnebel, `oil` = Weißölnebel, `zero` =
  ohne; Tür `open`/`closed` = Eingangstür des Versuchsobjekts), `Isoprop_220_R<n>` (Isopropanol, 500 g),
  `Hep_<Wanne>_S<n>_R<n>` (C7-UVCB-Heptangemisch; Hep_220_S1 300 g, Hep_160_S1 150 g, Hep_160_S2–S4 75 g; S = Serie mit
  eigener Messgeräte-Konfiguration), `PUR_R<n>` (Polyurethan, rund 300 mm, 95 g, mit Ethanol angezündet).
  Wanne = Kantenlänge der quadratischen Wanne in mm; `Ethyl_350` = rund, 350 mm (Vorversuch). R = Wiederholung.
- **Serienordner** meist `JJMMTT_V<n>_<Kamera>` oder `JJMMTT_V_0<n>_<Kamera>` (V = Versuchsnummer des Tages); dazu
  Schreibweisen wie `25-12-09_V2_C1`, `25-12-09V4_C1`, `25-12-09V5C1`, `251208_C1_V3`, `251208_C3_V3` und Ordner ohne
  Datum (`C1`, `N1`, `FZJ`, `100CANON`).
- **Räume:** F1 = Brandraum, F2, FC = Flur, F3 (Grundriss).

## Kameras

| Kürzel | Modell | Seriennr. (EXIF) | Format | Hinweis |
|---|---|---|---|---|
| C1 | Canon EOS R50 | 253030005587 | CR3 | BCL |
| C2 | Canon EOS M50 | 103030012246 | CR3 | BCL |
| C3 | Canon EOS M50 | 703045005027 | CR3 | BCL |
| N1 | Nikon D610 | – | NEF | BCL |
| S1 | Sony ILCE-7M3 | – | ARW | nur 02.–04.12. |
| J3 | Canon EOS R7 | 363034002727 | CR3 + JPG | Jülich; Ordner `FZJ` = Auszug aus der J3-Tagesserie (09.12.) |
| J4 | Canon EOS 80D | 233024001950 | CR2 | Jülich; Ordner `100CANON`, nur Hep_160_S2_R2 |

Dieselben BCL-Kameras C1, C2, C3 und N1 heißen in Hasenheide 2.0 B1–B4. Belichtung je Serie in `serien.csv` (aus EXIF).

## Positionen

**Bezeichnung:** Im Labbook heißt `U` = unten und `O` = oben, im LEDSA-Paper, im Grundriss und in dieser README
`L` = lower und `U` = upper (Labbook-F1U = F1L, Labbook-F1O = F1U). `serien.csv` und `positionen.csv` nennen beide.
Die Positionen mit langer Sichtachse heißen hier einheitlich L1 (Flur FC) und L2 (F3); das Labbook nennt sie in
Woche 2 L2/L3 (Belege in `HERLEITUNG.md`).

- **F-Positionen** (F1U/F1L, F2U/F2L, F3U/F3L): Kamera im Flur hinter einer Glasscheibe in einer Kernbohrung der
  Flurwand, Blick quer durch den Raum auf die LED-Streifen an der Fensterwand. Maßgeblich sind die Koordinaten laut
  Labbook (`x_m` < 0, Kamera hinter der Scheibe; die Scheibe liegt bei x = 0) mit `pane_distance_m`. Das LEDSA-Paper,
  sein FDS-Zwilling und der Grundriss setzen die Kamera vereinfacht auf die Scheibe (`x_paper_fds_m` = 0) und die
  LED-Streifen auf z = 0–2,5 m (`led_streifen.csv`, Spalten `…_paper_fds_m`).
- **L-Positionen** (L1, L2): Kamera im Gebäude, Blick entlang des Gebäudes auf LED 2 und LED 4. N1 stand laut Chronik
  (08.12.) in einem Schutzkasten.
- Die Lagen wechseln zwischen Woche 1 (02.–04.12.) und Woche 2 (ab 08.12.); maßgeblich ist die Spalte `woche` in
  `positionen.csv`. Koordinaten in m: Ursprung an der Marke 0,0,0 im Grundriss (Innenecke F1 an der Flurwand),
  x quer zum Gebäude Richtung Fenster, y entlang des Gebäudes Richtung F3, z über Boden.

## Zeit

- Zeitnullpunkt = `serien.csv`, Spalte `zuendung`: Startzeit der Messdaten (volle Minute, `experiment_metadata.txt`),
  wie in den Messdaten und im LEDSA-Paper. Die genaue Zündung (DEWESoft-Ereignis, ms, identisch mit dem Labbook-Ablauf)
  liegt 0,1–2,8 s später (Spalte `zuendung_genau`). `beginn_s`/`ende_s` = erstes/letztes Bild relativ zu `zuendung`,
  aus der EXIF-Zeit.
- Die EXIF-Zeit ist Ortszeit. Ein Abgleich der Kamerauhren ist für Hasenheide 1 **nicht dokumentiert**; Stichproben
  (Labbook-Ereignisse „Kamera aus/ein“ gegen letztes/erstes Bild) weichen um 2,5–14 s ab, ein belastbarer Uhrversatz
  folgt daraus nicht.
- Bilder immer nach EXIF-Zeit ordnen, nicht nach Dateinamen (Zählerüberläufe).

## Hinweise für die LEDSA-Auswertung

- **Vorlagen:** `configs/<Lauf>/<Serienordner>/` enthält je Serie eine LEDSA-0.13.0-Vorlage mit den Fakten dieser
  README (Bildordner relativ, Bildfolge, Zeit, Streifen mit Kantenkoordinaten, Kameralage, `pane_distance`). Die
  Kantenindizes (`led_array_edge_indices`) hängen von der LED-Suche ab und sind leer: nach `ledsa -s1` die IDs der
  obersten/untersten LED je Streifen eintragen; die Streifen in der Reihenfolge der Koordinaten. Auswerteparameter
  (Referenzbild, Perzentil, Radius, Inversion) sind Startwerte, keine geprüfte Auswertung.
- **Kamera und Scheibe:** `camera_position` = `x_m`/`y_m`/`z_m` aus `positionen.csv`. Zwischen Kamera und Scheibe ist
  kein Rauch: `pane_distance` (LEDSA ≥ 0.13) = Weg von der Kamera bis zur Scheibe entlang des Sichtstrahls; er hängt
  von der LED-Höhe ab (`pane_distance_min_m`–`pane_distance_max_m`, z. B. F1U Woche 2 0,241–0,264 m,
  F1L Woche 2 0,060–0,064 m); LEDSA nimmt einen Wert je Kamera (`pane_distance_m` = Mitte).
- **LED-Streifen:** senkrecht, Enden laut Labbook z = 0,055 m (BCL) bzw. 0,1 m (Jülich) bis 2,535 m (`led_streifen.csv`).
  Für `led_array_edge_coordinates` die jeweils im Bild sichtbaren End-LEDs verwenden; sind Streifenenden verdeckt,
  liegen diese innerhalb der Streifenenden. Farbe → Kanal: rot 0, grün 1, blau 2.
- **Zeit:** `start_time` = Spalte `zuendung`; `exif_time_infront_real_time` = 0 (Uhrversatz unbekannt, s. o.);
  `time_ref_img_*` leer lassen (sonst rechnet LEDSA 0.13 einen Versatz aus Referenzbild und -zeit).
- **Ausschlüsse:** Lücken und Ausfälle stehen je Serie in `luecken_ueber_30s` und `bemerkung`. Die Bildinhalte
  (verdeckte LEDs, Personen im Bild) sind für diese Übersicht nicht geprüft.

## Bekannte Mängel

- **Fehlende Serien** trotz Eintrag im Labbook: C1 bei Hep_220_S1_R4 und C2 bei Hep_160_S3_R1 (nicht mehr auffindbar),
  C2 bei PUR_R1 (kein Ordner), C3 bei Ethyl_295_zero_open_R1 (Ordner leer).
- **Vorzeitige Enden und Ausfälle:** z. B. C1 Ethyl_220_glycol_closed_R3 ab +126 s, C2 Hep_220_S1_R2 ab +1196 s (Akku leer),
  N1 PUR_R3 ab +527 s; alle in `serien.csv`.
- **Gegenüber der Quelle nicht übernommen:** der Ordner `Hep_160_S3_R1/3_LEDSA/251210_V_01_C2` (bytegleiche Kopie des
  C2-Ordners von Hep_160_S2_R2) und in `Hep_160_S2_R2/3_LEDSA/N1` 369 umbenannte Kopien `IMG_*.NEF` der Originale in
  `N1/Original/` (Details in `HERLEITUNG.md`).

## Bezug zum LEDSA-Paper

- Laufnamen im Paper: Hep_160_075 = Hep_160_S2–S4 (75 g), Hep_160_150 = Hep_160_S1 (150 g), Hep_220_300 = Hep_220_S1
  (300 g).
- Gestapelt ausgewertet (LEDSA v0.10.0, Konfigurationen von Kristian Börger): Hep_160_S2_R2 (F1, F2, F3), Hep_160_S2_R3
  (F2, F3), Hep_160_S4_R1 (F2) und Hep_160_S4_R2 (F2). Die unteren Kameras von S2_R2/R3 (C1–C3) und beide Kameras der
  S4-Läufe (C1 an F2U, C2 an F2L) sind auf dieser Platte; die oberen Kameras von S2_R2/R3 (J1–J3, F3U/F2U/F1U) gehören
  zu den Jülich-Tagesserien.
- Parameter dort: `camera_channels` 0 1 2 (Streifen in der Reihenfolge rot, grün, blau), linearer Löser, λ 0,5,
  25 Schichten über 0–2,5 m, 10 Referenzbilder, `time_sync_tolerance` 3 s, `reference_property` `sum_col_val`,
  `start_time` = volle Minute.
- Koordinaten dort vereinfacht: LED-Streifen z = 0–2,5 m; untere Kameras auf der Scheibe (x = 0), obere Kameras von
  S2_R2/R3 mit Labbook-x (F2U −0,26, F3U −0,243; F1U mit x/y = −0,058/2,06 von F1L und z von F1U), in S4 beide x = 0.
  Maßgeblich für diese Weitergabe ist das Labbook (`positionen.csv`).
- In der Paper-Auswertung ist F2U bei Hep_160_S4_R2 um +11 s verschoben, damit beide Kameras gleichzeitig beginnen; laut
  EXIF startet C1 (F2U) 11 s vor C2 (F2L). Ein Uhrversatz ist nicht belegt (s. Zeit).

## Veröffentlichungen

- Osburg et al., „Measuring and Modelling Smoke Light Extinction in Well-Ventilated, Multi-Room Compartment Fires:
  Co-located Transmissometry and A-priori FDS Validation“, Fire Safety Journal,
  https://doi.org/10.1016/j.firesaf.2026.104997 — Versuche, Messdaten und FDS dieser Kampagne (ohne LEDSA-Auswertung).
  Reproduktionspaket (Code, reduzierte Daten, FDS-Eingaben, ohne Bilder): https://doi.org/10.5281/zenodo.24054120.
- LEDSA-Paper zu dieser Kampagne (Osburg, Troff, Lange, Börger, Arnold), in Vorbereitung.
- LEDSA-Methode: Arnold et al. 2021, Fire and Materials, doi:10.1002/fam.2841; Börger et al. 2023, Fire Safety Journal,
  doi:10.1016/j.firesaf.2023.103929; Börger et al. 2024, Fire Technology, doi:10.1007/s10694-023-01470-z.

## Prüfsummen

`SHA256SUMS.txt` im `sha256sum`-Format (Prüfung in diesem Ordner: `sha256sum -c SHA256SUMS.txt`). Die Prüfsummen wurden
beim Lesen der Quelle berechnet; die Platte wurde nach dem Kopieren vollständig zurückgelesen und stimmt damit überein.
