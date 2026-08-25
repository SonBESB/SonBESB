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


def generate_debug_cutters_script(
    params: ElbowParameters,
    geometry: SegmentedElbowGeometry,
    script_name: str = DEFAULT_SCRIPT_NAME,
) -> GeneratedMiterJointScript:
    """V0.3.1B3C-1R2 — CUTTER VISUAL DEBUG, no cut performed.

    V0.3.1B3C-1R1 (corrected centered-BOX cutter math) was tested on
    real AutoCAD Plant 3D 2025: the script executed with no error, but
    after running only the calibration box remained visible -- Gajo A
    and Gajo B were gone, meaning the cutters removed the ENTIRE piece
    instead of just the intended wedge.

        B3C-1R1_SCRIPT_EXECUTION = PASS, BOX_CREATION = PASS,
        CALIBRATION_BOX_VISIBLE = PASS
        B3C-1R1_MITER_GEOMETRY = FAIL, GAJO_A_SURVIVES_CUT = FAIL,
        GAJO_B_SURVIVES_CUT = FAIL, COMMON_CUT_PLANE = NOT_VALIDATED

    Per the user's explicit instruction: no third guessed formula before
    SEEING the actual cutter geometry in Plant 3D. This generator
    produces a pure diagnostic fixture -- same Gajo 2 / Gajo 3, same
    joint_point, same plane_normal, same cutter centers/rotations as
    R1 (nothing about the position math changed; only whether the
    boolean cut is actually executed) -- with a literal, in-script
    toggle:

        DEBUG_CUTTERS = True   # cutters stay visible, no subtraction
        DEBUG_CUTTERS = False  # real cut: subtractFrom + erase + union (= R1 behavior)

    R2 always generates with DEBUG_CUTTERS = True. Flipping that one
    line to False locally reproduces exactly V0.3.1B3C-1R1's cutting
    behaviour -- so once the real cutter geometry is understood from
    this visual test, the same file can be hand-edited to try a
    corrected cut without waiting for a regenerated script, though any
    actual formula change should still come from this generator once
    the real cause is confirmed.

    The gajos ARE still hollowed (ext.subtractFrom(int) + int.erase()) --
    that inner-bore subtraction is unrelated to the miter cutters and
    was already hardware-confirmed by V0.3.1B3B-1, so keeping it does
    not reintroduce any unconfirmed risk into this diagnostic.
    """
    warnings: List[str] = []
    pieces = geometry.all_pieces
    if len(pieces) < 4:
        raise ValueError("Expected at least 4 pieces (2 stubs + >=2 gajos) to pick a representative joint.")
    gajo_a, gajo_b = pieces[2], pieces[3]
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

    cutter_a_center = _cutter_center(plane_point_p3d, normal_p3d, sign=+1.0)
    cutter_b_center = _cutter_center(plane_point_p3d, normal_p3d, sign=-1.0)
    cutter_a_translate = _fmt_vec(tuple(round(c, 6) for c in cutter_a_center))
    cutter_b_translate = _fmt_vec(tuple(round(c, 6) for c in cutter_b_center))

    len_a = round(gajo_a.length_mm, 6)
    len_b = round(gajo_b.length_mm, 6)
    overhang_len_a = round(gajo_a.length_mm + 2 * _INNER_CUT_OVERHANG_MM, 6)
    overhang_len_b = round(gajo_b.length_mm + 2 * _INNER_CUT_OVERHANG_MM, 6)

    p1_pos = _fmt_vec(_swap_yz(gajo_a.axis_start))
    p1_dir = _fmt_vec(_swap_yz(tuple(-c for c in gajo_a.direction)))
    p2_pos = _fmt_vec(_swap_yz(gajo_b.axis_end))
    p2_dir = _fmt_vec(_swap_yz(gajo_b.direction))

    calibration_translate = _fmt_vec(_CALIBRATION_BOX_TRANSLATE)

    warnings.append(
        "V0.3.1B3C-1R1 real: la ejecucion paso sin error pero el corte elimino Gajo A y "
        "Gajo B por completo (solo quedo visible la caja de calibracion). Este script (R2) "
        "NO ejecuta subtractFrom/erase/uniteWith sobre los cutters -- deja todo visible "
        "(GAJO_A, GAJO_B, CUTTER_A, CUTTER_B) para diagnosticar visualmente antes de probar "
        "una tercera formula a ciegas."
    )
    warnings.append(
        "DEBUG_CUTTERS = True en esta version: cambiar esa linea a False dentro del .py ya "
        "generado reproduce el comportamiento de corte real de B3C-1R1 (subtractFrom + "
        "erase + union) sin regenerar el script -- util para retomar una vez entendida la "
        "geometria real de los cutters, aunque cualquier correccion de formula debe seguir "
        "viniendo de este generador una vez confirmada la causa."
    )
    warnings.append(
        "El taladro interior (ext.subtractFrom(int)+int.erase()) SI se mantiene -- es "
        "independiente de los cutters de inglete y ya tiene confirmacion de hardware real "
        "desde V0.3.1B3B-1, mantenerlo no reintroduce riesgo sin confirmar en este diagnostico."
    )
    warnings.append(
        "Si los 4 objetos (GAJO_A, GAJO_B, CUTTER_A, CUTTER_B) resultan dificiles de "
        "distinguir por superposicion en la vista, el siguiente paso disponible es generar "
        "copias de los cutters desplazadas una distancia conocida en Z, manteniendo "
        "documentada la posicion matematica original -- no incluido en esta version porque "
        "el usuario lo pidio solo como respaldo, no como parte obligatoria de R2."
    )

    citations_block = "\n".join(f"#   - {url}" for url in SOURCE_CITATIONS)

    source = f'''"""{script_name}.py — V0.3.1B3C-1R2: CUTTER VISUAL DEBUG, sin corte ejecutado.

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

Golden Case: DN{params.dn_mm:g} {params.pn} {params.angle_deg:g} grados
  OD={params.od_mm:g} THK={params.thickness_mm:g} ID={round(inside_diameter_mm, 6):g} R={params.radius_mm:g}
  LE={params.le_mm:g} Z={geometry.z_mm:g}
  Junta probada aqui: Gajo 2 ({gajo_a.angle_deg:g} deg) / Gajo 3 ({gajo_b.angle_deg:g} deg)
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
    TooltipShort="Cutter visual debug (Gajo2/Gajo3) - sin corte",
    TooltipLong="V0.3.1B3C-1R2: fixture de diagnostico -- gajos y cutters visibles, sin ejecutar el corte. Ver docs/PLANT3D_CUSTOMSCRIPT.md, seccion V0.3.1.",
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
    ext_a = CYLINDER(s, R=radio_ext_mm, H={len_a:.6g}, O=0.0).rotateY({theta_a:.6g}).translate({start_a_p3d})
    int_a = CYLINDER(s, R=radio_int_mm, H={overhang_len_a:.6g}, O=-{_INNER_CUT_OVERHANG_MM:g}).rotateY({theta_a:.6g}).translate({start_a_p3d})
    ext_a.subtractFrom(int_a)
    int_a.erase()

    # Gajo 3 (hueco)
    ext_b = CYLINDER(s, R=radio_ext_mm, H={len_b:.6g}, O=0.0).rotateY({theta_b:.6g}).translate({start_b_p3d})
    int_b = CYLINDER(s, R=radio_int_mm, H={overhang_len_b:.6g}, O=-{_INNER_CUT_OVERHANG_MM:g}).rotateY({theta_b:.6g}).translate({start_b_p3d})
    ext_b.subtractFrom(int_b)
    int_b.erase()

    # Cutters -- MISMOS centro/rotacion que V0.3.1B3C-1R1 (ver docstring del
    # modulo generador para la verificacion algebraica). En modo debug NO se
    # restan de los gajos ni se borran, para poder inspeccionarlos por separado.
    # cutter_a: centro = joint_point + (H/2)*plane_normal (cara cercana en joint_point, mirando -normal).
    cutter_a = BOX(s, L={_CUTTER_L_MM:g}, W={_CUTTER_W_MM:g}, H={_CUTTER_H_MM:g}).rotateY({theta_cut:.6g}).translate({cutter_a_translate})

    # cutter_b: centro = joint_point - (H/2)*plane_normal (cara cercana en joint_point, mirando +normal).
    cutter_b = BOX(s, L={_CUTTER_L_MM:g}, W={_CUTTER_W_MM:g}, H={_CUTTER_H_MM:g}).rotateY({theta_cut:.6g}).translate({cutter_b_translate})

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

    s.setPoint({p1_pos}, {p1_dir}, 0.0)
    s.setPoint({p2_pos}, {p2_dir}, 0.0)

    # CALIBRATION_BOX_TEMPORARY -- no forma parte del codo, no se une ni se
    # resta de nada. Tres dimensiones distintas (L={_CALIBRATION_BOX_L_MM:g}, W={_CALIBRATION_BOX_W_MM:g}, H={_CALIBRATION_BOX_H_MM:g}) y sin
    # rotar, lejos de la geometria real, para confirmar visualmente que eje
    # mundial corresponde a cada parametro de BOX.
    calibration_box = BOX(s, L={_CALIBRATION_BOX_L_MM:g}, W={_CALIBRATION_BOX_W_MM:g}, H={_CALIBRATION_BOX_H_MM:g}).rotateY(0.0).translate({calibration_translate})
'''

    return GeneratedMiterJointScript(script_name=script_name, source_code=source, warnings=warnings)


def _select_cutter_sign(
    midpoint_p3d: Tuple[float, float, float],
    plane_point_p3d: Tuple[float, float, float],
    normal_p3d: Tuple[float, float, float],
) -> Tuple[float, float]:
    """side = dot(midpoint - plane_point, normal). The cutter that must
    remove the excess has to occupy the half-space OPPOSITE the piece's
    own body (sign = +1 keeps the +normal half-space, sign = -1 the
    -normal one -- see _cutter_center). Returns (sign, side) so callers
    can disclose the raw side value too."""
    side = sum((midpoint_p3d[i] - plane_point_p3d[i]) * normal_p3d[i] for i in range(3))
    return (1.0 if side < 0 else -1.0), side


def generate_single_side_cut_script(
    params: ElbowParameters,
    geometry: SegmentedElbowGeometry,
    script_name: str = DEFAULT_SCRIPT_NAME,
    invert_cutter: bool = False,
) -> GeneratedMiterJointScript:
    """V0.3.1B3C-1R3A -- SINGLE SIDE CUT: only Gajo A (hollow) + one BOX
    cutter, nothing else.

    V0.3.1B3C-1R2 (visual debug, no cut) was tested on real AutoCAD
    Plant 3D 2025: GAJO_A, GAJO_B, CUTTER_A and CUTTER_B all executed and
    stayed visible; the two big cutters sit in opposite half-spaces
    around the joint and their orientation is consistent with the
    bisector plane. The one remaining unknown is empirical, not
    positional: WHICH half-space each cutter actually removes when
    subtractFrom() runs. R1's full 2-piece cut had made both gajos
    disappear entirely -- this isolates the question to the smallest
    possible real test: one gajo, one cutter, one subtractFrom().

    Per the user's explicit instruction: joint_point, plane_normal, the
    cutter centers and rotateY(45) stay EXACTLY as already computed (no
    re-derivation, no touching core/geometry/segmented_elbow.py). The
    only thing this function adds is which SIGN of _cutter_center to use
    for Gajo A, chosen automatically (never hand-guessed) from
    side_a = dot(midpoint_gajo_a - joint_point, plane_normal): the cutter
    used must occupy the half-space OPPOSITE the piece's own body. Set
    invert_cutter=True to flip that automatic choice for a follow-up
    "R3A-inverted" run without touching any other number, in case the
    real test shows Gajo A vanishing under the first choice too.

    No Gajo B, no second cutter, no uniteWith, no calibration box --
    deliberately the smallest fixture that can still answer:
    GAJO_A survives? / CUT FACE appears? / CUT FACE passes joint? /
    CORRECT HALFSPACE removed?
    """
    warnings: List[str] = []
    pieces = geometry.all_pieces
    if len(pieces) < 4:
        raise ValueError("Expected at least 4 pieces (2 stubs + >=2 gajos) to pick a representative joint.")
    gajo_a, gajo_b = pieces[2], pieces[3]
    if gajo_a.cut_plane_end.point != gajo_b.cut_plane_start.point:
        raise ValueError("Gajo 2's end plane and Gajo 3's start plane must be the same shared bisector plane.")

    shared_plane = gajo_a.cut_plane_end

    def piece_theta(direction: Tuple[float, float, float]) -> float:
        dx, dy, dz = direction
        if abs(dz) > 1e-6:
            warnings.append(f"direction {direction!r} has a nonzero Z component -- planar-bend assumption violated.")
        return round(math.degrees(math.atan2(dx, dy)), 6)

    theta_a = piece_theta(gajo_a.direction)
    theta_cut = piece_theta(shared_plane.normal)

    start_a_p3d = _fmt_vec(_swap_yz(gajo_a.axis_start))
    plane_point_p3d = _swap_yz(shared_plane.point)
    normal_p3d = _swap_yz(shared_plane.normal)

    midpoint_a = tuple((gajo_a.axis_start[i] + gajo_a.axis_end[i]) / 2.0 for i in range(3))
    midpoint_a_p3d = _swap_yz(midpoint_a)
    base_sign, side_a = _select_cutter_sign(midpoint_a_p3d, plane_point_p3d, normal_p3d)
    cutter_sign = -base_sign if invert_cutter else base_sign

    cutter_center = _cutter_center(plane_point_p3d, normal_p3d, sign=cutter_sign)
    cutter_translate = _fmt_vec(tuple(round(c, 6) for c in cutter_center))

    len_a = round(gajo_a.length_mm, 6)
    overhang_len_a = round(gajo_a.length_mm + 2 * _INNER_CUT_OVERHANG_MM, 6)

    # Single port at Gajo A's own free (outer) end -- the joint end has no
    # port, there is nothing mating with it in this isolated fixture.
    p1_pos = _fmt_vec(_swap_yz(gajo_a.axis_start))
    p1_dir = _fmt_vec(_swap_yz(tuple(-c for c in gajo_a.direction)))

    warnings.append(
        f"side_a = dot(midpoint_gajo_a - joint_point, plane_normal) = {round(side_a, 6):g} "
        f"({'negativo' if side_a < 0 else 'positivo'}) -- el cuerpo de Gajo A queda del lado "
        f"{'negativo' if side_a < 0 else 'positivo'} del plano de junta. El cutter usado ocupa "
        f"el semiespacio {'positivo' if cutter_sign > 0 else 'negativo'} "
        f"(sign={cutter_sign:+.1f}{', INVERTIDO respecto del calculo automatico' if invert_cutter else ' -- lado opuesto al cuerpo, calculado automaticamente'})."
    )
    warnings.append(
        "V0.3.1B3C-1R2 real: GAJO_A, GAJO_B, CUTTER_A y CUTTER_B se vieron simultaneamente, "
        "en semiespacios opuestos, orientacion coherente con el plano bisector. La incertidumbre "
        "restante es unicamente cual semiespacio elimina realmente cada cutter al ejecutar "
        "subtractFrom() -- este fixture aisla esa pregunta al minimo: un gajo, un cutter, un corte."
    )
    warnings.append(
        "Fixture MINIMO a proposito: sin Gajo B, sin segundo cutter, sin uniteWith, sin "
        "calibration box. joint_point, plane_normal, rotateY(45) y el calculo de "
        "_cutter_center() NO cambiaron respecto de R1/R2 -- solo se decidio automaticamente "
        "que signo de semiespacio usar para Gajo A."
    )
    if not invert_cutter:
        warnings.append(
            "Si Gajo A desaparece por completo con este cutter, NO modificar joint_point, "
            "plane_normal ni core/geometry/segmented_elbow.py -- pedir la variante "
            "R3A-inverted (generate_single_side_cut_script(..., invert_cutter=True)), que usa "
            "el cutter del semiespacio contrario sin tocar ningun otro numero."
        )

    citations_block = "\n".join(f"#   - {url}" for url in SOURCE_CITATIONS)

    source = f'''"""{script_name}.py — V0.3.1B3C-1{"R3A-inverted" if invert_cutter else "R3A"}: SINGLE SIDE CUT, solo Gajo A + un cutter.

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
side_a = dot(midpoint_gajo_a - joint_point, plane_normal) = {round(side_a, 6):g}
({"negativo" if side_a < 0 else "positivo"}) -- el cutter debe ocupar el
semiespacio CONTRARIO al cuerpo del gajo, sign={cutter_sign:+.1f}.
{"Variante INVERTIDA: usa el signo contrario al calculo automatico (pedida solo si la variante base hizo desaparecer Gajo A)." if invert_cutter else ""}

No se modifico core/geometry/segmented_elbow.py, joint_point ni
plane_normal. No se avanza a Gajo B ni a B3C-2.

Verificar en Plant 3D:
  GAJO_A survives?            (deberia sobrevivir, no desaparecer)
  CUT FACE appears?           (deberia verse una cara de corte nueva)
  CUT FACE passes joint?      (la cara deberia pasar por el punto de union)
  CORRECT HALFSPACE removed?  (debe quitar solo la cuna, no toda la pieza)

Golden Case: DN{params.dn_mm:g} {params.pn} {params.angle_deg:g} grados
  OD={params.od_mm:g} THK={params.thickness_mm:g} R={params.radius_mm:g}
  LE={params.le_mm:g} Z={geometry.z_mm:g}
  Pieza probada aqui: Gajo 2 ({gajo_a.angle_deg:g} deg), sin Gajo 3.
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
    TooltipShort="Single side cut (Gajo A) - fixture minimo de diagnostico",
    TooltipLong="V0.3.1B3C-1{"R3A-inverted" if invert_cutter else "R3A"}: solo Gajo A hueco + un cutter BOX, un solo subtractFrom. Ver docs/PLANT3D_CUSTOMSCRIPT.md, seccion V0.3.1.",
    LengthUnit="mm",
    Ports=1,
)
@group("MainDimensions")
@param(OD=LENGTH, TooltipShort="Diametro exterior", TooltipLong="OD (mm) - Golden Case: {params.od_mm:g}", Ask4Dist=True)
@param(THK=LENGTH, TooltipShort="Espesor de pared", TooltipLong="Espesor (mm) - Golden Case: {params.thickness_mm:g}. ID = OD - 2*THK.")
@param(R=LENGTH, TooltipShort="Radio de curvatura (posiciones ya horneadas)", TooltipLong="R (mm) - Golden Case: {params.radius_mm:g}. Cambiar este valor en vivo NO recalcula la geometria.")
@param(LE=LENGTH, TooltipShort="Longitud tangente (no usada en este fixture)", TooltipLong="Le (mm) - Golden Case: {params.le_mm:g}. Este fixture no incluye los tramos Le.")
@param(Z=LENGTH, TooltipShort="Distancia vertice-cara (posiciones ya horneadas)", TooltipLong="Z (mm) - Golden Case: {geometry.z_mm:g}.")
def {script_name}(s, OD={params.od_mm:g}, THK={params.thickness_mm:g}, R={params.radius_mm:g}, LE={params.le_mm:g}, Z={geometry.z_mm:g}, OF=-1, K=1, **kw):
    """SINGLE_SIDE_CUT -- solo Gajo A hueco + un cutter BOX, un solo subtractFrom.

    NO representa el codo completo ni siquiera una junta a inglete
    completa -- es el fixture minimo para verificar que semiespacio
    elimina realmente un cutter BOX. Ver docs/PLANT3D_CUSTOMSCRIPT.md,
    seccion V0.3.1.
    """
    radio_ext_mm = OD / 2.0
    radio_int_mm = (OD - 2 * THK) / 2.0

    # Gajo A (hueco) -- taladro interior ya confirmado en real por B3B-1.
    ext_a = CYLINDER(s, R=radio_ext_mm, H={len_a:.6g}, O=0.0).rotateY({theta_a:.6g}).translate({start_a_p3d})
    int_a = CYLINDER(s, R=radio_int_mm, H={overhang_len_a:.6g}, O=-{_INNER_CUT_OVERHANG_MM:g}).rotateY({theta_a:.6g}).translate({start_a_p3d})
    ext_a.subtractFrom(int_a)
    int_a.erase()

    # Un solo cutter -- mismo joint_point/plane_normal/rotateY(45) que R1/R2,
    # semiespacio elegido automaticamente (side_a={round(side_a, 6):g}, sign={cutter_sign:+.1f}).
    cutter_a = BOX(s, L={_CUTTER_L_MM:g}, W={_CUTTER_W_MM:g}, H={_CUTTER_H_MM:g}).rotateY({theta_cut:.6g}).translate({cutter_translate})
    ext_a.subtractFrom(cutter_a)
    cutter_a.erase()

    s.setPoint({p1_pos}, {p1_dir}, 0.0)
'''

    return GeneratedMiterJointScript(script_name=script_name, source_code=source, warnings=warnings)


def generate_axis_corrected_side_cut_script(
    params: ElbowParameters,
    geometry: SegmentedElbowGeometry,
    script_name: str = DEFAULT_SCRIPT_NAME,
) -> GeneratedMiterJointScript:
    """V0.3.1B3C-1R4 -- CORRECT BOX AXIS MAPPING.

    R3A and R3A-inverted BOTH made Gajo A vanish completely on real
    hardware, under opposite half-space signs. That symmetry rules out
    the half-space sign as the cause (see
    plant3d_validation/registration_result.txt) and points at the
    cutter's actual SIZE along the rotated axis: BOX(s, L=2000, W=2000,
    H=500) assumed `H` controls the local-Z extent (the axis rotateY
    orients toward plane_normal), by analogy with CYLINDER's H. That
    analogy was never itself cited -- and re-reading the ALREADY-cited
    real excerpt in SOURCE_CITATIONS more carefully contradicts it:

        BOX(s, H=L, L=paB, W=A) used with
        s.setPoint((-L/2.0, 0.0, 0.0), ...) / s.setPoint((L/2.0, 0.0, 0.0), ...)

    Both ports sit on the LOCAL X AXIS (Y=Z=0), at +-L/2, and that same
    `L` value was passed to BOX's `H=` keyword -- i.e. `H` controls the
    local X extent, not Z. Combined with the real double-FAIL, the
    working hypothesis for this round is:

        BOX H -> local X      BOX L -> local Y      BOX W -> local Z

    (not L->X, W->Y, H->Z as R1/R2/R3A assumed). This is a corrected
    reading of evidence already on file, not a new unconfirmed source.

    Only the cutter's BOX(...) call changes: the thin (500mm) dimension
    now goes to `W` (the hypothesized local-Z/rotateY-oriented axis)
    instead of `H`, and the two large (2000mm) dimensions go to `H` and
    `L`. _cutter_center()'s math is untouched (still
    joint_point +- (thin/2)*plane_normal = +-250mm), joint_point,
    plane_normal, rotateY(45) for the cutter, rotateY(60) for Gajo A,
    and the half-space SIGN (same automatic side_a-based choice as
    R3A's base, non-inverted, variant per the user's explicit
    instruction not to re-test inversion this round) are all identical
    to prior rounds. No Gajo B, no uniteWith, no calibration box,
    Ports=1 -- same minimal fixture shape as R3A.
    """
    warnings: List[str] = []
    pieces = geometry.all_pieces
    if len(pieces) < 4:
        raise ValueError("Expected at least 4 pieces (2 stubs + >=2 gajos) to pick a representative joint.")
    gajo_a, gajo_b = pieces[2], pieces[3]
    if gajo_a.cut_plane_end.point != gajo_b.cut_plane_start.point:
        raise ValueError("Gajo 2's end plane and Gajo 3's start plane must be the same shared bisector plane.")

    shared_plane = gajo_a.cut_plane_end

    def piece_theta(direction: Tuple[float, float, float]) -> float:
        dx, dy, dz = direction
        if abs(dz) > 1e-6:
            warnings.append(f"direction {direction!r} has a nonzero Z component -- planar-bend assumption violated.")
        return round(math.degrees(math.atan2(dx, dy)), 6)

    theta_a = piece_theta(gajo_a.direction)
    theta_cut = piece_theta(shared_plane.normal)

    start_a_p3d = _fmt_vec(_swap_yz(gajo_a.axis_start))
    plane_point_p3d = _swap_yz(shared_plane.point)
    normal_p3d = _swap_yz(shared_plane.normal)

    midpoint_a = tuple((gajo_a.axis_start[i] + gajo_a.axis_end[i]) / 2.0 for i in range(3))
    midpoint_a_p3d = _swap_yz(midpoint_a)
    cutter_sign, side_a = _select_cutter_sign(midpoint_a_p3d, plane_point_p3d, normal_p3d)

    cutter_center = _cutter_center(plane_point_p3d, normal_p3d, sign=cutter_sign)
    cutter_translate = _fmt_vec(tuple(round(c, 6) for c in cutter_center))

    len_a = round(gajo_a.length_mm, 6)
    overhang_len_a = round(gajo_a.length_mm + 2 * _INNER_CUT_OVERHANG_MM, 6)

    p1_pos = _fmt_vec(_swap_yz(gajo_a.axis_start))
    p1_dir = _fmt_vec(_swap_yz(tuple(-c for c in gajo_a.direction)))

    warnings.append(
        "V0.3.1B3C-1R3A y R3A-inverted real: Gajo A desaparecio por completo en AMBOS signos "
        "de semiespacio -- eso descarta el signo como causa y apunta al TAMANO del cutter en el "
        "eje rotado. Releyendo la MISMA cita ya presente en SOURCE_CITATIONS (BOX(s, H=L, L=paB, "
        "W=A) con puertos en (-L/2,0,0)/(L/2,0,0), ambos sobre el eje local X, con ese mismo L "
        "pasado al parametro H=) se concluye que H controla el eje local X, no Z -- la analogia "
        "con CYLINDER (H=Z) nunca estuvo citada para BOX. Esta version (R4) usa "
        "H=2000/L=2000/W=500 en vez de L=2000/W=2000/H=500 -- el valor delgado (500mm) ahora va "
        "en W, la hipotesis de que W es el eje que rotateY orienta hacia plane_normal."
    )
    warnings.append(
        f"joint_point, plane_normal, rotateY(45) del cutter, rotateY(60) de Gajo A y el signo de "
        f"semiespacio (side_a={round(side_a, 6):g}, sign={cutter_sign:+.1f}, MISMO que R3A base, "
        f"no invertido por instruccion explicita del usuario) no cambiaron. Solo cambio la "
        f"asignacion de valores a los parametros H/L/W de BOX."
    )
    warnings.append(
        "Fixture minimo sin cambios: sin Gajo B, sin segundo cutter, sin uniteWith, sin "
        "calibration box, Ports=1 con un solo s.setPoint() en el extremo libre de Gajo A."
    )

    citations_block = "\n".join(f"#   - {url}" for url in SOURCE_CITATIONS)

    source = f'''"""{script_name}.py — V0.3.1B3C-1R4: CORRECT BOX AXIS MAPPING (H=X, L=Y, W=Z).

V0.3.1B3C-1R3A y R3A-inverted se probaron reales: Gajo A desaparecio
por completo en AMBOS signos de semiespacio, descartando el signo como
causa. Releyendo la cita ya presente en SOURCE_CITATIONS
(BOX(s, H=L, L=paB, W=A) con puertos en (-L/2,0,0)/(L/2,0,0), ambos
sobre el eje local X, con ese mismo L pasado a H=) se concluye que BOX
`H` controla el eje local X, no Z como se asumia por analogia con
CYLINDER (nunca citada para BOX).

Esta version cambia UNICAMENTE la asignacion de valores del cutter:
H=2000, L=2000, W=500 (antes L=2000, W=2000, H=500) -- el valor delgado
va ahora en W, hipotesis de que W es el eje que rotateY(45) orienta
hacia plane_normal. joint_point, plane_normal, rotateY(45),
rotateY(60) de Gajo A y el signo de semiespacio
(side_a={round(side_a, 6):g}, sign={cutter_sign:+.1f}, igual que R3A base,
NO invertido) no cambiaron.

Sin Gajo B, sin uniteWith, sin calibration box. No se modifico
core/geometry/segmented_elbow.py, joint_point ni plane_normal.

Verificar en Plant 3D:
  GAJO_A survives?            (deberia sobrevivir, no desaparecer)
  inclined cut face?          (deberia verse una cara de corte inclinada)
  cut passes joint point?     (la cara deberia pasar por el punto de union)

Golden Case: DN{params.dn_mm:g} {params.pn} {params.angle_deg:g} grados
  OD={params.od_mm:g} THK={params.thickness_mm:g} R={params.radius_mm:g}
  LE={params.le_mm:g} Z={geometry.z_mm:g}
  Pieza probada aqui: Gajo 2 ({gajo_a.angle_deg:g} deg), sin Gajo 3.
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
    TooltipShort="Axis-corrected side cut (Gajo A) - fixture minimo R4",
    TooltipLong="V0.3.1B3C-1R4: solo Gajo A hueco + un cutter BOX con mapeo de ejes corregido (H=X, L=Y, W=Z), un solo subtractFrom. Ver docs/PLANT3D_CUSTOMSCRIPT.md, seccion V0.3.1.",
    LengthUnit="mm",
    Ports=1,
)
@group("MainDimensions")
@param(OD=LENGTH, TooltipShort="Diametro exterior", TooltipLong="OD (mm) - Golden Case: {params.od_mm:g}", Ask4Dist=True)
@param(THK=LENGTH, TooltipShort="Espesor de pared", TooltipLong="Espesor (mm) - Golden Case: {params.thickness_mm:g}. ID = OD - 2*THK.")
@param(R=LENGTH, TooltipShort="Radio de curvatura (posiciones ya horneadas)", TooltipLong="R (mm) - Golden Case: {params.radius_mm:g}. Cambiar este valor en vivo NO recalcula la geometria.")
@param(LE=LENGTH, TooltipShort="Longitud tangente (no usada en este fixture)", TooltipLong="Le (mm) - Golden Case: {params.le_mm:g}. Este fixture no incluye los tramos Le.")
@param(Z=LENGTH, TooltipShort="Distancia vertice-cara (posiciones ya horneadas)", TooltipLong="Z (mm) - Golden Case: {geometry.z_mm:g}.")
def {script_name}(s, OD={params.od_mm:g}, THK={params.thickness_mm:g}, R={params.radius_mm:g}, LE={params.le_mm:g}, Z={geometry.z_mm:g}, OF=-1, K=1, **kw):
    """AXIS_CORRECTED_SIDE_CUT -- solo Gajo A hueco + un cutter BOX (H=X, L=Y, W=Z), un solo subtractFrom.

    NO representa el codo completo ni siquiera una junta a inglete
    completa -- es el fixture minimo para verificar el mapeo de ejes
    H/L/W de BOX. Ver docs/PLANT3D_CUSTOMSCRIPT.md, seccion V0.3.1.
    """
    radio_ext_mm = OD / 2.0
    radio_int_mm = (OD - 2 * THK) / 2.0

    # Gajo A (hueco) -- taladro interior ya confirmado en real por B3B-1.
    ext_a = CYLINDER(s, R=radio_ext_mm, H={len_a:.6g}, O=0.0).rotateY({theta_a:.6g}).translate({start_a_p3d})
    int_a = CYLINDER(s, R=radio_int_mm, H={overhang_len_a:.6g}, O=-{_INNER_CUT_OVERHANG_MM:g}).rotateY({theta_a:.6g}).translate({start_a_p3d})
    ext_a.subtractFrom(int_a)
    int_a.erase()

    # Un solo cutter -- mismo joint_point/plane_normal/rotateY(45) que R1-R3A,
    # mismo signo de semiespacio (side_a={round(side_a, 6):g}, sign={cutter_sign:+.1f}, no invertido).
    # CORREGIDO en R4: el valor delgado (500mm) va en W, no en H (ver docstring del modulo).
    cutter_a = BOX(s, H={_CUTTER_L_MM:g}, L={_CUTTER_W_MM:g}, W={_CUTTER_H_MM:g}).rotateY({theta_cut:.6g}).translate({cutter_translate})
    ext_a.subtractFrom(cutter_a)
    cutter_a.erase()

    s.setPoint({p1_pos}, {p1_dir}, 0.0)
'''

    return GeneratedMiterJointScript(script_name=script_name, source_code=source, warnings=warnings)
