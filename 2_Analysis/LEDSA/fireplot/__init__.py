"""fireplot: Matplotlib paper style for fire_preprint manuscripts.

Importing the package pins SOURCE_DATE_EPOCH (deterministic PDFs); see style.py.
"""
from .series import SeriesScheme, series_style
from .style import (COLUMN_WIDTH_MM, PREAMBLE, TEXT_FONT_SIZE_PT, apply_style,
                    figsize_single, latex_available, lint_figure, paper_style,
                    save_pdf, set_plot_style, tex)

__all__ = [
    "COLUMN_WIDTH_MM", "PREAMBLE", "SeriesScheme", "TEXT_FONT_SIZE_PT",
    "apply_style", "figsize_single",
    "latex_available", "lint_figure", "paper_style", "save_pdf", "series_style",
    "set_plot_style", "tex",
]
__version__ = "1.0.0"
