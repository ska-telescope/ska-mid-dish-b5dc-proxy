"""General utils for test devices."""
import queue
from typing import Any, List

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

    def wait_for_n_events(self, event_count: int, timeout: int = 3):
        """Wait for N number of events.

        Wait `timeout` seconds for each fetch.

        :param event_count: The number of events to wait for
        :type command_id: int
        :param timeout: the get timeout, defaults to 3
        :type timeout: int, optional
        :raises RuntimeError: If none are found
        :return: The result of the long running command
        :rtype: str
        """
        events = []
        try:
            while len(events) != event_count:
                event = self._queue.get(timeout=timeout)
                events.append(event)
            return events
        except queue.Empty as err:
            raise RuntimeError(
                f"Did not get {event_count} events, ",
                f"got {len(events)} events",
            ) from err

    def wait_for_progress_update(self, progress_message: str, timeout: int = 5) -> List[Any]:
        """Wait for a long running command progress update.

        Wait `timeout` seconds for each fetch.

        :param progress_message: The progress message to wait for
        :type progress_message: str
        :param timeout: the get timeout, defaults to 3
        :type timeout: int, optional
        :raises RuntimeError: If none are found
        :return: The result of the long running command
        :rtype: str
        """
        events = []
        try:
            while True:
                event = self._queue.get(timeout=timeout)
                events.append(event)
                if not event.attr_value:
                    continue
                if not isinstance(event.attr_value.value, tuple):
                    continue
                progress_update = str(event.attr_value.value)
                if (
                    progress_message in progress_update
                    and event.attr_value.name == "longrunningcommandprogress"
                ):
                    return events
        except queue.Empty as err:
            event_info = [(event.attr_value.name, event.attr_value.value) for event in events]
            raise RuntimeError(
                f"Never got a progress update with [{progress_message}],",
                f" but got [{event_info}]",
            ) from err

    def wait_for_command_result(self, command_id: str, command_result: Any, timeout: int = 3):
        """Wait for a long running command result.

        Wait `timeout` seconds for each fetch.

        :param command_id: The long running command ID
        :type command_id: str
        :param timeout: the get timeout, defaults to 3
        :type timeout: int, optional
        :raises RuntimeError: If none are found
        :return: The result of the long running command
        :rtype: str
        """
        try:
            while True:
                event = self._queue.get(timeout=timeout)
                if not event.attr_value:
                    continue
                if not isinstance(event.attr_value.value, tuple):
                    continue
                if len(event.attr_value.value) != 2:
                    continue
                (lrc_id, lrc_result) = event.attr_value.value
                if command_id == lrc_id and command_result == lrc_result:
                    return True
        except queue.Empty as err:
            raise RuntimeError(f"Never got an LRC result from command [{command_id}]") from err

    def wait_for_command_id(self, command_id: str, timeout: int = 3):
        """Wait for a long running command to complete.

        Wait `timeout` seconds for each fetch.

        :param command_id: The long running command ID
        :type command_id: str
        :param timeout: the get timeout, defaults to 3
        :type timeout: int, optional
        :raises RuntimeError: If none are found
        :return: The result of the long running command
        :rtype: str
        """
        events = []
        try:
            while True:
                event = self._queue.get(timeout=timeout)
                events.append(event)
                if not event.attr_value:
                    continue
                if not isinstance(event.attr_value.value, tuple):
                    continue
                if len(event.attr_value.value) != 2:
                    continue
                (lrc_id, _) = event.attr_value.value
                if command_id == lrc_id and event.attr_value.name == "longrunningcommandresult":
                    return events
        except queue.Empty as err:
            event_info = [(event.attr_value.name, event.attr_value.value) for event in events]
            raise RuntimeError(
                f"Never got an LRC result from command [{command_id}],",
                f" but got [{event_info}]",
            ) from err
