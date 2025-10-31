from risk.agents.plans import Planner
from risk.state.game_state import GameState
from risk.state.plan import Plan

from ...plans import MovementPlan

class RandomMovements(Planner):
    """
    A planner that creates random movement plans.
    """

    def __call__(self, *args, **kwds):
        return super().__call__(*args, **kwds)

    def construct_plan(self, state: GameState) -> Plan:
        # Implementation of random movement plan construction
        return MovementPlan(1)
