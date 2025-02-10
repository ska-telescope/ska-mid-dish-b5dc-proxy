"""Acceptance Test to verify attributes are readable."""
import pytest
from tango import AttrWriteType, DeviceProxy


@pytest.mark.acceptance
@pytest.mark.forked
@pytest.mark.parametrize(
    "attr, expecpted_read_val",
    [
        ("rfcmFrequency", 11.1),
        ("rfcmPllLock", 2),
        ("rfcmHAttenuation", 8.0),
        ("rfcmVAttenuation", 8.0),
        ("clkPhotodiodeCurrent", 0.0),
        ("hPolRfPowerIn", -36.667),
        ("vPolRfPowerIn", -36.667),
        ("hPolRfPowerOut", -36.667),
        ("vPolRfPowerOut", -36.667),
        ("rfTemperature", 157.8334749362787),
        ("rfcmPsuPcbTemperature", 157.8334749362787),
    ],
)
def test_attributes_read_only(
    b5dc_manager_proxy: DeviceProxy, attr: str, expecpted_read_val: float
) -> None:
    """Test the b5dc tango attributes read only."""
    b5dc_attr_type = b5dc_manager_proxy.get_attribute_config(attr).writable
    b5dc_attr_val = b5dc_manager_proxy.read_attribute(attr).value
    assert b5dc_attr_type is not None
    assert b5dc_attr_type == AttrWriteType.READ
    assert expecpted_read_val == b5dc_attr_val
