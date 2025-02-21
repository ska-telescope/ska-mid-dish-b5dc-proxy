"""Contains pytest fixtures for tango unit tests setup."""

from typing import Any
from unittest.mock import patch

import pytest
from tango.test_context import DeviceTestContext

from ska_mid_dish_b5dc_proxy.b5dc_manager import B5dcManager
from tests.utils import EventStore


@pytest.fixture
def b5dc_manager() -> Any:
    """Create b5dc manager."""
    with patch(("ska_mid_dish_b5dc_proxy.b5dc_cm.B5dcDeviceComponentManager.start_communicating")):
        tango_context = DeviceTestContext(B5dcManager, process=True)
        tango_context.start()
        device_proxy = tango_context.device

        yield device_proxy
        tango_context.stop()


@pytest.fixture(scope="function")
def event_store_class() -> EventStore:
    """Fixture for storing events."""
    return EventStore()
