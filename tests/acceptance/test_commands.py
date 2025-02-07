"""Acceptance test to verify the b5dc tango device commands."""


from random import randint
from typing import Any

import pytest
import tango
from ska_control_model import ResultCode
from ska_mid_dish_dcp_lib.device.b5dc_device_mappings import B5dcFrequency
from tango import DeviceProxy

from tests.unit.component_manager.test_b5dc_commands import (
    ATTENUATION_DB_IN_RANGE,
    ATTENUATION_DB_OUTSIDE_RANGE,
)

# from conftest import b5dc_manager_proxy


frequency_mapping = {
    B5dcFrequency.F_11_1_GHZ: 11.1,
    B5dcFrequency.F_13_2_GHZ: 13.2,
    B5dcFrequency.F_13_86_GHZ: 13.86,
}


@pytest.mark.acceptance
@pytest.mark.forked
def test_SetHPolAttenuation_with_valid_input(
    b5dc_manager_proxy: DeviceProxy, event_store_class: Any
) -> None:
    """Tests behavior when setting horizontal attenuations with valid values."""
    generated_h_attenuation = randint(0, ATTENUATION_DB_IN_RANGE)
    while generated_h_attenuation == b5dc_manager_proxy.read_attribute("rfcmHAttenuation").value:
        generated_h_attenuation = randint(0, ATTENUATION_DB_IN_RANGE)
    progress_event_store = event_store_class()
    b5dc_manager_proxy.subscribe_event(
        "longrunningcommandprogress", tango.EventType.CHANGE_EVENT, progress_event_store
    )

    result_event_store = event_store_class()
    b5dc_manager_proxy.subscribe_event(
        "longrunningcommandresult", tango.EventType.CHANGE_EVENT, result_event_store
    )
    [[_], [command_id]] = b5dc_manager_proxy.SetHPolAttenuation(generated_h_attenuation)
    progress_event_store.wait_for_progress_update(
        f"Called SetAttenuation with args (attenuation_db={generated_h_attenuation},"
        f"attn_reg_name=spi_rfcm_h_attenuation"
    )
    result_event_store.wait_for_command_id(command_id, 5)
    expected_h_attenuation = b5dc_manager_proxy.read_attribute("rfcmHAttenuation").value
    result_event_store.clear_queue()
    assert generated_h_attenuation == expected_h_attenuation


@pytest.mark.acceptance
@pytest.mark.forked
def test_SetVPolAttenuation_with_valid_input(
    b5dc_manager_proxy: DeviceProxy, event_store_class: Any
) -> None:
    """Tests behavior when setting vertical attenuations with valid values."""
    generated_v_attenuation = randint(0, ATTENUATION_DB_IN_RANGE)
    while generated_v_attenuation == b5dc_manager_proxy.read_attribute("rfcmVAttenuation").value:
        generated_v_attenuation = randint(0, ATTENUATION_DB_IN_RANGE)
    progress_event_store = event_store_class()
    b5dc_manager_proxy.subscribe_event(
        "longrunningcommandprogress", tango.EventType.CHANGE_EVENT, progress_event_store
    )

    result_event_store = event_store_class()
    b5dc_manager_proxy.subscribe_event(
        "longrunningcommandresult", tango.EventType.CHANGE_EVENT, result_event_store
    )
    [[_], [command_id]] = b5dc_manager_proxy.SetVPolAttenuation(generated_v_attenuation)
    progress_event_store.wait_for_progress_update(
        f"Called SetAttenuation with args (attenuation_db={generated_v_attenuation}, "
        f"attn_reg_name=spi_rfcm_v_attenuation"
    )
    result_event_store.wait_for_command_id(command_id, 5)
    expected_v_attentuation = b5dc_manager_proxy.read_attribute("rfcmVAttenuation").value
    result_event_store.clear_queue()
    assert generated_v_attenuation == expected_v_attentuation


@pytest.mark.acceptance
@pytest.mark.forked
@pytest.mark.parametrize(
    "set_frequency, expected_frequency",
    [
        (B5dcFrequency.F_11_1_GHZ, 11.1),
        (B5dcFrequency.F_13_2_GHZ, 13.2),
        (B5dcFrequency.F_13_86_GHZ, 13.86),
    ],
)
def test_SetFrequency_with_valid_input(
    b5dc_manager_proxy: DeviceProxy,
    event_store_class: Any,
    set_frequency: B5dcFrequency,
    expected_frequency: float,
) -> None:
    """Test SetFrequency behavior given valid frquency arguments."""
    progress_event_store = event_store_class()
    b5dc_manager_proxy.subscribe_event(
        "longrunningcommandprogress", tango.EventType.CHANGE_EVENT, progress_event_store
    )
    result_event_store = event_store_class()
    b5dc_manager_proxy.subscribe_event(
        "longrunningcommandresult", tango.EventType.CHANGE_EVENT, result_event_store
    )

    [[_], [command_id]] = b5dc_manager_proxy.SetFrequency(set_frequency)
    progress_event_store.wait_for_progress_update(
        f"Called SetFrequency with arg (frequency={set_frequency.value})"
    )
    result_event_store.wait_for_command_id(command_id, 5)
    updated_frequency = b5dc_manager_proxy.read_attribute("rfcmFrequency").value
    result_event_store.clear_queue()
    assert updated_frequency == expected_frequency


@pytest.mark.acceptance
@pytest.mark.forked
@pytest.mark.parametrize(
    "invalid_input_frequency",
    [
        ATTENUATION_DB_OUTSIDE_RANGE,
        5,
        6,
        7,
    ],
)
def test_SetFrequency_with_invalid_input(
    b5dc_manager_proxy: DeviceProxy, invalid_input_frequency: int
) -> None:
    """Test SetFrequency behavior with invalid arguments."""
    [[result_code], [message]] = b5dc_manager_proxy.SetFrequency(invalid_input_frequency)

    assert (
        message == f"Invalid frequency value supplied: {invalid_input_frequency}. "
        f"Expected B5dcFrequency enum value (ie: B5dcFrequency.F_11_1_GHZ(1), "
        f"B5dcFrequency.F_13_2_GHZ(2) or B5dcFrequency.F_13_86_GHZ(3))"
    )
    assert result_code == ResultCode.REJECTED
