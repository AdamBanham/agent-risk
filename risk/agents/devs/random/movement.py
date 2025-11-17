from ...plans import Planner, MovementPlan, RouteMovementStep, MovementStep
from risk.state import GameState
from risk.utils.movement import find_movement_sequence, Movement
from risk.utils.movement import find_safe_frontline_territories
from risk.utils.movement import find_connected_frontline_territories

from typing import Set, Dict
import random

class RandomMovement(Planner):
    """
    A planner that generates random movement plans.
    """

    def __init__(self, player_id: int, max_moves: int):
        super().__init__()
        self.player_id = player_id
        self.max_moves = max_moves

    def construct_plan(self, game_state: GameState) -> MovementPlan:
        # Implementation of random movement plan generation
        safes, frontlines = find_safe_frontline_territories(
            game_state=game_state, player_id=self.player_id
        )
        safes_ids = set(t.id for t in safes)
        frontlines_ids = set(t.id for t in frontlines)
        connections = dict(
            (
                s.id,
                set(
                    o.id
                    for o in find_connected_frontline_territories(
                        s, frontlines, safes + frontlines
                    )
                ),
            )
            for s in safes
        )

        plan = MovementPlan(self.max_moves)

        return plan


if __name__ == "__main__":
    pass
