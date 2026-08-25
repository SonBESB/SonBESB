"""V0.3.1B3A — real segmented-elbow exterior geometry (no miter cuts yet).

Builds on the two real-hardware PASSes recorded in
plant3d_validation/registration_result.txt:

    V0.3.1B1: CYLINDER(s, R=, H=, O=0.0).rotateY(...) alone -- PASS
    V0.3.1B2: same geometry + Ports=2 + 2x s.setPoint(...) -- PASS

This module takes the next step the user asked for: the real DN110/
PN10/90 segmented elbow (4 gajos + 2 Le stubs, 15-30-30-15), consuming
the ALREADY-BUILT `SegmentedElbowGeometry` from
core/geometry/segmented_elbow.py -- no second, independent trigonometry
implementation is written here or inside the generated script (the
generated .py cannot `import core...` anyway once copied into Plant 3D's
own Python environment, so every position/direction/length is computed
ONCE by our own tested engine and baked into the generated script as
literal numbers, exactly like custom_script_generator.py already does
for GOLDEN_CASE_PARAMETERS/GOLDEN_CASE_PORTS).

HONESTY CONTRACT -- read before editing (same standard as every other
V0.3/V0.3.1 module): every Plant 3D API element used below is backed by
a real source, see SOURCE_CITATIONS. What is explicitly NOT attempted
here:

  - True miter cuts (flat bisector-plane cuts between adjacent gajos).
    A real "creation of miter bend" forum thread was found describing a
    working script using ARC3DS/PYRAMID + rotateX/rotateZ + translate +
    subtractFrom for exactly this -- but WebFetch is blocked in this
    sandbox, so only a search-engine SUMMARY of that thread was
    reachable, never its literal code or the cut-plane math. Inventing
    that math from a paraphrase would violate the project's
    NO INVENTAR API DE PLANT 3D rule. Until that thread's real content
    (or an equivalent literal source) is available, this generator
    instead builds each gajo as a plain, un-cut CYLINDER positioned and
    oriented along the real segment axis, and unites all six pieces
    (2 Le stubs + 4 gajos) end to end. The result is a faceted,
    round-ended "sausage" silhouette that bends through the correct real
    angles at the correct real positions -- NOT a flat-mitered solid.
    This is exactly the disclosed simplification the user authorized
    ("B3A = geometria exterior ... no esconder esa simplificacion").
  - The hollow bore (ID = OD - 2*THK). subtractFrom() IS confirmed (see
    SOURCE_CITATIONS) and would be low-risk to add (a second, same-axis
    cylinder per piece), but is deliberately deferred to V0.3.1B3B so a
    real-hardware failure, if any, can be isolated to either the
    6-piece union (this file) or the hollow subtraction (B3B) -- the
    same one-variable-at-a-time discipline that made B1/B2 succeed.

Composition-order note (translate/rotateY): the one literal real example
found for `.translate(...)` chains it as
`CYLINDER(...).translate((0,0,H1))`, i.e. translate directly after
construction, with no rotation shown in that same chain. This project's
own B1/B2 evidence only confirms `CYLINDER(...).rotateY(angle)` with NO
translate at all. To avoid GUESSING whether Plant 3D composes
rotate-then-translate the same way as translate-then-rotate (their
results generally differ unless rotation pivots on the object's own
current position), every piece below is built as
`CYLINDER(...).rotateY(theta).translate(start)`: rotate FIRST, while the
piece is still based at the local origin (so rotating "about the
object" and "about the world origin" are identical -- the ambiguity is
moot), THEN translate exactly once to its final position (so whether
translate means "move to this absolute point" or "move by this offset"
is also moot, since the pre-translate position IS the origin). This
sidesteps two unconfirmed semantics instead of guessing either one.

Coordinate mapping: core/geometry/segmented_elbow.py builds the elbow in
its own XY plane (every z coordinate is exactly 0 -- see that module's
docstring). This project's only hardware-confirmed rotation
(`rotateY(90)` maps the CYLINDER's local Z axis to global +X, confirmed
by B1/B2) reaches exactly the Plant 3D XZ plane, not XY. Rather than
guess how rotateY/rotateZ compose together (unconfirmed), every point
and direction below is remapped by swapping the Y and Z components
(our (x, y, 0) -> Plant3D (x, 0, y)) so the whole bend is reproduced
using ONLY the single, already-hardware-confirmed rotateY axis. This is
a disclosed coordinate choice made by this generator, not a Plant 3D API
call -- it does not need a citation.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Tuple

from core.geometry.segmented_elbow import SegmentedElbowGeometry
from core.models.elbow import ElbowParameters

DEFAULT_SCRIPT_NAME = "HDPE_SEGMENTED_ELBOW"

SOURCE_CITATIONS = (
    # Carried over from V0.3/V0.3.1 (decorators, imports, CYLINDER,
    # rotateY, setPoint, entry point convention, Ask4Dist, OF/K
    # signature) -- all now additionally confirmed on real Plant 3D 2025
    # hardware via V0.3.1B1/B2, see plant3d_validation/registration_result.txt.
    "https://blog.autodesk.io/custom-python-scripts-for-autocad-plant-3d-part-2/",
    "https://blog.autodesk.io/custom-python-scripts-for-autocad-plant-3d-part-3/",
    "https://blog.autodesk.io/custom-python-scripts-for-autocad-plant-3d-part-4/",
    "https://static.au-uw2-prd.autodesk.com/PD1746_handout_1746_pd1746_20-_20scripting_20components_20for_20autocad_20plant_203d.pdf",
    "https://www.autodesk.com/support/technical/article/caas/tsarticles/ts/6z7yLhwAUHwiyYQaRqYdo.html",
    "https://forums.autodesk.com/autodesk/attachments/autodesk/autocad-plant-3d-forum-zh-cn/4870/1/v1_PD4214-L_Radhakrishnan_AnnexB_Custom-Script-Handout.pdf",
    "https://forums.autodesk.com/t5/autocad-plant-3d-forum/plant-3d-python-scripts-help-understanding-ask4dist/td-p/13829280",
    # New for V0.3.1B3A: translate()/rotateZ() literal quote, and the
    # BOX/CYLINDER/CONE/ARC3D/HALFSPHERE/TORUS + uniteWith/subtractFrom/
    # intersectWith primitive+modifier vocabulary (uniteWith used below;
    # subtractFrom/intersectWith NOT used yet, reserved for B3B/mitering):
    "https://forums.autodesk.com/t5/autocad-plant-3d-forum/rotate-have-some-problems-with-python/td-p/10782031",
    "https://forums.autodesk.com/t5/autocad-plant-3d-forum/custom-scripts/td-p/8038308",
    # Real miter-bend script exists here (ARC3DS/PYRAMID + subtractFrom)
    # but only a search-summary was reachable, not the literal code --
    # cited so the next investigator goes straight to it instead of
    # re-deriving the miter math from scratch:
    "https://forums.autodesk.com/t5/autocad-plant-3d-forum/creation-of-miter-bend-without-straight-parts/td-p/11005489",
    "https://forums.autodesk.com/t5/autocad-plant-3d-forum/how-to-create-mitered-elbow-mitered-tee-amp-mitered-reducer-in/td-p/8188547",
)


@dataclass(frozen=True)
class GeneratedElbowScript:
    script_name: str
    source_code: str
    warnings: List[str]


def _swap_yz(v: Tuple[float, float, float]) -> Tuple[float, float, float]:
    """Our (x, y, z=0) -> Plant3D (x, z, y). See module docstring."""
    return (v[0], v[2], v[1])


def _fmt_vec(v: Tuple[float, float, float]) -> str:
    return "(" + ", ".join(f"{round(c, 6):.6g}" for c in v) + ")"


def generate_segmented_elbow_script(
    params: ElbowParameters,
    geometry: SegmentedElbowGeometry,
    script_name: str = DEFAULT_SCRIPT_NAME,
) -> GeneratedElbowScript:
    """Bakes geometry.all_pieces (already computed by
    core/geometry/segmented_elbow.py) into literal CYLINDER/rotateY/
    translate calls, united into one exterior solid, plus the two real
    ports. Deterministic: identical (params, geometry, script_name)
    always produce byte-identical source_code.
    """
    warnings: List[str] = []
    pieces = geometry.all_pieces

    piece_lines = []
    var_names = []
    for i, piece in enumerate(pieces):
        dx, dy, dz = piece.direction
        if abs(dz) > 1e-6:
            warnings.append(
                f"{piece.label}: direction has a nonzero Z component ({dz!r}) -- "
                "this generator assumes a planar (Z=0) bend, per "
                "core/geometry/segmented_elbow.py's own documented construction."
            )
        theta_deg = math.degrees(math.atan2(dx, dy))
        start_p3d = _swap_yz(piece.axis_start)
        var = f"pieza_{i}"
        var_names.append(var)
        piece_lines.append(
            f"    {var} = CYLINDER(s, R=radio_mm, H={round(piece.length_mm, 6):.6g}, O=0.0)"
            f".rotateY({round(theta_deg, 6):.6g}).translate({_fmt_vec(start_p3d)})"
            f"  # {piece.label}"
        )

    union_lines = []
    for var in var_names[1:]:
        union_lines.append(f"    {var_names[0]}.uniteWith({var})")
        union_lines.append(f"    {var}.erase()")

    p1 = geometry.ports[0]
    p2 = geometry.ports[1]
    p1_pos = _swap_yz(p1.position_mm)
    p1_dir = _swap_yz(p1.direction)
    p2_pos = _swap_yz(p2.position_mm)
    p2_dir = _swap_yz(p2.direction)

    warnings.append(
        "uniteWith(...) se asume que necesita .erase() en el segundo objeto por "
        "analogia con subtractFrom()/intersectWith() (unica fuente que confirma "
        "explicitamente el patron .erase() tras una operacion booleana) -- no hay "
        "una cita literal de uniteWith()+erase() especificamente. Si Plant 3D se "
        "queja de un objeto fantasma o de una llamada .erase() invalida, esa es "
        "la primera hipotesis a revisar."
    )
    warnings.append(
        "Union de 6 piezas + angulos rotateY distintos de 90 (82.5/60/30/7.5/0) "
        "nunca antes probados en este entorno real -- solo rotateY(90) tiene "
        "confirmacion de hardware (V0.3.1B1/B2). Si falla, aislar probando "
        "primero union de solo 2 piezas antes de las 6."
    )
    warnings.append(
        "GEOMETRIA APROXIMADA: los 6 tramos son cilindros rectos sin corte a "
        "inglete -- las 3 juntas internas entre gajos son solapes de tapas "
        "redondas, no cortes planos a bisectriz. Ver docstring del modulo para "
        "por que (miter real diferido a B3-cortes, pendiente de una fuente "
        "citable completa)."
    )

    citations_block = "\n".join(f"#   - {url}" for url in SOURCE_CITATIONS)
    pieces_block = "\n".join(piece_lines)
    union_block = "\n".join(union_lines)

    source = f'''"""{script_name}.py — V0.3.1B3A: geometria real del codo (exterior, sin corte a inglete).

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

Golden Case: DN{params.dn_mm:g} {params.pn} {params.angle_deg:g} grados
  OD={params.od_mm:g} THK={params.thickness_mm:g} R={params.radius_mm:g}
  LE={params.le_mm:g} Z={geometry.z_mm:g}
  Segmentos: {params.segment_configuration.segment_angles_deg if params.segment_configuration else None}

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
{citations_block}
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
@param(OD=LENGTH, TooltipShort="Diametro exterior", TooltipLong="OD (mm) - Golden Case: {params.od_mm:g}", Ask4Dist=True)
@param(THK=LENGTH, TooltipShort="Espesor de pared (no usado en B3A)", TooltipLong="Espesor (mm) - reservado para V0.3.1B3B (taladro interior)")
@param(R=LENGTH, TooltipShort="Radio de curvatura (posiciones ya horneadas)", TooltipLong="R (mm) - Golden Case: {params.radius_mm:g}. Cambiar este valor en vivo NO recalcula la geometria (evita reimplementar trigonometria en Plant 3D).")
@param(LE=LENGTH, TooltipShort="Longitud tangente (posiciones ya horneadas)", TooltipLong="Le (mm) - Golden Case: {params.le_mm:g}. Mismo aviso que R.")
@param(Z=LENGTH, TooltipShort="Distancia vertice-cara (posiciones ya horneadas)", TooltipLong="Z (mm) - Golden Case: {geometry.z_mm:g}. Mismo aviso que R.")
def {script_name}(s, OD={params.od_mm:g}, THK={params.thickness_mm:g}, R={params.radius_mm:g}, LE={params.le_mm:g}, Z={geometry.z_mm:g}, OF=-1, K=1, **kw):
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

{pieces_block}

{union_block}

    s.setPoint({_fmt_vec(p1_pos)}, {_fmt_vec(p1_dir)}, 0.0)
    s.setPoint({_fmt_vec(p2_pos)}, {_fmt_vec(p2_dir)}, 0.0)
'''

    return GeneratedElbowScript(script_name=script_name, source_code=source, warnings=warnings)
