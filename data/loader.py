"""Reads the DIN 16963 HDPE elbow workbook into plain Python data.

This is the *only* module in the whole application allowed to know about
Excel cell layout. Everything downstream (data/repository.py and beyond)
works with the dataclasses defined below, so the workbook can later be
replaced, extended with more DN/PN/angle rows, or swapped for a different
data source (CSV, database, ...) by rewriting only this file.

No catalog value (DN, R, Le, Z, thickness, SDR, ...) is hardcoded here —
everything is read from the given .xlsx file at load time.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import openpyxl
from openpyxl.worksheet.worksheet import Worksheet

SHEET_BD_CODOS = "BD_Codos"
SHEET_BD_PN = "BD_PN"
ANGLE_SHEETS: Dict[int, str] = {30: "Codo 30", 45: "Codo 45", 60: "Codo 60", 90: "Codo 90"}

NOT_AVAILABLE_MARKERS = {"N/D", "N/A", "", None}


def _is_not_available(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and value.strip().upper() in {"N/D", "N/A", ""}:
        return True
    return False


def _header_index_map(ws: Worksheet, header_row: int = 1) -> Dict[str, int]:
    """Maps header text (as found in the sheet) to its 1-based column index."""
    mapping: Dict[str, int] = {}
    for cell in ws[header_row]:
        if cell.value is not None:
            mapping[str(cell.value).strip()] = cell.column
    return mapping


@dataclass(frozen=True)
class ElbowMasterRow:
    """One row of BD_Codos: dimensions that are angle-dependent only for Z."""

    dn_mm: float
    dn_equivalent_in: str
    radius_mm: float
    le_min_mm: float
    z_by_angle_deg: Dict[int, float] = field(default_factory=dict)


@dataclass(frozen=True)
class SegmentConfigurationRaw:
    """Segment breakdown text for one angle, as found in its 'Codo NN' sheet."""

    angle_deg: int
    source_text: str
    segment_angles_deg: Optional[List[float]]

    @property
    def is_itemized(self) -> bool:
        return self.segment_angles_deg is not None


@dataclass(frozen=True)
class ElbowDatabase:
    """Fully parsed, in-memory snapshot of the source workbook."""

    master_by_dn: Dict[float, ElbowMasterRow]
    thickness_by_dn_pn: Dict[float, Dict[str, Optional[float]]]
    sdr_by_pn: Dict[str, float]
    segment_config_by_angle: Dict[int, SegmentConfigurationRaw]
    pn_labels: List[str]

    @property
    def available_dn_mm(self) -> List[float]:
        return sorted(self.master_by_dn.keys())

    @property
    def available_angles_deg(self) -> List[int]:
        return sorted(self.segment_config_by_angle.keys())


def _parse_bd_codos(ws: Worksheet) -> Dict[float, ElbowMasterRow]:
    headers = _header_index_map(ws)
    required = ["DN mm", "DN equiv.", "R mm", "Le min mm", "Z 30° mm", "Z 45° mm", "Z 60° mm", "Z 90° mm"]
    missing = [h for h in required if h not in headers]
    if missing:
        raise ValueError(f"{SHEET_BD_CODOS}: encabezados esperados no encontrados: {missing}")

    rows: Dict[float, ElbowMasterRow] = {}
    for row_idx in range(2, ws.max_row + 1):
        dn_value = ws.cell(row=row_idx, column=headers["DN mm"]).value
        if dn_value is None:
            continue
        z_by_angle = {}
        for angle in (30, 45, 60, 90):
            z_value = ws.cell(row=row_idx, column=headers[f"Z {angle}° mm"]).value
            if z_value is not None:
                z_by_angle[angle] = float(z_value)
        rows[float(dn_value)] = ElbowMasterRow(
            dn_mm=float(dn_value),
            dn_equivalent_in=str(ws.cell(row=row_idx, column=headers["DN equiv."]).value),
            radius_mm=float(ws.cell(row=row_idx, column=headers["R mm"]).value),
            le_min_mm=float(ws.cell(row=row_idx, column=headers["Le min mm"]).value),
            z_by_angle_deg=z_by_angle,
        )
    return rows


def _parse_bd_pn(ws: Worksheet):
    headers = _header_index_map(ws)
    pn_labels = [h for h in headers if h.startswith("PN") and h != "SDR por PN"]
    if "DN mm" not in headers or not pn_labels:
        raise ValueError(f"{SHEET_BD_PN}: no se encontraron columnas DN/PN esperadas")

    thickness_by_dn_pn: Dict[float, Dict[str, Optional[float]]] = {}
    for row_idx in range(2, ws.max_row + 1):
        dn_value = ws.cell(row=row_idx, column=headers["DN mm"]).value
        if dn_value is None:
            continue
        per_pn: Dict[str, Optional[float]] = {}
        for pn_label in pn_labels:
            raw = ws.cell(row=row_idx, column=headers[pn_label]).value
            per_pn[pn_label] = None if _is_not_available(raw) else float(raw)
        thickness_by_dn_pn[float(dn_value)] = per_pn

    # "SDR por PN" mini-table: a label/value pair per row, in the two columns
    # immediately following the 'SDR por PN' header cell.
    if "SDR por PN" not in headers:
        raise ValueError(f"{SHEET_BD_PN}: no se encontro la tabla 'SDR por PN'")
    sdr_label_col = headers["SDR por PN"]
    sdr_value_col = sdr_label_col + 1
    sdr_by_pn: Dict[str, float] = {}
    for row_idx in range(2, ws.max_row + 1):
        label = ws.cell(row=row_idx, column=sdr_label_col).value
        value = ws.cell(row=row_idx, column=sdr_value_col).value
        if label is None or value is None:
            continue
        sdr_by_pn[str(label).strip()] = float(value)

    return thickness_by_dn_pn, sdr_by_pn, pn_labels


_ITEM_TOKEN_RE = re.compile(r"^(\d+(?:[.,]\d+)?)\s*°$")


def _parse_segment_configuration(raw_text: str) -> Optional[List[float]]:
    """Parses "15° - 30° - 30° - 15°" into [15.0, 30.0, 30.0, 15.0].

    Returns None (never a guessed list) when the text is not a clean,
    itemized angle breakdown — this is the case for the 30° sheet in the
    supplied workbook, which only has descriptive prose.
    """
    tokens = [t.strip() for t in raw_text.split("-")]
    angles: List[float] = []
    for token in tokens:
        match = _ITEM_TOKEN_RE.match(token)
        if not match:
            return None
        angles.append(float(match.group(1).replace(",", ".")))
    return angles or None


def _parse_angle_sheet_configuration(ws: Worksheet, angle_deg: int) -> SegmentConfigurationRaw:
    label_col, value_col = 2, 3  # column B holds labels, column C holds values
    for row_idx in range(1, ws.max_row + 1):
        label = ws.cell(row=row_idx, column=label_col).value
        if label is not None and str(label).strip() == "Configuración":
            raw_text = str(ws.cell(row=row_idx, column=value_col).value)
            return SegmentConfigurationRaw(
                angle_deg=angle_deg,
                source_text=raw_text,
                segment_angles_deg=_parse_segment_configuration(raw_text),
            )
    raise ValueError(f"{ANGLE_SHEETS[angle_deg]}: no se encontro la fila 'Configuración'")


def load_elbow_database(xlsx_path: Path) -> ElbowDatabase:
    """Parses the full workbook once and returns an immutable in-memory database."""
    wb = openpyxl.load_workbook(xlsx_path, data_only=True, read_only=True)
    try:
        master_by_dn = _parse_bd_codos(wb[SHEET_BD_CODOS])
        thickness_by_dn_pn, sdr_by_pn, pn_labels = _parse_bd_pn(wb[SHEET_BD_PN])
        segment_config_by_angle = {
            angle: _parse_angle_sheet_configuration(wb[sheet_name], angle)
            for angle, sheet_name in ANGLE_SHEETS.items()
        }
    finally:
        wb.close()

    return ElbowDatabase(
        master_by_dn=master_by_dn,
        thickness_by_dn_pn=thickness_by_dn_pn,
        sdr_by_pn=sdr_by_pn,
        segment_config_by_angle=segment_config_by_angle,
        pn_labels=pn_labels,
    )
