"""V0.3.1A tests for plant3d/generators/validation_script_generator.py.

This generator produces a deliberately minimal, VALIDATION_GEOMETRY_ONLY
CustomScript whose only job is to confirm SCRIPT EXECUTION, GEOMETRY API
and PORT API against a real AutoCAD Plant 3D install — it replaces the
V0.3 scaffold's entry point bug found on real Plant 3D 2025 hardware
(TESTACPSCRIPT returned NIL because the routine name did not match the
script name). See docs/PLANT3D_CUSTOMSCRIPT.md, seccion V0.3.1.
"""

import ast

from plant3d.generators.validation_script_generator import (
    DEFAULT_SCRIPT_NAME,
    SOURCE_CITATIONS,
    generate_validation_script,
    generate_validation_script_b1,
)


def test_validation_script_is_syntactically_valid_python():
    result = generate_validation_script()
    ast.parse(result.source_code)  # must not raise SyntaxError


def test_validation_script_is_deterministic():
    first = generate_validation_script()
    second = generate_validation_script()
    assert first.source_code == second.source_code


def test_entry_point_name_matches_script_name_by_default():
    """Regression guard for the real V0.3 bug found on Plant 3D 2025:
    TESTACPSCRIPT returned NIL because the routine name
    (UNCONFIRMED_PLANT3D_ENTRY_POINT) did not match the script name
    (HDPE_SEGMENTED_ELBOW)."""
    result = generate_validation_script()
    assert result.script_name == DEFAULT_SCRIPT_NAME
    assert f"def {DEFAULT_SCRIPT_NAME}(s, OD=" in result.source_code
    # The old broken name may still appear in the explanatory docstring
    # (narrating the real bug found on Plant 3D 2025) but must never be
    # used as an actual def target again.
    assert "def UNCONFIRMED_PLANT3D_ENTRY_POINT" not in result.source_code


def test_entry_point_name_matches_a_custom_script_name_too():
    result = generate_validation_script(script_name="OTHER_NAME")
    assert "def OTHER_NAME(s, OD=" in result.source_code
    assert f'"""OTHER_NAME.py' in result.source_code


def test_validation_script_is_clearly_marked_not_the_real_elbow():
    result = generate_validation_script()
    assert "VALIDATION_GEOMETRY_ONLY" in result.source_code
    assert "NOT the codo" in result.source_code
    assert "DIN 16963" in result.source_code


def test_validation_script_uses_the_confirmed_port_pattern():
    result = generate_validation_script()
    assert "s.setPoint((0.0, 0.0, 0.0), (-1.0, 0.0, 0.0), 0.0)" in result.source_code
    assert "s.setPoint((LE, 0.0, 0.0), (1.0, 0.0, 0.0), 0.0)" in result.source_code


def test_validation_script_keeps_golden_case_parameter_defaults():
    """OD/THK/R/LE/Z keep the DN110/PN10/90 defaults even though only
    OD/LE are used by this minimal geometry (THK/R/Z reserved for
    V0.3.1B)."""
    result = generate_validation_script()
    assert "OD=110.0, THK=6.6, R=165.0, LE=150.0, Z=315.0" in result.source_code


def test_validation_script_uses_the_confirmed_cylinder_signature():
    """CYLINDER(s, R=, H=, O=).rotateY(90.0) — corrected in V0.3.1A after
    an independent WebSearch corroboration (Autodesk KB article + Annex B
    handout) matched the user-proposed call, distinct from the earlier
    best-effort CYLINDER(OD, LE) guess."""
    result = generate_validation_script()
    body = result.source_code.split(f"def {DEFAULT_SCRIPT_NAME}(")[1]
    assert "CYLINDER(" in body
    assert "R=OD / 2.0" in body
    assert "H=LE" in body
    assert "O=0.0" in body
    assert ".rotateY(90.0)" in body
    # Nothing to union yet: only one primitive is built in V0.3.1A.
    assert ".uniteWith(" not in body


def test_validation_script_flags_deviation_from_users_setpoint_arity():
    """The user's proposed correction dropped the third argument from
    the first s.setPoint(...) call; this generator keeps 3 args on both
    (the literally-confirmed TESTSCRIPT2 shape) and must say so."""
    result = generate_validation_script()
    assert any("setPoint" in w and "2 argumentos" in w for w in result.warnings)


def test_validation_script_cites_sources():
    result = generate_validation_script()
    for citation in SOURCE_CITATIONS:
        assert citation in result.source_code


def test_validation_script_never_touches_proprietary_plant_files():
    result = generate_validation_script()
    for forbidden in (".pcat", ".pspx", ".pspc"):
        assert forbidden not in result.source_code


# --- V0.3.1B1: bare-minimum validation, no ports yet ----------------------


def test_b1_is_syntactically_valid_python():
    result = generate_validation_script_b1()
    ast.parse(result.source_code)


def test_b1_is_deterministic():
    first = generate_validation_script_b1()
    second = generate_validation_script_b1()
    assert first.source_code == second.source_code


def test_b1_entry_point_matches_script_name():
    result = generate_validation_script_b1()
    assert result.script_name == DEFAULT_SCRIPT_NAME
    assert f"def {DEFAULT_SCRIPT_NAME}(" in result.source_code
    assert "UNCONFIRMED_PLANT3D_ENTRY_POINT" not in result.source_code


def test_b1_uses_the_confirmed_signature_and_cylinder_call():
    """def NAME(s, OD=110.0, LE=150.0, OF=-1, K=1, **kw) + CYLINDER(s,
    R=OD/2.0, H=LE, O=0.0).rotateY(90) — both independently confirmed
    via WebSearch (TESTSCRIPT signature quote, Ask4Dist Community
    thread), not just accepted from the user's proposal."""
    result = generate_validation_script_b1()
    assert "OD=110.0,\n    LE=150.0,\n    OF=-1,\n    K=1,\n    **kw" in result.source_code
    body = result.source_code.split(f"def {DEFAULT_SCRIPT_NAME}(")[1]
    assert "R=OD / 2.0" in body
    assert "H=LE" in body
    assert "O=0.0" in body
    assert ".rotateY(90)" in body


def test_b1_has_no_ports_at_all():
    """B1's whole purpose is to isolate script/family execution before
    re-adding ports in B2 — the function body must not call setPoint,
    and metadata must declare Ports=1, not 2. (The narrative header
    legitimately mentions "s.setPoint(...)" in prose, describing what
    V0.3.1A already did and what B1 deliberately omits.)"""
    result = generate_validation_script_b1()
    body = result.source_code.split(f"def {DEFAULT_SCRIPT_NAME}(")[1]
    assert "setPoint" not in body
    assert "Ports=1" in result.source_code
    assert "Ports=2" not in result.source_code


def test_b1_does_not_declare_thk_r_z_or_pn_sdr():
    result = generate_validation_script_b1()
    assert "@param(THK" not in result.source_code
    assert "@param(R" not in result.source_code
    assert "@param(Z" not in result.source_code
    assert "@param(PN" not in result.source_code
    assert "@param(SDR" not in result.source_code
    body = result.source_code.split(f"def {DEFAULT_SCRIPT_NAME}(")[1]
    assert "PN" not in body
    assert "SDR" not in body


def test_b1_uses_ask4dist_on_od():
    result = generate_validation_script_b1()
    assert "Ask4Dist=True" in result.source_code


def test_b1_is_clearly_marked_not_the_real_elbow():
    result = generate_validation_script_b1()
    assert "VALIDATION_GEOMETRY_ONLY" in result.source_code
    assert "DIN 16963" in result.source_code


def test_b1_cites_sources_including_ask4dist_and_testscript_signature():
    result = generate_validation_script_b1()
    for citation in SOURCE_CITATIONS:
        assert citation in result.source_code


def test_b1_never_touches_proprietary_plant_files():
    result = generate_validation_script_b1()
    for forbidden in (".pcat", ".pspx", ".pspc"):
        assert forbidden not in result.source_code
