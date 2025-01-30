"""Test b5dc component manager."""

import time
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest

from ska_mid_dish_b5dc_proxy.b5dc_cm import B5dcDeviceComponentManager

NUM_OF_ATTRIBUTES = 11


def get_arguments_histogram(arg_list: Any) -> Any:
    """Create frequency counter of arguments."""
    args = [arg.args[0] for arg in arg_list]
    call_counts = {}
    for arg in args:
        if arg not in call_counts:
            call_counts[arg] = 1
        else:
            call_counts[arg] += 1

    return call_counts


@pytest.mark.unit
@pytest.mark.forked
def test_b5dc_comms_thread_created(b5dc_cm_setup: Any) -> None:
    """Verify b5dc thread created."""
    b5dc_cm, _ = b5dc_cm_setup
    assert b5dc_cm.loop_thread.is_alive()


@pytest.mark.unit
@pytest.mark.forked
def test_b5dc_variable_polling_update(b5dc_cm_setup: Any) -> None:
    """Verify variables are updated via polling."""
    _, mocks = b5dc_cm_setup
    update_sensor_mock = mocks[0]
    assert update_sensor_mock.call_count == NUM_OF_ATTRIBUTES


@pytest.mark.unit
@pytest.mark.forked
def test_b5dc_variable_sync_update(b5dc_cm_setup: Any) -> None:
    """Verify variables can be updated synchronously."""
    b5dc_cm, mocks = b5dc_cm_setup
    update_sensor_mock = mocks[0]
    b5dc_sensor_mock = mocks[1]
    update_component_state_mock = mocks[2]

    mock_frequency_val = 11.1
    b5dc_sensor_mock.return_value.rfcm_frequency = mock_frequency_val

    register_name = "spi_rfcm_frequency"
    b5dc_cm.sync_register_outside_event_loop(register_name)

    call_counts = get_arguments_histogram(update_sensor_mock.call_args_list)

    # 1 additional call for the initial periodic update
    assert call_counts[register_name] == 2
    # check that the last call to update component state has expected args
    assert update_component_state_mock.call_args.kwargs == {register_name: mock_frequency_val}


@pytest.mark.unit
@pytest.mark.forked
def test_b5dc_polling_update_frequency() -> None:
    """Verify polling update frequency."""
    update_period = 2
    wait_duration = 11

    with patch("ska_mid_dish_b5dc_proxy.b5dc_cm.B5dcInterface", AsyncMock()), patch(
        "ska_mid_dish_b5dc_proxy.b5dc_cm.B5dcPropertyParser", Mock()
    ), patch("ska_mid_dish_b5dc_proxy.b5dc_cm.B5dcDeviceSensors", Mock()), patch(
        "ska_mid_dish_b5dc_proxy.b5dc_cm.B5dcProtocol", Mock()
    ), patch.object(
        B5dcDeviceComponentManager, "_update_sensor_with_lock"
    ) as update_sensor_mock:
        b5dc_cm = B5dcDeviceComponentManager("127.0.0.1", 10001, update_period, Mock())
        b5dc_cm.start_communicating()

        max_try = 5
        for iterations in range(max_try):
            if not b5dc_cm.is_connection_established():
                time.sleep(1)
            else:
                break

        assert iterations < max_try - 1, "Connection not established"

        time.sleep(wait_duration)
        # expect wait_duration / update_period sensor updates
        call_counts = get_arguments_histogram(update_sensor_mock.call_args_list)

        assert len(call_counts) == NUM_OF_ATTRIBUTES
        assert all(value == wait_duration // update_period + 1 for value in call_counts.values())
