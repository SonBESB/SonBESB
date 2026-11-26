import pytest
from core.hydraulics.energy_profile import illustrative_profile
from core.hydraulics.system_curve import PipeSegment, evaluate_system, pressure_to_head_m

def test_profile_uses_real_elevation_not_an_effective_head_with_pressure_mixed_in():
    # Regresion: antes se le pasaba a esta funcion un "desnivel efectivo" que
    # ya sumaba una diferencia de presion de borde, lo que hacia que la cota
    # geometrica mostrada fuera ficticia (y disparaba "presion negativa"
    # espurias). La cota aqui debe ser la elevacion geometrica real, sin
    # importar cuanta presion de entrada se sume aparte.
    segs = [PipeSegment('A', 100, 200, 0.007)]
    elevation_gain_m = 10.0
    rows = illustrative_profile(segs, 0.02, 0.0, elevation_gain_m, 1000, 0.001, inlet_pressure_head_m=50.0)
    assert rows[-1]['cota_m'] == pytest.approx(elevation_gain_m)
    assert rows[0]['cota_m'] == pytest.approx(0.0)


def test_profile_inlet_pressure_head_adds_to_entry_energy_without_a_pump():
    segs = [PipeSegment('A', 100, 200, 0.007)]
    density = 1000.0
    inlet_bar = 2.0
    inlet_head_m = pressure_to_head_m(inlet_bar, density)
    rows = illustrative_profile(segs, 0.02, 0.0, 10.0, density, 0.001, inlet_pressure_head_m=inlet_head_m)
    detail = evaluate_system(segs, 0.02, 10.0, density, 0.001)
    total_loss = sum(e.total_head_loss_m for e in detail.segment_evaluations)
    assert rows[0]['energia_m'] == pytest.approx(inlet_head_m)
    assert rows[-1]['energia_m'] == pytest.approx(inlet_head_m - total_loss)
    # Presion residual real en destino: presion de entrada menos perdidas y elevacion ganada,
    # calculada de forma independiente del codigo bajo prueba.
    residual_head_m = inlet_head_m - total_loss - 10.0
    velocity_head = detail.segment_evaluations[0].velocity_m_s ** 2 / (2 * 9.80665)
    expected_bar = (residual_head_m - velocity_head) * density * 9.80665 / 1e5
    assert rows[-1]['presion_bar'] == pytest.approx(expected_bar)


def test_profile_energy_balance_and_velocity_step():
    segs = [PipeSegment('A',100,200,0.007),PipeSegment('B',150,150,0.007)]
    rows = illustrative_profile(segs,0.02,30,10,1000,0.001)
    detail = evaluate_system(segs,0.02,10,1000,0.001)
    assert rows[-1]['energia_m'] == pytest.approx(30-sum(e.total_head_loss_m for e in detail.segment_evaluations))
    assert rows[-1]['cota_m'] == 10
    assert rows[1]['energia_m'] == pytest.approx(rows[2]['energia_m'])
    assert rows[2]['piezometrica_m'] < rows[1]['piezometrica_m']
    for r in rows:
        assert r['presion_bar'] == pytest.approx((r['piezometrica_m']-r['cota_m'])*1000*9.80665/100000)
