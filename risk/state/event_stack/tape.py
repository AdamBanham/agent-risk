"""
This modules contains the abstraction for an event tape. 
An event tape differs from an event stack, as a tape is 
meant to be historical recording of a simulation.
"""

from .stack import EventStack, Event, Level
from typing import List, Tuple, Type, Dict, Set, Union
from dataclasses import dataclass, field

@dataclass
class EventTapeInfo:
    current_level:Union[Level, None]=None
    depth:int=0
    starts:Set[Union[Type[Event], Type[Level]]]=field(default_factory=set)
    ends:Set[Type[Event]]=field(default_factory=set)
    seen_parents:List[int]=field(default_factory=list)
    last_seen:int=-1

    def _cal_depth(self, event: Union[Event,Level]) -> int:
        """
        Calculate depth based on hierarchical pairs.
        """
        if type(event) in self.starts:
            # push a new depth into seen parents
            if self.last_seen >= 0:
                self.seen_parents.append(
                    self.seen_parents[self.last_seen] + 1
                )
                self.last_seen += 1
            else:
                self.seen_parents.append(1)
                self.last_seen = 0
            return self.seen_parents[self.last_seen] - 1
        
        elif type(event) in self.ends:
            # shift back the depth
            self.last_seen -= 1

        # if last seen is valid, return its depth
        if self.last_seen >= 0:
            return self.seen_parents[self.last_seen]
        # otherwise
        return 0

class EventTape(EventStack):
    """
    Event tape with hierarchical depth management based on paired event classes.
    
    This class represents an event tape, which is a historical recording of 
    events for a simulation. Unlike EventStack, it manages hierarchical depth 
    based on paired event classes rather than linear depth progression.
    """

    def __init__(self, pairs: List[Tuple[Union[Type[Event], Type[Level]], Type[Event]]] = None):
        """
        Initialize EventTape with hierarchical pairs.
        
        :param pairs: Pairs that define hierarchy boundaries 
                     (start_class, end_class) where start_class can be Event 
                     or Level, and end_class must be Event - elements between 
                     these pairs will have increased hierarchical depth
        :returns: None
        """
        super().__init__(name="EventTape")
        del self._lock
        
        # Initialize all attributes before setting _lock
        self._pairs = list() if pairs is None else pairs
        if len(self._pairs) > 0:
            self._starts = {pair[0] for pair in self._pairs}
            self._ends = {pair[1] for pair in self._pairs}
        else:
            self._starts = set()
            self._ends = set()
        
        self._info = EventTapeInfo(
            0, None, self._starts, self._ends
        )

        # Set lock last
        self._lock = 1
        
    def push(self, element: Union[Level, Event]) -> None:
        """
        Push element with hierarchical depth calculation.
        
        :param element: Event or Level to push onto tape
        :returns: None
        """
        self._info.depth = self._info._cal_depth(element)
        if isinstance(element, Level):
            self._info.current_level = element
        self.stack.append(element)

    def pop(self):
        """
        Event tapes are immutable - popping is not allowed.
        """
        pass

    def __str__(self) -> str:
           
        ret = "EventTape:-\n"
        
        # Reset state for display calculation
        info = EventTapeInfo(
            0, None, self._starts, self._ends, [], -1
        )
        
        # Calculate depths and build display in reverse order
        element_lines = []
        for element in self.stack:
            depth = info._cal_depth(element)
            indent = "  " * depth
            element_lines.append(f"{indent}{element}")
        
        # Display in reverse order (most recent first)
        ret += "\n".join(reversed(element_lines))
        ret += "\n"
        
        return ret