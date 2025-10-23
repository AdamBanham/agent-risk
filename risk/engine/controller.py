"""
A holder module for running the event stack and engine
processing loop.
"""

from typing import Union
from ..engine.base import Engine, EngineProccesableError, EngineProcessingError
from .base import DebugEngine, SideEffectEngine
from ..state import GameState
from ..state.event_stack import Event, Level
from ..state.event_stack import EventStack

from copy import deepcopy
import traceback

class SimulationController:
    """
    The controller responsible for managing the event stack
    and engine processing loop.
    """

    def __init__(self, 
        game_state: GameState, 
        engines: list[Engine],
        debug: bool = False):
        self.game_state = game_state
        self.engines = engines + [
            DebugEngine(),
            SideEffectEngine(),
            PauseEngine(self)
        ]
        self.event_stack = EventStack("event-stack")
        self._last = None
        self.debug = debug
        self._processing = True

    def _print_debug(self, message: str) -> None:
        if self.debug:
            print(f"[DEBUG] {message}")

    def step(self) -> bool:
        """
        Process a single element from the event stack.

        :returns:
            Whether an element was processed.
        """
        if self.event_stack.is_empty:
            return False
        
        if not self._processing:
            return True

        element = self.event_stack.pop()
        self._print_debug(f"Processing element: {element}")
        self._last = element
        for engine in self.engines:
            try :
                processable  = engine.processable(element)
            except Exception as e:
                error_event = EngineProccesableError(
                    engine.id, element, str(e)
                )
                self.event_stack.push(error_event)
                continue
            if engine.processable(element):
                self._print_debug(f"Engine '{engine.id}' processing element: {element}")
                try :
                    events = engine.process(self.game_state, element)
                except Exception as e:
                    error_event = EngineProcessingError(
                        engine.id, element, traceback.format_exc()
                    )
                    self.event_stack.push(error_event)
                    continue
                if events:
                    try : 
                        iter(events)
                    except Exception as e:
                        self.event_stack.push(
                            EngineProcessingError(
                                engine.id, element, 
                                "Engine returned non-iterable events."
                            )
                        )
                        continue
                    for event in events:
                        self.event_stack.push(event)

        return True

    def run(self):
        """
        Run the simulation processing loop until the event stack is empty.
        """
        while not self.event_stack.is_empty():
            processed = self.step()
            if not processed:
                break

    def mirror(self):
        """
        Create mirror of the current state of the controller.
        This is the intended way to allow for playout simulations from
        the current game state for agents.

        :returns:
            `SimulationController`
            A deep copy of the current simulation controller.
        """

        return SimulationController(
            game_state=deepcopy(self.game_state),
            engines=deepcopy(self.engines)
        )
    
    def add_engine(self, engine: Engine) -> None:
        """
        Add an engine to the controller's engine list.

        :param engine:
            `Engine`
            The engine to add.
        """

        self.engines.append(engine)

    def pause_processing(self) -> None:
        """
        Pause the processing of the event stack.
        """
        self._processing = False

    def resume_processing(self) -> None:
        """
        Resume the processing of the event stack.
        """
        self._processing = True
    

from ..state.event_stack import PauseProcessingEvent
import threading
    
class PauseEngine(Engine):
    """
    An engine that pauses processing when a specific event is encountered.
    """

    allowed_elements = [
        PauseProcessingEvent
    ]

    def __init__(self, controller: SimulationController):
        super().__init__("pause_engine")
        self.controller = controller
        self._thread = None
        self.delay = 0

    
    @staticmethod
    def _launch_pause(self: "PauseEngine", controller: SimulationController) -> None:
        """Launch a pause in processing for the specified duration."""
        import time
        start = time.time()
        controller.pause_processing()
        while time.time() - start < self.delay:
            time.sleep(0.1)
            print(f"[SYSTEM] Pausing for {self.delay - (time.time() - start):.2f} seconds...", end="\r")
        controller.resume_processing()
        self._thread = None
        print("\033[2K\033[1G", end="", flush=True)

    def process(self, state: GameState, element: Union[Event, Level]) -> None:
        """Pause processing when the specified event is encountered."""
        if isinstance(element, PauseProcessingEvent):
            delay = element.context.delay

            if self._thread:
                self.delay += delay
            else:
                self.delay = delay
                self._thread = threading.Thread(
                    target=PauseEngine._launch_pause,
                    args=(self, self.controller)
                )
                self._thread.start()

        return super().process(state, element)
            