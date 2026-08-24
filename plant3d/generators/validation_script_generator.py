"""V0.3.1A — VALIDATION_GEOMETRY_ONLY CustomScript generator.

Real evidence from AutoCAD Plant 3D 2025 (see
plant3d_validation/registration_result.txt) showed:

    REGISTER (PLANTREGISTERCUSTOMSCRIPTS)      = PASS
    ACP_ADAPTER ((arxload "PnP3dACPAdapter"))  = PASS
    TESTACPSCRIPT ((testacpscript "HDPE_SEGMENTED_ELBOW")) = NIL, no geometry
    ROOT CAUSE = the V0.3 scaffold's script file was named
    HDPE_SEGMENTED_ELBOW.py but defined UNCONFIRMED_PLANT3D_ENTRY_POINT()
    as its entry point. Plant 3D's shape lookup requires the routine
    name to match the script name — this is independently corroborated
    by the community's own TESTACPSCRIPT troubleshooting notes ("if a
    command returns NIL, the script name specified may not exactly match
    the Python class or script name", see SOURCE_CITATIONS) and by a
    real, literally-quoted example following that convention
    (TESTSCRIPT2, see below).

This generator produces a corrected, deliberately minimal script: ONE
straight CYLINDER (correctly oriented along X via .rotateY(90.0)) with
two ports, built only from Plant 3D API elements independently
corroborated by real script excerpts (see SOURCE_CITATIONS). Its purpose
is narrow: confirm SCRIPT EXECUTION, GEOMETRY API and PORT API work end
to end on a real Plant 3D 2025 install, before attempting the real DIN
16963 segmented geometry (V0.3.1B). It is explicitly NOT the codo —
every emitted artifact is labeled VALIDATION_GEOMETRY_ONLY, never
claimed to represent the DIN 16963 elbow.

UPDATE (second correction, still V0.3.1A): the first cut of this script
used CYLINDER(OD, LE) — a best-effort argument-order guess, explicitly
flagged as unconfirmed. The user then supplied a corrected call,
CYLINDER(s, R=D/2.0, H=L, O=0.0).rotateY(90.0), attributing it to
Autodesk documentation. Rather than taking that on trust alone, this
project re-ran the same WebSearch-only investigation used throughout
V0.3/V0.3.1 (WebFetch stays blocked in this sandbox — only search
snippets are reachable) and found an INDEPENDENT corroboration: a
result citing the official Autodesk KB article "Plant 3D Custom Python
scripting for catalog parts Reference" and the "Annex B: Creating Custom
Component Scripts in Plant 3D" handout describes a real TESTSCRIPT that
builds "CYLINDER(s, R=D/2, H=L, O=0.0).rotateY(90)" — the same call
shape, from a source distinct from the user's own claim. See
SOURCE_CITATIONS for both. CYLINDER(s, R=, H=, O=).rotateY(...) is
therefore now used with a confidence level closer to the entry-point/
setPoint pattern than to a guess — though still only via WebSearch
snippets, not a fetched primary document, so it is not treated as
absolutely final until the real install confirms it.

The entry point signature and both s.setPoint(...) calls below ARE a
close match to a literal, independently-found real example — a
"TESTSCRIPT2" elbow/tube test script:

    def TESTSCRIPT2(s, D=80.0, L=150.0, OF=-1, **kw):
        ...
        s.setPoint((0.0, 0.0, 0.0), (-1.0, 0.0, 0.0), 0.0)
        s.setPoint((L, 0.0, 0.0), (1.0, 0.0, 0.0), 0.0)

Both calls use 3 positional args (position, direction, 0.0). The user's
proposed correction dropped the third argument from the FIRST setPoint
call only (leaving the second one with it) — most likely a transcription
slip, since nothing in their message described changing setPoint's
arity, only CYLINDER's. This generator keeps 3 args on BOTH calls, since
that is what the one literal citation this project actually has (above)
shows, and a mismatched 2-vs-3-arg pair is not itself evidence of
anything — it was flagged back to the user rather than followed as
written. .uniteWith(...) is still not used here: this script builds only
one primitive, so there is nothing to union yet (that belongs to
V0.3.1B, once real segments need combining).

— see SOURCE_CITATIONS.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

DEFAULT_SCRIPT_NAME = "HDPE_SEGMENTED_ELBOW"

SOURCE_CITATIONS = (
    "https://blog.autodesk.io/custom-python-scripts-for-autocad-plant-3d-part-2/",
    "https://blog.autodesk.io/custom-python-scripts-for-autocad-plant-3d-part-3/",
    "https://static.au-uw2-prd.autodesk.com/PD1746_handout_1746_pd1746_20-_20scripting_20components_20for_20autocad_20plant_203d.pdf",
    "https://mgfx.co.za/blog/uncategorized/plant-3d-adding-custom-components-part-2-breaking-down-the-code/",
    "https://enginine.com/2025/11/11/custom-python-scripts-for-autocad-plant-3d-case-study-of-tubing-fittings-part-1/",
    "https://pipingcontent.com/blog/plant3d-python-testacpscript-debugging-loop",
    "https://forums.autodesk.com/t5/autocad-plant-3d-forum/testacpscript-unknown-command/td-p/11901666",
    # Added for the CYLINDER(s, R=, H=, O=).rotateY(...) correction:
    "https://www.autodesk.com/support/technical/article/caas/tsarticles/ts/6z7yLhwAUHwiyYQaRqYdo.html",
    "https://forums.autodesk.com/autodesk/attachments/autodesk/autocad-plant-3d-forum-zh-cn/4870/1/v1_PD4214-L_Radhakrishnan_AnnexB_Custom-Script-Handout.pdf",
)


@dataclass(frozen=True)
class GeneratedValidationScript:
    script_name: str
    source_code: str
    warnings: List[str]


def generate_validation_script(script_name: str = DEFAULT_SCRIPT_NAME) -> GeneratedValidationScript:
    """V0.3.1A: deterministic, ast-valid VALIDATION_GEOMETRY_ONLY script.

    Deliberately NOT derived from ElbowParameters/SegmentedElbowGeometry
    — this is a diagnostic fixture to validate the real Plant 3D API
    surface, not the golden-case pipeline (that stays in
    custom_script_generator.py, to be wired to real geometry in
    V0.3.1B once this fixture confirms the API on real hardware).
    """
    citations_block = "\n".join(f"#   - {url}" for url in SOURCE_CITATIONS)

    source = f'''"""{script_name}.py — V0.3.1A: VALIDATION_GEOMETRY_ONLY, NOT the codo DIN 16963.

Fixes the V0.3 scaffold's entry-point bug found on real AutoCAD Plant 3D
2025 hardware (see plant3d_validation/registration_result.txt):
PLANTREGISTERCUSTOMSCRIPTS and the PnP3dACPAdapter both loaded without
error, but (testacpscript "{script_name}") returned NIL and produced no
geometry, because the routine was named UNCONFIRMED_PLANT3D_ENTRY_POINT
instead of {script_name}. Plant 3D's shape lookup requires the routine
name to match the script name.

This version's ONLY job is to confirm SCRIPT EXECUTION, GEOMETRY API and
PORT API on the real install: ONE straight cylinder, two ports. It is
NOT dimensionally meaningful as a codo yet — see
docs/PLANT3D_CUSTOMSCRIPT.md, seccion V0.3.1, for the real evidence and
sources behind every call below, and for what V0.3.1B still needs.
"""

# ---------------------------------------------------------------------------
# Metadata: same decorators/imports confirmed for V0.3 (see
# docs/PLANT3D_CUSTOMSCRIPT.md), plus the additional sources below that
# corroborate CYLINDER / setPoint / the entry-point-matches-script-name
# rule / TESTACPSCRIPT behavior used in this V0.3.1A fixture:
{citations_block}
# ---------------------------------------------------------------------------
from aqa.math import *
from varmain.primitiv import *
from varmain.custom import *


@activate(
    Group="Fitting",
    TooltipShort="VALIDATION_GEOMETRY_ONLY (V0.3.1A) - not the codo yet",
    TooltipLong="V0.3.1A: un solo tramo recto, usado solo para validar SCRIPT/GEOMETRY/PORT API en Plant 3D 2025 real. No representa el codo DIN 16963.",
    LengthUnit="mm",
    Ports=2,
)
@group("MainDimensions")
@param(OD=LENGTH, TooltipShort="Diametro exterior", TooltipLong="OD (mm) - Golden Case: 110")
@param(THK=LENGTH, TooltipShort="Espesor de pared (no usado en V0.3.1A)", TooltipLong="Espesor (mm) - reservado para V0.3.1B")
@param(R=LENGTH, TooltipShort="Radio de curvatura (no usado en V0.3.1A)", TooltipLong="R (mm) - reservado para V0.3.1B")
@param(LE=LENGTH, TooltipShort="Longitud del tramo de prueba", TooltipLong="Le (mm) - Golden Case: 150")
@param(Z=LENGTH, TooltipShort="Distancia vertice-cara (no usado en V0.3.1A)", TooltipLong="Z (mm) - reservado para V0.3.1B")
def {script_name}(s, OD=110.0, THK=6.6, R=165.0, LE=150.0, Z=315.0, **kw):
    """VALIDATION_GEOMETRY_ONLY -- un solo tramo recto (CYLINDER), NO el codo DIN 16963.

    THK/R/Z se reciben (mismos nombres/defaults del Golden Case
    DN110/PN10/90) pero todavia no se usan: esta version solo prueba que
    CYLINDER(...) + s.setPoint(...) funcionan en un Plant 3D 2025 real.
    Ver docs/PLANT3D_CUSTOMSCRIPT.md, seccion V0.3.1.
    """
    # CYLINDER(s, R=, H=, O=).rotateY(90.0): firma corroborada por una
    # fuente independiente de la que aporto el usuario (KB oficial de
    # Autodesk + handout Annex B, ver SOURCE_CITATIONS arriba) -- no se
    # tomo la correccion del usuario solo de confianza, se re-verifico.
    # "R" es el nombre del parametro real de CYLINDER, no confundir con
    # el parametro @param(R=...) del codo (radio de curvatura, sin usar
    # todavia en V0.3.1A): aqui R = OD / 2.0 (radio del tubo).
    tramo = CYLINDER(
        s,
        R=OD / 2.0,
        H=LE,
        O=0.0,
    ).rotateY(90.0)

    # Puertos: forma de llamada (posicion, direccion, 0.0) confirmada por
    # el ejemplo real citado literalmente (TESTSCRIPT2) -- ver
    # SOURCE_CITATIONS arriba. Se mantienen 3 argumentos en ambas
    # llamadas (la correccion propuesta traia solo 2 en la primera; sin
    # evidencia de esa variante, se preservo la forma ya confirmada).
    s.setPoint((0.0, 0.0, 0.0), (-1.0, 0.0, 0.0), 0.0)
    s.setPoint((LE, 0.0, 0.0), (1.0, 0.0, 0.0), 0.0)
'''

    warnings = [
        "CYLINDER(s, R=OD/2.0, H=LE, O=0.0).rotateY(90.0): firma corroborada por "
        "una fuente independiente (KB Autodesk + Annex B handout), no solo por la "
        "correccion aportada por el usuario -- ver docs/PLANT3D_CUSTOMSCRIPT.md "
        "seccion V0.3.1. Aun asi solo via snippets de WebSearch (WebFetch sigue "
        "bloqueado), por lo que la confirmacion final sigue siendo la prueba real.",
        "La primera llamada s.setPoint(...) de la correccion propuesta por el "
        "usuario traia solo 2 argumentos (sin el 0.0 final); se mantuvo con 3 "
        "argumentos en ambas llamadas, que es la forma con cita literal "
        "confirmada (TESTSCRIPT2) -- posible error de transcripcion del usuario, "
        "senalado en vez de seguido tal cual.",
        ".uniteWith(...) no se usa en V0.3.1A: solo hay un primitivo (un "
        "CYLINDER), no hay nada que unir todavia -- eso queda para V0.3.1B.",
    ]

    return GeneratedValidationScript(script_name=script_name, source_code=source, warnings=warnings)
