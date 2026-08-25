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
    "https://docplayer.net/38668628-Annex-b-creating-custom-component-scripts-in-plant-3d.html",
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


_INNER_CUT_OVERHANG_MM = 5.0  # same disclosed CAD margin as V0.3.1B3B-1


def generate_segmented_elbow_script(
    params: ElbowParameters,
    geometry: SegmentedElbowGeometry,
    script_name: str = DEFAULT_SCRIPT_NAME,
    hollow: bool = False,
) -> GeneratedElbowScript:
    """Bakes geometry.all_pieces (already computed by
    core/geometry/segmented_elbow.py) into literal CYLINDER/rotateY/
    translate calls, united into one solid, plus the two real ports.
    Deterministic: identical (params, geometry, script_name, hollow)
    always produce byte-identical source_code.

    hollow=False (V0.3.1B3A, real-hardware PASS): each piece is a solid
    CYLINDER -- see plant3d_validation/registration_result.txt.

    hollow=True (V0.3.1B3B-2): each piece becomes an (outer CYLINDER)
    .subtractFrom(inner CYLINDER) hollow tube BEFORE the 6 pieces are
    united -- exactly the per-piece order the user specified, and the
    same subtractFrom()/erase() pattern already confirmed for real by
    V0.3.1B3B-1's isolated single-tube test, using the same disclosed
    axial overhang on the inner cutting cylinder. The uniteWith()+erase()
    chain and the rotateY/translate math are completely untouched from
    the already-PASSed B3A version -- hollow=True only changes how each
    individual piece is built, not how the 6 pieces are combined.
    """
    warnings: List[str] = []
    pieces = geometry.all_pieces
    inside_diameter_mm = params.od_mm - 2 * params.thickness_mm

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
        theta_deg = round(math.degrees(math.atan2(dx, dy)), 6)
        start_vec = _fmt_vec(_swap_yz(piece.axis_start))
        length_mm = round(piece.length_mm, 6)
        var = f"ext_{i}" if hollow else f"pieza_{i}"
        var_names.append(var)
        if not hollow:
            piece_lines.append(
                f"    {var} = CYLINDER(s, R=radio_mm, H={length_mm:.6g}, O=0.0)"
                f".rotateY({theta_deg:.6g}).translate({start_vec})  # {piece.label}"
            )
        else:
            int_var = f"int_{i}"
            overhang_h = round(piece.length_mm + 2 * _INNER_CUT_OVERHANG_MM, 6)
            piece_lines.append(
                f"    {var} = CYLINDER(s, R=radio_ext_mm, H={length_mm:.6g}, O=0.0)"
                f".rotateY({theta_deg:.6g}).translate({start_vec})  # {piece.label} (exterior)\n"
                f"    {int_var} = CYLINDER(s, R=radio_int_mm, H={overhang_h:.6g}, O=-{_INNER_CUT_OVERHANG_MM:g})"
                f".rotateY({theta_deg:.6g}).translate({start_vec})  # {piece.label} (interior, taladro)\n"
                f"    {var}.subtractFrom({int_var})\n"
                f"    {int_var}.erase()"
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
    if not hollow:
        warnings.append(
            "Union de 6 piezas + angulos rotateY distintos de 90 (82.5/60/30/7.5/0) "
            "nunca antes probados en este entorno real -- solo rotateY(90) tiene "
            "confirmacion de hardware (V0.3.1B1/B2). Si falla, aislar probando "
            "primero union de solo 2 piezas antes de las 6."
        )
    else:
        warnings.append(
            "subtractFrom()+erase() por pieza SI tiene confirmacion de hardware "
            "real (V0.3.1B3B-1, tubo recto aislado) -- lo nuevo aqui es aplicarlo "
            "6 veces seguidas dentro de la misma cadena ya validada de B3A "
            "(uniteWith/rotateY/translate). Si falla al aplicarlo a toda la "
            "cadena, aislar probando primero 2 piezas huecas antes de las 6, "
            "sin tocar la matematica de posiciones."
        )
        warnings.append(
            "El taladro de cada pieza se sobre-extiende "
            f"{_INNER_CUT_OVERHANG_MM:g}mm por extremo (mismo margen de modelado "
            "usado y confirmado en V0.3.1B3B-1) -- esto tambien deberia dejar el "
            "taladro continuo a traves de los solapes entre gajos, aunque eso no "
            "esta confirmado hasta verlo en Plant 3D real."
        )
    warnings.append(
        "GEOMETRIA APROXIMADA: los 6 tramos son cilindros rectos sin corte a "
        "inglete -- las 3 juntas internas entre gajos son solapes de tapas "
        "redondas, no cortes planos a bisectriz. Ver docstring del modulo para "
        "por que (miter real diferido a V0.3.1B3C, pendiente de una fuente "
        "citable completa)."
    )

    citations_block = "\n".join(f"#   - {url}" for url in SOURCE_CITATIONS)
    pieces_block = "\n".join(piece_lines)
    union_block = "\n".join(union_lines)

    if not hollow:
        version_label = "V0.3.1B3A"
        header_summary = (
            "geometria real del codo (exterior, sin corte a inglete)"
        )
        header_body = f'''APROXIMACION DISCLOSED (ver docs/PLANT3D_CUSTOMSCRIPT.md, seccion V0.3.1):
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
tres elementos tiene confirmacion de hardware todavia.'''
        activate_tooltip_short = "Codo HDPE segmentado (geometria exterior, sin corte a inglete)"
        activate_tooltip_long = (
            f"{version_label}: codo DIN 16963 DN110/PN10/90 -- geometria exterior real "
            "(4 gajos + 2 tramos Le), sin corte a inglete ni taladro interior todavia."
        )
        thk_short = "Espesor de pared (no usado en B3A)"
        thk_long = "Espesor (mm) - reservado para V0.3.1B3B (taladro interior)"
        radio_setup = "    radio_mm = OD / 2.0\n"
        func_docstring = f'''"""V0.3.1B3A -- geometria exterior real del codo, sin corte a inglete ni taladro.

    ANGLE se mantiene fijo en 90 grados (no se agrega como @param): ningun
    tipo de parametro Plant 3D para angulos fue confirmado en la
    investigacion de V0.3 (solo LENGTH). THK/R/LE/Z se reciben (mismos
    nombres/defaults del Golden Case) pero las posiciones de los 6 tramos
    ya vienen horneadas desde core/geometry/segmented_elbow.py para
    R={params.radius_mm:g}/LE={params.le_mm:g}/Z={geometry.z_mm:g} -- cambiar R/LE/Z en vivo no
    recalcula la geometria todavia; solo OD afecta el radio real del tubo
    (radio_mm abajo). Ver docs/PLANT3D_CUSTOMSCRIPT.md, seccion V0.3.1.
    """'''
    else:
        version_label = "V0.3.1B3B-2"
        header_summary = "codo hueco (6 piezas, sin corte a inglete)"
        header_body = f'''APROXIMACION DISCLOSED (ver docs/PLANT3D_CUSTOMSCRIPT.md, seccion V0.3.1):
misma cadena de 6 piezas de V0.3.1B3A (ya PASS real: rotateY/translate/
uniteWith/erase), pero cada pieza ahora es (cilindro exterior)
.subtractFrom(cilindro interior) ANTES de unirse -- el mismo patron
subtractFrom()+erase() ya confirmado en real por V0.3.1B3B-1 (tubo recto
aislado), aplicado 6 veces. Las 3 uniones internas SIGUEN siendo solapes
de tapas redondas, NO cortes a inglete (eso es V0.3.1B3C, todavia sin
implementar -- ver docstring del modulo).

Golden Case: DN{params.dn_mm:g} {params.pn} {params.angle_deg:g} grados
  OD={params.od_mm:g} THK={params.thickness_mm:g} ID={round(inside_diameter_mm, 6):g} R={params.radius_mm:g}
  LE={params.le_mm:g} Z={geometry.z_mm:g}
  Segmentos: {params.segment_configuration.segment_angles_deg if params.segment_configuration else None}

Evidencia real previa (ver plant3d_validation/registration_result.txt):
  V0.3.1B1    (CYLINDER+rotateY(90), Ports=1, sin setPoint)     = PASS
  V0.3.1B2    (mismo + Ports=2 + 2x s.setPoint)                 = PASS
  V0.3.1B3A   (6 piezas + translate + rotateY!=90 + uniteWith)  = PASS
  V0.3.1B3B-1 (subtractFrom() aislado, 1 tubo recto hueco)      = PASS
Esta version (B3B-2) es la primera en combinar subtractFrom() con la
cadena de 6 piezas -- ninguna de las piezas individuales de B3A fue
huecada todavia en real.'''
        activate_tooltip_short = "Codo HDPE segmentado hueco (sin corte a inglete)"
        activate_tooltip_long = (
            f"{version_label}: codo DIN 16963 DN110/PN10/90 -- geometria hueca real "
            "(4 gajos + 2 tramos Le, OD/ID/THK), sin corte a inglete todavia."
        )
        thk_short = "Espesor de pared (usado para el taladro)"
        thk_long = "Espesor (mm) - Golden Case: {:g}. ID = OD - 2*THK.".format(params.thickness_mm)
        radio_setup = "    radio_ext_mm = OD / 2.0\n    radio_int_mm = (OD - 2 * THK) / 2.0\n"
        func_docstring = f'''"""V0.3.1B3B-2 -- codo hueco real (6 piezas), sin corte a inglete todavia.

    ANGLE se mantiene fijo en 90 grados (mismo motivo que B3A: ningun tipo
    de parametro Plant 3D para angulos fue confirmado). R/LE/Z se reciben
    (mismos nombres/defaults del Golden Case) pero las posiciones de los
    6 tramos ya vienen horneadas desde core/geometry/segmented_elbow.py
    para R={params.radius_mm:g}/LE={params.le_mm:g}/Z={geometry.z_mm:g} -- cambiar R/LE/Z en vivo
    no recalcula la geometria todavia. OD y THK SI afectan el taladro
    real de cada pieza (radio_ext_mm/radio_int_mm abajo). Ver
    docs/PLANT3D_CUSTOMSCRIPT.md, seccion V0.3.1.
    """'''

    source = f'''"""{script_name}.py — {version_label}: {header_summary}.

{header_body}
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
    TooltipShort="{activate_tooltip_short}",
    TooltipLong="{activate_tooltip_long}",
    LengthUnit="mm",
    Ports=2,
)
@group("MainDimensions")
@param(OD=LENGTH, TooltipShort="Diametro exterior", TooltipLong="OD (mm) - Golden Case: {params.od_mm:g}", Ask4Dist=True)
@param(THK=LENGTH, TooltipShort="{thk_short}", TooltipLong="{thk_long}")
@param(R=LENGTH, TooltipShort="Radio de curvatura (posiciones ya horneadas)", TooltipLong="R (mm) - Golden Case: {params.radius_mm:g}. Cambiar este valor en vivo NO recalcula la geometria (evita reimplementar trigonometria en Plant 3D).")
@param(LE=LENGTH, TooltipShort="Longitud tangente (posiciones ya horneadas)", TooltipLong="Le (mm) - Golden Case: {params.le_mm:g}. Mismo aviso que R.")
@param(Z=LENGTH, TooltipShort="Distancia vertice-cara (posiciones ya horneadas)", TooltipLong="Z (mm) - Golden Case: {geometry.z_mm:g}. Mismo aviso que R.")
def {script_name}(s, OD={params.od_mm:g}, THK={params.thickness_mm:g}, R={params.radius_mm:g}, LE={params.le_mm:g}, Z={geometry.z_mm:g}, OF=-1, K=1, **kw):
    {func_docstring}
{radio_setup}
{pieces_block}

{union_block}

    s.setPoint({_fmt_vec(p1_pos)}, {_fmt_vec(p1_dir)}, 0.0)
    s.setPoint({_fmt_vec(p2_pos)}, {_fmt_vec(p2_dir)}, 0.0)
'''

    return GeneratedElbowScript(script_name=script_name, source_code=source, warnings=warnings)
