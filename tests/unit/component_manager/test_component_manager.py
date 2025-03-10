"""Test b5dc component manager."""

import json
import time
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest

from ska_mid_dish_b5dc_proxy.b5dc_cm import B5dcDeviceComponentManager
from ska_mid_dish_b5dc_proxy.models.constants import B5DC_BUILD_STATE_DEVICE_NAME

from .conftest import (
    B5DC_BACKPLANE_VER_TEST,
    B5DC_COMM_VER_TEST,
    B5DC_DEVICE_IP,
    B5DC_FW_VER_TEST,
    B5DC_ICD_VER_TEST,
    B5DC_MDL_NAME_TEST,
    B5DC_PSU_VER_TEST,
    B5DC_RF_PCB_VER_TEST,
    B5DC_RF_PSU_VER_TEST,
    B5DC_VER_TEST,
)

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
def test_b5dc_build_state_populated(b5dc_cm_setup: Any) -> None:
    """Verify b5dc build state populated."""
    b5dc_cm, _ = b5dc_cm_setup

    expected_firmware_file = f"{B5DC_MDL_NAME_TEST}_{B5DC_FW_VER_TEST}.fpg"
    build_state_json = json.loads(b5dc_cm.component_state["buildstate"])

    assert build_state_json["device"] == B5DC_BUILD_STATE_DEVICE_NAME
    assert build_state_json["device"] == B5DC_BUILD_STATE_DEVICE_NAME
    assert build_state_json["device_ip"] == B5DC_DEVICE_IP
    assert build_state_json["device_version"] == B5DC_VER_TEST
    assert build_state_json["comms_engine_version"] == B5DC_COMM_VER_TEST
    assert build_state_json["rfcm_psu_version"] == B5DC_RF_PSU_VER_TEST
    assert build_state_json["rfcm_pcb_version"] == B5DC_RF_PCB_VER_TEST
    assert build_state_json["backplane_version"] == B5DC_BACKPLANE_VER_TEST
    assert build_state_json["psu_version"] == B5DC_PSU_VER_TEST
    assert build_state_json["icd_version"] == B5DC_ICD_VER_TEST
    assert build_state_json["fpga_firmware_file"] == expected_firmware_file


@pytest.mark.unit
@pytest.mark.forked
def test_b5dc_build_state_default(b5dc_cm_with_comms_failed: Any) -> None:
    """Verify b5dc build state updated if comms failed."""
    b5dc_cm, _ = b5dc_cm_with_comms_failed

    build_state_json = json.loads(b5dc_cm.component_state["buildstate"])

    assert build_state_json["device"] == B5DC_BUILD_STATE_DEVICE_NAME
    assert (
        build_state_json["device_ip"]
        == "Failed to retrieve build state data for band 5 down converter."
    )
    assert build_state_json["device_version"] == ""
    assert build_state_json["comms_engine_version"] == ""
    assert build_state_json["rfcm_psu_version"] == ""
    assert build_state_json["rfcm_pcb_version"] == ""
    assert build_state_json["backplane_version"] == ""
    assert build_state_json["psu_version"] == ""
    assert build_state_json["icd_version"] == ""
    assert build_state_json["fpga_firmware_file"] == ""


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

    mock_frequency_val = 11.1
    b5dc_sensor_mock.return_value.rfcm_frequency = mock_frequency_val

    register_name = "spi_rfcm_frequency"
    b5dc_cm.sync_register_outside_event_loop(register_name)

    call_counts = get_arguments_histogram(update_sensor_mock.call_args_list)

    # 1 additional call for the initial periodic update
    assert call_counts[register_name] == 2
    # check that the last call to update component state has expected args
    assert b5dc_cm.component_state[register_name] == mock_frequency_val


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
    ) as update_sensor_mock, patch.object(
        B5dcDeviceComponentManager, "_update_build_state"
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

        time.sleep(wait_duration)
        # expect wait_duration / update_period sensor updates
        call_counts = get_arguments_histogram(update_sensor_mock.call_args_list)

        assert len(call_counts) == NUM_OF_ATTRIBUTES
        assert all(value == wait_duration // update_period + 1 for value in call_counts.values())
