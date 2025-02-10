"""Test attribute and change events are configured and received."""

from typing import Callable

import pytest
from tango import DevFailed, DeviceProxy, EventType, utils

polled_attributes = [
    "rfcmPllLock",
    "clkPhotodiodeCurrent",
    "hPolRfPowerIn",
    "vPolRfPowerIn",
    "hPolRfPowerOut",
    "vPolRfPowerOut",
    "rfTemperature",
    "rfcmPsuPcbTemperature",
]

# Omit attributes inherited from the base device when testing event configuration
attrs_without_events_configured = ["loggingLevel", "loggingTargets", "versionId"]

RECEIVE_EVENT_TIMEOUT = 30


@pytest.mark.acceptance
def test_attr_change_events_configured(b5dc_manager_proxy: DeviceProxy):
    """Test that change events are configured for all B5dc manager attributes."""
    b5dc_manager_attrs = b5dc_manager_proxy.get_attribute_list()

    change_events_configured_for_all_attrs = True
    for attr in b5dc_manager_attrs:
        if attr not in attrs_without_events_configured:
            try:
                b5dc_manager_proxy.subscribe_event(
                    attr, EventType.CHANGE_EVENT, utils.EventCallback()
                )
            except DevFailed as err:
                assert err.args[0].reason == "API_AttributePollingNotStarted"
                print(f"Change event not configured for attribute: {attr}")
                change_events_configured_for_all_attrs = False

    assert change_events_configured_for_all_attrs


@pytest.mark.acceptance
def test_attr_archive_events_configured(b5dc_manager_proxy: DeviceProxy):
    """Test that archive events are configured for all B5dc manager attributes."""
    b5dc_manager_attrs = b5dc_manager_proxy.get_attribute_list()

    archive_events_configured_for_all_attrs = True
    for attr in b5dc_manager_attrs:
        if attr not in attrs_without_events_configured:
            try:
                b5dc_manager_proxy.subscribe_event(
                    attr, EventType.ARCHIVE_EVENT, utils.EventCallback()
                )
            except DevFailed as err:
                assert err.args[0].reason == "API_AttributePollingNotStarted"
                print(f"Archive event not configured for attribute: {attr}")
                archive_events_configured_for_all_attrs = False

    assert archive_events_configured_for_all_attrs


@pytest.mark.parametrize(
    "sensor_attr",
    polled_attributes,
)
@pytest.mark.parametrize(
    "evt_type",
    [EventType.CHANGE_EVENT, EventType.ARCHIVE_EVENT],
)
@pytest.mark.acceptance
def test_events_received(
    b5dc_manager_proxy: DeviceProxy,
    event_store_class: Callable,
    sensor_attr: str,
    evt_type: EventType,
):
    """Test polling mechanism pushes change and archive events."""
    event_store_class = event_store_class()

    try:
        subscription_id = b5dc_manager_proxy.subscribe_event(
            sensor_attr, evt_type, event_store_class
        )
        event_store_class.clear_queue()
        event_store_class.wait_for_n_events(event_count=1, timeout=RECEIVE_EVENT_TIMEOUT)
    finally:
        b5dc_manager_proxy.unsubscribe_event(subscription_id)
