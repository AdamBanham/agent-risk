"""
This module contains the logic for Behaviour Tree (BT)
Random Agent Implementation.
"""
from risk.agents import BaseAgent

from .placement import RandomPlacements
from .attack import RandomAttacks
from .movement import RandomMovements


class BTRandomAgent(BaseAgent):
    """
    A simple BT agent that makes random decisions during placement, attack,
    and defense phases.
    """

    def __init__(self, player_id: int, attack_probability: float):
        super().__init__(
            player_id, "BT-Random-Agent-{}".format(player_id), attack_probability
        )

    def decide_placement(self, game_state, goal):
        print(f"bt-random-agent-{self.player_id} planning for placement")

        terrs = game_state.get_territories_owned_by(self.player_id)

        planner = RandomPlacements(
            self.player_id,
            game_state.placements_left,
            [t.id for t in terrs],
            game_state,
        )
        planner.construct_plan()
        plan = planner.plan

        events = []
        while not plan.is_done():
            step = plan.pop_step()
            events.extend(step.execute(game_state))

        return events

    def decide_attack(self, game_state, goal):
        print(f"bt-random-agent-{self.player_id} planning for attacking")

        terrs = game_state.get_territories_owned_by(self.player_id)

        planner = RandomAttacks(
            self.player_id,
            10,
            [t.id for t in terrs],
            game_state,
            self.attack_probability,
        )
        planner.construct_plan()
        plan = planner.plan

        events = []
        while not plan.is_done():
            step = plan.pop_step()
            events.extend(step.execute(game_state))

        return events

    def decide_movement(self, game_state, goal):
        print(f"bt-random-agent-{self.player_id} planning for movement")

        planner = RandomMovements(
            self.player_id,
            1,
            [t.id for t in game_state.get_territories_owned_by(self.player_id)],
            game_state,
        )
        plan = planner.construct_plan()

        events = []
        while not plan.is_done():
            step = plan.pop_step()
            events.extend(step.execute(game_state))

        return events
