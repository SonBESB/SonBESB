"""Transforms an already-built ElbowParameters + SegmentedElbowGeometry
into a Plant 3D CustomScript (.py) text — WITHOUT re-deriving any
dimension. Every number in the output is read from the objects passed
in; this module contains no trigonometry, no tolerance, no segment logic
of its own (see core/geometry/segmented_elbow.py for all of that).

Pipeline this module sits in:

    Excel / Source Data -> ElbowParameters -> SegmentedElbowGeometry
        -> Plant3DCustomScriptGenerator -> Plant3D .PY

HONESTY CONTRACT (read before editing): this project has no access to a
real AutoCAD Plant 3D installation or its SDK (see
docs/PLANT3D_ENVIRONMENT.md for the investigation that established this).
The only verified Plant 3D syntax available comes from quoted fragments
of Autodesk's own public documentation (cited inline below and in
docs/PLANT3D_CUSTOMSCRIPT.md). Every function/class/call this module has
NOT seen quoted from a real source is emitted as data (a plain dict) or a
comment, never as an invented Python call presented as if it were real
Plant 3D API. Do not add speculative API calls to make the generated
script "look more complete" — that is exactly what the V0.3 spec
prohibits.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from core.geometry.segmented_elbow import SegmentedElbowGeometry
from core.library.elbow_registration import ComponentRegistration
from core.models.elbow import ElbowParameters
from plant3d.generators.port_mapping import PlantPortMapping, map_ports

DEFAULT_SCRIPT_NAME = "HDPE_SEGMENTED_ELBOW"

# Citations for the metadata block below — see docs/PLANT3D_CUSTOMSCRIPT.md
# for the full investigation. Kept here too so the generated file's
# provenance travels with the code that produced it.
SOURCE_CITATIONS = (
    "https://help.autodesk.com/view/PLNT3D/2023/ENU/?guid=GUID-D86E0252-5123-41DA-8B72-202AD8D48558",
    "https://blog.autodesk.io/custom-python-scripts-for-autocad-plant-3d-part-2/",
    "https://blog.autodesk.io/custom-python-scripts-for-autocad-plant-3d-part-3/",
    "https://static.au-uw2-prd.autodesk.com/PD1746_handout_1746_pd1746_20-_20scripting_20components_20for_20autocad_20plant_203d.pdf",
)


def _fmt_vector(vector) -> str:
    return "[" + ", ".join(f"{v:.6g}" for v in vector) + "]"


def _port_data_block(mappings: List[PlantPortMapping]) -> str:
    lines = ["GOLDEN_CASE_PORTS = ["]
    for m in mappings:
        lines.append("    {")
        lines.append(f'        "plant_port_index": {m.plant_port_index},')
        lines.append(f'        "source_port_id": "{m.source_port_id}",')
        lines.append(f'        "position_mm": {_fmt_vector(m.position_mm)},')
        lines.append(f'        "direction": {_fmt_vector(m.direction)},')
        lines.append(f'        "nominal_diameter_mm": {m.nominal_diameter_mm!r},')
        lines.append(f'        "outside_diameter_mm": {m.outside_diameter_mm!r},')
        lines.append(f'        "source_end_type": "{m.source_end_type}",')
        lines.append(f'        "plant_end_type": "{m.plant_end_type}",')
        lines.append(f'        "plant_end_type_confirmed": {m.plant_end_type_confirmed!r},')
        lines.append("    },")
    lines.append("]")
    return "\n".join(lines)


@dataclass(frozen=True)
class GeneratedCustomScript:
    script_name: str
    source_code: str
    port_mappings: List[PlantPortMapping]
    warnings: List[str]


def generate_custom_script(
    params: ElbowParameters,
    geometry: SegmentedElbowGeometry,
    registration: ComponentRegistration,
    script_name: str = DEFAULT_SCRIPT_NAME,
) -> GeneratedCustomScript:
    """Builds the .py CustomScript text for one already-validated elbow.

    Deterministic: identical (params, geometry, registration, script_name)
    always produce byte-identical source_code — no timestamps, no
    non-reproducible ordering.
    """
    warnings: List[str] = []
    port_mappings = map_ports(geometry)
    if any(not m.plant_end_type_confirmed for m in port_mappings):
        warnings.append(
            "plant_end_type no confirmado contra una instalacion real de Plant 3D; "
            "queda como REQUIRES_PLANT_CONFIGURATION (ver docs/PLANT3D_CUSTOMSCRIPT.md)."
        )

    citations_block = "\n".join(f"#   - {url}" for url in SOURCE_CITATIONS)

    header = f'''"""{script_name}.py — generado por Piping Component Generator (V0.3 Proof of Concept)

ESTADO: SCAFFOLD — NOT_VERIFIED_AGAINST_REAL_PLANT3D_API
No ejecutar PLANTREGISTERCUSTOMSCRIPTS contra este archivo esperando que
compile: la seccion de geometria/puertos deliberadamente NO contiene
llamadas reales a la API de Plant 3D (ver docs/PLANT3D_CUSTOMSCRIPT.md
para por que, y que falta).

Componente: {registration.family.display_name} ({registration.family.key})
Norma: {registration.standard.organization.value} {registration.standard.code} Parte {registration.standard.part}
Material: {registration.material.family.value} {registration.material.grade}
Estado de cumplimiento: {registration.compliance_status.value}
Caso: DN{params.dn_mm:g} {params.pn} {params.angle_deg:g} grados
"""

# ---------------------------------------------------------------------------
# Metadata verificada contra documentacion publica de Autodesk (fragmentos
# citados textualmente durante la investigacion de V0.3):
{citations_block}
# Los nombres de import, los decoradores @activate/@group/@param y los
# argumentos Group/TooltipShort/TooltipLong/LengthUnit/Ports/FirstPortEndtypes
# provienen de esas fuentes. Todo lo demas en este archivo es un
# marcador explicito, no una llamada real.
# ---------------------------------------------------------------------------
from aqa.math import *
from varmain.primitiv import *
from varmain.custom import *


@activate(
    Group="Fitting",
    TooltipShort="{registration.family.display_name}",
    TooltipLong="{registration.family.display_name} ({registration.standard.organization.value} {registration.standard.code} Parte {registration.standard.part}). Generado por Piping Component Generator.",
    LengthUnit="mm",
    Ports=2,
)
@group("MainDimensions")
@param(OD=LENGTH, TooltipShort="Diametro exterior", TooltipLong="OD (mm) - Golden Case: {params.od_mm:g}")
@param(THK=LENGTH, TooltipShort="Espesor de pared", TooltipLong="Espesor (mm) - Golden Case: {params.thickness_mm:g}")
@param(R=LENGTH, TooltipShort="Radio de curvatura", TooltipLong="R (mm) - Golden Case: {params.radius_mm:g}")
@param(LE=LENGTH, TooltipShort="Longitud tangente", TooltipLong="Le (mm) - Golden Case: {params.le_mm:g}")
@param(Z=LENGTH, TooltipShort="Distancia vertice-cara", TooltipLong="Z = Le + R*tan(angulo/2) (mm) - Golden Case: {geometry.z_mm:g}")
# ANGLE_DEG: ningun tipo de parametro Plant 3D para angulos fue confirmado
# en esta investigacion (solo LENGTH quedo evidenciado). NO se inventa un
# tipo — se deja como TODO explicito.
# @param(ANGLE_DEG=<TIPO_NO_CONFIRMADO>, TooltipShort="Angulo del codo")  # TODO
def UNCONFIRMED_PLANT3D_ENTRY_POINT():
    """Placeholder only — NOT sourced.

    Python decorators must wrap a function or class, so the @activate /
    @group / @param stack above (which IS sourced, see SOURCE_CITATIONS)
    needs a target to stay syntactically valid. This function's NAME and
    BODY are not from any real Plant 3D script this project has seen —
    only the decorators above it are. Replace this whole function once
    the real entry point signature is confirmed on an actual Plant 3D
    installation.
    """
    raise NotImplementedError(
        "NOT_VERIFIED_AGAINST_REAL_PLANT3D_API: geometry/port placement "
        "calls belong here once confirmed against a real installation."
    )


# ---------------------------------------------------------------------------
# Datos de referencia (Golden Case) — estructuras de datos planas, NO son
# llamadas a la API de Plant 3D. Sirven para que quien complete este
# script (con acceso real al SDK) tenga los valores exactos ya validados
# por el motor geometrico de Piping Component Generator, sin tener que
# recalcular nada.
# ---------------------------------------------------------------------------
GOLDEN_CASE_PARAMETERS = {{
    "od_mm": {params.od_mm!r},
    "thickness_mm": {params.thickness_mm!r},
    "inside_diameter_mm": {round(params.inside_diameter_mm, 6)!r},
    "radius_mm": {params.radius_mm!r},
    "le_mm": {params.le_mm!r},
    "z_mm": {geometry.z_mm!r},
    "angle_deg": {params.angle_deg!r},
    "segment_angles_deg": {params.segment_configuration.segment_angles_deg if params.segment_configuration else None!r},
}}

{_port_data_block(port_mappings)}


# ---------------------------------------------------------------------------
# GEOMETRIA Y PUERTOS — NOT_VERIFIED_AGAINST_REAL_PLANT3D_API
#
# TODO (requiere inspeccionar varmain.primitiv / varmain.custom reales en
# una instalacion de Plant 3D — ver docs/PLANT3D_CUSTOMSCRIPT.md):
#   1. Construir el solido usando GOLDEN_CASE_PARAMETERS (o los valores
#      @param recibidos en vivo): 2 tramos rectos (Le) + los gajos a
#      inglete de core/geometry/segmented_elbow.py. NO reescribir esta
#      geometria aqui — si esta funcion necesita los puntos/planos
#      exactos, deben pasarse desde
#      plant3d/generators/custom_script_generator.py, no recalcularse.
#   2. Colocar los puertos 1..2 de GOLDEN_CASE_PORTS en su
#      position_mm/direction. La llamada real de Plant 3D para esto (un
#      hilo del foro de Autodesk menciona "setPoint") no fue confirmada.
#   3. Asignar el EndType real de cada puerto una vez confirmado un
#      codigo de extremo para termofusion HDPE via PLANTENDCODES en una
#      instalacion real — mientras tanto queda como
#      "REQUIRES_PLANT_CONFIGURATION" (ver GOLDEN_CASE_PORTS arriba).
# ---------------------------------------------------------------------------
'''

    return GeneratedCustomScript(
        script_name=script_name,
        source_code=header,
        port_mappings=port_mappings,
        warnings=warnings,
    )
