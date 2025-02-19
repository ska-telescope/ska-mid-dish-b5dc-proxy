"""Contains pytest fixtures for tango unit tests setup."""

import time
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest

from ska_mid_dish_b5dc_manager.b5dc_cm import B5dcDeviceComponentManager

B5DC_DEVICE_IP = "127.0.0.1"
B5DC_VER_TEST = "B5dc version 123"
B5DC_COMM_VER_TEST = "B5dc comms 123"
B5DC_RF_PSU_VER_TEST = "B5dc rfcm psu 123"
B5DC_RF_PCB_VER_TEST = "B5dc rfcm pcb 123"
B5DC_BACKPLANE_VER_TEST = "B5dc backplane 123"
B5DC_PSU_VER_TEST = "B5dc psu 123"
B5DC_ICD_VER_TEST = "B5dc icd 123"
B5DC_FW_VER_TEST = "123"
B5DC_MDL_NAME_TEST = "fpga_model_name"


@pytest.fixture(scope="function")
def b5dc_cm_setup() -> Any:
    """Create component manager for testing."""
    with patch("ska_mid_dish_b5dc_manager.b5dc_cm.B5dcInterface", AsyncMock()), patch(
        "ska_mid_dish_b5dc_manager.b5dc_cm.B5dcPropertyParser", Mock()
    ), patch(
        "ska_mid_dish_b5dc_manager.b5dc_cm.B5dcDeviceSensors", Mock()
    ) as b5dc_sensor_mock, patch(
        "ska_mid_dish_b5dc_manager.b5dc_cm.B5dcProtocol", Mock()
    ), patch(
        "ska_mid_dish_b5dc_manager.b5dc_cm.B5dcIicDevice", Mock()
    ), patch(
        "ska_mid_dish_b5dc_manager.b5dc_cm.B5dcFpgaFirmware", Mock()
    ) as b5dc_fw_mock, patch(
        "ska_mid_dish_b5dc_manager.b5dc_cm.B5dcPhysicalConfiguration", Mock()
    ) as b5dc_pca_mock, patch.object(
        B5dcDeviceComponentManager, "_update_sensor_with_lock"
    ) as update_sensor_mock:
        b5dc_pca_mock.return_value.update_pca_info = AsyncMock()
        b5dc_pca_mock.return_value.b5dc_version = B5DC_VER_TEST
        b5dc_pca_mock.return_value.b5dc_comms_engine_version = B5DC_COMM_VER_TEST
        b5dc_pca_mock.return_value.b5dc_rfcm_psu_version = B5DC_RF_PSU_VER_TEST
        b5dc_pca_mock.return_value.b5dc_rfcm_pcb_version = B5DC_RF_PCB_VER_TEST
        b5dc_pca_mock.return_value.b5dc_backplane_version = B5DC_BACKPLANE_VER_TEST
        b5dc_pca_mock.return_value.b5dc_psu_version = B5DC_PSU_VER_TEST
        b5dc_pca_mock.return_value.b5dc_icd_version = B5DC_ICD_VER_TEST

        b5dc_fw_mock.return_value.update_firmware_build_timestamp = AsyncMock()
        b5dc_fw_mock.return_value.b5dc_build_time = B5DC_FW_VER_TEST

        b5dc_fw_mock.return_value.update_model_filename = AsyncMock()
        b5dc_fw_mock.return_value.b5dc_file_model_name = B5DC_MDL_NAME_TEST

        b5dc_cm = B5dcDeviceComponentManager(B5DC_DEVICE_IP, 10001, Mock(), Mock())
        b5dc_cm.start_communicating()

        max_try = 5
        for iterations in range(max_try):
            if not b5dc_cm.is_connection_established():
                time.sleep(1)
            else:
                break

        assert iterations < max_try - 1, "Connection not established"

        yield b5dc_cm, [update_sensor_mock, b5dc_sensor_mock]


@pytest.fixture(scope="function")
def b5dc_cm_with_comms_failed() -> Any:
    """Create component manager for testing where the comms to b5dc failed."""
    with patch("ska_mid_dish_b5dc_manager.b5dc_cm.B5dcInterface", AsyncMock()), patch(
        "ska_mid_dish_b5dc_manager.b5dc_cm.B5dcPropertyParser", Mock()
    ), patch(
        "ska_mid_dish_b5dc_manager.b5dc_cm.B5dcDeviceSensors", Mock()
    ) as b5dc_sensor_mock, patch(
        "ska_mid_dish_b5dc_manager.b5dc_cm.B5dcProtocol", Mock()
    ), patch(
        "ska_mid_dish_b5dc_manager.b5dc_cm.B5dcIicDevice", Mock()
    ), patch(
        "ska_mid_dish_b5dc_manager.b5dc_cm.B5dcFpgaFirmware", Mock()
    ) as b5dc_fw_mock, patch(
        "ska_mid_dish_b5dc_manager.b5dc_cm.B5dcPhysicalConfiguration", Mock()
    ) as b5dc_pca_mock, patch.object(
        B5dcDeviceComponentManager, "_update_sensor_with_lock"
    ) as update_sensor_mock:
        b5dc_pca_mock.return_value = None
        b5dc_fw_mock.return_value = None

        b5dc_cm = B5dcDeviceComponentManager(B5DC_DEVICE_IP, 10001, Mock(), Mock())
        b5dc_cm.start_communicating()

        max_try = 5
        for iterations in range(max_try):
            if not b5dc_cm.is_connection_established():
                time.sleep(1)
            else:
                break

        assert iterations < max_try - 1, "Connection not established"

        yield b5dc_cm, [update_sensor_mock, b5dc_sensor_mock]


@pytest.fixture(scope="function")
def callbacks() -> dict:
    """Return a dictionary of callbacks."""
    return {
        "comm_state_cb": Mock(),
        "comp_state_cb": Mock(),
        "task_cb": Mock(),
    }
