"""Tests del importador de tabla de requisitos (CSV -> session_state)."""

from __future__ import annotations

from core.hydraulics.requirements_import import (
    build_session_state_updates,
    normalize_key,
    parse_number_es,
    parse_requirements_csv,
)

OT120_CSV = """Parametro,Valor
Proyecto,OT-120 - Nueva Sala de Descanso
Fluido,Agua
Temperatura,20 °C
Material de tuberia,HDPE PE100
Diametro exterior,110 mm
Clase de presion,PN10
SDR,17
Diametro interior,96.8 mm
Rugosidad absoluta,0.0015 mm
Longitud de tuberia,120 m
Cota inicial (Tie-in),990.00 m s.n.m.
Cota final (sala),1002.50 m s.n.m.
Desnivel geometrico,+12.50 m
Presion disponible en Tie-in,2.5 bar
Presion requerida en destino,1.5 bar
Caudal de diseno,82 L/min = 1.3667 L/s
Perdidas singulares,10%
Numero de tramos,1
"""


def test_normalize_key_strips_accents_and_punctuation():
    assert normalize_key("Diámetro interior (mm)") == "diametro_interior_mm"
    assert normalize_key("Presión requerida en destino") == "presion_requerida_en_destino"


def test_parse_number_es_handles_comma_decimal_and_units():
    assert parse_number_es("12,50 m") == 12.5
    assert parse_number_es("2,50 bar") == 2.5
    assert parse_number_es("96.8 mm") == 96.8
    assert parse_number_es("0,0015 mm") == 0.0015
    assert parse_number_es("+12.50 m") == 12.5
    assert parse_number_es("") is None
    assert parse_number_es(None) is None


def test_parse_number_es_takes_the_side_after_equals():
    assert parse_number_es("82 L/min = 1.3667 L/s") == 1.3667


def test_parse_requirements_csv_reads_two_column_table():
    parsed = parse_requirements_csv(OT120_CSV)
    assert parsed["proyecto"] == "OT-120 - Nueva Sala de Descanso"
    assert parsed["fluido"] == "Agua"
    assert parsed["desnivel_geometrico"] == "+12.50 m"


def test_build_session_state_updates_fills_the_ot120_case():
    parsed = parse_requirements_csv(OT120_CSV)
    updates, applied, ignored = build_session_state_updates(parsed)

    assert updates["pump_project_name"] == "OT-120 - Nueva Sala de Descanso"
    assert updates["pump_liquid"] == "Agua"
    assert updates["pump_fluid_temp"] == 20.0
    assert updates["pump_static_head"] == 12.5
    assert updates["pump_p_tiein_bar"] == 2.5
    assert updates["pump_p_destino_bar"] == 1.5
    assert updates["pump_source_0"] == "Manual"
    assert updates["pump_di_0"] == 96.8
    assert updates["pump_rough_0"] == 0.0015
    assert updates["pump_len_0"] == 120.0
    assert updates["pump_pn_0"] == "PN10"
    assert updates["pump_minor_mode_0"] == "Aún no sé los accesorios — estimar como % de la fricción"
    assert updates["pump_minor_pct_0"] == 10.0
    assert updates["pump_no_pump_mode"] is True
    assert updates["pump_design_flow_l_s"] == 1.3667

    assert any("Proyecto" in a for a in applied)
    # Campos que el importador declara fuera de alcance a proposito.
    assert any("sdr" in i.lower() for i in ignored)
    assert any("material de tuberia" in i.lower() for i in ignored)
    assert any("numero de tramos" in i.lower() for i in ignored)


def test_build_session_state_updates_ignores_unmatched_fluid_label():
    updates, applied, ignored = build_session_state_updates({"fluido": "Salmuera concentrada"})
    assert "pump_liquid" not in updates
    assert any("Salmuera concentrada" in i for i in ignored)


def test_build_session_state_updates_ignores_unmatched_pn_class():
    parsed = {"diametro_interior": "100", "clase_pn": "PN99"}
    updates, applied, ignored = build_session_state_updates(parsed)
    assert "pump_pn_0" not in updates
    assert any("PN99" in i for i in ignored)


def test_build_session_state_updates_empty_input_changes_nothing():
    updates, applied, ignored = build_session_state_updates({})
    assert updates == {}
    assert applied == []
    assert ignored == []
