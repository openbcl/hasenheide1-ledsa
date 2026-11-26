"""Consistent series styles across all figures of a paper.

Colour encodes the group (e.g. configuration, material, specimen), marker and
line style encode the subgroup (e.g. load level, repeat). Define ONE scheme per
project and use it in every figure, so the same series looks the same
everywhere::

    SCHEME = SeriesScheme(
        group_colors={"A": "C0", "B": "C1", "C": "C2"},
        subgroup_markers={"low": "o", "high": "s"},
        subgroup_linestyles={"low": "--", "high": "-"},
        group_labels={"A": "Configuration A"},
    )
    ax.plot(t, y, **SCHEME.style("A", "low"))

Unknown keys raise KeyError instead of falling back to a default: a silent
default is how two figures end up disagreeing about a series.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Mapping


def _default_label(group: str, subgroup: str | None) -> str:
    return group if subgroup is None else f"{group}, {subgroup}"


@dataclass(frozen=True)
class SeriesScheme:
    group_colors: Mapping[str, str]
    subgroup_markers: Mapping[str, str] = field(default_factory=dict)
    subgroup_linestyles: Mapping[str, str] = field(default_factory=dict)
    group_labels: Mapping[str, str] = field(default_factory=dict)
    subgroup_labels: Mapping[str, str] = field(default_factory=dict)
    label_format: Callable[[str, str | None], str] = _default_label

    def style(self, group: str, subgroup: str | None = None) -> dict:
        """Keyword arguments for ``ax.plot``: color, marker, linestyle, label."""
        kw = {"color": self.group_colors[group]}
        if subgroup is not None:
            if self.subgroup_markers:
                kw["marker"] = self.subgroup_markers[subgroup]
            if self.subgroup_linestyles:
                kw["linestyle"] = self.subgroup_linestyles[subgroup]
        kw["label"] = self.label_format(
            self.group_labels.get(group, group),
            None if subgroup is None else self.subgroup_labels.get(subgroup, subgroup))
        return kw


def series_style(scheme: SeriesScheme, group: str, subgroup: str | None = None) -> dict:
    """Functional form of ``scheme.style(group, subgroup)``."""
    return scheme.style(group, subgroup)
