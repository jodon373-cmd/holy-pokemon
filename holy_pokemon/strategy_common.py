"""Shared identity, key normalization, and deterministic CSV export helpers."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterable, Mapping, Any

PHYSICAL_FIELDS = ("year", "set_name", "card_number", "card_name", "edition", "finish", "language")


def physical_key(row: Mapping[str, Any]) -> tuple[str, ...]:
    return tuple(str(row.get(k, "")).strip().lower() for k in PHYSICAL_FIELDS)


def slab_key(row: Mapping[str, Any]) -> tuple[str, ...]:
    return (
        str(row.get("grader", "")).upper(),
        str(row.get("grade", "")),
        str(row.get("slab_generation", "unknown")),
        str(row.get("grade_designation", "unknown")),
    )


def export_csv(path: str | Path, rows: Iterable[Mapping[str, Any]], fields: Iterable[str] = ()) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    row_list = list(rows)
    columns = list(dict.fromkeys([*fields, *(key for row in row_list for key in row)]))
    if not columns:
        columns = ["status", "data_requirement"]
    with out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        for row in row_list:
            writer.writerow({
                k: json.dumps(v, sort_keys=True) if isinstance(v, (list, dict, tuple)) else ("'" + v if isinstance(v, str) and v.lstrip().startswith(("=", "+", "-", "@")) else v)
                for k, v in row.items()
            })
    return out
