"""Formats ElbowParameters into the label/value rows the UI displays.

Kept separate from app_streamlit.py for the same reason as plotly_view.py:
presentation formatting is not widget wiring.
"""

from __future__ import annotations

from typing import List, Tuple

from core.models.common import ComponentMode
from core.models.elbow import ElbowParameters

NO_DISPONIBLE = "NO DISPONIBLE"
NOT_APPLICABLE_CUSTOM = "N/A (modo personalizado)"


def _fmt(value, unit: str = "", missing: bool = False, not_applicable: bool = False) -> str:
    if not_applicable:
        return NOT_APPLICABLE_CUSTOM
    if missing or value is None:
        return NO_DISPONIBLE
    if isinstance(value, float) and value == int(value):
        value = int(value)
    return f"{value}{unit}"


def build_result_rows(params: ElbowParameters, missing_fields: List[str]) -> List[Tuple[str, str]]:
    is_custom = params.mode is ComponentMode.CUSTOM
    config = params.segment_configuration

    if config is None:
        config_text = NO_DISPONIBLE if not is_custom else NOT_APPLICABLE_CUSTOM
    elif config.is_itemized:
        config_text = " - ".join(f"{a:g}°" for a in config.segment_angles_deg)
    else:
        config_text = f"{config.source_text} (segmentos no desglosados en la fuente)"

    rows = [
        ("DN (mm)", _fmt(params.dn_mm, not_applicable=is_custom)),
        ("Equivalencia (pulgadas)", _fmt(params.dn_equivalent_in, not_applicable=is_custom)),
        ("PN", _fmt(params.pn, not_applicable=is_custom)),
        ("SDR", _fmt(params.sdr, missing="sdr" in missing_fields, not_applicable=is_custom)),
        ("OD (mm)", _fmt(params.od_mm)),
        ("Espesor (mm)", _fmt(params.thickness_mm)),
        ("Diametro interior (mm)", _fmt(round(params.inside_diameter_mm, 2))),
        ("Angulo (deg)", _fmt(params.angle_deg)),
        ("Radio R (mm)", _fmt(params.radius_mm)),
        ("Le (mm)", _fmt(params.le_mm)),
        ("Z (mm)", _fmt(params.z_mm, missing="z_mm" in missing_fields)),
        ("Configuracion de segmentos", config_text),
        ("Cumplimiento DIN 16963", "SI" if params.din16963_compliant else "NO"),
    ]
    return rows
