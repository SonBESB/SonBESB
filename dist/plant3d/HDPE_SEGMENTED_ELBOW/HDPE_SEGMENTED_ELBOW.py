"""HDPE_SEGMENTED_ELBOW.py — V0.3.1A: VALIDATION_GEOMETRY_ONLY, NOT the codo DIN 16963.

Fixes the V0.3 scaffold's entry-point bug found on real AutoCAD Plant 3D
2025 hardware (see plant3d_validation/registration_result.txt):
PLANTREGISTERCUSTOMSCRIPTS and the PnP3dACPAdapter both loaded without
error, but (testacpscript "HDPE_SEGMENTED_ELBOW") returned NIL and produced no
geometry, because the routine was named UNCONFIRMED_PLANT3D_ENTRY_POINT
instead of HDPE_SEGMENTED_ELBOW. Plant 3D's shape lookup requires the routine
name to match the script name.

This version's ONLY job is to confirm SCRIPT EXECUTION, GEOMETRY API and
PORT API on the real install: ONE straight cylinder, two ports. It is
NOT dimensionally meaningful as a codo yet — see
docs/PLANT3D_CUSTOMSCRIPT.md, seccion V0.3.1, for the real evidence and
sources behind every call below, and for what V0.3.1B still needs.
"""

# ---------------------------------------------------------------------------
# Metadata: same decorators/imports confirmed for V0.3 (see
# docs/PLANT3D_CUSTOMSCRIPT.md), plus the additional sources below that
# corroborate CYLINDER / setPoint / the entry-point-matches-script-name
# rule / TESTACPSCRIPT behavior used in this V0.3.1A fixture:
#   - https://blog.autodesk.io/custom-python-scripts-for-autocad-plant-3d-part-2/
#   - https://blog.autodesk.io/custom-python-scripts-for-autocad-plant-3d-part-3/
#   - https://static.au-uw2-prd.autodesk.com/PD1746_handout_1746_pd1746_20-_20scripting_20components_20for_20autocad_20plant_203d.pdf
#   - https://mgfx.co.za/blog/uncategorized/plant-3d-adding-custom-components-part-2-breaking-down-the-code/
#   - https://enginine.com/2025/11/11/custom-python-scripts-for-autocad-plant-3d-case-study-of-tubing-fittings-part-1/
#   - https://pipingcontent.com/blog/plant3d-python-testacpscript-debugging-loop
#   - https://forums.autodesk.com/t5/autocad-plant-3d-forum/testacpscript-unknown-command/td-p/11901666
# ---------------------------------------------------------------------------
from aqa.math import *
from varmain.primitiv import *
from varmain.custom import *


@activate(
    Group="Fitting",
    TooltipShort="VALIDATION_GEOMETRY_ONLY (V0.3.1A) - not the codo yet",
    TooltipLong="V0.3.1A: un solo tramo recto, usado solo para validar SCRIPT/GEOMETRY/PORT API en Plant 3D 2025 real. No representa el codo DIN 16963.",
    LengthUnit="mm",
    Ports=2,
)
@group("MainDimensions")
@param(OD=LENGTH, TooltipShort="Diametro exterior", TooltipLong="OD (mm) - Golden Case: 110")
@param(THK=LENGTH, TooltipShort="Espesor de pared (no usado en V0.3.1A)", TooltipLong="Espesor (mm) - reservado para V0.3.1B")
@param(R=LENGTH, TooltipShort="Radio de curvatura (no usado en V0.3.1A)", TooltipLong="R (mm) - reservado para V0.3.1B")
@param(LE=LENGTH, TooltipShort="Longitud del tramo de prueba", TooltipLong="Le (mm) - Golden Case: 150")
@param(Z=LENGTH, TooltipShort="Distancia vertice-cara (no usado en V0.3.1A)", TooltipLong="Z (mm) - reservado para V0.3.1B")
def HDPE_SEGMENTED_ELBOW(s, OD=110.0, THK=6.6, R=165.0, LE=150.0, Z=315.0, **kw):
    """VALIDATION_GEOMETRY_ONLY -- un solo tramo recto (CYLINDER), NO el codo DIN 16963.

    THK/R/Z se reciben (mismos nombres/defaults del Golden Case
    DN110/PN10/90) pero todavia no se usan: esta version solo prueba que
    CYLINDER(...) + s.setPoint(...) funcionan en un Plant 3D 2025 real.
    Ver docs/PLANT3D_CUSTOMSCRIPT.md, seccion V0.3.1.
    """
    # HONESTY NOTE: (OD, LE) como orden de argumentos de CYLINDER es una
    # reconstruccion best-effort a partir de multiples ejemplos reales
    # independientes (ver SOURCE_CITATIONS arriba), NO una firma citada
    # literalmente. Si esto falla o dibuja algo incorrecto en el
    # entorno real, eso ES evidencia nueva a reportar.
    tramo = CYLINDER(OD, LE)

    # Puertos: esta forma exacta de llamada (posicion, direccion, 0.0) es
    # una coincidencia cercana con un ejemplo real citado literalmente
    # (TESTSCRIPT2) -- ver SOURCE_CITATIONS arriba.
    s.setPoint((0.0, 0.0, 0.0), (-1.0, 0.0, 0.0), 0.0)
    s.setPoint((LE, 0.0, 0.0), (1.0, 0.0, 0.0), 0.0)
