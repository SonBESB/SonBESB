"""Query API for normalized-mode elbow lookups (MODE A).

Wraps the parsed ElbowDatabase (data/loader.py) and turns a (DN, PN, angle)
selection into either a fully populated ElbowParameters or a clear
AVAILABLE / NOT_AVAILABLE / INCOMPLETE verdict — never a guessed value.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from core.models.common import ComponentMode, DataAvailability, EndType, Port
from core.models.elbow import ElbowParameters, SegmentConfiguration
from core.standards.din16963 import is_within_din16963_scope, scope_note
from data.loader import ElbowDatabase, load_elbow_database

DEFAULT_XLSX_PATH = Path(__file__).resolve().parent / "raw" / "Codos_HDPE_Parametricos_DIN16963.xlsx"


@dataclass
class LookupResult:
    status: DataAvailability
    elbow: Optional[ElbowParameters]
    missing_fields: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)


class ElbowRepository:
    """Read-only access to the segmented HDPE elbow catalog."""

    def __init__(self, database: ElbowDatabase):
        self._db = database

    @classmethod
    def from_excel(cls, xlsx_path: Path = DEFAULT_XLSX_PATH) -> "ElbowRepository":
        return cls(load_elbow_database(xlsx_path))

    def available_dn_mm(self) -> List[float]:
        return self._db.available_dn_mm

    def available_pn_labels(self) -> List[str]:
        return self._db.pn_labels

    def available_angles_deg(self) -> List[int]:
        return self._db.available_angles_deg

    def lookup(self, dn_mm: float, pn_label: str, angle_deg: int) -> LookupResult:
        notes: List[str] = []
        missing_fields: List[str] = []

        master = self._db.master_by_dn.get(dn_mm)
        if master is None:
            return LookupResult(
                status=DataAvailability.NOT_AVAILABLE,
                elbow=None,
                notes=[f"DN {dn_mm} mm no existe en la base de datos."],
            )

        thickness_row = self._db.thickness_by_dn_pn.get(dn_mm)
        thickness_mm = thickness_row.get(pn_label) if thickness_row else None
        if thickness_mm is None:
            return LookupResult(
                status=DataAvailability.NOT_AVAILABLE,
                elbow=None,
                notes=[f"La combinacion DN {dn_mm} mm / {pn_label} no esta disponible en el catalogo (N/D)."],
            )

        sdr = self._db.sdr_by_pn.get(pn_label)
        if sdr is None:
            missing_fields.append("sdr")
            notes.append(f"No se encontro SDR para {pn_label}.")

        z_mm = master.z_by_angle_deg.get(angle_deg)
        if z_mm is None:
            missing_fields.append("z_mm")
            notes.append(f"No se encontro Z para angulo {angle_deg}°.")

        segment_config_raw = self._db.segment_config_by_angle.get(angle_deg)
        segment_configuration: Optional[SegmentConfiguration] = None
        if segment_config_raw is None:
            missing_fields.append("segment_configuration")
            notes.append(f"No se encontro configuracion de segmentos para {angle_deg}°.")
        else:
            segment_configuration = SegmentConfiguration(
                total_angle_deg=float(angle_deg),
                is_itemized=segment_config_raw.is_itemized,
                segment_angles_deg=segment_config_raw.segment_angles_deg,
                source_text=segment_config_raw.source_text,
            )
            if not segment_config_raw.is_itemized:
                notes.append(
                    f"La fuente no desglosa los segmentos para {angle_deg}° "
                    "(solo texto descriptivo); no se inventa un desglose."
                )

        out_of_scope_note = scope_note(dn_mm)
        if out_of_scope_note:
            notes.append(out_of_scope_note)

        od_mm = dn_mm  # HDPE pipe convention: nominal diameter == outside diameter.
        elbow = ElbowParameters(
            mode=ComponentMode.NORMALIZED,
            dn_mm=dn_mm,
            dn_equivalent_in=master.dn_equivalent_in,
            pn=pn_label,
            sdr=sdr,
            od_mm=od_mm,
            thickness_mm=thickness_mm,
            angle_deg=float(angle_deg),
            radius_mm=master.radius_mm,
            le_mm=master.le_min_mm,
            z_mm=z_mm,
            segment_configuration=segment_configuration,
            end_type=EndType.BUTT_FUSION,
            ports=[Port(id="P1", end_type=EndType.BUTT_FUSION), Port(id="P2", end_type=EndType.BUTT_FUSION)],
            din16963_compliant=is_within_din16963_scope(dn_mm),
            notes=notes,
        )

        status = DataAvailability.INCOMPLETE if missing_fields else DataAvailability.AVAILABLE
        return LookupResult(status=status, elbow=elbow, missing_fields=missing_fields, notes=notes)
