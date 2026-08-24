from cad.backends.base_backend import SolidCadBackend  # noqa: F401  (sanity: existing import path unaffected)
from core.library.support_family import SUPPORT_FAMILIES, SupportFamilyDefinition
from plant3d.publishers.base import PublishResultStatus
from plant3d.publishers.catalog_part import CatalogPartPublisher
from plant3d.publishers.equipment import EquipmentPublisher
from plant3d.publishers.support import SupportPublisher


def test_no_support_families_are_invented_yet():
    assert SUPPORT_FAMILIES == {}


def test_support_family_definition_shape_is_all_optional():
    definition = SupportFamilyDefinition(key="TEST_CONSOLE", display_name="Consola de prueba")
    assert definition.drawing_reference is None
    assert definition.user_inputs == []
    assert definition.database_values == {}
    assert definition.load_limits == {}


def test_all_publishers_return_not_implemented():
    for publisher in (CatalogPartPublisher(), SupportPublisher(), EquipmentPublisher()):
        result = publisher.publish(None)
        assert result.status is PublishResultStatus.NOT_IMPLEMENTED
        assert "PLANT3D_BACKEND_NOT_IMPLEMENTED" == result.status.value
