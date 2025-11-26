"""
This module contains the logic for Monte Carlo Tree Search (MCTS)
Defensive Agent Implementation.
"""

from risk.utils.logging import info
from ...agent import BaseAgent

from .placement import PlacementPlanner


class MCTSDefensiveAgent(BaseAgent):
    """
    A simple MCTS agent that makes defensive decisions during placement, attack,
    and defense phases.
    """

    def __init__(self, player_id: int, attack_probability: float = 0.5):
        super().__init__(
            player_id,
            "mcts-defensive-agent-{}".format(player_id),
            attack_probability=attack_probability,
        )

    def decide_placement(self, game_state, goal):
        info(f"{self.name} deciding placement...")

        planner = PlacementPlanner(
            self.player_id, game_state.placements_left
        )
        plan = planner.construct_plan(game_state)

        events = []
        while not plan.is_done():
            step = plan.pop_step()
            events.extend(step.execute(game_state))

        return events

    def decide_attack(self, game_state, goal):
        info(f"{self.name} deciding attacks...")
        return super().decide_attack(game_state, goal)

    def decide_movement(self, game_state, goal):
        info(f"{self.name} deciding movement...")
        return super().decide_movement(game_state, goal)
