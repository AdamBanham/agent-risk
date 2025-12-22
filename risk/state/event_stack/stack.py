"""
This module describes the event stack data structure used
to manage simulation events.
"""

from typing import Union, Dict, List
from uuid import uuid5, UUID

EVENT_NAMESPACE = UUID("83565e68-4400-496e-a9fe-932f80bcf803")
LEVEL_NAMESPACE = UUID("38c0f2c1-6ef3-4d4b-8845-7d2a378b3a88")
STACK_NAMESPACE = UUID("7557cad3-83c5-429a-ba3c-20cae6623b45")


class EventContext:
    """
    A base class for holding an immutable context dictionary.
    """

    def __init__(self, context: Dict[str, object] = None):
        if context is not None:
            for key, val in context.items():
                setattr(self, key, val)
        self._lock = 1

    def _make_dict(self) -> Dict[str, object]:
        return dict(
            (attr, getattr(self, attr)) for attr in self.__dict__ if attr != "_lock"
        )

    def __getitem__(self, key):
        return getattr(self, key)

    def __setattr__(self, name, value):
        if hasattr(self, "_lock"):
            raise TypeError("Contexts are immutable!")
        else:
            super().__setattr__(name, value)

    def __repr__(self):
        return repr(self._make_dict())


class Event:
    """
    A base class for events in the simulation.
    """

    def __init__(self, name: str, context: Dict[str, object] = None):
        self.name = name
        self.context = EventContext(context) if context is not None else EventContext()
        self.id = uuid5(EVENT_NAMESPACE, str(self))
        self._lock = 1

    def __str__(self) -> str:
        return f"Event: {self.name}, Context: {self.context}"

    def __repr__(self) -> str:
        return f"Event({repr(self.name)},{repr(self.context)})"

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, value):
        if isinstance(value, Event):
            return self.id == value.id
        return False

    def __setattr__(self, name, value):
        if hasattr(self, "_lock"):
            raise TypeError("Events are immutable!")
        else:
            super().__setattr__(name, value)


class Level:
    """
    A level in the event stack, representing a context or scope.
    """

    def __init__(self, name: str):
        self.name = name
        self.id = uuid5(LEVEL_NAMESPACE, str(self))
        self._lock = 1

    def __str__(self) -> str:
        return f"Level: {self.name}"

    def __repr__(self) -> str:
        return f"Level({repr(self.name)})"

    def __setattr__(self, name, value):
        if hasattr(self, "_lock"):
            raise TypeError("Levels are immutable!")
        super().__setattr__(name, value)

    def __eq__(self, value):
        if isinstance(value, Level):
            return self.id == value.id
        return False

    def __hash__(self):
        return hash(self.id)


class EventStackInfo:
    current_level: Union[Level, None] = None
    depth: int = 0

    def __init__(self):
        self.current_level = None
        self.depth = 0


class EventStack:
    """
    A stack to manage simulation events.
    """

    def __init__(self, name: str, layers: List[Union[Event, Level]] = None):
        self.stack = []
        self.name = name
        self.id = uuid5(STACK_NAMESPACE, name)
        self._info = EventStackInfo()
        if layers:
            for layer in layers:
                self.push(layer)
        self._lock = 1

    def push(self, element: Union[Level, Event]) -> None:
        """
        Push an event onto the stack.
        """
        if isinstance(element, Level):
            self._info.depth += 1
            self._info.current_level = element
        self.stack.append(element)

    def pop(self) -> Union[None, Level, Event]:
        """
        Pop an event off the stack.
        """
        if self.is_empty:
            return None
        if isinstance(self.peek(), Level):
            self._info.depth -= 1
            if self.depth > 0:
                self._info.current_level = self._find_next_level(self.stack[:-1])
            else:
                self._info.current_level = None

        return self.stack.pop()

    def peek(self) -> Union[None, Level, Event]:
        """
        Peek at the top event on the stack without removing it.
        """
        if self.is_empty:
            return None
        return self.stack[-1]

    def _find_next_level(self, stack) -> Union[None, Level]:
        """
        Walks the stack to find the closest level.
        """
        for item in reversed(stack):
            if isinstance(item, Level):
                return item
        return None

    @property
    def current_level(self) -> Union[None, Level]:
        """
        Gets the current level from the top of the stack.
        """
        return self._info.current_level

    @property
    def depth(self) -> int:
        """
        Gets the depth of the current stack (i.e. how many levels deep is
        the current top event).
        """
        return self._info.depth

    @property
    def is_empty(self) -> bool:
        """
        Check if the stack is empty.
        """
        return len(self.stack) == 0

    @property
    def size(self) -> int:
        """
        Get the current size of the stack.
        """
        return len(self.stack)

    def substack(self, layers: int) -> "EventStack":
        """
        From the bottom up create a substack of the current stack with up
        to `layers` in it.
        """

        return EventStack(self.name + f"-sub-{layers}", layers=self.stack[:layers])

    def topstack(self, layers: int):
        """
        From the top to bottom, create a substack fo the current stack with
        up to `layers` in it.
        """
        return EventStack(
            self.name + f"-sub-{layers}", layers=self.stack[-1 * layers :]
        )

    def clear(self):
        """
        Clears the stack.
        """
        self.stack.clear()

    def __len__(self):
        return self.size

    def __setattr__(self, name, value):
        if hasattr(self, "_lock"):
            raise TypeError("Stacks are immutable, outside of modifying the stack")
        super().__setattr__(name, value)

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, value):
        if isinstance(value, EventStack):
            return self.id == value.id
        return False

    def __str__(self):
        ret = "Stack:-\n"
        depth = self.depth
        for el in reversed(self.stack):
            text = str(el)
            ret += "  ".join(["" for _ in range(depth)]) + text + "\n"
            if isinstance(el, Level):
                depth -= 1
        return ret
