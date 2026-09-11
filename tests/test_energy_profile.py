import pytest
from core.hydraulics.energy_profile import illustrative_profile
from core.hydraulics.system_curve import PipeSegment, evaluate_system

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
