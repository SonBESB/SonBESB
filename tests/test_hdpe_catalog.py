import pytest
from core.hydraulics.hdpe_catalog import load_hdpe_catalog, hdpe_pressure_limit
from core.hydraulics.fluids import water_properties, custom_fluid


def test_catalog_uses_published_thickness_and_absent_cells():
    rows=load_hdpe_catalog()['rows']
    assert len(rows)==173
    assert len({(r['outside_diameter_mm'],r['sdr']) for r in rows})==173
    assert all(r['inside_diameter_mm']==pytest.approx(r['outside_diameter_mm']-2*r['wall_thickness_mm']) for r in rows)
    r=next(r for r in rows if r['outside_diameter_mm']==250 and r['sdr']==17)
    assert r['wall_thickness_mm']==14.8
    assert r['inside_diameter_mm']==220.4  # Do not substitute DE*(1-2/SDR).
    assert not any(r['outside_diameter_mm']==560 and r['sdr']==9 for r in rows)
    assert sum(bool(r['issues']) for r in rows)==3


def test_hdpe_pressure_reference_never_used_outside_scope():
    row={'pressure_class':10}
    assert hdpe_pressure_limit(row,water_properties(20))==10
    assert hdpe_pressure_limit(row,water_properties(40)) is None
    assert hdpe_pressure_limit(row,water_properties(10)) is None
    assert hdpe_pressure_limit(row,custom_fluid('Otro',1000,.001,20)) is None
