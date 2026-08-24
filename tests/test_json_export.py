from core.serialization.json_export import SCHEMA_VERSION, elbow_to_dict
from data.repository import ElbowRepository


def test_json_schema_matches_spec_example():
    repository = ElbowRepository.from_excel()
    result = repository.lookup(dn_mm=315, pn_label="PN10", angle_deg=90)

    payload = elbow_to_dict(result.elbow)

    assert payload["schema"] == SCHEMA_VERSION
    component = payload["component"]
    assert component["type"] == "HDPE_SEGMENTED_ELBOW"
    assert component["material"] == "PE100"
    assert component["mode"] == "NORMALIZED"
    assert component["dn_mm"] == 315
    assert component["pn"] == "PN10"
    assert component["sdr"] == 17
    assert component["od_mm"] == 315
    assert component["thickness_mm"] == 18.7
    assert component["id_mm"] == 277.6
    assert component["angle_deg"] == 90
    assert component["radius_mm"] == 473
    assert component["le_mm"] == 300
    assert component["z_mm"] == 773


def test_json_ports_have_p1_and_p2():
    repository = ElbowRepository.from_excel()
    result = repository.lookup(dn_mm=315, pn_label="PN10", angle_deg=90)

    payload = elbow_to_dict(result.elbow)
    ports = payload["component"]["ports"]
    assert {p["id"] for p in ports} == {"P1", "P2"}
    for port in ports:
        assert "position_mm" in port
        assert "direction" in port
        assert "end_type" in port
