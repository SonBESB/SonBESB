"""HDPE_SEGMENTED_ELBOW.py — V0.3.1B1: VALIDATION_GEOMETRY_ONLY, sin puertos todavia.

Etapa siguiente a V0.3.1A (que ya probo CYLINDER(...).rotateY(...) + 2
puertos via s.setPoint(...)). Esta version quita TODO lo demas para
aislar una sola pregunta: puede nuestra propia familia
(HDPE_SEGMENTED_ELBOW, mismo nombre de archivo y de rutina) ejecutarse
bajo el lookup de componentes/familias de Plant 3D. NO agrega puertos,
NO usa THK/R/Z/PN/SDR, NO es geometria segmentada, NO toca Catalog
Builder/Spec Editor/EndType. Ver docs/PLANT3D_CUSTOMSCRIPT.md, seccion
V0.3.1, para el plan completo (V0.3.1B1 -> B2 -> B3, sin saltar etapas).

Prueba real siguiente:
    (testacpscript "HDPE_SEGMENTED_ELBOW" "OD" "110" "LE" "150")
Resultado esperado: un cilindro OD=110mm x L=150mm.
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
# ---------------------------------------------------------------------------
from aqa.math import *
from varmain.primitiv import *
from varmain.custom import *


@activate(
    Group="Support",
    TooltipShort="HDPE Segmented Elbow Validation",
    TooltipLong="Temporary validation geometry",
    LengthUnit="mm",
    Ports=1,
)
@group("MainDimensions")
@param(
    OD=LENGTH,
    TooltipShort="Outside Diameter",
    Ask4Dist=True,
)
@param(
    LE=LENGTH,
    TooltipLong="Validation Length",
)
def HDPE_SEGMENTED_ELBOW(
    s,
    OD=110.0,
    LE=150.0,
    OF=-1,
    K=1,
    **kw
):
    """VALIDATION_GEOMETRY_ONLY -- sin puertos, sin THK/R/Z, NO el codo DIN 16963.

    OF/K se reciben (misma forma que el ejemplo real citado
    literalmente, ver SOURCE_CITATIONS arriba) pero no se usan todavia.
    Unico objetivo: confirmar que esta familia ejecuta bajo Plant 3D
    real antes de reintroducir puertos (V0.3.1B2).
    """
    CYLINDER(
        s,
        R=OD / 2.0,
        H=LE,
        O=0.0,
    ).rotateY(90)
