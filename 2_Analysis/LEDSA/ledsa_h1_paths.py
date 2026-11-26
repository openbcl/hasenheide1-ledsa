# -*- coding: utf-8 -*-
"""Pfade ausserhalb des Repos (METHODS.md section 2).

setup/ledsa_h1_series.csv (Spalte folder_w) und die config.ini unter runs/ schreiben die Bildordner mit dem Platzhalter
<H1_IMAGES_ROOT>; img_path ersetzt ihn beim Lesen durch die Umgebungsvariable H1_IMAGES_ROOT (Wurzel des
Rohbildbaums, nicht im Repo). need_env liest eine Pflicht-Umgebungsvariable fuer Daten ausserhalb des Repos.
"""
import os

IMG_TOKEN = "<H1_IMAGES_ROOT>"


def need_env(name, what):
    v = os.environ.get(name)
    if not v:
        raise SystemExit(f"[--] {name} nicht gesetzt ({what}; nicht in diesem Repo)")
    return v


def img_path(p):
    """Bildordner/-datei mit Platzhalter -> Pfad unter H1_IMAGES_ROOT (Pfade ohne Platzhalter unveraendert)."""
    s = str(p)
    if IMG_TOKEN not in s:
        return s
    return s.replace(IMG_TOKEN, need_env("H1_IMAGES_ROOT", "Wurzel des Rohbildbaums").rstrip("\\/"))
