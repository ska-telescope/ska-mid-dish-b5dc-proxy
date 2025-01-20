"""Test client can subscribe to archive and change events."""

import pytest
import tango

attributes = [
    "rfcmFrequency",
    "rfcmPllLock",
    "rfcmHAttenuation",
    "rfcmVAttenuation",
    "clkPhotodiodeCurrent",
    "hPolRfPowerIn",
    "vPolRfPowerIn",
    "hPolRfPowerOut",
    "vPolRfPowerOut",
    "rfTemperature",
    "rfcmPsuPcbTemperature",
]


@pytest.mark.unit
@pytest.mark.forked
def test_client_test_attributes_exist(b5dc_proxy):
    """Verify b5dc attributes exposed."""
    attr = b5dc_proxy.get_attribute_list()
    assert set(attributes).issubset(set(attr))


@pytest.mark.parametrize("attr", attributes)
@pytest.mark.unit
@pytest.mark.forked
def test_client_receives_archive_event(b5dc_proxy, event_store, attr):
    """Verify archive events are configured."""
    b5dc_proxy.subscribe_event(
        attr,
        tango.EventType.ARCHIVE_EVENT,
        event_store,
    )

    assert event_store.get_queue_events()


@pytest.mark.parametrize("attr", attributes)
@pytest.mark.unit
@pytest.mark.forked
def test_client_receives_change_event(b5dc_proxy, event_store, attr):
    """Verify change events are configured."""
    b5dc_proxy.subscribe_event(
        attr,
        tango.EventType.CHANGE_EVENT,
        event_store,
    )

    assert event_store.get_queue_events()
