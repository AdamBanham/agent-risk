"""
A holder module for running the event stack and engine
processing loop.
"""

from ..engine.base import Engine, EngineProccesableError, EngineProcessingError
from ..state import GameState
from ..state.event_stack import EventStack

from copy import deepcopy

class SimulationController:
    """
    The controller responsible for managing the event stack
    and engine processing loop.
    """

    def __init__(self, 
        game_state: GameState, 
        engines: list[Engine]):
        self.game_state = game_state
        self.engines = engines
        self.event_stack = EventStack("event-stack")
        self._last = None

    def step(self) -> bool:
        """
        Process a single element from the event stack.

        :returns:
            Whether an element was processed.
        """
        if self.event_stack.is_empty:
            return False

        element = self.event_stack.pop()
        print(f"Processing element: {element}")
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
                print(f"Engine '{engine.id}' processing element: {element}")
                try :
                    events = engine.process(self.game_state, element)
                except Exception as e:
                    error_event = EngineProcessingError(
                        engine.id, element, str(e)
                    )
                    self.event_stack.push(error_event)
                    continue
                if events:
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
    

from .base import DebugEngine, SideEffectEngine
from .turns import (
    RiskGameEngine,
    RiskTurnEngine,
    RiskPlacementEngine,
    RiskAttackEngine,
    RiskMovementEngine
)

RISK_ENGINES = [
    DebugEngine(),
    SideEffectEngine(),
    RiskGameEngine(),
    RiskTurnEngine(),
    RiskPlacementEngine(),
    RiskAttackEngine(),
    RiskMovementEngine()
]

class RiskSimulationController(SimulationController):
    """
    The controller responsible for managing the event stack
    and engine processing loop for the Risk simulation.
    """

    def __init__(self, 
        game_state: GameState):
        super().__init__(game_state, RISK_ENGINES)