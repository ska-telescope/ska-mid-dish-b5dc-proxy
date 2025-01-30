# pylint: disable=protected-access
"""Test component manager handling of unhappy path on SetFrequency cmd call."""
import time
from unittest.mock import AsyncMock, Mock, patch

import pytest
from ska_control_model import TaskStatus
from ska_mid_dish_dcp_lib.device.b5dc_device import B5dcDeviceAttenuationException
from ska_mid_dish_dcp_lib.device.b5dc_device_mappings import B5dcFrequency

from ska_mid_dish_b5dc_proxy.b5dc_cm import B5dcDeviceComponentManager

ATTENUATION_DB_IN_RANGE = 31
ATTENUATION_DB_OUTSIDE_RANGE = -1


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
        b5dc_cm.start_communicating()

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


@pytest.mark.unit
@pytest.mark.forked
@pytest.mark.parametrize(
    "frequency_to_set",
    [
        B5dcFrequency.F_11_1_GHZ,
        B5dcFrequency.F_13_2_GHZ,
        B5dcFrequency.F_13_86_GHZ,
    ],
)
def test_b5dc_set_frequency_method_with_valid_input(
    frequency_to_set: B5dcFrequency, callbacks: dict
) -> None:
    """Verify SetFrequency returns expected LRC updates on supplying valid input."""
    update_period = 2
    with patch("ska_mid_dish_b5dc_proxy.b5dc_cm.B5dcInterface", AsyncMock()), patch(
        "ska_mid_dish_b5dc_proxy.b5dc_cm.B5dcPropertyParser", Mock()
    ), patch("ska_mid_dish_b5dc_proxy.b5dc_cm.B5dcProtocol", Mock()):
        b5dc_cm = B5dcDeviceComponentManager("127.0.0.1", 10001, update_period, Mock())
        b5dc_cm.start_communicating()

    max_try = 5
    for iterations in range(max_try):
        if not b5dc_cm.is_connection_established():
            time.sleep(1)
        else:
            break

    assert iterations < max_try - 1, "Connection not established"

    b5dc_cm._b5dc_device_freq_conf = AsyncMock()

    # Set the frequency and verify that expected lrc updates are published
    b5dc_cm._set_frequency(frequency_to_set, task_callback=callbacks["task_cb"])

    expected_call_kwargs = (
        {
            "status": TaskStatus.IN_PROGRESS,
            "progress": f"Called SetFrequency with arg (frequency={frequency_to_set})",
        },
        {
            "status": TaskStatus.COMPLETED,
            "result": f"SetFrequency({frequency_to_set}) completed",
        },
    )

    wait_count = 1
    while wait_count <= 3:
        if callbacks["task_cb"].call_count < len(expected_call_kwargs):
            time.sleep(0.2)
            wait_count += 1
        else:
            break

    call_args_list = callbacks["task_cb"].call_args_list

    for count, call in enumerate(call_args_list):
        _, kwargs = call
        assert kwargs == expected_call_kwargs[count]


@pytest.mark.unit
@pytest.mark.forked
@pytest.mark.parametrize(
    "attenuation_register",
    [
        "spi_rfcm_h_attenuation",
        "spi_rfcm_v_attenuation",
    ],
)
def test_b5dc_set_attenuation_with_valid_input(attenuation_register: str, callbacks: dict) -> None:
    """Verify SetAttenuation returns expected LRC updates on supplying valid input."""
    update_period = 2
    with patch("ska_mid_dish_b5dc_proxy.b5dc_cm.B5dcInterface", AsyncMock()), patch(
        "ska_mid_dish_b5dc_proxy.b5dc_cm.B5dcPropertyParser", Mock()
    ), patch("ska_mid_dish_b5dc_proxy.b5dc_cm.B5dcProtocol", Mock()):
        b5dc_cm = B5dcDeviceComponentManager("127.0.0.1", 10001, update_period, Mock())
        b5dc_cm.start_communicating()

    max_try = 5
    for iterations in range(max_try):
        if not b5dc_cm.is_connection_established():
            time.sleep(1)
        else:
            break

    assert iterations < max_try - 1, "Connection not established"

    b5dc_cm._b5dc_device_attn_conf = AsyncMock()

    # Set the attenuation and verify that expected lrc updates are published
    b5dc_cm._set_attenuation(
        ATTENUATION_DB_IN_RANGE,
        attenuation_register,
        task_callback=callbacks["task_cb"],
    )

    expected_call_kwargs = (
        {
            "status": TaskStatus.IN_PROGRESS,
            "progress": "Called SetAttenuation with args "
            f"(attenuation_db={ATTENUATION_DB_IN_RANGE}, "
            f"attn_reg_name={attenuation_register})",
        },
        {
            "status": TaskStatus.COMPLETED,
            "result": f"SetAttenuation({ATTENUATION_DB_IN_RANGE}, "
            f"{attenuation_register}) completed",
        },
    )

    wait_count = 1
    while wait_count <= 3:
        if callbacks["task_cb"].call_count < len(expected_call_kwargs):
            time.sleep(0.2)
            wait_count += 1
        else:
            break

    call_args_list = callbacks["task_cb"].call_args_list

    for count, call in enumerate(call_args_list):
        _, kwargs = call
        assert kwargs == expected_call_kwargs[count]


@pytest.mark.unit
@pytest.mark.forked
@pytest.mark.parametrize(
    "attenuation_register",
    [
        "spi_rfcm_h_attenuation",
        "spi_rfcm_v_attenuation",
    ],
)
def test_b5dc_set_attenuation_with_invalid_input(
    attenuation_register: str, callbacks: dict
) -> None:
    """Verify SetAttenuation returns expected LRC updates on invalid input."""
    update_period = 2
    with patch("ska_mid_dish_b5dc_proxy.b5dc_cm.B5dcInterface", AsyncMock()), patch(
        "ska_mid_dish_b5dc_proxy.b5dc_cm.B5dcPropertyParser", Mock()
    ), patch("ska_mid_dish_b5dc_proxy.b5dc_cm.B5dcProtocol", Mock()):
        b5dc_cm = B5dcDeviceComponentManager("127.0.0.1", 10001, update_period, Mock())
        b5dc_cm.start_communicating()

    max_try = 5
    for iterations in range(max_try):
        if not b5dc_cm.is_connection_established():
            time.sleep(1)
        else:
            break

    assert iterations < max_try - 1, "Connection not established"

    b5dc_cm._b5dc_device_attn_conf.set_attenuation = AsyncMock(
        side_effect=B5dcDeviceAttenuationException("ex")
    )

    b5dc_cm._set_attenuation(
        ATTENUATION_DB_IN_RANGE,
        attenuation_register,
        task_callback=callbacks["task_cb"],
    )

    b5dc_cm._b5dc_device_attn_conf.set_attenuation.assert_called_once()

    expected_call_kwargs = (
        {
            "status": TaskStatus.IN_PROGRESS,
            "progress": "Called SetAttenuation with args "
            f"(attenuation_db={ATTENUATION_DB_IN_RANGE}, "
            f"attn_reg_name={attenuation_register})",
        },
        {
            "status": TaskStatus.FAILED,
            "result": "An error occured on setting the B5dc attenuation "
            f"on {attenuation_register}: ex",
        },
    )

    wait_count = 1
    while wait_count <= 3:
        if callbacks["task_cb"].call_count < len(expected_call_kwargs):
            time.sleep(0.2)
            wait_count += 1
        else:
            break

    call_args_list = callbacks["task_cb"].call_args_list

    for count, call in enumerate(call_args_list):
        _, kwargs = call
        assert kwargs == expected_call_kwargs[count]
