"""Test component manager handling of unhappy path on SetFrequency cmd call."""
import time
from unittest.mock import AsyncMock, Mock, patch

import pytest
from ska_control_model import TaskStatus

from ska_mid_dish_b5dc_proxy.b5dc_cm import B5dcDeviceComponentManager


@pytest.mark.unit
@pytest.mark.forked
def test_b5dc_set_frequency_rejects_invalid_freq() -> None:
    """Verify SetFrequency returns TaskStatus.REJECTED for invalid freq. arg."""
    update_period = 2
    with patch("ska_mid_dish_b5dc_proxy.b5dc_cm.B5dcInterface", AsyncMock()), patch(
        "ska_mid_dish_b5dc_proxy.b5dc_cm.B5dcPropertyParser", Mock()
    ), patch("ska_mid_dish_b5dc_proxy.b5dc_cm.B5dcDeviceConfigureFrequency", Mock()), patch(
        "ska_mid_dish_b5dc_proxy.b5dc_cm.B5dcProtocol", Mock()
    ):
        b5dc_cm = B5dcDeviceComponentManager("127.0.0.1", 10001, update_period, Mock())

    max_try = 5
    for iterations in range(max_try):
        if not b5dc_cm.is_connection_established():
            time.sleep(1)
        else:
            break

    assert iterations < max_try - 1, "Connection not established"

    invalid_frequency_enum_value = 5

    cmd_handler_return = b5dc_cm.set_frequency(invalid_frequency_enum_value, None)

    expected_return = (
        TaskStatus.REJECTED,
        f"Invalid frequency value supplied: {invalid_frequency_enum_value}. Expected "
        f"B5dcFrequency enum value (ie: B5dcFrequency.F_11_1_GHZ(1), "
        f"B5dcFrequency.F_13_2_GHZ(2) or B5dcFrequency.F_13_86_GHZ(3))",
    )

    assert cmd_handler_return == expected_return
