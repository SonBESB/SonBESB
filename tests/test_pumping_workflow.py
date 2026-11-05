import json
from unittest.mock import patch
from streamlit.testing.v1 import AppTest

def test_guided_hdpe_pdf_and_temperature_scope():
    with patch('ui.pump_operating_view.st.download_button') as download:
        at=AppTest.from_string('from ui.pump_operating_view import render_pump_operating_point_tab\nrender_pump_operating_point_tab()').run(timeout=30)
        assert not at.exception, at.exception
        at.button(key='nav_to_pipes').click().run()
        assert at.session_state['nav_stage']=='2 · Tuberías'
        at.selectbox(key='pump_source_0').select('HDPE PE100 · Duratec').run()
        assert not at.exception, at.exception
        calls={c.kwargs['mime']:c.kwargs['data'] for c in download.call_args_list}
        case=json.loads(calls['application/json'])
        assert case['tramos'][0]['diametro_interior_mm']==220.4,case['tramos']
        assert case['presion_vs_pn'][0]['pn_bar']==10
        assert calls['application/pdf'].startswith(b'%PDF-')
        at.number_input(key='pump_fluid_temp').set_value(40.0).run()
        assert not at.exception, at.exception
        case=json.loads(download.call_args.kwargs['data'])
        assert case['presion_vs_pn'] is None
        at.checkbox(key='pump_surge_enabled').check().run()
        assert not at.exception, at.exception
        at.number_input(key='pump_surge_hdpe_E_0').set_value(800.0).run()
        assert not at.exception, at.exception
        at.button(key='pump_add_scenario').click().run()
        assert not at.exception, at.exception


def test_stepper_buttons_jump_directly_to_a_stage():
    with patch('ui.pump_operating_view.st.download_button'):
        at = AppTest.from_string(
            "from ui.pump_operating_view import render_pump_operating_point_tab\nrender_pump_operating_point_tab()"
        ).run(timeout=30)
        assert not at.exception, at.exception
        assert at.session_state['nav_stage'] == '1 · Líquido'

        at.button(key='stepper_nav_stage_2').click().run()
        assert not at.exception, at.exception
        assert at.session_state['nav_stage'] == '3 · Bomba'

        at.button(key='stepper_nav_stage_0').click().run()
        assert not at.exception, at.exception
        assert at.session_state['nav_stage'] == '1 · Líquido'
