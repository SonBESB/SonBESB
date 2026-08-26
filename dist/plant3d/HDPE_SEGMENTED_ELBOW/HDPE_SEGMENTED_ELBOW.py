"""HDPE_SEGMENTED_ELBOW.py — V0.3.1B3C-1R4B: axis-corrected side cut, solo Gajo B.

V0.3.1B3C-1R4 se probo real: GAJO_A_SURVIVES_CUT, HOLLOW_GEOMETRY_RETAINED,
INCLINED_CUT_FACE, BOX_AXIS_MAPPING y CORRECT_HALFSPACE_REMOVED, todos
PASS, con BOX(s, H=2000, L=2000, W=500). Esta version repite exactamente
la misma construccion para Gajo B: mismo mapeo H/L/W, mismo rotateY(45),
joint_point y plane_normal sin cambios.

Unico elemento nuevo: el signo de semiespacio para Gajo B se eligio
automaticamente a partir de
side_b = dot(midpoint_gajo_b - joint_point, plane_normal) = 41.25
(positivo) -- el cutter debe ocupar el
semiespacio CONTRARIO al cuerpo del gajo, sign=-1.0.

Sin Gajo A, sin uniteWith, sin calibration box. No se modifico
core/geometry/segmented_elbow.py, joint_point ni plane_normal.

Verificar en Plant 3D:
  GAJO_B_SURVIVES_CUT
  HOLLOW_GEOMETRY_RETAINED
  INCLINED_CUT_FACE

Golden Case: DN110 PN10 90 grados
  OD=110 THK=6.6 R=165
  LE=150 Z=315
  Pieza probada aqui: Gajo 3 (30 deg), sin Gajo 2.
"""

# ---------------------------------------------------------------------------
# Metadata (ver docs/PLANT3D_CUSTOMSCRIPT.md para el detalle de cada fuente
# citada):
#   - https://blog.autodesk.io/custom-python-scripts-for-autocad-plant-3d-part-2/
#   - https://blog.autodesk.io/custom-python-scripts-for-autocad-plant-3d-part-3/
#   - https://blog.autodesk.io/custom-python-scripts-for-autocad-plant-3d-part-4/
#   - https://static.au-uw2-prd.autodesk.com/PD1746_handout_1746_pd1746_20-_20scripting_20components_20for_20autocad_20plant_203d.pdf
#   - https://www.autodesk.com/support/technical/article/caas/tsarticles/ts/6z7yLhwAUHwiyYQaRqYdo.html
#   - https://forums.autodesk.com/autodesk/attachments/autodesk/autocad-plant-3d-forum-zh-cn/4870/1/v1_PD4214-L_Radhakrishnan_AnnexB_Custom-Script-Handout.pdf
#   - https://forums.autodesk.com/t5/autocad-plant-3d-forum/plant-3d-python-scripts-help-understanding-ask4dist/td-p/13829280
#   - https://forums.autodesk.com/t5/autocad-plant-3d-forum/rotate-have-some-problems-with-python/td-p/10782031
#   - https://forums.autodesk.com/t5/autocad-plant-3d-forum/custom-scripts/td-p/8038308
#   - https://docplayer.net/38668628-Annex-b-creating-custom-component-scripts-in-plant-3d.html
#   - https://forums.autodesk.com/t5/autocad-plant-3d-forum/plant3d-python-libraries-assessment/td-p/12635204
#   - https://forums.autodesk.com/t5/autocad-plant-3d-forum/creation-of-miter-bend-without-straight-parts/td-p/11005489
#   - https://forums.autodesk.com/t5/autocad-plant-3d-forum/how-to-create-mitered-elbow-mitered-tee-amp-mitered-reducer-in/td-p/8188547
#   - user-supplied Autodesk Community excerpt (V0.3.1B3C-1 real result message, no URL given): BOX(s, H=L, L=paB, W=A) with s.setPoint((-L/2.0,0,0),...)/s.setPoint((L/2.0,0,0),...); and BOX(...).translate((pa03*10.0, pa03*10.0, 0.0)).rotateZ(45.0) as a cutter with H=L=pa03*20.0
#   - https://enginine.com/2025/11/11/custom-python-scripts-for-autocad-plant-3d-case-study-of-tubing-fittings-part-1/
# ---------------------------------------------------------------------------
from aqa.math import *
from varmain.primitiv import *
from varmain.custom import *


@activate(
    Group="Fitting",
    TooltipShort="Axis-corrected side cut (Gajo B) - fixture minimo R4B",
    TooltipLong="V0.3.1B3C-1R4B: solo Gajo B hueco + un cutter BOX con mapeo de ejes validado (H=X, L=Y, W=Z), un solo subtractFrom. Ver docs/PLANT3D_CUSTOMSCRIPT.md, seccion V0.3.1.",
    LengthUnit="mm",
    Ports=1,
)
@group("MainDimensions")
@param(OD=LENGTH, TooltipShort="Diametro exterior", TooltipLong="OD (mm) - Golden Case: 110", Ask4Dist=True)
@param(THK=LENGTH, TooltipShort="Espesor de pared", TooltipLong="Espesor (mm) - Golden Case: 6.6. ID = OD - 2*THK.")
@param(R=LENGTH, TooltipShort="Radio de curvatura (posiciones ya horneadas)", TooltipLong="R (mm) - Golden Case: 165. Cambiar este valor en vivo NO recalcula la geometria.")
@param(LE=LENGTH, TooltipShort="Longitud tangente (no usada en este fixture)", TooltipLong="Le (mm) - Golden Case: 150. Este fixture no incluye los tramos Le.")
@param(Z=LENGTH, TooltipShort="Distancia vertice-cara (posiciones ya horneadas)", TooltipLong="Z (mm) - Golden Case: 315.")
def HDPE_SEGMENTED_ELBOW(s, OD=110, THK=6.6, R=165, LE=150, Z=315, OF=-1, K=1, **kw):
    """AXIS_CORRECTED_SIDE_CUT_GAJO_B -- solo Gajo B hueco + un cutter BOX (H=X, L=Y, W=Z), un solo subtractFrom.

    NO representa el codo completo ni la junta a inglete completa --
    es el mismo fixture minimo de R4, aplicado a Gajo B. Ver
    docs/PLANT3D_CUSTOMSCRIPT.md, seccion V0.3.1.
    """
    radio_ext_mm = OD / 2.0
    radio_int_mm = (OD - 2 * THK) / 2.0

    # Gajo B (hueco) -- taladro interior ya confirmado en real por B3B-1.
    ext_b = CYLINDER(s, R=radio_ext_mm, H=85.4103, O=0.0).rotateY(30).translate((-48.3274, 0, 48.3274))
    int_b = CYLINDER(s, R=radio_int_mm, H=95.4103, O=-5).rotateY(30).translate((-48.3274, 0, 48.3274))
    ext_b.subtractFrom(int_b)
    int_b.erase()

    # Un solo cutter -- mapeo H/L/W confirmado en real por R4, mismo
    # rotateY(45) que R1-R4, signo de semiespacio elegido automaticamente
    # (side_b=41.25, sign=-1.0).
    cutter_b = BOX(s, H=2000, L=2000, W=500).rotateY(45).translate((-225.104, 0, -128.449))
    ext_b.subtractFrom(cutter_b)
    cutter_b.erase()

    s.setPoint((-5.62224, 0, 122.295), (0.5, 0, 0.866025), 0.0)
