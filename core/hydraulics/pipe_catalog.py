"""PEXGOL 2023 draft catalog. Printed values are preserved, never auto-approved."""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import json
import math
from core.library.provenance import DataProvenance

CLASSES = (6, 8, 10, 12, 15, 19, 24, 30)
# Manufacturer table 9.1, bar for water, C=1.25. Not the rounded class headings.
PRESSURES = {
    10: (6.8,8.5,11.2,13.5,17,21.4,26.9,33.9),
    20: (6,7.6,9.9,11.9,15,18.9,23.8,30),
    30: (5.3,6.7,8.8,10.6,13.3,16.8,21.1,26.6),
    40: (4.7,5.9,7.8,9.4,11.8,14.9,18.7,23.6),
    50: (4.1,5.2,7,8.3,10.5,13.2,16.7,21.1),
    60: (3.8,4.8,6.3,7.5,9.5,11.9,15,18.9),
    70: (3.4,4.3,5.6,6.7,8.5,10.7,13.4,16.9),
    80: (3,3.8,5.1,6.1,7.5,9.5,12,15.1),
    90: (2.7,3.4,4.5,5.4,6.8,8.6,10.9,13.7),
    95: (2.6,3.2,4.1,4.9,6.4,8.1,10.3,12.9),
    100: (2.1,2.7,3.5,4.2,5.5,7,9,11.2),
    105: (1.8,2.2,2.8,3.4,4.5,5.5,7,8.7),
    110: (1.5,1.9,2.4,2.9,3.8,4.7,5.9,7.5),
}

@lru_cache(maxsize=1)
def load_pexgol_catalog() -> dict:
    path = Path(__file__).resolve().parents[2] / 'data_sources/pexgol_catalog/dimensions.json'
    return json.loads(path.read_text(encoding='utf-8'))


def catalog_provenance(page: int) -> DataProvenance:
    catalog = load_pexgol_catalog()
    return DataProvenance(document=catalog['document'], document_revision=catalog['revision'],
                          page=str(page), section='Dimensiones y clasificacion de presion',
                          notes='DRAFT_UNVERIFIED: transcripcion pendiente de revision humana.')


def allowed_pressure_bar(pressure_class: int, temperature_c: float) -> tuple[float, int]:
    """Use next tabulated temperature (conservative step); no extrapolation."""
    if not math.isfinite(temperature_c) or not 10 <= temperature_c <= 110:
        raise ValueError('PEXGOL: tabla 9.1 disponible solo entre 10 y 110 C; sin extrapolacion.')
    index = CLASSES.index(pressure_class)
    reference_temperature = next(t for t in PRESSURES if t >= temperature_c)
    return PRESSURES[reference_temperature][index], reference_temperature
