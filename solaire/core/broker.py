"""
Sometimes various widgets within the editor need to be updated of certain
events, or wish to broadcast state changes to any widget that cares.

PySide's signals are great when widgets have a direct reference to each
other, but this can create a very messy web of dependencies.

Herein is a basic observer pattern event broker for widgets to broadcast
state changes or values to subscribers.

This broker supports both synchronous and asynchronous subscribers,
automatically detecting the subscriber type and handling accordingly.

Example usage:

>>> from solaire.core import broker

    # Mix sync and async subscribers freely
>>> def sync_handler(event):
>>>     print(f'Immediate: {event.data}')

>>> async def async_handler(event):
>>>     await asyncio.sleep(0.1)
>>>     print(f'Async: {event.data}')

>>> broker.register_subscriber('editor', 'file_open', sync_handler)
>>> broker.register_subscriber('editor', 'file_open', async_handler)

    # Fire-and-forget
>>> broker.emit(Event('editor', 'file_open', '/file.py'))

    # Or await all
>>> await broker.emit_async(Event('editor', 'file_open', '/file.py'))
"""


import sys
import types
import asyncio
import inspect
from collections import defaultdict
from dataclasses import dataclass
from typing import Any
from typing import Callable
from typing import Awaitable
from typing import Union


@dataclass
class Event(object):
    """
    What gets emitted by a broadcaster, or source, to the broker.
    This is what a subscriber will receive.
    """
    source: str
    """The tool or widget emitting the event."""
    name: str
    """The event name - file_open, refresh, etc."""
    data: Any = None
    """The payload data - file path, timestamp, etc."""


DUMMY_EVENT = Event('', '')
"""
A blank event for functions that do not require payload data but would like to
subscribe to an event.

This can be used as the default arg so that the same function can be called
independently of event triggering.
"""


BROKER_SOURCE = 'BROKER'
"""A source for broker observability and maintenance."""

broker_update_event = Event('BROKER', 'UPDATE')
"""
An event for when the broker itself is affected, rather than event info being
forwarded to subscribers.
"""

END_POINT = Union[Callable[[Event], None], Callable[[Event], Awaitable[None]]]
"""
The end point that event info is forwarded to. These are the actions that
will execute when an event is triggered. Can be sync or async.
"""

_source_dict_type = dict[str, list[END_POINT]]

_SOURCES: dict[str, _source_dict_type] = {
    'BROKER': {
        'UPDATE': []
    }
}
"""The broker's record of each topic name to event_name:subscriber records.

This is kept outside of the replaced module class to create a protected
closure around the event topic:subscriber structure.
"""
# Topics could evolve to a string channel name and a list of follow-up
# channels for the key. The message would run through the list and,
# after each callable, refer back to the _topics dict to see the list
# of further follow-up callables before being sent to the consumer.
# i.e. more complex logic based on future needs.
# -----------------------------------------------------------------------------
# For now, it is a simple
# {
#   source_name: {
#       event_name: [subscriber_funcs]
#   }
# }
# dictionary structure, with topics being the first key, and event names being
# the keys within a given topic. Event names hold lists of callable subscriber
# objects that the event is forwarded to.


class EventBroker(types.ModuleType):
    """
    Primary event coordinator.

    Supports both synchronous and asynchronous subscribers.
    Use emit() for fire-and-forget behavior.
    Use emit_async() to await all subscribers.
    """

    Event = Event  # Closure to keep Event type valid at runtime.
    DUMMY_EVENT = DUMMY_EVENT  # Closure to keep valid at runtime.

    def __init__(self, name: str) -> None:
        super().__init__(name)
        self._broker_update = broker_update_event
        self._setup_topics()

    def _setup_topics(self) -> None:
        """Setup default topics. May grow over time."""
        self.register_source(BROKER_SOURCE)

    def register_source(self, source_name: str) -> None:
        """
        Register a source in the broker.
        Only adds entries if they do not exist.
        """
        if source_name not in _SOURCES:
            _SOURCES[source_name] = defaultdict(list)
            self.emit(self._broker_update)

    def register_subscriber(
            self,
            source_name: str,
            event_name: str,
            subscriber: END_POINT
    ) -> None:
        """
        Register a subscriber (sync or async) to an event.

        The subscriber type is automatically detected. Async subscribers
        are identified via inspect.iscoroutinefunction().

        Args:
            source_name: The event source to subscribe to
            event_name: The specific event name to subscribe to
            subscriber: A callable that accepts an Event (sync or async)
        """
        self.register_source(source_name)
        source_dict: _source_dict_type = _SOURCES[source_name]

        # We do not value check here as _SOURCE_DICT is default-dict[list].
        subscribers: list[END_POINT] = source_dict[event_name]
        if subscriber not in subscribers:
            subscribers.append(subscriber)
        self.emit(self._broker_update)

    @staticmethod
    def emit(event: Event) -> None:
        """
        Synchronously emit an event to all subscribers.

        Synchronous subscribers are called immediately.
        Asynchronous subscribers are scheduled as background tasks.

        This method does not wait for async subscribers to complete.
        Use emit_async() if you need to await all subscribers.

        Args:
            event: The event to emit
        Raises:
            ValueError: If the event source is not registered
        """
        source_name = event.source
        if source_name not in _SOURCES:
            raise ValueError(
                f'{source_name} is not currently registered in the broker!'
            )

        source = _SOURCES[event.source]
        # We do not value check here as _SOURCE_DICT is default-dict[list].
        subscribers: list[END_POINT] = source[event.name]

        for subscriber in subscribers:
            if inspect.iscoroutinefunction(subscriber):
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.create_task(subscriber(event))
                    else:
                        loop.run_until_complete(subscriber(event))
                except RuntimeError:
                    asyncio.run(subscriber(event))
            else:
                subscriber(event)

    @staticmethod
    async def emit_async(event: Event) -> None:
        """
        Asynchronously emit an event and await all subscribers.

        Both synchronous and asynchronous subscribers are awaited.
        Synchronous subscribers are wrapped to run in the executor.

        This is useful when you need to ensure all event processing
        is complete before continuing.

        Args:
            event: The event to emit
        Raises:
            ValueError: If the event source is not registered
        """
        source_name = event.source
        if source_name not in _SOURCES:
            raise ValueError(
                f'{source_name} is not currently registered in the broker!'
            )

        source = _SOURCES[event.source]
        subscribers: list[END_POINT] = source[event.name]

        tasks = []
        for subscriber in subscribers:
            if inspect.iscoroutinefunction(subscriber):
                tasks.append(subscriber(event))
            else:
                loop = asyncio.get_event_loop()
                tasks.append(loop.run_in_executor(None, subscriber, event))

        if tasks:
            await asyncio.gather(*tasks)


# This is here to protect the _SOURCES dict, creating a "protective closure".
custom_module = EventBroker(sys.modules[__name__].__name__)
sys.modules[__name__] = custom_module

# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Required for static type checkers to accept these names as members of
# this module.
# -----------------------------------------------------------------------------


def register_source(source_name: str) -> None:
    pass


def register_subscriber(
        source_name: str,
        event_name: str,
        subscriber: END_POINT
) -> None:
    pass


def emit(event: Event) -> None:
    pass


async def emit_async(event: Event) -> None:
    pass
