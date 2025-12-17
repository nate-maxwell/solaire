"""
Sometimes various widgets within the editor need to be updated of certain
events, or wish to broadcast state changes to any widget that cares.

PySide's signals are great when widgets have a direct reference to each
other, but this can create a very messy web of dependencies.

Herein is a basic observer pattern event broker for widgets to broadcast
state changes or values to subscribers.
"""


import sys
import types
from collections import defaultdict
from dataclasses import dataclass
from typing import Any
from typing import Callable


@dataclass
class Event(object):
    """What gets emitted by a broadcaster, or source, to the broker.
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
"""An event for when the broker itself is affected, rather than event info
being forwarded to subscribers.
"""

END_POINT = Callable[[Event], None]
"""The end point that event info is forwarded to. These are the actions that
will execute when an event is triggered.
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
    """Primary event coordinator."""

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
        """Register a source in the broker.
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
        self.register_source(source_name)
        source_dict: _source_dict_type = _SOURCES[source_name]

        # We do not value check here as _SOURCE_DICT is default-dict[list].
        subscribers: list[END_POINT] = source_dict[event_name]
        if subscriber not in subscribers:
            subscribers.append(subscriber)
        self.emit(self._broker_update)

    @staticmethod
    def emit(event: Event) -> None:
        source_name = event.source
        if source_name not in _SOURCES:
            raise ValueError(
                f'{source_name} is not currently registered in the broker!'
            )

        source = _SOURCES[event.source]
        # We do not value check here as _SOURCE_DICT is default-dict[list].
        subscribers: list[END_POINT] = source[event.name]
        for i in subscribers:
            i(event)


# This is here to protect the _SOURCES dict, creating a "protective closure".
custom_module = EventBroker(sys.modules[__name__].__name__)
sys.modules[__name__] = custom_module

# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Required for static type checkers to accept these names as members of
# this module.
# -----------------------------------------------------------------------------


def register_source(source_name: str) -> None:
    """Adds a topic by the given name to the broker."""


def register_subscriber(
        source_name: str,
        event_name: str,
        subscriber: END_POINT
) -> None:
    """Registers an end point, or subscriber, to the task name of the given
    topic.
    All triggered event's info will be forwarded to each subscriber.
    Subscribers are callables that take and execute on work unit data.
    """


def emit(event: Event) -> None:
    """Sends the WorkUnit to the extrapolated subscribers.

    The logic for routing the unit of work may expand over time, sending units
    on more complex topics based on information extracted from the unit fields.
    """
