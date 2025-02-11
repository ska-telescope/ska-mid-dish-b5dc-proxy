"""Acceptance Test to verify attributes are readable."""
import pytest
from tango import AttrWriteType, DeviceProxy


@pytest.mark.acceptance
@pytest.mark.forked
@pytest.mark.parametrize(
    "attr",
    [
        "rfcmFrequency",
        "rfcmPllLock",
        "rfcmHAttenuation",
        "rfcmVAttenuation",
        "clkPhotodiodeCurrent",
        "hPolRfPowerIn",
        "vPolRfPowerIn",
        "hPolRfPowerOut",
        "vPolRfPowerOut",
        "rfTemperature",
        "rfcmPsuPcbTemperature",
    ],
)
def test_attributes_are_configured_read_only(b5dc_manager_proxy: DeviceProxy, attr: str) -> None:
    """Test the b5dc tango attributes configurations are read only."""
    b5dc_attr_type = b5dc_manager_proxy.get_attribute_config(attr).writable
    assert b5dc_attr_type is not None
    assert b5dc_attr_type == AttrWriteType.READ


@pytest.mark.acceptance
@pytest.mark.forked
@pytest.mark.parametrize(
    "attr",
    [
        "rfcmFrequency",
        "rfcmPllLock",
        "rfcmHAttenuation",
        "rfcmVAttenuation",
        "clkPhotodiodeCurrent",
        "hPolRfPowerIn",
        "vPolRfPowerIn",
        "hPolRfPowerOut",
        "vPolRfPowerOut",
        "rfTemperature",
        "rfcmPsuPcbTemperature",
    ],
)
def test_read_attribute(b5dc_manager_proxy: DeviceProxy, attr: str):
    """Tests the read behavior of b5dc tango attributes."""
    b5dc_attr_val = b5dc_manager_proxy.read_attribute(attr).value
    assert b5dc_attr_val is not None
