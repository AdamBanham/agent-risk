"""
This module contains the logic for Data Petri Net (DPN)
Random Agent Implementation.
"""

from ...agent import BaseAgent
from risk.utils.logging import info

from .placement import RandomPlacement
from .attack import RandomAttacks
from .movement import RandomMovement


class DPNRandomAgent(BaseAgent):
    """
    A simple DPN agent that makes random decisions during placement, attack,
    and defense phases.
    """

    def __init__(self, player_id: int, attack_probability: float = 0.5):
        super().__init__(
            player_id, "dpn-agent-random-{}".format(player_id), attack_probability
        )

    def decide_placement(self, game_state, goal):
        info(f"{self.name} deciding placement")
        planner = RandomPlacement(self.player_id, game_state.placements_left)
        plan = planner.construct_plan(game_state)

        events = []
        while not plan.is_done():
            step = plan.pop_step()
            events.extend(step.execute(game_state))
        return events

    def decide_attack(self, game_state, goal):
        info(f"{self.name} deciding attack")
        planner = RandomAttacks(
            self.player_id, 10, self.attack_probability
        )
        plan = planner.construct_plan(game_state)

        events = []
        while not plan.is_done():
            step = plan.pop_step()
            events.extend(step.execute(game_state))
        return events

    def decide_movement(self, game_state, goal):
        info(f"{self.name} deciding movement")
        planner = RandomMovement(
            self.player_id, 1
        )
        plan = planner.construct_plan(game_state)

        events = []
        while not plan.is_done():
            step = plan.pop_step()
            events.extend(step.execute(game_state))
        return events
