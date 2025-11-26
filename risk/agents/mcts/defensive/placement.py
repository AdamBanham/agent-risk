from risk.agents.plans import Planner
from risk.state.game_state import GameState
from risk.utils.logging import debug
from risk.utils import map as mapping
from ...plans import PlacementPlan, TroopPlacementStep

import random

from mcts.base.base import BaseState, BaseAction
from mcts.searcher.mcts import MCTS


class Placement(BaseAction):
    """
    Places troops on a territory.
    """

    def __init__(self, territory: int):
        super().__init__()
        self.territory = territory

    def to_step(self):
        return TroopPlacementStep(self.territory, 1)

    def __eq__(self, other):
        if isinstance(other, Placement):
            return self.territory == other.territory
        return False

    def __hash__(self):
        return hash((self.territory))


class PlacementState(BaseState):
    """
    State representing the placement phase.
    """

    def __init__(
        self, placements_left: int, map: mapping.Graph, player: int, frontlines: int
    ):
        self.placements_left = placements_left
        self.player = player
        self.map = map
        self.frontlines = frontlines

    def get_current_player(self) -> int:
        return 1  # Maximizer

    def get_possible_actions(self) -> [Placement]:
        actions = []
        if self.placements_left > 0:
            for terr in self.map.nodes_for_player(self.player):
                actions.append(Placement(terr.id))
        return actions

    def take_action(self, action: Placement) -> "PlacementState":
        new_map = self.map.clone()
        new_map.get_node(action.territory).value += 1
        return PlacementState(
            self.placements_left - 1, new_map, self.player, self.frontlines
        )

    def is_terminal(self) -> bool:
        return self.placements_left == 0

    def get_reward(self):
        safe_map = mapping.construct_safe_view(self.map, self.player)
        armies = sorted(
            [self.map.get_node(t.id).value for t in safe_map.frontline_nodes],
            reverse=True,
        )[: self.frontlines]
        armies_on_top = sum(t for t in armies)

        return (1 / (self.placements_left + 1)) * armies_on_top


def extractStatistics(searcher, action) -> dict:
    """Return simple statistics for ``action`` from ``searcher``."""
    statistics = {}
    statistics["rootNumVisits"] = searcher.root.numVisits
    statistics["rootTotalReward"] = searcher.root.totalReward
    statistics["actionNumVisits"] = searcher.root.children[action].numVisits
    statistics["actionTotalReward"] = searcher.root.children[action].totalReward
    return statistics


class PlacementPlanner(Planner):
    """A planner for placing troops aggressively in Risk."""

    def __init__(self, player_id: int, placements: int):
        super().__init__()
        self.player = player_id
        self.placements = placements

    def construct_plan(self, state: GameState) -> PlacementPlan:
        """Create a placement plan for the given player in the current state."""

        plan = PlacementPlan(self.placements)
        max_fronts = len(
            mapping.construct_safe_view(state.map, self.player).frontline_nodes
        )
        max_runtime = 500  # milliseconds

        actions = []
        for _ in range(self.placements):
            mcts_state = PlacementState(
                self.placements,
                state.map.clone(),
                self.player,
                random.randint(1, max_fronts),
            )
            mcts = MCTS(time_limit=max(10, max_runtime // self.placements))
            action, reward = mcts.search(mcts_state, need_details=True)
            actions.append(action)
            mcts_state = mcts_state.take_action(action)

            debug(extractStatistics(mcts, action))

        debug(f"Generated actions for placement plan: {actions}")

        # Convert actions to plan steps
        for action in actions:
            step = action.to_step()
            plan.add_step(step)
        return plan


if __name__ == "__main__":
    from risk.state import GameState
    from risk.utils.logging import setLevel, info
    from logging import DEBUG
    import random

    setLevel(DEBUG)

    game_state = GameState.create_new_game(25, 2, 50)
    game_state.initialise()

    for _ in range(10):

        planner = PlacementPlanner(player_id=0, placements=random.randint(1, 10))
        plan = planner.construct_plan(game_state)

        info(
            f"Constructed Placement Plan: {plan}, expected placements: {planner.placements}"
        )
        for step in plan.steps:
            info(f"Step: {step}")

        input("Press Enter to continue...")
