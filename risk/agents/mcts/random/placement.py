from risk.agents.plans import Planner
from risk.state.game_state import GameState
from risk.state.plan import Plan
from risk.utils.rewards import calculate_player_position_rewards
from risk.utils.copy import copy_game_state
from risk.utils.replay import simulate_turns, SimulationConfiguration
from risk.utils.logging import debug, info
from ...plans import PlacementPlan, TroopPlacementStep

from mcts.base.base import BaseState, BaseAction
from mcts.searcher.mcts import MCTS

from typing import List
import random

class PlacementAction(BaseAction):
    """
    An action representing a placement decision.
    """

    def __init__(self, territory_id: int, num_armies: int, act: bool):
        self.territory_id = territory_id
        self.num_armies = num_armies
        self.act = act

    def execute(self, state: 'PlacementState') -> 'PlacementState':
        if self.act:
            return PlacementState(
                state.placements_left - self.num_armies, state.terrs
            )
        else:
            return PlacementState(
                state.placements_left, state.terrs, acting=False
            )

    def is_acting(self) -> bool:
        return self.act

    def to_step(self):
        if self.act:
            return TroopPlacementStep(self.territory_id, self.num_armies)
        else:
            return None

    def __str__(self):
        return str((self.territory_id, self.num_armies))

    def __repr__(self):
        return str(self)

    def __eq__(self, other):
        if isinstance(other, PlacementAction):
            return (
                self.territory_id == other.territory_id
                and self.num_armies == other.num_armies
            )
        return False

    def __hash__(self):
        return hash((self.territory_id, self.num_armies))


class PlacementState(BaseState):
    """
    A state representing the placement phase for MCTS.
    """

    def __init__(
        self, placements_left: int, terrs: set[int], acting: bool = True,
    ):
        self.placements_left = placements_left
        self.acting = acting
        self.terrs = terrs
        if self.placements_left <= 0 or not self.acting:
            self._actions = []
        else:
            self._actions = []
            for drop in range(1, self.placements_left + 1):
                debug(f"Possible placement: {drop} troops")
                self._actions.extend([
                    PlacementAction(terr, drop, True)
                    for terr in self.terrs
                ])
            self._actions.append(PlacementAction(-1, 0, False)) 
            random.shuffle(self._actions)

    def get_current_player(self):
        return 1.0

    def get_possible_actions(self) -> List[PlacementAction]:
        return self._actions

    def take_action(self, action: PlacementAction) -> "PlacementState":
        return action.execute(self)

    def is_terminal(self) -> bool:
        return self.placements_left <= 0 or not self.acting

    def get_reward(self) -> float:
        base = 1.0 / (1.0 + self.placements_left)
        jitter = 0.25 + random.random() * (base - 0.25)
        return base + jitter


def extractStatistics(searcher, action) -> dict:
    """Return simple statistics for ``action`` from ``searcher``."""
    statistics = {}
    statistics["rootNumVisits"] = searcher.root.numVisits
    statistics["rootTotalReward"] = searcher.root.totalReward
    statistics["actionNumVisits"] = searcher.root.children[action].numVisits
    statistics["actionTotalReward"] = searcher.root.children[action].totalReward
    return statistics


class RandomPlacements(Planner):
    """
    A planner that creates random placement plans.
    """

    def __call__(self, *args, **kwds):
        return super().__call__(*args, **kwds)

    def construct_plan(self, state: GameState, placements: int) -> Plan:
        # Implementation of random placement plan construction
        plan = PlacementPlan(placements)
        max_runtime = 50 # milliseconds
        terrs = set(
            terr.id 
            for terr 
            in state.get_territories_owned_by(state.current_player_id)
        )
        mcts_state = PlacementState(placements, terrs)
        mcts = MCTS(time_limit=max_runtime)
        action, reward = mcts.search(mcts_state, need_details=True)

        debug(extractStatistics(mcts, action))

        # recursively extract actions
        seq_actions = []
        node = mcts.root.children[action]
        seq_actions.append(action)
        depth = 0
        debug(f"Depth {depth}: Selected Action: {action}")
        while len(node.children.values()) > 0:
            for child in node.children.values():
                debug(
                    f"Child: {child}, Total Reward: {child.totalReward}, Num Visits: {child.numVisits}"
                )
            action, node = max(node.children.items(), key=lambda n: n[1].totalReward)
            depth += 1
            debug(f"Depth {depth}: Selected Action: {action}")
            seq_actions.append(action)

        # Convert actions to plan steps
        for action in seq_actions:
            step = action.to_step()
            plan.add_step(step)
        return plan


if __name__ == "__main__":
    from risk.utils.logging import setLevel
    from logging import INFO, DEBUG

    setLevel(DEBUG)

    state = GameState.create_new_game(25, 2, 50)
    state.initialise()

    planner = RandomPlacements()
    plan = planner.construct_plan(state, 4)

    print("****")
    print(f"Generated Placement Plan: {plan}")
    for step in plan.steps:
        print(step)
