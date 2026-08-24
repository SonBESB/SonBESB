"""HDPE_SEGMENTED_ELBOW.py — generado por Piping Component Generator (V0.3 Proof of Concept)

ESTADO: SCAFFOLD — NOT_VERIFIED_AGAINST_REAL_PLANT3D_API
No ejecutar PLANTREGISTERCUSTOMSCRIPTS contra este archivo esperando que
compile: la seccion de geometria/puertos deliberadamente NO contiene
llamadas reales a la API de Plant 3D (ver docs/PLANT3D_CUSTOMSCRIPT.md
para por que, y que falta).

Componente: Codo HDPE segmentado (HDPE_SEGMENTED_ELBOW)
Norma: DIN 16963 Parte 1
Material: HDPE PE100
Estado de cumplimiento: SOURCE_DATA
Caso: DN110 PN10 90 grados
"""

# ---------------------------------------------------------------------------
# Metadata verificada contra documentacion publica de Autodesk (fragmentos
# citados textualmente durante la investigacion de V0.3):
#   - https://help.autodesk.com/view/PLNT3D/2023/ENU/?guid=GUID-D86E0252-5123-41DA-8B72-202AD8D48558
#   - https://blog.autodesk.io/custom-python-scripts-for-autocad-plant-3d-part-2/
#   - https://blog.autodesk.io/custom-python-scripts-for-autocad-plant-3d-part-3/
#   - https://static.au-uw2-prd.autodesk.com/PD1746_handout_1746_pd1746_20-_20scripting_20components_20for_20autocad_20plant_203d.pdf
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
    TooltipShort="Codo HDPE segmentado",
    TooltipLong="Codo HDPE segmentado (DIN 16963 Parte 1). Generado por Piping Component Generator.",
    LengthUnit="mm",
    Ports=2,
)
@group("MainDimensions")
@param(OD=LENGTH, TooltipShort="Diametro exterior", TooltipLong="OD (mm) - Golden Case: 110")
@param(THK=LENGTH, TooltipShort="Espesor de pared", TooltipLong="Espesor (mm) - Golden Case: 6.6")
@param(R=LENGTH, TooltipShort="Radio de curvatura", TooltipLong="R (mm) - Golden Case: 165")
@param(LE=LENGTH, TooltipShort="Longitud tangente", TooltipLong="Le (mm) - Golden Case: 150")
@param(Z=LENGTH, TooltipShort="Distancia vertice-cara", TooltipLong="Z = Le + R*tan(angulo/2) (mm) - Golden Case: 315")
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
GOLDEN_CASE_PARAMETERS = {
    "od_mm": 110,
    "thickness_mm": 6.6,
    "inside_diameter_mm": 96.8,
    "radius_mm": 165.0,
    "le_mm": 150.0,
    "z_mm": 315.0,
    "angle_deg": 90.0,
    "segment_angles_deg": [15.0, 30.0, 30.0, 15.0],
}

GOLDEN_CASE_PORTS = [
    {
        "plant_port_index": 1,
        "source_port_id": "P1",
        "position_mm": [-315, 3.85764e-14, 0],
        "direction": [-1, 1.22465e-16, 0],
        "nominal_diameter_mm": 110,
        "outside_diameter_mm": 110,
        "source_end_type": "BUTT_FUSION",
        "plant_end_type": "REQUIRES_PLANT_CONFIGURATION",
        "plant_end_type_confirmed": False,
    },
    {
        "plant_port_index": 2,
        "source_port_id": "P2",
        "position_mm": [1.92882e-14, 315, 0],
        "direction": [6.12323e-17, 1, 0],
        "nominal_diameter_mm": 110,
        "outside_diameter_mm": 110,
        "source_end_type": "BUTT_FUSION",
        "plant_end_type": "REQUIRES_PLANT_CONFIGURATION",
        "plant_end_type_confirmed": False,
    },
]


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
