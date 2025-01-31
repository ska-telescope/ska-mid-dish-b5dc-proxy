"""General utils for test devices."""
import queue
from typing import Any

import tango


class EventStore:
    """Store events with useful functionality."""

    def __init__(self) -> None:
        """Init Store."""
        self._queue: Any = queue.Queue()

    def push_event(self, event: tango.EventData) -> None:
        """Store the event.

        :param event: Tango event
        :type event: tango.EventData
        """
        self._queue.put(event)

    def clear_queue(self) -> None:
        """Clear out the queue."""
        while not self._queue.empty():
            self._queue.get()

    def get_queue_events(self, timeout: int = 3) -> Any:
        """Get all the events out of the queue."""
        items = []
        try:
            while True:
                items.append(self._queue.get(timeout=timeout))
        except queue.Empty:
            return items

    def get_queue_values(self, timeout: int = 3) -> Any:
        """Get the values from the queue."""
        items = []
        try:
            while True:
                event = self._queue.get(timeout=timeout)
                items.append((event.attr_value.name, event.attr_value.value))
        except queue.Empty:
            return items
