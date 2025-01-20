"""Contains pytest fixtures for tango unit tests setup."""

from unittest.mock import patch

import pytest
from tango.test_context import DeviceTestContext

from ska_mid_dish_b5dc_proxy.b5dc_proxy import B5dcProxy
from tests.utils import EventStore


@pytest.fixture
def b5dc_proxy():
    """Create b5dc proxy."""
    with patch(("ska_mid_dish_b5dc_proxy.b5dc_cm.B5dcDeviceComponentManager.start_communicating")):
        tango_context = DeviceTestContext(B5dcProxy, process=True)
        tango_context.start()
        device_proxy = tango_context.device

        yield device_proxy
        tango_context.stop()


@pytest.fixture(scope="function")
def event_store():
    """Fixture for storing events."""
    return EventStore()
