# -*- coding: utf-8 -*-
"""Kontrollbild der Streifenenden (oben/unten je Array) im Referenzbild der LED-Suche, mit den gefundenen LEDs.
Aufruf (Conda-Env ledsa): python la_crops.py <Lauf> <Kamera> [<Bildnummer>]  -> runs/<Lauf>/<Pos>_<Kamera>/ends.png"""
import contextlib
import io
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import la  # noqa: E402
from ledsa.core.image_reading import read_img_array_from_img  # noqa: E402
from ledsa.data_extraction.step_1_functions import find_search_areas  # noqa: E402

run, cam = sys.argv[1], sys.argv[2]
r = la.series(run, cam)
w = la.windows(run, cam, need_checked=False)
img_id = int(sys.argv[3]) if len(sys.argv) > 3 else int(w.ref_s1_id.iloc[0])
path = Path(la.img_path(r.folder_w)) / r.name_string.format(img_id)
img = read_img_array_from_img(str(path), channel=0, rotation=0).astype(float)
with contextlib.redirect_stdout(io.StringIO()):
    s, _ = find_search_areas(img, int(w.radius_px.iloc[0]), float(w.percentile.iloc[0]))
import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
fig, axs = plt.subplots(1, 4, figsize=(14, 7))
H = 260
for j, q in enumerate(w.itertuples()):
    col_fit = np.polyval([q.fit_c2, q.fit_c1, q.fit_c0], s[:, 1])
    m = (s[:, 1] >= q.row0) & (s[:, 1] <= q.row1) & (np.abs(s[:, 2] - col_fit) <= q.half_width_px)
    rows = s[m, 1]
    for i, (lab, rc) in enumerate((("oben", rows.min()), ("unten", rows.max()))):
        ax = axs[2 * j + i]
        r0, r1 = int(max(rc - H, 0)), int(min(rc + H, img.shape[0]))
        c = int(np.polyval([q.fit_c2, q.fit_c1, q.fit_c0], rc))
        c0, c1 = max(c - 90, 0), min(c + 90, img.shape[1])
        sub = img[r0:r1, c0:c1]
        ax.imshow(np.log1p(np.clip(sub - np.percentile(sub, 20), 0, None)), cmap="gray", extent=(c0, c1, r1, r0))
        mm = m & (s[:, 1] >= r0) & (s[:, 1] < r1)
        ax.plot(s[mm, 2] + 12, s[mm, 1], "_", color="lime", ms=6)
        ax.set_title(f"A{q.array} {q.led} {lab}", fontsize=9)
fig.suptitle(f"{run} {cam} {path.name}", fontsize=10)
fig.tight_layout()
out = la.workdir(run, cam) / "ends.png"
fig.savefig(out, dpi=100)
print(out)
