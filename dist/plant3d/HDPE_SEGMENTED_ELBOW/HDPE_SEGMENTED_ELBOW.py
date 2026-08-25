"""HDPE_SEGMENTED_ELBOW.py — V0.3.1B2: VALIDATION_GEOMETRY_ONLY, con 2 puertos.

V0.3.1B1 (mismo CYLINDER(...).rotateY(...), Ports=1, sin setPoint) fue
PROBADO REAL en AutoCAD Plant 3D 2025 y devolvio <Entity name: ...> con
un cilindro visible OD=110/L=150 (ver
plant3d_validation/registration_result.txt): CYLINDER_API, ROTATEY_API,
GEOMETRY_CREATION y TESTACPSCRIPT_ENTITY_RETURN = PASS.

Esta version agrega EXACTAMENTE dos cosas sobre B1: Ports=2 y dos
llamadas s.setPoint(...) (P1 en el origen mirando -X, P2 en (LE,0,0)
mirando +X) -- la misma forma de llamada (posicion, direccion, 0.0) ya
confirmada desde V0.3.1A. Sigue sin THK/R/Z/PN/SDR/EndType/ButtFusion/
geometria segmentada -- eso empieza en V0.3.1B3. Ver
docs/PLANT3D_CUSTOMSCRIPT.md, seccion V0.3.1, para el plan completo.

Prueba real siguiente:
    (testacpscript "HDPE_SEGMENTED_ELBOW" "OD" "110" "LE" "150")
Resultado esperado: el mismo <Entity name: ...> y cilindro visible de
B1, ahora con P1/P2 tambien definidos.
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
    TooltipLong="Temporary validation geometry with two ports",
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
    """VALIDATION_GEOMETRY_ONLY -- mismo cilindro de B1 (PASS real), ahora con P1/P2.

    OF/K se reciben (misma forma que el ejemplo real citado
    literalmente, ver SOURCE_CITATIONS arriba) pero no se usan todavia.
    Unico objetivo de B2: confirmar Ports=2 + s.setPoint(...) sin tocar
    la geometria ya validada en real por B1.
    """
    CYLINDER(
        s,
        R=OD / 2.0,
        H=LE,
        O=0.0,
    ).rotateY(90)

    s.setPoint(
        (0.0, 0.0, 0.0),
        (-1.0, 0.0, 0.0),
        0.0,
    )

    s.setPoint(
        (LE, 0.0, 0.0),
        (1.0, 0.0, 0.0),
        0.0,
    )
