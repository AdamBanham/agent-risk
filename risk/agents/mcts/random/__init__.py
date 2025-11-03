"""
This module contains the logic for Monte Carlo Tree Search (MCTS)
Random Agent Implementation.
"""

from typing import List

from risk.state.game_state import GameState
from risk.agents import BaseAgent
from risk.state.plan import Goal
from risk.utils.logging import debug, info

from .attack import RandomAttacks
from .movement import RandomMovements
from .placement import RandomPlacements


class MCSTRandomAgent(BaseAgent):
    """
    A simple MCTS agent that makes random decisions during placement, attack,
    and defense phases.
    """

    def __init__(self, player_id: int, attack_probability: float = 0.6):
        super().__init__(
            player_id, "MCTS-Random-Agent-{}".format(player_id), attack_probability
        )

    def decide_placement(self, state: GameState, goal: Goal = None) -> List:
        debug(f"mcts-random-agent-{self.player_id} planning placement")
        planner = RandomPlacements()
        plan = planner.construct_plan(state, state.placements_left)

        events = []
        while not plan.is_done():
            events.extend(plan.pop_step().execute(state))
        return events

    def decide_attack(self, state: GameState, goal: Goal = None) -> List:
        debug(f"mcts-random-agent-{self.player_id} planning attack")
        planner = RandomAttacks(
            10, player=self.player_id, attack_probability=self.attack_probability
        )
        plan = planner.construct_plan(state)

        events = []
        while not plan.is_done():
            events.extend(plan.pop_step().execute(state))
        return events

    def decide_movement(self, state: GameState, goal: Goal = None) -> List:
        debug(f"mcts-random-agent-{self.player_id} planning movement")
        planner = RandomMovements(player=self.player_id)
        plan = planner.construct_plan(state)

        events = []
        while not plan.is_done():
            events.extend(plan.pop_step().execute(state))
        return events
