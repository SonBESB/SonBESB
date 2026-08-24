"""DIN 16963 scope notes for segmented HDPE elbows.

The source workbook's BUSCADOR sheet carries an explicit note: DN 1200-1600
values are provided by the manufacturer catalog but are *not* covered by the
official DIN 16963 standard. This module is the single place that encodes
that scope boundary so the rest of the app never silently claims standard
compliance for out-of-scope DN values.
"""

from __future__ import annotations

from typing import Optional

# Largest DN (mm) explicitly covered by DIN 16963 in the source catalog.
# DN values above this are manufacturer-extrapolated reference data only.
DIN16963_MAX_SCOPE_DN_MM = 1000

OUT_OF_SCOPE_NOTE = (
    "DN {dn_mm} mm figura en el catalogo pero DIN 16963 no lo cubre "
    "oficialmente (nota de la fuente: DN 1200-1600 no cubiertos por la "
    "norma). Usar como referencia de fabricante, no como dato normado."
)


def is_within_din16963_scope(dn_mm: Optional[float]) -> bool:
    """True when dn_mm is within the DN range DIN 16963 formally covers."""
    if dn_mm is None:
        return False
    return dn_mm <= DIN16963_MAX_SCOPE_DN_MM


def scope_note(dn_mm: Optional[float]) -> Optional[str]:
    """Human-readable note to attach to a component when out of scope."""
    if dn_mm is not None and not is_within_din16963_scope(dn_mm):
        return OUT_OF_SCOPE_NOTE.format(dn_mm=int(dn_mm) if float(dn_mm).is_integer() else dn_mm)
    return None
