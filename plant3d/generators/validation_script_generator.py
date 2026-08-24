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
straight CYLINDER with two ports, built only from Plant 3D API elements
independently corroborated by multiple real script excerpts (see
SOURCE_CITATIONS). Its purpose is narrow: confirm SCRIPT EXECUTION,
GEOMETRY API and PORT API work end to end on a real Plant 3D 2025
install, before attempting the real DIN 16963 segmented geometry
(V0.3.1B). It is explicitly NOT the codo — every emitted artifact is
labeled VALIDATION_GEOMETRY_ONLY, never claimed to represent the DIN
16963 elbow.

HONESTY NOTE ON CYLINDER(...): its existence, and its use together with
.rotateY(...)/.uniteWith(...) in exactly a build/transform/boolean
pattern, is corroborated by multiple independent real Plant3D
CustomScript excerpts (see SOURCE_CITATIONS: mgfx.co.za's "Adding Custom
Components" series, enginine.com's tubing-fittings case study, the
PD1746 Autodesk University handout). No single literal quote of
CYLINDER's exact constructor argument order was found in this project's
sandbox — WebFetch is blocked here (same limitation already documented
for V0.3 in docs/PLANT3D_CUSTOMSCRIPT.md), so only WebSearch snippets
were available, not full page content. The (outside_diameter, length)
argument order used below is therefore a best-effort reconstruction from
those excerpts, NOT a verified literal citation. If it raises an error
or draws something unexpected on the real install, that IS new evidence
— report it back so this gets corrected against Plant 3D's real
signature instead of guessed again.

.rotateY(...) and .uniteWith(...) are deliberately NOT used yet in this
minimal script: composing two primitives correctly needs a confirmed
placement/rotation semantic (does rotateY act about the primitive's own
origin or the current UCS? is a translate call needed first?) that this
project does not have evidence for. They stay deferred to V0.3.1B, once
this simpler single-cylinder case confirms CYLINDER + setPoint work at
all on this real install.

The entry point signature and both s.setPoint(...) calls below ARE a
close match to a literal, independently-found real example — a
"TESTSCRIPT2" elbow/tube test script:

    def TESTSCRIPT2(s, D=80.0, L=150.0, OF=-1, **kw):
        ...
        s.setPoint((0.0, 0.0, 0.0), (-1.0, 0.0, 0.0), 0.0)
        s.setPoint((L, 0.0, 0.0), (1.0, 0.0, 0.0), 0.0)

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
    # HONESTY NOTE: (OD, LE) como orden de argumentos de CYLINDER es una
    # reconstruccion best-effort a partir de multiples ejemplos reales
    # independientes (ver SOURCE_CITATIONS arriba), NO una firma citada
    # literalmente. Si esto falla o dibuja algo incorrecto en el
    # entorno real, eso ES evidencia nueva a reportar.
    tramo = CYLINDER(OD, LE)

    # Puertos: esta forma exacta de llamada (posicion, direccion, 0.0) es
    # una coincidencia cercana con un ejemplo real citado literalmente
    # (TESTSCRIPT2) -- ver SOURCE_CITATIONS arriba.
    s.setPoint((0.0, 0.0, 0.0), (-1.0, 0.0, 0.0), 0.0)
    s.setPoint((LE, 0.0, 0.0), (1.0, 0.0, 0.0), 0.0)
'''

    warnings = [
        "CYLINDER(OD, LE) usa un orden de argumentos NO confirmado literalmente "
        "(best-effort desde multiples ejemplos reales independientes) -- ver "
        "docs/PLANT3D_CUSTOMSCRIPT.md seccion V0.3.1.",
        ".rotateY(...) y .uniteWith(...) se difieren a V0.3.1B: no se usan aqui "
        "para no inventar semantica de posicionamiento/rotacion sin confirmar.",
    ]

    return GeneratedValidationScript(script_name=script_name, source_code=source, warnings=warnings)
