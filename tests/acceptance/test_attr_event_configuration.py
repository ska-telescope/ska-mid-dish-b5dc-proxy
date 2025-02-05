"""Test that attribute and change events are configured for all B5dc Proxy attributes."""

import pytest
from tango import DevFailed, DeviceProxy, EventType, utils


@pytest.mark.acceptance
def test_attr_change_events_configured(b5dc_manager_proxy: DeviceProxy):
    """Test that change events are configured for all B5dc manager attributes."""
    b5dc_manager_attrs = b5dc_manager_proxy.get_attribute_list()

    change_events_configured_for_all_attrs = True
    for attr in b5dc_manager_attrs:
        try:
            b5dc_manager_proxy.subscribe_event(attr, EventType.CHANGE_EVENT, utils.EventCallback())
        except DevFailed as err:
            assert err.args[0].reason == "API_AttributePollingNotStarted"
            change_events_configured_for_all_attrs = False

    assert change_events_configured_for_all_attrs


@pytest.mark.acceptance
def test_attr_archive_events_configured(b5dc_manager_proxy: DeviceProxy):
    """Test that archive events are configured for all B5dc manager attributes."""
    b5dc_manager_attrs = b5dc_manager_proxy.get_attribute_list()

    archive_events_configured_for_all_attrs = True
    for attr in b5dc_manager_attrs:
        try:
            b5dc_manager_proxy.subscribe_event(
                attr, EventType.ARCHIVE_EVENT, utils.EventCallback()
            )
        except DevFailed as err:
            assert err.args[0].reason == "API_AttributePollingNotStarted"
            archive_events_configured_for_all_attrs = False

    assert archive_events_configured_for_all_attrs
