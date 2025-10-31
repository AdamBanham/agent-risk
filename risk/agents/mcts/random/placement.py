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
import asyncio


class PlacementAction(BaseAction):
    """
    An action representing a placement decision.
    """

    def __init__(self, territory_id: int, num_armies: int, act: bool):
        self.territory_id = territory_id
        self.num_armies = num_armies
        self.act = act

    def execute(self, state: GameState) -> GameState:
        # Implementation of placement action execution
        if self.act:
            state.get_territory(self.territory_id).add_armies(self.num_armies)
        return state

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
        self, game_state: GameState, placements_left: int, acting: bool = True
    ):
        self.game_state = game_state
        self.placements_left = placements_left
        self.acting = acting
        self._rewards = None
        self._terrs = [
            t.id
            for t in game_state.get_territories_owned_by(game_state.current_player_id)
        ]
        if self.placements_left <= 0 or not self.acting:
            self._actions = []
        else:
            self._actions =[
                PlacementAction(terr.id, 1, True)
                for terr in self.game_state.get_territories_owned_by(
                    self.game_state.current_player_id
                )
            ]

    def get_current_player(self):
        return 1.0

    def get_possible_actions(self) -> List[PlacementAction]:
        return self._actions
        

    def take_action(self, action: PlacementAction) -> "PlacementState":
        new_game_state = copy_game_state(self.game_state)
        new_game_state = action.execute(new_game_state)
        if not action.is_acting():
            return PlacementState(new_game_state, self.placements_left, acting=False)
        return PlacementState(new_game_state, self.placements_left - action.num_armies)

    def is_terminal(self) -> bool:
        return self.placements_left <= 0 or not self.acting

    def get_reward(self) -> float:
        if self._rewards is None and self.is_terminal():
            # Simulate some turns to evaluate the placement
            print("simulating...")
            future, _ = simulate_turns(self.game_state, 2)
            self._rewards = calculate_player_position_rewards(
                future
            )[self.game_state.current_player_id]
        elif self._rewards is None:
            self._rewards = 1 / self.placements_left + 1

        return self._rewards
    
def policy(state: PlacementState) -> float:

    return state.get_reward()


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
        max_runtime = 100
        run_time_per_action = max_runtime / placements
        sim_state = copy_game_state(state)

        mcts_state = PlacementState(sim_state, placements)
        mcts = MCTS(time_limit=max_runtime, rollout_policy=policy)
        action, reward = mcts.search(mcts_state, need_details=True)

        print(extractStatistics(mcts, action))

        seq_actions = []
        node = mcts.root.children[action]
        seq_actions.append(action)
        while len(node.children.values()) > 0:
            print(node.children.values())
            for child in node.children.values():
                print(
                    f"Child: {child}, Total Reward: {child.totalReward}, Num Visits: {child.numVisits}"
                )
            node = max(node.children.values(), key=lambda n: n.numVisits)

        print(seq_actions)

        info(f"Best action: {node}, Expected reward: {node.totalReward}")
        for action in seq_actions:
            step = action.to_step()
            plan.add_step(step)
        return plan


if __name__ == "__main__":
    from risk.utils.logging import setLevel
    from logging import INFO

    setLevel(INFO)

    state = GameState.create_new_game(25, 2, 50)
    state.initialise()

    planner = RandomPlacements()
    plan = planner.construct_plan(state, 4)

    print("****")
    print(f"Generated Placement Plan: {plan}")
    for step in plan.steps:
        print(step)
