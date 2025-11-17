"""
This module contains the logic for Discrete EVent System simulator (DEVS)
Random Agent Implementation.
"""

from risk.agents.agent import BaseAgent
from risk.utils.logging import debug

from .placement import RandomPlacement
from .attack import RandomAttack
from .movement import RandomMovement


class DEVSRandomAgent(BaseAgent):
    """
    A simple DEVS agent that makes random decisions during placement, attack,
    and defense phases.
    """

    def __init__(self, player_id: int, attack_probability: float = 0.5):
        super().__init__(
            player_id, "devs-random-agent-{}".format(player_id), attack_probability
        )

    def decide_placement(self, game_state, goal):
        debug(f"{self.name} - planning for placement")
        planner = RandomPlacement(self.player_id, game_state.placements_left)
        plan = planner.construct_plan(game_state)

        events = []
        while not plan.is_done():
            step = plan.pop_step()
            events.extend(step.execute(game_state))

        debug(f"result :: {events}")
        return events

    def decide_attack(self, game_state, goal):
        debug(f"{self.name} - planning for attack")
        planner = RandomAttack(self.player_id, 10, self.attack_probability)
        plan = planner.construct_plan(game_state)

        events = []
        while not plan.is_done():
            step = plan.pop_step()
            events.extend(step.execute(game_state))
        
        debug(f"result :: {events}")
        return events

    def decide_movement(self, game_state, goal):
        debug(f"{self.name} - planning for movement")
        planner = RandomMovement(self.player_id, 1)
        plan = planner.construct_plan(game_state)

        events = []
        while not plan.is_done():
            step = plan.pop_step()
            events.extend(step.execute(game_state))

        debug(f"result :: {events}")
        return events
