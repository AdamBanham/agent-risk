"""
This module contains the logic for Data Petri Net (DPN)
Random Agent Implementation.
"""

from ...agent import BaseAgent
from risk.state.plan import Goal
from risk.utils.logging import info

from .placement import RandomPlacement


class DPNRandomAgent(BaseAgent):
    """
    A simple DPN agent that makes random decisions during placement, attack,
    and defense phases.
    """

    def __init__(self, player_id: int, attack_probability: float = 0.5):
        super().__init__(
            player_id, "DPN-Random-Agent-{}".format(player_id), attack_probability
        )

    def decide_placement(self, game_state, goal):
        info("dpn-agent-random deciding placement")
        planner = RandomPlacement(self.player_id, game_state.placements_left)
        plan = planner.construct_plan(game_state)   

        events = []
        while not plan.is_done():
            step = plan.pop_step()
            events.extend(step.execute(game_state))
        return events

    def decide_attack(self, game_state, goal):
        info("dpn-agent-random deciding attack")
        return super().decide_attack(game_state, goal)

    def decide_movement(self, game_state, goal):
        info("dpn-agent-random deciding movement")
        return super().decide_movement(game_state, goal)
