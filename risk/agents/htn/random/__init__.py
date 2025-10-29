"""
This module contains the logic for Hierarchical Task Network (HTN)
Random Agent Implementation.
"""

from ...agent import BaseAgent
from risk.state import GameState

from .placement import RandomPlacements
from .attack import RandomAttacks


class HTNRandomAgent(BaseAgent):
    """
    A simple HTN agent that makes random decisions during placement, attack,
    and defense phases.
    """

    def __init__(self, player_id: int, attack_probability: float = 0.5):
        super().__init__(player_id, "HTN-Random-Agent-{}".format(player_id), attack_probability)

    def decide_placement(self, state: GameState, goal) -> object:
        print(
            f"htn-random-agent-{self.player_id} - planning for placement"
        )

        plan = RandomPlacements.construct_plan(
            self.player_id,
            state.placements_left,
            set(t.id for t in state.get_territories_owned_by(self.player_id)),
        )

        events = []
        while not plan.is_done():
            step = plan.pop_step()
            events.extend(step.execute(state))

        return events
    
    def decide_attack(self, game_state, goal):
        print(
            f"htn-random-agent-{self.player_id} - planning for attacking"
        )

        plan = RandomAttacks.construct_plan(
            self.player_id,
            10,
            self.attack_probability,
            game_state,
        )

        events = []
        while not plan.is_done():
            step = plan.pop_step()
            events.extend(step.execute(game_state))

        return events
    
    def decide_movement(self, game_state, goal):
        return super().decide_movement(game_state, goal)
