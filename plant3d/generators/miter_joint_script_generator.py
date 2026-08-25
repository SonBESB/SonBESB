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

UNCONFIRMED ASSUMPTION, explicitly disclosed (this is the one real risk
in this file): BOX's local origin/corner convention. No source found
states whether BOX(s, L, W, H) spans local [0, L] x [0, W] x [0, H] from
its origin (matching CYLINDER's confirmed O=0-starts-at-origin pattern)
or is centered on its origin. This generator ASSUMES the corner
convention (consistent with CYLINDER, the only primitive this project
has actually hardware-tested), and compensates by shifting the box's
translate target by (-L/2, -W/2) in its own local frame (rotated the
same way as the box itself) so its footprint ends up centered on the
cut plane regardless -- computed once, in Python, at generation time
(see `_rotate_y`/`_cutter_translate` below), not as a second Plant 3D
call. L and W are made deliberately huge (2000 mm, ~18x the pipe OD) so
that even if this assumption is wrong, the resulting position error is
small relative to the box size and the cut is still very likely to fall
where intended. If B3C-1 fails or visibly mis-cuts, THIS assumption is
the first thing to revisit -- and the real result either way is new
evidence for BOX's actual convention.

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
)

_CUTTER_L_MM = 2000.0
_CUTTER_W_MM = 2000.0
_CUTTER_H_MM = 500.0
_INNER_CUT_OVERHANG_MM = 5.0  # same disclosed margin as V0.3.1B3B-1/B3B-2


@dataclass(frozen=True)
class GeneratedMiterJointScript:
    script_name: str
    source_code: str
    warnings: List[str]


def _swap_yz(v: Tuple[float, float, float]) -> Tuple[float, float, float]:
    """Our (x, y, z=0) -> Plant3D (x, z, y). Same convention as
    segmented_elbow_script_generator.py."""
    return (v[0], v[2], v[1])


def _rotate_y(v: Tuple[float, float, float], theta_deg: float) -> Tuple[float, float, float]:
    """Mirrors Plant 3D's confirmed rotateY(...) behaviour
    (Ry(90)*(0,0,1) = (1,0,0), hardware-confirmed by B1/B2), so the
    lateral centering offset for the cutter box is rotated consistently
    with the box itself -- computed here in Python, not a second Plant
    3D call."""
    theta = math.radians(theta_deg)
    x, y, z = v
    return (x * math.cos(theta) + z * math.sin(theta), y, -x * math.sin(theta) + z * math.cos(theta))


def _fmt_vec(v: Tuple[float, float, float]) -> str:
    return "(" + ", ".join(f"{round(c, 6):.6g}" for c in v) + ")"


def _cutter_translate(plane_point_p3d: Tuple[float, float, float], theta_deg: float) -> Tuple[float, float, float]:
    """Plane point + the box's own (-L/2, -W/2, 0) local shift, rotated
    by the same theta as the box -- centers the box's footprint on the
    plane point under the disclosed corner-anchored assumption (see
    module docstring)."""
    local_shift = (-_CUTTER_L_MM / 2.0, -_CUTTER_W_MM / 2.0, 0.0)
    rotated_shift = _rotate_y(local_shift, theta_deg)
    return tuple(plane_point_p3d[i] + rotated_shift[i] for i in range(3))


def generate_single_miter_joint_script(
    params: ElbowParameters,
    geometry: SegmentedElbowGeometry,
    script_name: str = DEFAULT_SCRIPT_NAME,
) -> GeneratedMiterJointScript:
    """V0.3.1B3C-1: Gajo 2 + Gajo 3 (both hollow, per B3B-2's already
    real-hardware-confirmed subtractFrom pattern), joined at their real
    shared bisector plane via one BOX cutter per side. Independent
    fixture -- does not touch or import
    segmented_elbow_script_generator.py's 6-piece chain. Deterministic:
    identical (params, geometry, script_name) always produce
    byte-identical source_code.
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

    cutter_a_translate = _fmt_vec(tuple(round(c, 6) for c in _cutter_translate(plane_point_p3d, theta_cut)))
    cutter_b_translate = _fmt_vec(tuple(round(c, 6) for c in _cutter_translate(plane_point_p3d, theta_cut + 180.0)))

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

    warnings.append(
        "BOX(s, L, W, H) no tiene parametro O confirmado (a diferencia de CYLINDER) -- "
        "su convencion de origen local (esquina vs centrado) NO esta confirmada por "
        "ninguna fuente encontrada. Este generador ASUME esquina-en-origen (igual que "
        "CYLINDER con O=0) y compensa desplazando la traslacion en (-L/2, -W/2) rotado -- "
        "ver docstring del modulo. Si el corte queda mal ubicado, esta es la primera "
        "hipotesis a revisar."
    )
    warnings.append(
        "subtractFrom()+erase() por pieza y rotateY/translate SI tienen confirmacion de "
        "hardware real (B3A/B3B-1/B3B-2). BOX(...) como cuerpo cortador NUNCA fue probado "
        "en este entorno real todavia -- ese es precisamente el objetivo de B3C-1."
    )
    warnings.append(
        "El plano de corte compartido (cut_plane_end de Gajo 2 == cut_plane_start de "
        "Gajo 3) se verifico programaticamente antes de generar este script -- ver "
        "tests/test_plant3d_miter_joint_script.py."
    )
    warnings.append(
        "GEOMETRIA APROXIMADA todavia en el resto del codo: este fixture SOLO corta la "
        "junta Gajo2/Gajo3 -- no modifica ni prueba las otras dos juntas (Gajo1/Gajo2, "
        "Gajo4/leg2), eso es V0.3.1B3C-2, solo despues de que B3C-1 pase en real."
    )

    citations_block = "\n".join(f"#   - {url}" for url in SOURCE_CITATIONS)

    source = f'''"""{script_name}.py — V0.3.1B3C-1: VALIDATION_MITER_JOINT_ONLY, una sola junta real a inglete.

NO es el codo completo -- es un fixture aislado con SOLO Gajo 2 + Gajo 3
(la junta representativa 30/30 del Golden Case), cada uno ya hueco
(mismo patron subtractFrom()+erase() ya confirmado en real por B3B-1/
B3B-2), cortados contra su plano bisectriz REAL compartido (calculado
una sola vez por core/geometry/segmented_elbow.py, horneado aqui como
constantes -- ningun calculo trigonometrico se repite en este script).
NO modifica la cadena completa de 6 piezas de B3B-2 (queda intacta en
plant3d/generators/segmented_elbow_script_generator.py).

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
Este archivo (B3C-1) es el primero en usar BOX(...) como cuerpo
cortador -- ver HONESTY CONTRACT en
plant3d/generators/miter_joint_script_generator.py para la unica
suposicion no confirmada (convencion de origen de BOX).
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
    TooltipShort="Junta a inglete unica (Gajo2/Gajo3) - fixture de validacion",
    TooltipLong="V0.3.1B3C-1: una sola junta real a inglete entre dos gajos huecos, NO el codo completo. Ver docs/PLANT3D_CUSTOMSCRIPT.md, seccion V0.3.1.",
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
    ext_a = CYLINDER(s, R=radio_ext_mm, H={len_a:.6g}, O=0.0).rotateY({theta_a:.6g}).translate({start_a_p3d})
    int_a = CYLINDER(s, R=radio_int_mm, H={overhang_len_a:.6g}, O=-{_INNER_CUT_OVERHANG_MM:g}).rotateY({theta_a:.6g}).translate({start_a_p3d})
    ext_a.subtractFrom(int_a)
    int_a.erase()

    # Gajo 3 (hueco)
    ext_b = CYLINDER(s, R=radio_ext_mm, H={len_b:.6g}, O=0.0).rotateY({theta_b:.6g}).translate({start_b_p3d})
    int_b = CYLINDER(s, R=radio_int_mm, H={overhang_len_b:.6g}, O=-{_INNER_CUT_OVERHANG_MM:g}).rotateY({theta_b:.6g}).translate({start_b_p3d})
    ext_b.subtractFrom(int_b)
    int_b.erase()

    # HONESTY NOTE: BOX(...) como cuerpo cortador, primera vez en este proyecto sin
    # confirmacion de hardware -- ver HONESTY CONTRACT arriba en el modulo generador.
    # cutter_a remueve de Gajo 2 el material mas alla del plano bisectriz (lado Gajo 3).
    cutter_a = BOX(s, L={_CUTTER_L_MM:g}, W={_CUTTER_W_MM:g}, H={_CUTTER_H_MM:g}).rotateY({theta_cut:.6g}).translate({cutter_a_translate})
    ext_a.subtractFrom(cutter_a)
    cutter_a.erase()

    # cutter_b remueve de Gajo 3 el material mas alla del plano bisectriz (lado Gajo 2).
    cutter_b = BOX(s, L={_CUTTER_L_MM:g}, W={_CUTTER_W_MM:g}, H={_CUTTER_H_MM:g}).rotateY({theta_cut + 180.0:.6g}).translate({cutter_b_translate})
    ext_b.subtractFrom(cutter_b)
    cutter_b.erase()

    ext_a.uniteWith(ext_b)
    ext_b.erase()

    s.setPoint({p1_pos}, {p1_dir}, 0.0)
    s.setPoint({p2_pos}, {p2_dir}, 0.0)
'''

    return GeneratedMiterJointScript(script_name=script_name, source_code=source, warnings=warnings)
