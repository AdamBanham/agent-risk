

from risk.engine.controller import SimulationController
from risk.state.event_stack.events import (
    PlayingEvent, AgentTurnEndEvent, 
    AttackPhase, AttackPhaseEndEvent, 
    MovementPhase, MovementPhaseEndEvent, 
    PlacementPhase, PlacementPhaseEndEvent,
    GameEvent
) 
from risk.state.game_state import GameState
from .base import RecordStackEngine
from .turns import (
    RiskGameEngine,
    RiskTurnEngine,
    RiskPlacementEngine,
    RiskAttackEngine,
    RiskMovementEngine
)

RISK_ENGINES = [
    RiskGameEngine(),
    RiskTurnEngine(),
    RiskPlacementEngine(),
    RiskAttackEngine(),
    RiskMovementEngine()
]

class RiskRecordEngine(RecordStackEngine):
    """
    An engine that records specific event pairs for undo/redo functionality.
    """

    def __init__(self):
        super().__init__(
            pairs=[
                (PlayingEvent, AgentTurnEndEvent),
                (PlacementPhase, PlacementPhaseEndEvent),
                (AttackPhase, AttackPhaseEndEvent),
                (MovementPhase, MovementPhaseEndEvent)
            ]
        )

class RiskSimulationController(SimulationController):
    """
    The controller responsible for managing the event stack
    and engine processing loop for the Risk simulation.
    """

    def __init__(self, 
        game_state: GameState):
        super().__init__(game_state, RISK_ENGINES)
        self.tape = RiskRecordEngine()
        self.add_engine(self.tape)
        self.event_stack.push(
            GameEvent()
        )
