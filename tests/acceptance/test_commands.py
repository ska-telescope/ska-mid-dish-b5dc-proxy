"""Acceptance test to verify the b5dc tango device commands."""


from typing import Any

import pytest
import tango
from ska_control_model import ResultCode
from ska_mid_dish_dcp_lib.device.b5dc_device_mappings import B5dcFrequency
from tango import DeviceProxy

from tests.unit.component_manager.test_b5dc_commands import ATTENUATION_DB_OUTSIDE_RANGE

frequency_mapping = {
    B5dcFrequency.F_11_1_GHZ: 11.1,
    B5dcFrequency.F_13_2_GHZ: 13.2,
    B5dcFrequency.F_13_86_GHZ: 13.86,
}


@pytest.mark.acceptance
@pytest.mark.forked
@pytest.mark.parametrize(
    "type_of_attenuation, attenuation_register",
    [
        ("rfcmHAttenuation", "spi_rfcm_h_attenuation"),
        ("rfcmVAttenuation", "spi_rfcm_v_attenuation"),
    ],
)
def test_SetAttenuation_with_valid_input(
    b5dc_manager_proxy: DeviceProxy,
    event_store_class: Any,
    type_of_attenuation: str,
    attenuation_register: str,
):
    """Tests behavior when setting attenuations with valid values."""
    generated_attenuation = (b5dc_manager_proxy.read_attribute(type_of_attenuation).value + 1) % 32
    generated_attenuation = int(generated_attenuation)
    progress_event_store = event_store_class()
    b5dc_manager_proxy.subscribe_event(
        "longrunningcommandprogress", tango.EventType.CHANGE_EVENT, progress_event_store
    )

    result_event_store = event_store_class()
    b5dc_manager_proxy.subscribe_event(
        "longrunningcommandresult", tango.EventType.CHANGE_EVENT, result_event_store
    )
    if type_of_attenuation == "rfcmHAttenuation":
        [[_], [command_id]] = b5dc_manager_proxy.SetHPolAttenuation(generated_attenuation)
        progress_event_store.wait_for_progress_update(
            f"Called SetAttenuation with args (attenuation_db={generated_attenuation}, "
            f"attn_reg_name={attenuation_register}"
        )
        result_event_store.wait_for_command_id(command_id, timeout=5)
        expected_attenuation = b5dc_manager_proxy.read_attribute(type_of_attenuation).value
        assert generated_attenuation == expected_attenuation
    else:
        [[_], [command_id]] = b5dc_manager_proxy.SetVPolAttenuation(generated_attenuation)
        progress_event_store.wait_for_progress_update(
            f"Called SetAttenuation with args (attenuation_db={generated_attenuation}, "
            f"attn_reg_name={attenuation_register}"
        )
        result_event_store.wait_for_command_id(command_id, timeout=5)
        expected_attenuation = b5dc_manager_proxy.read_attribute(type_of_attenuation).value
        assert generated_attenuation == expected_attenuation


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
    result_event_store.wait_for_command_id(command_id, timeout=5)
    updated_frequency = b5dc_manager_proxy.read_attribute("rfcmFrequency").value
    assert updated_frequency == expected_frequency


@pytest.mark.acceptance
@pytest.mark.forked
@pytest.mark.parametrize(
    "invalid_input_frequency",
    [
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


@pytest.mark.acceptance
@pytest.mark.forked
@pytest.mark.parametrize(
    "type_of_attenuation, attenuation_register",
    [
        ("rfcmVAttenuation", "spi_rfcm_v_attenuation"),
        ("rfcmHAttenuation", "spi_rfcm_h_attenuation"),
    ],
)
def test_SetAttenuation_with_invalid_input(
    b5dc_manager_proxy: DeviceProxy,
    event_store_class: Any,
    type_of_attenuation: str,
    attenuation_register: str,
):
    """Tests behavior when setting the attenuations with invalid values."""
    progress_event_store = event_store_class()
    b5dc_manager_proxy.subscribe_event(
        "longrunningcommandprogress", tango.EventType.CHANGE_EVENT, progress_event_store
    )

    result_event_store = event_store_class()
    b5dc_manager_proxy.subscribe_event(
        "longrunningcommandresult", tango.EventType.CHANGE_EVENT, result_event_store
    )
    if type_of_attenuation == "rfcmHAttenuation":
        [[_], [command_id]] = b5dc_manager_proxy.SetHPolAttenuation(ATTENUATION_DB_OUTSIDE_RANGE)
        progress_event_store.wait_for_progress_update(
            f"Called SetAttenuation with args (attenuation_db={ATTENUATION_DB_OUTSIDE_RANGE}, "
            f"attn_reg_name={attenuation_register}"
        )
        expected_result = (
            '"An error occured on setting the B5dc attenuation on '
            + 'spi_rfcm_h_attenuation: Attenuation must be >= 0 and less than (32.0)"'
        )
        result_event_store.wait_for_command_result(command_id, expected_result, timeout=5)
    else:
        [[_], [command_id]] = b5dc_manager_proxy.SetVPolAttenuation(ATTENUATION_DB_OUTSIDE_RANGE)
        progress_event_store.wait_for_progress_update(
            f"Called SetAttenuation with args (attenuation_db={ATTENUATION_DB_OUTSIDE_RANGE}, "
            f"attn_reg_name={attenuation_register}"
        )
        expected_result = (
            '"An error occured on setting the B5dc attenuation on '
            + 'spi_rfcm_v_attenuation: Attenuation must be >= 0 and less than (32.0)"'
        )
        result_event_store.wait_for_command_result(command_id, expected_result, timeout=5)
