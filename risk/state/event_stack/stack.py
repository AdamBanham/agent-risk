"""
This module describes the event stack data structure used
to manage simulation events.
"""

from typing import Union

class Event:
    """
    A base class for events in the simulation.
    """

    def __init__(self, name: str):
        self.name = name

    def __str__(self) -> str:
        return f"Event: {self.name}"

    def __repr__(self) -> str:
        return f"Event({repr(self.name)})"

class Level:
    """
    A level in the event stack, representing a context or scope.
    """

    def __init__(self, name: str):
        self.name = name

    def __str__(self) -> str:
        return f"Level: {self.name}"

    def __repr__(self) -> str:
        return f"Level({repr(self.name)})"

class EventStack:
    """
    A stack to manage simulation events.
    """

    def __init__(self):
        self.stack = []

    def push(self, event:Union[Level, Event]) -> None:
        """
        Push an event onto the stack.
        """
        self.stack.append(event)

    def pop(self) -> Union[None, Level, Event]:
        """
        Pop an event off the stack.
        """
        if self.is_empty():
            return None
        return self.stack.pop()

    def peek(self) -> Union[None, Level, Event]:
        """
        Peek at the top event on the stack without removing it.
        """
        if self.is_empty():
            return None
        return self.stack[-1]
    
    def current_level(self) -> Union[None, Level]:
        """
        Get the current level from the top of the stack.
        """
        for item in reversed(self.stack):
            if isinstance(item, Level):
                return item
        return None

    def is_empty(self) -> bool:
        """
        Check if the stack is empty.
        """
        return len(self.stack) == 0

    def size(self) -> int:
        """
        Get the current size of the stack.
        """
        return len(self.stack)