"""Dummy test to run the k8s test job."""

import pytest
import tango


@pytest.mark.acceptance
@pytest.mark.forked
def test_b5dc_manager_is_pingable(b5dc_manager_proxy: tango.DeviceProxy) -> None:
    """Checks if the B5DC Manager is reachable."""
    b5dc_manager_proxy.ping()
