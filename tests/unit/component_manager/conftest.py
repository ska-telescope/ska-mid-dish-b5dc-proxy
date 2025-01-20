"""Contains pytest fixtures for tango unit tests setup."""

import time
from unittest.mock import AsyncMock, Mock, patch

import pytest

from ska_mid_dish_b5dc_proxy.b5dc_cm import B5dcDeviceComponentManager


@pytest.fixture
def b5dc_cm_setup():
    """Create component manager for testing."""
    with patch("ska_mid_dish_b5dc_proxy.b5dc_cm.B5dcInterface", AsyncMock()), patch(
        "ska_mid_dish_b5dc_proxy.b5dc_cm.B5dcPropertyParser", Mock()
    ), patch(
        "ska_mid_dish_b5dc_proxy.b5dc_cm.B5dcDeviceSensors", Mock()
    ) as b5dc_sensor_mock, patch(
        "ska_mid_dish_b5dc_proxy.b5dc_cm.B5dcProtocol", Mock()
    ), patch.object(
        B5dcDeviceComponentManager, "_update_sensor_with_lock"
    ) as update_sensor_mock, patch.object(
        B5dcDeviceComponentManager, "_update_component_state"
    ) as update_component_state_mock:
        b5dc_cm = B5dcDeviceComponentManager("127.0.0.1", 10001, Mock(), Mock())

        max_try = 5
        for iterations in range(max_try):
            if not b5dc_cm.is_connection_established():
                time.sleep(1)
            else:
                break

        assert iterations < max_try - 1, "Connection not established"

        yield b5dc_cm, [update_sensor_mock, b5dc_sensor_mock, update_component_state_mock]
