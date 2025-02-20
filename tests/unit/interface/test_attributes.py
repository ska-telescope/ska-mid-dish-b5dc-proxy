"""Test client can subscribe to archive and change events."""

from typing import Any

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
def test_client_test_attributes_exist(b5dc_manager: Any) -> None:
    """Verify b5dc attributes exposed."""
    attr = b5dc_manager.get_attribute_list()
    assert set(attributes).issubset(set(attr))


@pytest.mark.parametrize("attr", attributes)
@pytest.mark.unit
@pytest.mark.forked
def test_client_receives_archive_event(
    b5dc_manager: Any, event_store_class: Any, attr: Any
) -> None:
    """Verify archive events are configured."""
    b5dc_manager.subscribe_event(
        attr,
        tango.EventType.ARCHIVE_EVENT,
        event_store_class,
    )

    assert event_store_class.get_queue_events()


@pytest.mark.parametrize("attr", attributes)
@pytest.mark.unit
@pytest.mark.forked
def test_client_receives_change_event(
    b5dc_manager: Any, event_store_class: Any, attr: Any
) -> None:
    """Verify change events are configured."""
    b5dc_manager.subscribe_event(
        attr,
        tango.EventType.CHANGE_EVENT,
        event_store_class,
    )

    assert event_store_class.get_queue_events()
