"""HDPE_SEGMENTED_ELBOW.py — V0.3.1B3B-2: codo hueco (6 piezas, sin corte a inglete).

APROXIMACION DISCLOSED (ver docs/PLANT3D_CUSTOMSCRIPT.md, seccion V0.3.1):
misma cadena de 6 piezas de V0.3.1B3A (ya PASS real: rotateY/translate/
uniteWith/erase), pero cada pieza ahora es (cilindro exterior)
.subtractFrom(cilindro interior) ANTES de unirse -- el mismo patron
subtractFrom()+erase() ya confirmado en real por V0.3.1B3B-1 (tubo recto
aislado), aplicado 6 veces. Las 3 uniones internas SIGUEN siendo solapes
de tapas redondas, NO cortes a inglete (eso es V0.3.1B3C, todavia sin
implementar -- ver docstring del modulo).

Golden Case: DN110 PN10 90 grados
  OD=110 THK=6.6 ID=96.8 R=165
  LE=150 Z=315
  Segmentos: [15.0, 30.0, 30.0, 15.0]

Evidencia real previa (ver plant3d_validation/registration_result.txt):
  V0.3.1B1    (CYLINDER+rotateY(90), Ports=1, sin setPoint)     = PASS
  V0.3.1B2    (mismo + Ports=2 + 2x s.setPoint)                 = PASS
  V0.3.1B3A   (6 piezas + translate + rotateY!=90 + uniteWith)  = PASS
  V0.3.1B3B-1 (subtractFrom() aislado, 1 tubo recto hueco)      = PASS
Esta version (B3B-2) es la primera en combinar subtractFrom() con la
cadena de 6 piezas -- ninguna de las piezas individuales de B3A fue
huecada todavia en real.
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
#   - https://forums.autodesk.com/t5/autocad-plant-3d-forum/creation-of-miter-bend-without-straight-parts/td-p/11005489
#   - https://forums.autodesk.com/t5/autocad-plant-3d-forum/how-to-create-mitered-elbow-mitered-tee-amp-mitered-reducer-in/td-p/8188547
# ---------------------------------------------------------------------------
from aqa.math import *
from varmain.primitiv import *
from varmain.custom import *


@activate(
    Group="Fitting",
    TooltipShort="Codo HDPE segmentado hueco (sin corte a inglete)",
    TooltipLong="V0.3.1B3B-2: codo DIN 16963 DN110/PN10/90 -- geometria hueca real (4 gajos + 2 tramos Le, OD/ID/THK), sin corte a inglete todavia.",
    LengthUnit="mm",
    Ports=2,
)
@group("MainDimensions")
@param(OD=LENGTH, TooltipShort="Diametro exterior", TooltipLong="OD (mm) - Golden Case: 110", Ask4Dist=True)
@param(THK=LENGTH, TooltipShort="Espesor de pared (usado para el taladro)", TooltipLong="Espesor (mm) - Golden Case: 6.6. ID = OD - 2*THK.")
@param(R=LENGTH, TooltipShort="Radio de curvatura (posiciones ya horneadas)", TooltipLong="R (mm) - Golden Case: 165. Cambiar este valor en vivo NO recalcula la geometria (evita reimplementar trigonometria en Plant 3D).")
@param(LE=LENGTH, TooltipShort="Longitud tangente (posiciones ya horneadas)", TooltipLong="Le (mm) - Golden Case: 150. Mismo aviso que R.")
@param(Z=LENGTH, TooltipShort="Distancia vertice-cara (posiciones ya horneadas)", TooltipLong="Z (mm) - Golden Case: 315. Mismo aviso que R.")
def HDPE_SEGMENTED_ELBOW(s, OD=110, THK=6.6, R=165, LE=150, Z=315, OF=-1, K=1, **kw):
    """V0.3.1B3B-2 -- codo hueco real (6 piezas), sin corte a inglete todavia.

    ANGLE se mantiene fijo en 90 grados (mismo motivo que B3A: ningun tipo
    de parametro Plant 3D para angulos fue confirmado). R/LE/Z se reciben
    (mismos nombres/defaults del Golden Case) pero las posiciones de los
    6 tramos ya vienen horneadas desde core/geometry/segmented_elbow.py
    para R=165/LE=150/Z=315 -- cambiar R/LE/Z en vivo
    no recalcula la geometria todavia. OD y THK SI afectan el taladro
    real de cada pieza (radio_ext_mm/radio_int_mm abajo). Ver
    docs/PLANT3D_CUSTOMSCRIPT.md, seccion V0.3.1.
    """
    radio_ext_mm = OD / 2.0
    radio_int_mm = (OD - 2 * THK) / 2.0

    ext_0 = CYLINDER(s, R=radio_ext_mm, H=150, O=0.0).rotateY(90).translate((-315, 0, 0))  # Tramo recto Le (lado P1) (exterior)
    int_0 = CYLINDER(s, R=radio_int_mm, H=160, O=-5).rotateY(90).translate((-315, 0, 0))  # Tramo recto Le (lado P1) (interior, taladro)
    ext_0.subtractFrom(int_0)
    int_0.erase()
    ext_1 = CYLINDER(s, R=radio_ext_mm, H=43.0736, O=0.0).rotateY(82.5).translate((-165, 0, 0))  # Gajo 1 (exterior)
    int_1 = CYLINDER(s, R=radio_int_mm, H=53.0736, O=-5).rotateY(82.5).translate((-165, 0, 0))  # Gajo 1 (interior, taladro)
    ext_1.subtractFrom(int_1)
    int_1.erase()
    ext_2 = CYLINDER(s, R=radio_ext_mm, H=85.4103, O=0.0).rotateY(60).translate((-122.295, 0, 5.62224))  # Gajo 2 (exterior)
    int_2 = CYLINDER(s, R=radio_int_mm, H=95.4103, O=-5).rotateY(60).translate((-122.295, 0, 5.62224))  # Gajo 2 (interior, taladro)
    ext_2.subtractFrom(int_2)
    int_2.erase()
    ext_3 = CYLINDER(s, R=radio_ext_mm, H=85.4103, O=0.0).rotateY(30).translate((-48.3274, 0, 48.3274))  # Gajo 3 (exterior)
    int_3 = CYLINDER(s, R=radio_int_mm, H=95.4103, O=-5).rotateY(30).translate((-48.3274, 0, 48.3274))  # Gajo 3 (interior, taladro)
    ext_3.subtractFrom(int_3)
    int_3.erase()
    ext_4 = CYLINDER(s, R=radio_ext_mm, H=43.0736, O=0.0).rotateY(7.5).translate((-5.62224, 0, 122.295))  # Gajo 4 (exterior)
    int_4 = CYLINDER(s, R=radio_int_mm, H=53.0736, O=-5).rotateY(7.5).translate((-5.62224, 0, 122.295))  # Gajo 4 (interior, taladro)
    ext_4.subtractFrom(int_4)
    int_4.erase()
    ext_5 = CYLINDER(s, R=radio_ext_mm, H=150, O=0.0).rotateY(0).translate((0, 0, 165))  # Tramo recto Le (lado P2) (exterior)
    int_5 = CYLINDER(s, R=radio_int_mm, H=160, O=-5).rotateY(0).translate((0, 0, 165))  # Tramo recto Le (lado P2) (interior, taladro)
    ext_5.subtractFrom(int_5)
    int_5.erase()

    ext_0.uniteWith(ext_1)
    ext_1.erase()
    ext_0.uniteWith(ext_2)
    ext_2.erase()
    ext_0.uniteWith(ext_3)
    ext_3.erase()
    ext_0.uniteWith(ext_4)
    ext_4.erase()
    ext_0.uniteWith(ext_5)
    ext_5.erase()

    s.setPoint((-315, 0, 0), (-1, 0, 0), 0.0)
    s.setPoint((0, 0, 315), (0, 0, 1), 0.0)
