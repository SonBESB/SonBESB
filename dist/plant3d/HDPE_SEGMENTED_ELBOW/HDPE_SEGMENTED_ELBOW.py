"""HDPE_SEGMENTED_ELBOW.py — V0.3.1B3B-1: VALIDATION_HOLLOW_GEOMETRY_ONLY.

Prueba minima de subtractFrom(): UN tubo recto hueco (OD110/ID96.8/e6.6),
antes de aplicar el mismo principio a las 6 piezas de B3A (eso sera
V0.3.1B3B-2). NO es el codo, NO es siquiera la forma exterior de B3A --
es un tubo recto simple, igual de forma al de B1/B2, con un taladro.

B3A (6 piezas, CYLINDER+rotateY+translate+uniteWith+erase) ya fue
PROBADO REAL y paso (ver plant3d_validation/registration_result.txt).
Este script no lo toca -- aisla unicamente subtractFrom().

Prueba real siguiente:
    (testacpscript "HDPE_SEGMENTED_ELBOW" "OD" "110" "THK" "6.6" "LE" "150")
Resultado esperado: un tubo recto visiblemente HUECO (no solido) de
OD=110mm, ID=96.8mm, largo 150mm.
"""

# ---------------------------------------------------------------------------
# Metadata (ver docs/PLANT3D_CUSTOMSCRIPT.md para el detalle de cada
# fuente citada):
#   - https://blog.autodesk.io/custom-python-scripts-for-autocad-plant-3d-part-2/
#   - https://blog.autodesk.io/custom-python-scripts-for-autocad-plant-3d-part-3/
#   - https://static.au-uw2-prd.autodesk.com/PD1746_handout_1746_pd1746_20-_20scripting_20components_20for_20autocad_20plant_203d.pdf
#   - https://mgfx.co.za/blog/uncategorized/plant-3d-adding-custom-components-part-2-breaking-down-the-code/
#   - https://enginine.com/2025/11/11/custom-python-scripts-for-autocad-plant-3d-case-study-of-tubing-fittings-part-1/
#   - https://pipingcontent.com/blog/plant3d-python-testacpscript-debugging-loop
#   - https://forums.autodesk.com/t5/autocad-plant-3d-forum/testacpscript-unknown-command/td-p/11901666
#   - https://www.autodesk.com/support/technical/article/caas/tsarticles/ts/6z7yLhwAUHwiyYQaRqYdo.html
#   - https://forums.autodesk.com/autodesk/attachments/autodesk/autocad-plant-3d-forum-zh-cn/4870/1/v1_PD4214-L_Radhakrishnan_AnnexB_Custom-Script-Handout.pdf
#   - https://forums.autodesk.com/t5/autocad-plant-3d-forum/plant-3d-python-scripts-help-understanding-ask4dist/td-p/13829280
#   - https://blog.autodesk.io/custom-python-scripts-for-autocad-plant-3d-part-4/
#   - https://pdfcoffee.com/custom-python-scripts-for-autocad-plant-3d-part-2-autocad-devblog-pdf-free.html
#   - https://forums.autodesk.com/t5/autocad-plant-3d-forum/custom-scripts/td-p/8038308
#   - https://docplayer.net/38668628-Annex-b-creating-custom-component-scripts-in-plant-3d.html
# ---------------------------------------------------------------------------
from aqa.math import *
from varmain.primitiv import *
from varmain.custom import *


@activate(
    Group="Support",
    TooltipShort="HDPE Hollow Tube Validation",
    TooltipLong="VALIDATION_HOLLOW_GEOMETRY_ONLY: straight hollow tube via subtractFrom",
    LengthUnit="mm",
    Ports=2,
)
@group("MainDimensions")
@param(
    OD=LENGTH,
    TooltipShort="Outside Diameter",
    Ask4Dist=True,
)
@param(
    THK=LENGTH,
    TooltipLong="Wall thickness",
)
@param(
    LE=LENGTH,
    TooltipLong="Validation Length",
)
def HDPE_SEGMENTED_ELBOW(
    s,
    OD=110.0,
    THK=6.6,
    LE=150.0,
    OF=-1,
    K=1,
    **kw
):
    """VALIDATION_HOLLOW_GEOMETRY_ONLY -- un tubo recto hueco, NO el codo.

    ID se calcula como OD - 2*THK (misma ecuacion que
    core/models/elbow.py, no una formula nueva). El cilindro interior se
    construye 5mm mas largo por cada extremo (margen de
    modelado propio, no una convencion de Plant 3D) para garantizar un
    taladro pasante limpio.
    """
    id_mm = OD - 2 * THK

    tubo_exterior = CYLINDER(s, R=OD / 2.0, H=LE, O=0.0).rotateY(90)
    tubo_interior = CYLINDER(s, R=id_mm / 2.0, H=LE + 10, O=-5).rotateY(90)

    tubo_exterior.subtractFrom(tubo_interior)
    tubo_interior.erase()

    s.setPoint((0.0, 0.0, 0.0), (-1.0, 0.0, 0.0), 0.0)
    s.setPoint((LE, 0.0, 0.0), (1.0, 0.0, 0.0), 0.0)
