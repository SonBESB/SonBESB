"""V0.3.1B3C-1 — single real miter joint, isolated fixture.

Per the user's explicit staged request: validate ONE real bisector-plane
miter cut between two adjacent, already-hollow gajos before touching the
full 6-piece B3B-2 chain (which stays untouched — this is an independent
fixture, not a modification of segmented_elbow_script_generator.py).

Uses the representative 30/30 joint (Gajo 2 / Gajo 3), consuming
`ElbowSegment.axis_start/axis_end/direction/cut_plane_start/
cut_plane_end` exactly as already computed by
core/geometry/segmented_elbow.py — no trigonometry is re-derived here or
inside the generated script. `cut_plane_end` of Gajo 2 and
`cut_plane_start` of Gajo 3 are the SAME plane by construction (see that
module's `_bisector_normal`), which is exactly the property a miter
joint needs: both pieces cut against one shared plane.

HONESTY CONTRACT — investigation done before writing any of this (see
SOURCE_CITATIONS and docs/PLANT3D_CUSTOMSCRIPT.md, seccion V0.3.1):

  - BOX(s, L, W, H): confirmed literal signature (L=length, W=width,
    H=height) from a real Autodesk Community answer, which also
    explicitly states BOX has NO `O` offset parameter (unlike
    CYLINDER) -- passing one would error.
  - subtractFrom()/erase(), rotateY(...), translate(...): already
    confirmed and, for subtractFrom/rotateY/translate specifically,
    already validated on real Plant 3D 2025 hardware by
    V0.3.1B3A/B3B-1/B3B-2 (see plant3d_validation/registration_result.txt).
  - A real forum thread ("Creation of miter bend without straight
    parts") uses ARC3DS(s, D, D2, R, A, S) to build an ENTIRE multi-
    segment bend as one primitive, with PYRAMID(s, L, W, H, HT) as a
    cutting tool for the miter joints. This was investigated and
    deliberately NOT adopted here: (1) only a search-engine summary was
    reachable (WebFetch stays blocked in this sandbox), never the
    literal cut-plane math; (2) it is not confirmed whether ARC3DS
    supports the ASYMMETRIC 15-30-30-15 segmentation this project's
    Golden Case requires, versus only uniform per-segment angles -- and
    getting that wrong would silently produce the wrong fitting. This
    project's own already-validated per-piece CYLINDER approach
    (B3A/B3B) already correctly reproduces the exact asymmetric
    configuration, so BOX (not PYRAMID/ARC3DS) is used here as the
    cutting tool, keeping the already-proven CYLINDER pieces unchanged.

V0.3.1B3C-1 REAL RESULT (see plant3d_validation/registration_result.txt):
API PASS / GEOMETRY FAIL. BOX, its rotate/translate, and subtractFrom
all executed without error, but the two cut faces did NOT coincide --
a real gap/overcut. Root cause: the "BOX origin = corner" assumption
below was WRONG. This is the corrected V0.3.1B3C-1R1 version -- same
fixture (Gajo 2 + Gajo 3, same joint), only the cutter's
orientation/position algorithm changed.

CORRECTED CONVENTION (BOX is CENTERED, not corner-anchored), confirmed
by two independent pieces of real evidence:

  1. The user supplied a real Autodesk Community script excerpt:
     `s01 = BOX(s, H=L, L=paB, W=A)` used with
     `s.setPoint((-L/2.0, 0.0, 0.0), ...)` /
     `s.setPoint((L/2.0, 0.0, 0.0), ...)` -- the H-axis ports sit at
     +-L/2 from the box's own origin, i.e. the box is centered on that
     axis. A second excerpt cuts one box with another via
     `BOX(...).translate((pa03*10.0, pa03*10.0, 0.0)).rotateZ(45.0)` for
     a cutter with `H=L=pa03*20.0` -- the translate offset is exactly
     HALF the cutter's own H/L extent, which only makes sense if the box
     is centered (translating by half its own size puts one face at the
     target and the far face 1x the extent beyond it).
  2. An independent WebSearch (not prompted by the user's excerpt) found
     a third, separate example: `BOX(s, L=W, W=H, H=D).translate((0, 0,
     H / 2.0))`, described explicitly as producing a box "centered at
     H/2.0" -- the same technique, from a different source.

Given two independent real sources agree, this generator now assumes
BOX(s, L, W, H) spans local [-L/2, L/2] x [-W/2, W/2] x [-H/2, H/2] from
its own origin, and positions each cutter by translating its origin to
`joint_point +- (H/2)*plane_normal` (the sign selects which half-space
the cutter occupies) -- NO L/W compensation is needed anymore, since a
centered box's L/W footprint is automatically centered on wherever its
origin lands (this also drops the old `_rotate_y`-based lateral shift
entirely). Verified algebraically (and covered by a test) that each
cutter's near face -- center -+ (H/2)*plane_normal -- lands exactly on
joint_point, i.e. dot(X - joint_point, plane_normal) = 0 for both.

This is still new-to-hardware for THIS specific application (a plane at
an oblique, non-90-degree angle to the pieces being cut) -- if
V0.3.1B3C-1R1 still mis-cuts, the corrected convention above is very
unlikely to be the cause (it now rests on two independent real
citations plus an algebraic proof); the next thing to question would be
whether rotateY alone can reach an arbitrary plane in 3-space the same
way it did for the planar (Z=0) piece placements, or whether Plant 3D's
rotate composes around a different pivot than assumed. To help rule
that out empirically instead of guessing again, this version also drops
a small, distinctly-sized, un-rotated CALIBRATION_BOX_TEMPORARY well
away from the actual geometry (never united, never subtracted) so its
three different edge lengths (L, W, H) let a human visually confirm
which world axis each BOX parameter actually controls, per the user's
explicit request -- instead of silently re-guessing again if something
is still off.

SOURCE_CITATIONS (compiled during this file's investigation):
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Tuple

from core.geometry.segmented_elbow import SegmentedElbowGeometry
from core.models.elbow import ElbowParameters

DEFAULT_SCRIPT_NAME = "HDPE_SEGMENTED_ELBOW"

SOURCE_CITATIONS = (
    # Carried over, all now with real Plant 3D 2025 hardware confirmation
    # via B1/B2/B3A/B3B-1/B3B-2 (see plant3d_validation/registration_result.txt):
    "https://blog.autodesk.io/custom-python-scripts-for-autocad-plant-3d-part-2/",
    "https://blog.autodesk.io/custom-python-scripts-for-autocad-plant-3d-part-3/",
    "https://blog.autodesk.io/custom-python-scripts-for-autocad-plant-3d-part-4/",
    "https://static.au-uw2-prd.autodesk.com/PD1746_handout_1746_pd1746_20-_20scripting_20components_20for_20autocad_20plant_203d.pdf",
    "https://www.autodesk.com/support/technical/article/caas/tsarticles/ts/6z7yLhwAUHwiyYQaRqYdo.html",
    "https://forums.autodesk.com/autodesk/attachments/autodesk/autocad-plant-3d-forum-zh-cn/4870/1/v1_PD4214-L_Radhakrishnan_AnnexB_Custom-Script-Handout.pdf",
    "https://forums.autodesk.com/t5/autocad-plant-3d-forum/plant-3d-python-scripts-help-understanding-ask4dist/td-p/13829280",
    "https://forums.autodesk.com/t5/autocad-plant-3d-forum/rotate-have-some-problems-with-python/td-p/10782031",
    "https://forums.autodesk.com/t5/autocad-plant-3d-forum/custom-scripts/td-p/8038308",
    "https://docplayer.net/38668628-Annex-b-creating-custom-component-scripts-in-plant-3d.html",
    # New for V0.3.1B3C-1: BOX(s, L, W, H) literal signature, and the
    # real miter-bend thread (ARC3DS/PYRAMID) investigated but not
    # adopted -- see module docstring:
    "https://forums.autodesk.com/t5/autocad-plant-3d-forum/plant3d-python-libraries-assessment/td-p/12635204",
    "https://forums.autodesk.com/t5/autocad-plant-3d-forum/creation-of-miter-bend-without-straight-parts/td-p/11005489",
    "https://forums.autodesk.com/t5/autocad-plant-3d-forum/how-to-create-mitered-elbow-mitered-tee-amp-mitered-reducer-in/td-p/8188547",
    # New for V0.3.1B3C-1R1: BOX is CENTERED, not corner-anchored -- one
    # citation is the user's own real Autodesk Community excerpt (no URL
    # supplied with the message), the other an independently-found
    # WebSearch result describing the same "translate by H/2 = centered"
    # technique from a different source:
    "user-supplied Autodesk Community excerpt (V0.3.1B3C-1 real result message, no URL given): "
    "BOX(s, H=L, L=paB, W=A) with s.setPoint((-L/2.0,0,0),...)/s.setPoint((L/2.0,0,0),...); "
    "and BOX(...).translate((pa03*10.0, pa03*10.0, 0.0)).rotateZ(45.0) as a cutter with H=L=pa03*20.0",
    "https://enginine.com/2025/11/11/custom-python-scripts-for-autocad-plant-3d-case-study-of-tubing-fittings-part-1/",
)

_CUTTER_L_MM = 2000.0
_CUTTER_W_MM = 2000.0
_CUTTER_H_MM = 500.0
_INNER_CUT_OVERHANG_MM = 5.0  # same disclosed margin as V0.3.1B3B-1/B3B-2

_CALIBRATION_BOX_L_MM = 30.0
_CALIBRATION_BOX_W_MM = 15.0
_CALIBRATION_BOX_H_MM = 5.0
_CALIBRATION_BOX_TRANSLATE = (800.0, 800.0, 800.0)  # far from the real geometry, never touched by any boolean op


@dataclass(frozen=True)
class GeneratedMiterJointScript:
    script_name: str
    source_code: str
    warnings: List[str]


def _swap_yz(v: Tuple[float, float, float]) -> Tuple[float, float, float]:
    """Our (x, y, z=0) -> Plant3D (x, z, y). Same convention as
    segmented_elbow_script_generator.py."""
    return (v[0], v[2], v[1])


def _fmt_vec(v: Tuple[float, float, float]) -> str:
    return "(" + ", ".join(f"{round(c, 6):.6g}" for c in v) + ")"


def _cutter_center(
    plane_point_p3d: Tuple[float, float, float],
    normal_p3d: Tuple[float, float, float],
    sign: float,
) -> Tuple[float, float, float]:
    """Center of a centered BOX(s, L, W, H) so its near face -- center
    -+ (H/2)*normal -- lands exactly on plane_point_p3d, occupying the
    half-space on the `sign` side of the plane (sign=+1 or -1). No L/W
    compensation needed: a centered box's L/W footprint is automatically
    centered on wherever its origin (== geometric center) is placed."""
    half_h = _CUTTER_H_MM / 2.0
    return tuple(plane_point_p3d[i] + sign * half_h * normal_p3d[i] for i in range(3))


def generate_single_miter_joint_script(
    params: ElbowParameters,
    geometry: SegmentedElbowGeometry,
    script_name: str = DEFAULT_SCRIPT_NAME,
) -> GeneratedMiterJointScript:
    """V0.3.1B3C-1R1: Gajo 2 + Gajo 3 (both hollow, per B3B-2's already
    real-hardware-confirmed subtractFrom pattern), joined at their real
    shared bisector plane via one CENTERED BOX cutter per side (corrected
    convention -- see module docstring for the real V0.3.1B3C-1 result
    that revealed the old corner-anchored assumption was wrong).
    Independent fixture -- does not touch or import
    segmented_elbow_script_generator.py's 6-piece chain, and does not
    modify core/geometry/segmented_elbow.py or recompute any of its
    centerline/joint/cut-plane math. Deterministic: identical (params,
    geometry, script_name) always produce byte-identical source_code.
    """
    warnings: List[str] = []
    pieces = geometry.all_pieces
    if len(pieces) < 4:
        raise ValueError("Expected at least 4 pieces (2 stubs + >=2 gajos) to pick a representative joint.")
    gajo_a, gajo_b = pieces[2], pieces[3]  # Gajo 2, Gajo 3 -- the 30deg/30deg representative joint
    if gajo_a.cut_plane_end.point != gajo_b.cut_plane_start.point:
        raise ValueError("Gajo 2's end plane and Gajo 3's start plane must be the same shared bisector plane.")

    inside_diameter_mm = params.od_mm - 2 * params.thickness_mm
    shared_plane = gajo_a.cut_plane_end

    def piece_theta(direction: Tuple[float, float, float]) -> float:
        dx, dy, dz = direction
        if abs(dz) > 1e-6:
            warnings.append(f"direction {direction!r} has a nonzero Z component -- planar-bend assumption violated.")
        return round(math.degrees(math.atan2(dx, dy)), 6)

    theta_a = piece_theta(gajo_a.direction)
    theta_b = piece_theta(gajo_b.direction)
    theta_cut = piece_theta(shared_plane.normal)

    start_a_p3d = _fmt_vec(_swap_yz(gajo_a.axis_start))
    start_b_p3d = _fmt_vec(_swap_yz(gajo_b.axis_start))
    plane_point_p3d = _swap_yz(shared_plane.point)
    normal_p3d = _swap_yz(shared_plane.normal)

    # Corrected V0.3.1B3C-1R1 cutter placement: BOX is CENTERED (see
    # module docstring), so each cutter's center is simply
    # joint_point +- (H/2)*plane_normal -- no L/W compensation, and both
    # cutters use the SAME rotateY(theta_cut) (only the translate center
    # differs, choosing which half-space each occupies).
    cutter_a_center = _cutter_center(plane_point_p3d, normal_p3d, sign=+1.0)
    cutter_b_center = _cutter_center(plane_point_p3d, normal_p3d, sign=-1.0)
    cutter_a_translate = _fmt_vec(tuple(round(c, 6) for c in cutter_a_center))
    cutter_b_translate = _fmt_vec(tuple(round(c, 6) for c in cutter_b_center))

    len_a = round(gajo_a.length_mm, 6)
    len_b = round(gajo_b.length_mm, 6)
    overhang_len_a = round(gajo_a.length_mm + 2 * _INNER_CUT_OVERHANG_MM, 6)
    overhang_len_b = round(gajo_b.length_mm + 2 * _INNER_CUT_OVERHANG_MM, 6)

    # Ports at the two FREE (outer) ends of this isolated 2-piece
    # fixture -- Gajo 2's own start, Gajo 3's own end -- pointing
    # outward, same setPoint call shape confirmed since V0.3.1A.
    p1_pos = _fmt_vec(_swap_yz(gajo_a.axis_start))
    p1_dir = _fmt_vec(_swap_yz(tuple(-c for c in gajo_a.direction)))
    p2_pos = _fmt_vec(_swap_yz(gajo_b.axis_end))
    p2_dir = _fmt_vec(_swap_yz(gajo_b.direction))

    calibration_translate = _fmt_vec(_CALIBRATION_BOX_TRANSLATE)

    warnings.append(
        "V0.3.1B3C-1 real (script anterior) fue API PASS / GEOMETRY FAIL: BOX, rotate, "
        "translate y subtractFrom ejecutaron sin error, pero los cortes no coincidian -- "
        "la suposicion 'BOX origin = corner' era incorrecta. Esta version (R1) usa la "
        "convencion CENTRADA, respaldada por dos fuentes reales independientes (ver "
        "docstring del modulo) mas una comprobacion algebraica en "
        "tests/test_plant3d_miter_joint_script.py. Si R1 tambien falla, la convencion de "
        "BOX ya no es la primera sospecha (esta corroborada dos veces) -- revisar en su "
        "lugar si rotateY solo alcanza un subconjunto de orientaciones en 3D, usando el "
        "CALIBRATION_BOX_TEMPORARY incluido abajo."
    )
    warnings.append(
        "El plano de corte compartido (cut_plane_end de Gajo 2 == cut_plane_start de "
        "Gajo 3) se verifico programaticamente antes de generar este script, y se "
        "comprobo algebraicamente que dot(cara_cercana_del_cutter - joint_point, "
        "plane_normal) = 0 para ambos cutters -- ver tests/test_plant3d_miter_joint_script.py."
    )
    warnings.append(
        "CALIBRATION_BOX_TEMPORARY incluido: un BOX pequeno con L/W/H distintos (30/15/5mm), "
        "lejos de la geometria real, nunca unido ni restado -- solo para confirmar "
        "visualmente que eje mundial corresponde a cada parametro de BOX. Borrar esta "
        "linea una vez confirmado (no forma parte del codo)."
    )
    warnings.append(
        "GEOMETRIA APROXIMADA todavia en el resto del codo: este fixture SOLO corta la "
        "junta Gajo2/Gajo3 -- no modifica ni prueba las otras dos juntas (Gajo1/Gajo2, "
        "Gajo4/leg2), eso es V0.3.1B3C-2, solo despues de que B3C-1R1 pase en real."
    )

    citations_block = "\n".join(f"#   - {url}" for url in SOURCE_CITATIONS)

    source = f'''"""{script_name}.py — V0.3.1B3C-1R1: VALIDATION_MITER_JOINT_ONLY, cutter corregido (BOX centrado).

NO es el codo completo -- es un fixture aislado con SOLO Gajo 2 + Gajo 3
(la misma junta representativa 30/30 del Golden Case que V0.3.1B3C-1),
cada uno ya hueco (mismo patron subtractFrom()+erase() ya confirmado en
real por B3B-1/B3B-2), cortados contra su plano bisectriz REAL
compartido (calculado una sola vez por core/geometry/segmented_elbow.py,
horneado aqui como constantes -- ningun calculo trigonometrico se repite
en este script, y esa matematica NO se modifico). NO modifica la cadena
completa de 6 piezas de B3B-2 (queda intacta en
plant3d/generators/segmented_elbow_script_generator.py).

V0.3.1B3C-1 (version anterior) fue API PASS / GEOMETRY FAIL en real: las
operaciones booleanas con BOX ejecutaron sin error, pero los dos cortes
no coincidian (gap/overcut). Causa: la suposicion "BOX origin = corner"
era incorrecta. Esta version (R1) corrige SOLO el algoritmo de
posicionamiento del cutter -- usa la convencion CENTRADA de BOX,
respaldada por evidencia real independiente (ver
plant3d/generators/miter_joint_script_generator.py para el detalle
completo).

Golden Case: DN{params.dn_mm:g} {params.pn} {params.angle_deg:g} grados
  OD={params.od_mm:g} THK={params.thickness_mm:g} ID={round(inside_diameter_mm, 6):g} R={params.radius_mm:g}
  LE={params.le_mm:g} Z={geometry.z_mm:g}
  Segmentos: {params.segment_configuration.segment_angles_deg if params.segment_configuration else None}
  Junta probada aqui: Gajo 2 ({gajo_a.angle_deg:g} deg) / Gajo 3 ({gajo_b.angle_deg:g} deg)

Evidencia real previa (ver plant3d_validation/registration_result.txt):
  V0.3.1B1     (CYLINDER+rotateY(90), Ports=1, sin setPoint)      = PASS
  V0.3.1B2     (mismo + Ports=2 + 2x s.setPoint)                  = PASS
  V0.3.1B3A    (6 piezas + translate + rotateY!=90 + uniteWith)   = PASS
  V0.3.1B3B-1  (subtractFrom() aislado, 1 tubo recto hueco)       = PASS
  V0.3.1B3B-2  (subtractFrom() en las 6 piezas, conducto continuo) = PASS
  V0.3.1B3C-1  (BOX cutter, esquina-en-origen)  = API PASS / GEOMETRY FAIL
"""

# ---------------------------------------------------------------------------
# Metadata (ver docs/PLANT3D_CUSTOMSCRIPT.md para el detalle de cada fuente
# citada):
{citations_block}
# ---------------------------------------------------------------------------
from aqa.math import *
from varmain.primitiv import *
from varmain.custom import *


@activate(
    Group="Fitting",
    TooltipShort="Junta a inglete unica (Gajo2/Gajo3) - fixture de validacion R1",
    TooltipLong="V0.3.1B3C-1R1: una sola junta real a inglete entre dos gajos huecos, cutter BOX corregido a convencion centrada. NO el codo completo. Ver docs/PLANT3D_CUSTOMSCRIPT.md, seccion V0.3.1.",
    LengthUnit="mm",
    Ports=2,
)
@group("MainDimensions")
@param(OD=LENGTH, TooltipShort="Diametro exterior", TooltipLong="OD (mm) - Golden Case: {params.od_mm:g}", Ask4Dist=True)
@param(THK=LENGTH, TooltipShort="Espesor de pared", TooltipLong="Espesor (mm) - Golden Case: {params.thickness_mm:g}. ID = OD - 2*THK.")
@param(R=LENGTH, TooltipShort="Radio de curvatura (posiciones ya horneadas)", TooltipLong="R (mm) - Golden Case: {params.radius_mm:g}. Cambiar este valor en vivo NO recalcula la geometria.")
@param(LE=LENGTH, TooltipShort="Longitud tangente (no usada en este fixture)", TooltipLong="Le (mm) - Golden Case: {params.le_mm:g}. Este fixture no incluye los tramos Le.")
@param(Z=LENGTH, TooltipShort="Distancia vertice-cara (posiciones ya horneadas)", TooltipLong="Z (mm) - Golden Case: {geometry.z_mm:g}.")
def {script_name}(s, OD={params.od_mm:g}, THK={params.thickness_mm:g}, R={params.radius_mm:g}, LE={params.le_mm:g}, Z={geometry.z_mm:g}, OF=-1, K=1, **kw):
    """VALIDATION_MITER_JOINT_ONLY -- Gajo2 + Gajo3 huecos, unidos por UNA junta real a inglete (cutter corregido).

    NO representa el codo DIN 16963 completo -- solo la junta 30/30
    (Gajo 2 / Gajo 3) del Golden Case. R/LE/Z se reciben pero las
    posiciones de las dos piezas y del plano de corte ya vienen
    horneadas desde core/geometry/segmented_elbow.py (matematica NO
    modificada). OD/THK SI afectan el taladro real (radio_ext_mm/
    radio_int_mm abajo). Ver docs/PLANT3D_CUSTOMSCRIPT.md, seccion V0.3.1.
    """
    radio_ext_mm = OD / 2.0
    radio_int_mm = (OD - 2 * THK) / 2.0

    # Gajo 2 (hueco) -- mismo patron subtractFrom()+erase() ya confirmado por B3B-1/B3B-2
    ext_a = CYLINDER(s, R=radio_ext_mm, H={len_a:.6g}, O=0.0).rotateY({theta_a:.6g}).translate({start_a_p3d})
    int_a = CYLINDER(s, R=radio_int_mm, H={overhang_len_a:.6g}, O=-{_INNER_CUT_OVERHANG_MM:g}).rotateY({theta_a:.6g}).translate({start_a_p3d})
    ext_a.subtractFrom(int_a)
    int_a.erase()

    # Gajo 3 (hueco)
    ext_b = CYLINDER(s, R=radio_ext_mm, H={len_b:.6g}, O=0.0).rotateY({theta_b:.6g}).translate({start_b_p3d})
    int_b = CYLINDER(s, R=radio_int_mm, H={overhang_len_b:.6g}, O=-{_INNER_CUT_OVERHANG_MM:g}).rotateY({theta_b:.6g}).translate({start_b_p3d})
    ext_b.subtractFrom(int_b)
    int_b.erase()

    # CORREGIDO en R1: BOX centrado (ver docstring del modulo). Mismo angulo
    # rotateY(theta_cut) para AMBOS cutters -- solo el centro (translate)
    # cambia de lado, seleccionando el semiespacio correcto para cada pieza.
    # cutter_a: centro = joint_point + (H/2)*plane_normal -> quita el lado hacia Gajo 3.
    cutter_a = BOX(s, L={_CUTTER_L_MM:g}, W={_CUTTER_W_MM:g}, H={_CUTTER_H_MM:g}).rotateY({theta_cut:.6g}).translate({cutter_a_translate})
    ext_a.subtractFrom(cutter_a)
    cutter_a.erase()

    # cutter_b: centro = joint_point - (H/2)*plane_normal -> quita el lado hacia Gajo 2.
    cutter_b = BOX(s, L={_CUTTER_L_MM:g}, W={_CUTTER_W_MM:g}, H={_CUTTER_H_MM:g}).rotateY({theta_cut:.6g}).translate({cutter_b_translate})
    ext_b.subtractFrom(cutter_b)
    cutter_b.erase()

    ext_a.uniteWith(ext_b)
    ext_b.erase()

    s.setPoint({p1_pos}, {p1_dir}, 0.0)
    s.setPoint({p2_pos}, {p2_dir}, 0.0)

    # CALIBRATION_BOX_TEMPORARY -- no forma parte del codo, no se une ni se
    # resta de nada. Tres dimensiones distintas (L={_CALIBRATION_BOX_L_MM:g}, W={_CALIBRATION_BOX_W_MM:g}, H={_CALIBRATION_BOX_H_MM:g}) y sin
    # rotar, lejos de la geometria real, para confirmar visualmente que eje
    # mundial corresponde a cada parametro de BOX. Borrar una vez confirmado.
    calibration_box = BOX(s, L={_CALIBRATION_BOX_L_MM:g}, W={_CALIBRATION_BOX_W_MM:g}, H={_CALIBRATION_BOX_H_MM:g}).rotateY(0.0).translate({calibration_translate})
'''

    return GeneratedMiterJointScript(script_name=script_name, source_code=source, warnings=warnings)
