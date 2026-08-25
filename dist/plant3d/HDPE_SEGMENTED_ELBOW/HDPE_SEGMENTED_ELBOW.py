"""HDPE_SEGMENTED_ELBOW.py — V0.3.1B3C-1: VALIDATION_MITER_JOINT_ONLY, una sola junta real a inglete.

NO es el codo completo -- es un fixture aislado con SOLO Gajo 2 + Gajo 3
(la junta representativa 30/30 del Golden Case), cada uno ya hueco
(mismo patron subtractFrom()+erase() ya confirmado en real por B3B-1/
B3B-2), cortados contra su plano bisectriz REAL compartido (calculado
una sola vez por core/geometry/segmented_elbow.py, horneado aqui como
constantes -- ningun calculo trigonometrico se repite en este script).
NO modifica la cadena completa de 6 piezas de B3B-2 (queda intacta en
plant3d/generators/segmented_elbow_script_generator.py).

Golden Case: DN110 PN10 90 grados
  OD=110 THK=6.6 ID=96.8 R=165
  LE=150 Z=315
  Segmentos: [15.0, 30.0, 30.0, 15.0]
  Junta probada aqui: Gajo 2 (30 deg) / Gajo 3 (30 deg)

Evidencia real previa (ver plant3d_validation/registration_result.txt):
  V0.3.1B1     (CYLINDER+rotateY(90), Ports=1, sin setPoint)      = PASS
  V0.3.1B2     (mismo + Ports=2 + 2x s.setPoint)                  = PASS
  V0.3.1B3A    (6 piezas + translate + rotateY!=90 + uniteWith)   = PASS
  V0.3.1B3B-1  (subtractFrom() aislado, 1 tubo recto hueco)       = PASS
  V0.3.1B3B-2  (subtractFrom() en las 6 piezas, conducto continuo) = PASS
Este archivo (B3C-1) es el primero en usar BOX(...) como cuerpo
cortador -- ver HONESTY CONTRACT en
plant3d/generators/miter_joint_script_generator.py para la unica
suposicion no confirmada (convencion de origen de BOX).
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
# ---------------------------------------------------------------------------
from aqa.math import *
from varmain.primitiv import *
from varmain.custom import *


@activate(
    Group="Fitting",
    TooltipShort="Junta a inglete unica (Gajo2/Gajo3) - fixture de validacion",
    TooltipLong="V0.3.1B3C-1: una sola junta real a inglete entre dos gajos huecos, NO el codo completo. Ver docs/PLANT3D_CUSTOMSCRIPT.md, seccion V0.3.1.",
    LengthUnit="mm",
    Ports=2,
)
@group("MainDimensions")
@param(OD=LENGTH, TooltipShort="Diametro exterior", TooltipLong="OD (mm) - Golden Case: 110", Ask4Dist=True)
@param(THK=LENGTH, TooltipShort="Espesor de pared", TooltipLong="Espesor (mm) - Golden Case: 6.6. ID = OD - 2*THK.")
@param(R=LENGTH, TooltipShort="Radio de curvatura (posiciones ya horneadas)", TooltipLong="R (mm) - Golden Case: 165. Cambiar este valor en vivo NO recalcula la geometria.")
@param(LE=LENGTH, TooltipShort="Longitud tangente (no usada en este fixture)", TooltipLong="Le (mm) - Golden Case: 150. Este fixture no incluye los tramos Le.")
@param(Z=LENGTH, TooltipShort="Distancia vertice-cara (posiciones ya horneadas)", TooltipLong="Z (mm) - Golden Case: 315.")
def HDPE_SEGMENTED_ELBOW(s, OD=110, THK=6.6, R=165, LE=150, Z=315, OF=-1, K=1, **kw):
    """VALIDATION_MITER_JOINT_ONLY -- Gajo2 + Gajo3 huecos, unidos por UNA junta real a inglete.

    NO representa el codo DIN 16963 completo -- solo la junta 30/30
    (Gajo 2 / Gajo 3) del Golden Case. R/LE/Z se reciben pero las
    posiciones de las dos piezas y del plano de corte ya vienen
    horneadas desde core/geometry/segmented_elbow.py. OD/THK SI afectan
    el taladro real (radio_ext_mm/radio_int_mm abajo). Ver
    docs/PLANT3D_CUSTOMSCRIPT.md, seccion V0.3.1.
    """
    radio_ext_mm = OD / 2.0
    radio_int_mm = (OD - 2 * THK) / 2.0

    # Gajo 2 (hueco) -- mismo patron subtractFrom()+erase() ya confirmado por B3B-1/B3B-2
    ext_a = CYLINDER(s, R=radio_ext_mm, H=85.4103, O=0.0).rotateY(60).translate((-122.295, 0, 5.62224))
    int_a = CYLINDER(s, R=radio_int_mm, H=95.4103, O=-5).rotateY(60).translate((-122.295, 0, 5.62224))
    ext_a.subtractFrom(int_a)
    int_a.erase()

    # Gajo 3 (hueco)
    ext_b = CYLINDER(s, R=radio_ext_mm, H=85.4103, O=0.0).rotateY(30).translate((-48.3274, 0, 48.3274))
    int_b = CYLINDER(s, R=radio_int_mm, H=95.4103, O=-5).rotateY(30).translate((-48.3274, 0, 48.3274))
    ext_b.subtractFrom(int_b)
    int_b.erase()

    # HONESTY NOTE: BOX(...) como cuerpo cortador, primera vez en este proyecto sin
    # confirmacion de hardware -- ver HONESTY CONTRACT arriba en el modulo generador.
    # cutter_a remueve de Gajo 2 el material mas alla del plano bisectriz (lado Gajo 3).
    cutter_a = BOX(s, L=2000, W=2000, H=500).rotateY(45).translate((-755.434, -1000, 755.434))
    ext_a.subtractFrom(cutter_a)
    cutter_a.erase()

    # cutter_b remueve de Gajo 3 el material mas alla del plano bisectriz (lado Gajo 2).
    cutter_b = BOX(s, L=2000, W=2000, H=500).rotateY(225).translate((658.779, -1000, -658.779))
    ext_b.subtractFrom(cutter_b)
    cutter_b.erase()

    ext_a.uniteWith(ext_b)
    ext_b.erase()

    s.setPoint((-122.295, 0, 5.62224), (-0.866025, -0, -0.5), 0.0)
    s.setPoint((-5.62224, 0, 122.295), (0.5, 0, 0.866025), 0.0)
