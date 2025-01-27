# pylint: disable=W0621
"""Contains pytest fixtures for other tests setup."""

import pytest
import tango


@pytest.fixture
def b5dc_manager_device_fqdn() -> str:
    """Return the ds manager tango fqdn."""
    return "mid-dish/b5dc-manager/SKA001"


@pytest.fixture
def b5dc_manager_proxy(b5dc_manager_device_fqdn: str) -> tango.DeviceProxy:
    """Return a tango proxy to the b5dc manager."""
    return tango.DeviceProxy(b5dc_manager_device_fqdn)
