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
def test_attributes_read_only(b5dc_manager_proxy: DeviceProxy, attr: str) -> None:
    """Test the b5dc tango attributes read only."""
    b5dc_attr = b5dc_manager_proxy.get_attribute_config(attr).writable
    assert b5dc_attr is not None
    assert b5dc_attr == AttrWriteType.READ
