"""Paper style for Matplotlib figures that go into a fire_preprint manuscript.

* Text is rendered by LaTeX (``text.usetex``) with ``preamble.tex``, which loads
  the same fonts and siunitx conventions as the document class, so figure text
  matches the body text.
* Figure PDFs are byte-deterministic: re-running an unchanged script yields an
  identical file (no spurious git diffs, verifiable reproduction).
* Without a LaTeX installation the style falls back to a mathtext look-alike
  instead of failing.

Typical use::

    import fireplot as fp

    with fp.paper_style():
        fig, ax = plt.subplots(figsize=fp.figsize_single(0.6))
        ...
        fp.save_pdf(fig, "manuscript/figures/example")
"""
from __future__ import annotations

import hashlib
import os
import shutil
import string
from contextlib import contextmanager
from pathlib import Path

import matplotlib as mpl

# ---------------------------------------------------------------------------
# Deterministic PDF output
# ---------------------------------------------------------------------------
# Matplotlib stamps each PDF with a wall-clock /CreationDate and derives the
# trailer /ID from it, so re-running a script yields byte-different PDFs even
# when the content is identical. A fixed SOURCE_DATE_EPOCH makes both
# deterministic. Set at import time, before any savefig, and only if the caller
# has not pinned it already. 1136073600 = 2006-01-01 UTC (arbitrary fixed
# instant). pdfTeX honours the same variable, but for /CreationDate and the
# trailer /ID only when FORCE_SOURCE_DATE=1 is set as well.
REPRO_EPOCH = "1136073600"
os.environ.setdefault("SOURCE_DATE_EPOCH", REPRO_EPOCH)
os.environ.setdefault("FORCE_SOURCE_DATE", "1")


def _stable_subset_prefix(charset) -> str:
    """Deterministic replacement for ``PdfFile._get_subset_prefix``.

    Matplotlib 3.11 derives the six-letter font-subset tag from Python's
    ``hash()`` of a frozenset of the subset's glyphs. That hash is randomised
    per process (PYTHONHASHSEED), so every run wrote a different tag (e.g.
    ``NLGHQA+NewTXMI`` vs ``SHLMKY+NewTXMI``) and a byte-different PDF. Here
    the tag is a SHA-1 of the sorted glyphs. The tag is only an identifier (PDF
    Reference, 5.5.3); rendering is unchanged.
    """
    n = int.from_bytes(
        hashlib.sha1(repr(sorted(map(repr, charset))).encode()).digest()[:8], "big")
    out = ""
    for _ in range(6):
        n, r = divmod(n, 26)
        out += string.ascii_uppercase[r]
    return out + "+"


try:
    from matplotlib.backends.backend_pdf import PdfFile as _PdfFile
    # Only present (and only needed) from Matplotlib 3.11 on. 3.10.8 tags
    # subsets differently and was byte-deterministic across hash seeds in
    # scripts/check_figure_repro.py without this patch.
    if hasattr(_PdfFile, "_get_subset_prefix"):
        _PdfFile._get_subset_prefix = staticmethod(_stable_subset_prefix)
except ImportError:  # pragma: no cover - PDF backend unavailable
    pass


# ---------------------------------------------------------------------------
# Figure size
# ---------------------------------------------------------------------------
# \textwidth of fire_preprint.cls: A4 (210 mm) minus 2 x 30 mm margins. Check
# with \printlength{\textwidth} in the document; change both together.
COLUMN_WIDTH_MM = 150.0
MM_TO_INCH = 1.0 / 25.4

# Body text size of fire_preprint.cls (\LoadClass[12pt]{article}). All figure
# text (axis labels, tick labels, legend, annotations) uses this size, so a
# figure included at its natural width reads like the text around it. Change
# both together.
TEXT_FONT_SIZE_PT = 12.0


def figsize_single(aspect: float = 0.62, width_mm: float | None = None) -> tuple[float, float]:
    """(width, height) in inches for a figure as wide as the text column.

    aspect = height / width. Include the figure with
    ``\\includegraphics{...}`` at its natural size (no ``width=`` scaling), so
    the figure text keeps the body-text size (TEXT_FONT_SIZE_PT) in print.
    """
    width_in = (COLUMN_WIDTH_MM if width_mm is None else width_mm) * MM_TO_INCH
    return width_in, width_in * aspect


# ---------------------------------------------------------------------------
# rcParams
# ---------------------------------------------------------------------------
PREAMBLE = Path(__file__).resolve().parent / "preamble.tex"

_COMMON_RC = {
    "lines.linewidth": 1.2,
    "lines.markersize": 4.0,
    "axes.linewidth": 0.8,
    "xtick.direction": "in",
    "ytick.direction": "in",
    "xtick.minor.visible": True,
    "ytick.minor.visible": True,
    "xtick.major.size": 3.0,
    "ytick.major.size": 3.0,
    "xtick.minor.size": 1.5,
    "ytick.minor.size": 1.5,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.02,
    # embed TrueType as Type 42 (text stays text) where usetex is not used
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
}


def _font_sizes(font_size: float) -> dict:
    return {
        "font.size": font_size,
        "axes.labelsize": font_size,
        "axes.titlesize": font_size,
        "legend.fontsize": font_size,
        "xtick.labelsize": font_size,
        "ytick.labelsize": font_size,
    }


def set_plot_style(*, preamble_path: str | Path | None = None,
                   font_size: float = TEXT_FONT_SIZE_PT, dpi: int = 300) -> None:
    """Global paper style with LaTeX text rendering. Call before creating figures.

    Prefer the ``paper_style()`` context manager, which restores the previous
    rcParams afterwards.
    """
    preamble = Path(preamble_path or PREAMBLE).read_text(encoding="utf-8")
    mpl.rcParams.update({
        "text.usetex": True,
        "text.latex.preamble": preamble,
        "font.family": "serif",
        **_font_sizes(font_size),
        **_COMMON_RC,
        "figure.dpi": dpi,
        "savefig.dpi": dpi,
    })


def apply_style(font_size: float = TEXT_FONT_SIZE_PT, dpi: int = 300) -> None:
    """The paper style WITHOUT LaTeX (mathtext, STIX serif): the fallback.

    Label strings written for usetex render here too as long as they follow the
    conventions in docs/plotstyle.md ($...$ for maths, no \\si, no Unicode).
    """
    mpl.rcParams.update({
        "text.usetex": False,
        "font.family": "STIXGeneral",
        "mathtext.fontset": "stix",
        **_font_sizes(font_size),
        **_COMMON_RC,
        "figure.dpi": dpi,
        "savefig.dpi": dpi,
    })


def latex_available() -> bool:
    """True if the tools Matplotlib's usetex needs are on PATH."""
    return bool(shutil.which("latex") and shutil.which("dvipng"))


@contextmanager
def paper_style(font_size: float = TEXT_FONT_SIZE_PT, *, preamble_path: str | Path | None = None,
                require_latex: bool = False):
    """Apply the paper style inside the ``with`` block only; yields True if LaTeX renders.

    Create AND save the figure inside the block. Scoping matters when several
    plotting modules run in one process: a globally set usetex would otherwise
    leak into figures that do not expect it.

    Without LaTeX, falls back to ``apply_style()`` with a warning, or raises if
    ``require_latex`` is set (use that for figures that go into the manuscript).
    """
    with mpl.rc_context():
        if latex_available():
            set_plot_style(preamble_path=preamble_path, font_size=font_size)
        elif require_latex:
            raise RuntimeError("paper_style(require_latex=True): latex/dvipng not on PATH")
        else:
            print("[fireplot] WARNING: no LaTeX found; using the mathtext fallback style")
            apply_style(font_size=font_size)
        yield bool(mpl.rcParams["text.usetex"])


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------
_TEX_ESCAPES = {
    "\\": r"\textbackslash{}",
    "_": r"\_",
    "%": r"\%",
    "&": r"\&",
    "#": r"\#",
    "$": r"\$",
    "{": r"\{",
    "}": r"\}",
    "^": r"\^{}",
    "~": r"\~{}",
}


def tex(s: str) -> str:
    """Free text (file names, IDs, legend entries from data) for a label.

    Under usetex (the current ``text.usetex`` setting), LaTeX special
    characters are escaped in a single pass; without LaTeX the string is
    returned unchanged. Call it where the style is active (inside
    ``paper_style()``). Do not pass maths through this function: write maths as
    ``$...$`` directly.
    """
    if not mpl.rcParams["text.usetex"]:
        return s
    return "".join(_TEX_ESCAPES.get(c, c) for c in s)


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------
def lint_figure(fig) -> list[str]:
    """Violations of the figure conventions (docs/plotstyle.md) in ``fig``.

    Checks: no axes titles or suptitle (the caption carries that information),
    ASCII-only text, no siunitx commands in labels, axis labels of the form
    "Quantity / unit".
    """
    issues = []
    if fig.get_suptitle():
        issues.append(f"suptitle {fig.get_suptitle()!r}: put it in the caption")
    # Tick labels are generated by Matplotlib (e.g. a Unicode minus in the
    # fallback style) and are not checked.
    ticks = set()
    for ax in fig.axes:
        for axis in (ax.xaxis, ax.yaxis):
            for tick in axis.get_major_ticks() + axis.get_minor_ticks():
                ticks.update((id(tick.label1), id(tick.label2)))
    for i, ax in enumerate(fig.axes):
        for loc in ("left", "center", "right"):
            if ax.get_title(loc):
                issues.append(f"axes {i}: title {ax.get_title(loc)!r}: put it in the caption")
        for which, label in (("x", ax.get_xlabel()), ("y", ax.get_ylabel())):
            if label and " / " not in label:
                issues.append(f"axes {i}: {which} label {label!r} is not 'Quantity / unit'")
    for t in fig.findobj(mpl.text.Text):
        s = t.get_text()
        if not s or id(t) in ticks:
            continue
        if any(ord(c) > 127 for c in s):
            issues.append(f"non-ASCII text {s!r}: use LaTeX/mathtext commands")
        if "\\si" in s or "\\SI" in s or "\\qty" in s or "\\unit" in s:
            issues.append(f"siunitx command in {s!r}: write plain units")
    return issues


def save_pdf(fig, stem: str | Path, *, lint: bool = True) -> Path:
    """Save ``fig`` as ``<stem>.pdf`` (directories created as needed).

    With ``lint`` (default) the figure is checked against the conventions first
    and a ValueError lists every violation.
    """
    if lint:
        issues = lint_figure(fig)
        if issues:
            raise ValueError("figure violates the conventions:\n  " + "\n  ".join(issues))
    stem = Path(stem)
    stem.parent.mkdir(parents=True, exist_ok=True)
    out = stem.with_suffix(".pdf")
    fig.savefig(out)
    return out
