"""Duratec PE100 dimensions from user-supplied catalog, table 5.1.1."""
from functools import lru_cache
from pathlib import Path
import json

@lru_cache(maxsize=1)
def load_hdpe_catalog():
    return json.loads((Path(__file__).resolve().parents[2] / 'data_sources/hdpe_catalog/dimensions.json').read_text())


def hdpe_pressure_limit(row, fluid):
    # Only the reference condition explicitly provided by table 5.1.1.
    return row['pressure_class'] if fluid is not None and fluid.name == 'Agua' and fluid.temperature_c == 20.0 else None
