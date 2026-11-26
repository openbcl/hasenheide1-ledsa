# Software environments

Two Python environments were used (Windows 11, Git Bash for the shell scripts in `2_Analysis/LEDSA/tools/`).

| Environment | Used for | Python | File |
|---|---|---|---|
| LEDSA environment (conda) | LEDSA itself (`python -m ledsa ...`) and the scripts that call LEDSA or read raw images in this environment (`ledsa_h1_config.py`, `ledsa_h1_s1scan.py`, `ledsa_h1_probe.py`, `ledsa_h1_track.py`; `ledsa_h1_noise.py` with rawpy) | 3.12.14 | `requirements-ledsa-env.txt` (`pip freeze`) |
| Analysis environment (venv) | post-processing, result tables and figures (`ledsa_h1_profiles.py`, `ledsa_h1_stage4.py`, `checks/*.py`), the setup and mask scripts (`ledsa_h1_setup.py`, `ledsa_h1_ledz.py`, `ledsa_h1_mask.py`), `ledsa_h1_stage0.py`, the stage-2 checks (`tools/stage2_check.py`, `tools/stage2_order.py`, `tools/stage2_trackcheck.py`), the drift checks that read raw images with `rawpy` (`ledsa_h1_drift*.py`, `tools/drift_regions.py`) and `tools/plot_drift.py` | 3.12.11 | `requirements-analysis.txt` (`pip freeze`) |

The environment of most scripts is named in their docstring ("hh2-venv" = the analysis environment, "Conda-Env ledsa" =
the LEDSA environment); `tools/env.sh` locates both (`LEDSA_PY`, `HH2_PY`).

**LEDSA version.** LEDSA 0.13.0, tag `v0.13.0` of
[FireDynamics/LEDSmokeAnalysis](https://github.com/FireDynamics/LEDSmokeAnalysis), commit
`8555ca074816d070453c9fdbdd8170ec166ec503`. It was run from an exported source tree (`git archive` of the tag,
checked out with Windows line endings) that `tools/env.sh` puts on `PYTHONPATH` (variable `LEDSA_EXPORT`); `env.sh`
stops if `import ledsa` resolves to any other location. The source tree used is identical in content to the tag:
`python env/ledsa_tree_hash.py <root>` (recipe in its docstring: all files except `__pycache__/` and `*.pyc`, per
file, sorted by the bytes of the relative path, `path NUL sha256(content with CRLF -> LF) LF`; SHA-256 over all lines) gives for both the source tree used
and `git archive v0.13.0`: 117 files, `13c6a02b50a27cddbc20f1f7626ec02d6c1fb60a6e43b60db9a204d8eec8c738`
(checked on 2026-11-25).

The conda environment also contains an older pip installation of LEDSA (0.9.4) that was **not** used for computing;
it is left out of `requirements-ledsa-env.txt`. LEDSA 0.13.0 itself needs *some* installed `ledsa` distribution:
it writes `importlib.metadata.version("ledsa")` into its output headers (e.g. `ledsa/analysis/ExtinctionCoefficients.py`,
line 100), which fails with `PackageNotFoundError` if none is installed. To rebuild the LEDSA environment: conda
environment with Python 3.12.14, `pip install -r env/requirements-ledsa-env.txt`, then either
`pip install --no-deps ledsa==0.9.4` (as here; the headers then say 0.9.4) or `pip install --no-deps <tree of tag
v0.13.0>` (the headers then say 0.13.0), and put the v0.13.0 tree on `PYTHONPATH` via `LEDSA_EXPORT` as
`tools/env.sh` expects. `tools/env.sh` looks for the conda environment at
`%USERPROFILE%\.conda\envs\ledsa\python.exe` (else set `LEDSA_PY`), for the tree at `%LOCALAPPDATA%\ledsa_v0130`
(else set `LEDSA_EXPORT`) and for the analysis venv at `%LOCALAPPDATA%\hh2_analysis_venv` (else set `HH2_PY` to an absolute path, e.g.
`$PWD/.venv/Scripts/python.exe` from the repository root; the shell scripts change directory). LEDSA 0.13.0 writes the version of the *installed* package into the
header of its output files, so the k files in `runs/` say "LEDSA 0.9.4" although 0.13.0 computed them (see
`METHODS.md`, §2).

**Figures** need a LaTeX installation (`latex`, `dvipng` on `PATH`; the packages loaded by
`fireplot/preamble.tex`: inputenc, fontenc, amsmath, newtxtext, newtxmath, siunitx, mhchem, nicefrac; the figures
in this repository were made with MiKTeX 26.2: pdfTeX 4.26, dvipng 1.16, newtxtext 1.744, newtxmath 1.754), because `fireplot` renders text with LaTeX (`2_Analysis/LEDSA/fireplot/`,
see `fireplot/ORIGIN.txt`). Without LaTeX, `python ledsa_h1_profiles.py csv` still writes the tables. The figure PDFs
are byte-reproducible for a fixed toolchain (Matplotlib, TeX distribution, fonts), not across machines.
