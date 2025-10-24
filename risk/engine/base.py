"""
This module contains the base class for what an engine is
within the architecture of the simulation framework.

Engines are responsible for processing events on the stack,
engines can push new events onto the stack in their processing,
they can also create side effects to be applied to the current
world state.

----
Examples
----
.. code-block:: python


"""

from risk.state.event_stack import Event, Level
from risk.state import GameState

from typing import List, Union


class Engine:
    """
    The behaviour contract of an engine within the simulation framework.
    Ideally, engines are stateless and can be instantiated multiple times
    without side effects. Their responses to elements on the stack should
    be deterministic based on the current world state and the parameters of
    the given elements.

    .. attributes ::
       - id:
            `str`
            A unique identifier for this engine.

    .. required-methods ::
        - processable:
            `processable(element: Union[Event, Level]) -> bool`


        - process:
            `process(state: GameState, element: Union[Event, Level]) -> None`

    .. optional-methods ::

    """

    allowed_elements: List[Union[Event, Level]] = []

    def __init__(self, engine_id: str):
        self.id = engine_id

    def processable(self, element: Union[Event, Level]) -> bool:
        """
        Determine if this engine can process the given event or level.

        :param element:
          `Event | Level`
          The event or level to check.

        :returns:
            Whether this engine can process the given event or level.
        """
        return isinstance(element, tuple(self.allowed_elements))

    def process(self, state: GameState, element: Union[Event, Level]) -> None:
        """
        Process the given event or level.

        :param state:
            `GameState`

            The current game state to process against.

        :param element:
          `Event | Level`

          The event or level to process.
        """
        pass


class EngineProcessingError(Event):
    """An error event indicating that an engine failed to process an element."""

    def __init__(self, engine_id: str, element: Union[Event, Level], message: str):
        super().__init__(
            (
                f"Engine '{engine_id}' failed to process element:"
                f" {element}. Reason: {message}"
            )
        )


class EngineProccesableError(Event):
    """An error event indicating that no engine could check whether to
    an element is processable."""

    def __init__(self, element: Union[Event, Level]):
        super().__init__(
            f"No engine could check whether element: {element} is processable."
        )


class DebugEngine(Engine):
    """A simple engine that logs processing actions for debugging purposes."""

    def __init__(self):
        super().__init__("debug_engine")

    def processable(self, element: Union[Event, Level]) -> bool:
        """This debug engine can process all events and levels."""
        if isinstance(element, (EngineProcessingError, EngineProccesableError)):
            return True
        return False

    def process(self, state: GameState, element: Union[Event]) -> None:
        """Log the processing of the event or level."""
        print(f"[DEBUG] Engine crashed out : {element.name}")

        return None


from ..state.event_stack import SideEffectEvent


class SideEffectEngine(Engine):
    """An engine that applies side effects to the game state."""

    def __init__(self):
        super().__init__("side_effect_engine")

    def processable(self, element: Union[Event, Level]) -> bool:
        """This side effect engine can process all events and levels."""
        return isinstance(element, SideEffectEvent)

    def process(self, state: GameState, element: SideEffectEvent) -> None:
        """Apply side effects to the game state."""
        events = element.apply(state)
        return events


from ..state.event_stack import EventTape


class RecordStackEngine(Engine):
    """An engine that records the event stack state for analysis."""

    def __init__(self, pairs=None):
        super().__init__("record_stack_engine")
        self.stack = EventTape(pairs=pairs)

    def processable(self, element: Union[Event, Level]) -> bool:
        """This record stack engine can process all events and levels."""
        return True

    def process(self, state: GameState, element: Union[Event, Level]) -> None:
        """Record the event stack state."""
        self.stack.push(element)

        return None
