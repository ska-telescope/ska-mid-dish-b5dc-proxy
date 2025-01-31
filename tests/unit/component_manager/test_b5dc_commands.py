# pylint: disable=protected-access
"""Test component manager handling of unhappy path on SetFrequency cmd call."""
import time
from unittest.mock import AsyncMock

import pytest
from ska_control_model import TaskStatus
from ska_mid_dish_dcp_lib.device.b5dc_device import B5dcDeviceAttenuationException
from ska_mid_dish_dcp_lib.device.b5dc_device_mappings import B5dcFrequency

ATTENUATION_DB_IN_RANGE = 31
ATTENUATION_DB_OUTSIDE_RANGE = -1


@pytest.mark.unit
@pytest.mark.forked
def test_b5dc_set_frequency_rejects_invalid_freq(b5dc_cm_setup) -> None:
    """Verify SetFrequency returns TaskStatus.REJECTED for invalid freq. arg."""
    b5dc_cm, _ = b5dc_cm_setup

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
    frequency_to_set: B5dcFrequency, callbacks: dict, b5dc_cm_setup
) -> None:
    """Verify SetFrequency returns expected LRC updates on supplying valid input."""
    b5dc_cm, _ = b5dc_cm_setup
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
def test_b5dc_set_attenuation_with_valid_input(
    attenuation_register: str, callbacks: dict, b5dc_cm_setup
) -> None:
    """Verify SetAttenuation returns expected LRC updates on supplying valid input."""
    b5dc_cm, _ = b5dc_cm_setup
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
    attenuation_register: str, callbacks: dict, b5dc_cm_setup
) -> None:
    """Verify SetAttenuation returns expected LRC updates on invalid input."""
    b5dc_cm, _ = b5dc_cm_setup

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
