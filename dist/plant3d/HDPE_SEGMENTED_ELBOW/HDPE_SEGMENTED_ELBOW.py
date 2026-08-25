"""HDPE_SEGMENTED_ELBOW.py — V0.3.1B3A: geometria real del codo (exterior, sin corte a inglete).

APROXIMACION DISCLOSED (ver docs/PLANT3D_CUSTOMSCRIPT.md, seccion V0.3.1):
los 4 gajos + 2 tramos Le se construyen como CYLINDER rectos, posicionados
y orientados en sus posiciones/angulos REALES (calculados una sola vez por
core/geometry/segmented_elbow.py, horneados aqui como constantes -- ningun
calculo trigonometrico se repite dentro de este script), y unidos con
uniteWith(). Las 3 uniones internas son SOLAPES de cilindros de tapa
redonda, NO cortes planos a inglete todavia (esa parte requiere una fuente
citable completa que este proyecto no ha podido leer -- WebFetch sigue
bloqueado en el sandbox de desarrollo). Tampoco incluye el taladro interior
(THK/ID) -- ver V0.3.1B3B.

Golden Case: DN110 PN10 90 grados
  OD=110 THK=6.6 R=165
  LE=150 Z=315
  Segmentos: [15.0, 30.0, 30.0, 15.0]

Evidencia real previa (ver plant3d_validation/registration_result.txt):
  V0.3.1B1 (CYLINDER+rotateY(90), Ports=1, sin setPoint)      = PASS
  V0.3.1B2 (mismo + Ports=2 + 2x s.setPoint)                  = PASS
Esta version (B3A) es la primera en usar: translate(...), angulos
rotateY != 90, y union de 6 piezas via uniteWith() -- ninguno de estos
tres elementos tiene confirmacion de hardware todavia.
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
#   - https://forums.autodesk.com/t5/autocad-plant-3d-forum/creation-of-miter-bend-without-straight-parts/td-p/11005489
#   - https://forums.autodesk.com/t5/autocad-plant-3d-forum/how-to-create-mitered-elbow-mitered-tee-amp-mitered-reducer-in/td-p/8188547
# ---------------------------------------------------------------------------
from aqa.math import *
from varmain.primitiv import *
from varmain.custom import *


@activate(
    Group="Fitting",
    TooltipShort="Codo HDPE segmentado (geometria exterior, sin corte a inglete)",
    TooltipLong="V0.3.1B3A: codo DIN 16963 DN110/PN10/90 -- geometria exterior real (4 gajos + 2 tramos Le), sin corte a inglete ni taladro interior todavia.",
    LengthUnit="mm",
    Ports=2,
)
@group("MainDimensions")
@param(OD=LENGTH, TooltipShort="Diametro exterior", TooltipLong="OD (mm) - Golden Case: 110", Ask4Dist=True)
@param(THK=LENGTH, TooltipShort="Espesor de pared (no usado en B3A)", TooltipLong="Espesor (mm) - reservado para V0.3.1B3B (taladro interior)")
@param(R=LENGTH, TooltipShort="Radio de curvatura (posiciones ya horneadas)", TooltipLong="R (mm) - Golden Case: 165. Cambiar este valor en vivo NO recalcula la geometria (evita reimplementar trigonometria en Plant 3D).")
@param(LE=LENGTH, TooltipShort="Longitud tangente (posiciones ya horneadas)", TooltipLong="Le (mm) - Golden Case: 150. Mismo aviso que R.")
@param(Z=LENGTH, TooltipShort="Distancia vertice-cara (posiciones ya horneadas)", TooltipLong="Z (mm) - Golden Case: 315. Mismo aviso que R.")
def HDPE_SEGMENTED_ELBOW(s, OD=110, THK=6.6, R=165, LE=150, Z=315, OF=-1, K=1, **kw):
    """V0.3.1B3A -- geometria exterior real del codo, sin corte a inglete ni taladro.

    ANGLE se mantiene fijo en 90 grados (no se agrega como @param): ningun
    tipo de parametro Plant 3D para angulos fue confirmado en la
    investigacion de V0.3 (solo LENGTH). THK/R/LE/Z se reciben (mismos
    nombres/defaults del Golden Case) pero las posiciones de los 6 tramos
    ya vienen horneadas desde core/geometry/segmented_elbow.py para
    R=165/LE=150/Z=315 -- cambiar R/LE/Z en vivo no recalcula la
    geometria todavia; solo OD afecta el radio real del tubo (radio_mm
    abajo). Ver docs/PLANT3D_CUSTOMSCRIPT.md, seccion V0.3.1.
    """
    radio_mm = OD / 2.0

    pieza_0 = CYLINDER(s, R=radio_mm, H=150, O=0.0).rotateY(90).translate((-315, 0, 0))  # Tramo recto Le (lado P1)
    pieza_1 = CYLINDER(s, R=radio_mm, H=43.0736, O=0.0).rotateY(82.5).translate((-165, 0, 0))  # Gajo 1
    pieza_2 = CYLINDER(s, R=radio_mm, H=85.4103, O=0.0).rotateY(60).translate((-122.295, 0, 5.62224))  # Gajo 2
    pieza_3 = CYLINDER(s, R=radio_mm, H=85.4103, O=0.0).rotateY(30).translate((-48.3274, 0, 48.3274))  # Gajo 3
    pieza_4 = CYLINDER(s, R=radio_mm, H=43.0736, O=0.0).rotateY(7.5).translate((-5.62224, 0, 122.295))  # Gajo 4
    pieza_5 = CYLINDER(s, R=radio_mm, H=150, O=0.0).rotateY(0).translate((0, 0, 165))  # Tramo recto Le (lado P2)

    pieza_0.uniteWith(pieza_1)
    pieza_1.erase()
    pieza_0.uniteWith(pieza_2)
    pieza_2.erase()
    pieza_0.uniteWith(pieza_3)
    pieza_3.erase()
    pieza_0.uniteWith(pieza_4)
    pieza_4.erase()
    pieza_0.uniteWith(pieza_5)
    pieza_5.erase()

    s.setPoint((-315, 0, 0), (-1, 0, 0), 0.0)
    s.setPoint((0, 0, 315), (0, 0, 1), 0.0)
