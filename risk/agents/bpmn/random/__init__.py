"""
This module contains the logic for Business Process Model and Notation (BPMN)
Random Agent Implementation.
"""

from risk.agents.agent import BaseAgent
from risk.utils.logging import info

from .placement import RandomPlacement
from .attack import RandomAttack
from .movement import RandomMovement


class BPMNRandomAgent(BaseAgent):
    """
    A simple BPMN agent that makes random decisions during placement, attack,
    and defense phases.
    """

    def __init__(self, player_id: int, attack_probability: float = 0.5):
        super().__init__(
            player_id, "BPMN-Random-Agent-{}".format(player_id), attack_probability
        )

    def decide_placement(self, game_state, goal):
        info(f"{self.name} - planning for placement")
        planner = RandomPlacement(self.player_id, game_state.placements_left)
        plan = planner.construct_plan(game_state)

        events = []
        while not plan.is_done():
            step = plan.pop_step()
            events.extend(step.execute(game_state))
        return events

    def decide_attack(self, game_state, goal):
        info(f"{self.name} - planning for attack")
        planner = RandomAttack(self.player_id, 10, self.attack_probability)
        plan = planner.construct_plan(game_state)

        events = []
        while not plan.is_done():
            step = plan.pop_step()
            events.extend(step.execute(game_state))
        return events

    def decide_movement(self, game_state, goal):
        info(f"{self.name} - planning for movement")
        planner = RandomMovement(self.player_id, 1)
        plan = planner.construct_plan(game_state)

        events = []
        while not plan.is_done():
            step = plan.pop_step()
            events.extend(step.execute(game_state))
        return events
