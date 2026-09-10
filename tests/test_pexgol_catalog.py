import math
import pytest
from core.hydraulics.pipe_catalog import load_pexgol_catalog, allowed_pressure_bar, CLASSES
from core.hydraulics.pressure_rating import build_shutoff_pressure_profile
from core.hydraulics.system_curve import PipeSegment


def test_draft_catalog_preserves_inconsistent_printed_dimensions():
    rows = load_pexgol_catalog()['rows']
    assert len(rows) == 170
    assert {r['pressure_class'] for r in rows} == set(CLASSES)
    assert all(r['review_status'] == 'DRAFT_UNVERIFIED' for r in rows)
    row = next(r for r in rows if r['pressure_class'] == 19 and r['outside_diameter_mm'] == 225)
    assert row['wall_thickness_mm'] == 25.2
    assert row['inside_diameter_mm'] == 175
    assert len(row['issues']) == 2
    assert sum(bool(r['issues']) for r in rows) == 26


def test_pressure_uses_table_not_class_heading_and_next_temperature():
    assert allowed_pressure_bar(10, 20) == (9.9, 20)
    assert allowed_pressure_bar(15, 20.1) == (13.3, 30)
    assert allowed_pressure_bar(30, 110) == (7.5, 110)


@pytest.mark.parametrize('temperature', [9.9, 110.1, math.nan, math.inf])
def test_pressure_never_extrapolates(temperature):
    with pytest.raises(ValueError):
        allowed_pressure_bar(10, temperature)


def test_mixed_pressure_profile_uses_individual_allowable_values():
    segments = [PipeSegment(label=f'T{i}', length_m=100, inside_diameter_mm=219, roughness_mm=0.0007, fitting_counts={}) for i in range(2)]
    checks = build_shutoff_pressure_profile(segments, 100, 0, 1000, ['PN16', 'PEXGOL Clase 10'], allowable_pressures_bar=[16, 7.8])
    assert checks[0].passed
    assert not checks[1].passed
    assert checks[1].pn_bar == 7.8
    with pytest.raises(ValueError):
        build_shutoff_pressure_profile(segments, 100, 0, 1000, ['PN16']*2, allowable_pressures_bar=[10])
    with pytest.raises(ValueError):
        build_shutoff_pressure_profile(segments, 100, 0, 1000, ['PN16']*2, allowable_pressures_bar=[10, math.nan])


def test_ui_mixed_catalog_export_and_temperature_scope():
    import json
    from unittest.mock import patch
    from streamlit.testing.v1 import AppTest
    with patch('ui.pump_operating_view.st.download_button') as download:
        at = AppTest.from_string('from ui.pump_operating_view import render_pump_operating_point_tab\nrender_pump_operating_point_tab()').run(timeout=30)
        at.selectbox(key='pump_source_0').select('PEXGOL 2023 (borrador)').run()
        at.selectbox(key='pump_pex_ref_0_10').select(10).run()
        at.number_input(key='pump_n_segments').set_value(2).run()
        at.number_input(key='pump_fluid_temp').set_value(40.0).run()
        assert not at.exception
        case = json.loads(download.call_args.kwargs['data'])
        assert case['tramos'][0]['diametro_interior_mm'] == 219
        assert case['tramos'][0]['catalogo']['review_status'] == 'DRAFT_UNVERIFIED'
        assert case['tramos'][0]['catalogo']['provenance']['page'] == '11'
        assert case['tramos'][0]['catalogo']['allowable_pressure_bar'] == 7.8
        assert case['presion_vs_pn'][0]['pn_bar'] == 7.8
        assert case['tramos'][1]['catalogo'] is None
        at.checkbox(key='pump_surge_enabled').check().run()
        at.checkbox(key='pump_surge_pex_E_use_0').check().run()
        assert not at.exception
        case = json.loads(download.call_args.kwargs['data'])
        assert case['tramos'][0]['catalogo']['surge_elastic_modulus_pa'] == 465e6
        assert case['golpe_de_ariete']['celeridad_m_s'] > 0
        at.checkbox(key='pump_fluid_custom').check().run()
        at.number_input(key='pump_fluid_density').set_value(1000.0)
        at.number_input(key='pump_fluid_visc').set_value(0.001).run()
        assert not at.exception
        case = json.loads(download.call_args.kwargs['data'])
        assert case['presion_vs_pn'] is None
        at.selectbox(key='pump_source_0').select('Manual').run()
        assert not at.exception
        case = json.loads(download.call_args.kwargs['data'])
        assert case['tramos'][0]['catalogo'] is None
        assert case['tramos'][0]['diametro_interior_mm'] == 250
