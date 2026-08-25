"""HDPE_SEGMENTED_ELBOW.py — V0.3.1B3C-1R3A-inverted: SINGLE SIDE CUT, solo Gajo A + un cutter.

V0.3.1B3C-1R2 (visual debug) se probo real: GAJO_A, GAJO_B, CUTTER_A y
CUTTER_B se vieron simultaneamente en semiespacios opuestos, orientacion
coherente con el plano bisector. Unica incertidumbre restante: que
semiespacio elimina realmente cada cutter al ejecutar subtractFrom().

Este fixture es el minimo posible para responder eso: SOLO Gajo A
(hueco, mismo patron ya confirmado por B3B-1) + UN cutter BOX, un solo
subtractFrom(). Sin Gajo B, sin segundo cutter, sin uniteWith, sin
calibration box.

joint_point, plane_normal, rotateY(45) y _cutter_center() NO cambiaron
respecto de R1/R2. Lo unico nuevo: el signo de semiespacio para el
cutter de Gajo A se eligio automaticamente a partir de
side_a = dot(midpoint_gajo_a - joint_point, plane_normal) = -41.25
(negativo) -- el cutter debe ocupar el
semiespacio CONTRARIO al cuerpo del gajo, sign=-1.0.
Variante INVERTIDA: usa el signo contrario al calculo automatico (pedida solo si la variante base hizo desaparecer Gajo A).

No se modifico core/geometry/segmented_elbow.py, joint_point ni
plane_normal. No se avanza a Gajo B ni a B3C-2.

Verificar en Plant 3D:
  GAJO_A survives?            (deberia sobrevivir, no desaparecer)
  CUT FACE appears?           (deberia verse una cara de corte nueva)
  CUT FACE passes joint?      (la cara deberia pasar por el punto de union)
  CORRECT HALFSPACE removed?  (debe quitar solo la cuna, no toda la pieza)

Golden Case: DN110 PN10 90 grados
  OD=110 THK=6.6 R=165
  LE=150 Z=315
  Pieza probada aqui: Gajo 2 (30 deg), sin Gajo 3.
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
    TooltipShort="Single side cut (Gajo A) - fixture minimo de diagnostico",
    TooltipLong="V0.3.1B3C-1R3A-inverted: solo Gajo A hueco + un cutter BOX, un solo subtractFrom. Ver docs/PLANT3D_CUSTOMSCRIPT.md, seccion V0.3.1.",
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
    """SINGLE_SIDE_CUT -- solo Gajo A hueco + un cutter BOX, un solo subtractFrom.

    NO representa el codo completo ni siquiera una junta a inglete
    completa -- es el fixture minimo para verificar que semiespacio
    elimina realmente un cutter BOX. Ver docs/PLANT3D_CUSTOMSCRIPT.md,
    seccion V0.3.1.
    """
    radio_ext_mm = OD / 2.0
    radio_int_mm = (OD - 2 * THK) / 2.0

    # Gajo A (hueco) -- taladro interior ya confirmado en real por B3B-1.
    ext_a = CYLINDER(s, R=radio_ext_mm, H=85.4103, O=0.0).rotateY(60).translate((-122.295, 0, 5.62224))
    int_a = CYLINDER(s, R=radio_int_mm, H=95.4103, O=-5).rotateY(60).translate((-122.295, 0, 5.62224))
    ext_a.subtractFrom(int_a)
    int_a.erase()

    # Un solo cutter -- mismo joint_point/plane_normal/rotateY(45) que R1/R2,
    # semiespacio elegido automaticamente (side_a=-41.25, sign=-1.0).
    cutter_a = BOX(s, L=2000, W=2000, H=500).rotateY(45).translate((-225.104, 0, -128.449))
    ext_a.subtractFrom(cutter_a)
    cutter_a.erase()

    s.setPoint((-122.295, 0, 5.62224), (-0.866025, -0, -0.5), 0.0)
