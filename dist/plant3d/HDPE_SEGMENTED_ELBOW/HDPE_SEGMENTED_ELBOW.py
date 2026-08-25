"""HDPE_SEGMENTED_ELBOW.py — V0.3.1B3C-1R2: CUTTER VISUAL DEBUG, sin corte ejecutado.

V0.3.1B3C-1R1 (BOX centrado) se probo real y ejecuto SIN ERROR, pero
elimino Gajo A y Gajo B por completo -- solo quedo visible la caja de
calibracion (ver plant3d_validation/registration_result.txt):

  B3C-1R1_SCRIPT_EXECUTION = PASS   BOX_CREATION = PASS
  CALIBRATION_BOX_VISIBLE  = PASS
  B3C-1R1_MITER_GEOMETRY = FAIL   GAJO_A_SURVIVES_CUT = FAIL
  GAJO_B_SURVIVES_CUT    = FAIL   COMMON_CUT_PLANE = NOT_VALIDATED

Esta version es un fixture EXCLUSIVAMENTE de diagnostico: mismo Gajo 2 +
Gajo 3, mismo joint_point, misma plane_normal, mismos centros/
rotaciones de cutter que R1 (ningun numero de posicion cambio) -- pero
NO ejecuta subtractFrom/erase/uniteWith sobre los cutters. Los 4 objetos
(GAJO_A hueco, GAJO_B hueco, CUTTER_A, CUTTER_B) quedan visibles y
separados para inspeccionar fisicamente en Plant 3D antes de intentar
una tercera formula sin haber visto la geometria real de los cutters.

Toggle incluido en el script:
    DEBUG_CUTTERS = True   # esta version: cutters visibles, sin resta
    DEBUG_CUTTERS = False  # comportamiento de R1: resta real + union

No se modifico core/geometry/segmented_elbow.py, joint_point ni
plane_normal. No se avanza a B3C-2.

Golden Case: DN110 PN10 90 grados
  OD=110 THK=6.6 ID=96.8 R=165
  LE=150 Z=315
  Junta probada aqui: Gajo 2 (30 deg) / Gajo 3 (30 deg)
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
    TooltipShort="Cutter visual debug (Gajo2/Gajo3) - sin corte",
    TooltipLong="V0.3.1B3C-1R2: fixture de diagnostico -- gajos y cutters visibles, sin ejecutar el corte. Ver docs/PLANT3D_CUSTOMSCRIPT.md, seccion V0.3.1.",
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
    """CUTTER_VISUAL_DEBUG -- Gajo2 + Gajo3 huecos + ambos cutters, TODOS visibles, sin corte.

    NO representa el codo DIN 16963 completo, y en modo DEBUG_CUTTERS=True
    tampoco representa una junta a inglete real todavia -- es un
    fixture de calibracion visual. R/LE/Z se reciben pero las posiciones
    ya vienen horneadas desde core/geometry/segmented_elbow.py (sin
    modificar). Ver docs/PLANT3D_CUSTOMSCRIPT.md, seccion V0.3.1.
    """
    DEBUG_CUTTERS = True  # True = cutters visibles, sin resta. False = corte real (comportamiento R1).

    radio_ext_mm = OD / 2.0
    radio_int_mm = (OD - 2 * THK) / 2.0

    # Gajo 2 (hueco) -- taladro interior ya confirmado en real por B3B-1, se mantiene.
    ext_a = CYLINDER(s, R=radio_ext_mm, H=85.4103, O=0.0).rotateY(60).translate((-122.295, 0, 5.62224))
    int_a = CYLINDER(s, R=radio_int_mm, H=95.4103, O=-5).rotateY(60).translate((-122.295, 0, 5.62224))
    ext_a.subtractFrom(int_a)
    int_a.erase()

    # Gajo 3 (hueco)
    ext_b = CYLINDER(s, R=radio_ext_mm, H=85.4103, O=0.0).rotateY(30).translate((-48.3274, 0, 48.3274))
    int_b = CYLINDER(s, R=radio_int_mm, H=95.4103, O=-5).rotateY(30).translate((-48.3274, 0, 48.3274))
    ext_b.subtractFrom(int_b)
    int_b.erase()

    # Cutters -- MISMOS centro/rotacion que V0.3.1B3C-1R1 (ver docstring del
    # modulo generador para la verificacion algebraica). En modo debug NO se
    # restan de los gajos ni se borran, para poder inspeccionarlos por separado.
    # cutter_a: centro = joint_point + (H/2)*plane_normal (cara cercana en joint_point, mirando -normal).
    cutter_a = BOX(s, L=2000, W=2000, H=500).rotateY(45).translate((128.449, 0, 225.104))

    # cutter_b: centro = joint_point - (H/2)*plane_normal (cara cercana en joint_point, mirando +normal).
    cutter_b = BOX(s, L=2000, W=2000, H=500).rotateY(45).translate((-225.104, 0, -128.449))

    if DEBUG_CUTTERS:
        pass  # GAJO_A, GAJO_B, CUTTER_A, CUTTER_B quedan todos visibles, sin tocar.
    else:
        # Comportamiento de V0.3.1B3C-1R1 (corte real):
        ext_a.subtractFrom(cutter_a)
        cutter_a.erase()
        ext_b.subtractFrom(cutter_b)
        cutter_b.erase()
        ext_a.uniteWith(ext_b)
        ext_b.erase()

    s.setPoint((-122.295, 0, 5.62224), (-0.866025, -0, -0.5), 0.0)
    s.setPoint((-5.62224, 0, 122.295), (0.5, 0, 0.866025), 0.0)

    # CALIBRATION_BOX_TEMPORARY -- no forma parte del codo, no se une ni se
    # resta de nada. Tres dimensiones distintas (L=30, W=15, H=5) y sin
    # rotar, lejos de la geometria real, para confirmar visualmente que eje
    # mundial corresponde a cada parametro de BOX.
    calibration_box = BOX(s, L=30, W=15, H=5).rotateY(0.0).translate((800, 800, 800))
