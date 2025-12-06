from risk.agents.plans import Planner
from risk.state.game_state import GameState
from risk.state.plan import Plan
from risk.utils.logging import debug
from ...plans import PlacementPlan, TroopPlacementStep

from mcts.base.base import BaseState
from mcts.searcher.mcts import MCTS
from ..base import NoAction, BaseAgentAction
from ..base import extractStatistics

from typing import List, Collection
import random


class NoPlacement(NoAction):
    """
    Noop for placement.
    """

    def __init__(self):
        super().__init__()

    def execute(self, state: "PlacementState"):
        return PlacementState(
            state.placements_left, state.terrs, state._actions + [self]
        )


class PlacementAction(BaseAgentAction):
    """
    An action representing a placement decision.
    """

    def __init__(self, territory_id: int, num_armies: int):
        super().__init__(False)
        self.territory_id = territory_id
        self.num_armies = num_armies

    def execute(self, state: "PlacementState") -> "PlacementState":
        return PlacementState(
            state.placements_left - 1, state.terrs, state._actions + [self]
        )

    def to_step(self):
        return TroopPlacementStep(self.territory_id, self.num_armies)

    def __str__(self):
        return str((self.territory_id, self.num_armies))

    def __repr__(self):
        return str(self)

    def __eq__(self, other):
        if isinstance(other, PlacementAction):
            return other.id == self.id
        return False

    def __hash__(self):
        return hash((self.id, self.territory_id, self.num_armies))


class PlacementState(BaseState):
    """
    A state representing the placement phase for MCTS.
    """

    def __init__(
        self,
        placements_left: int,
        terrs: set[int],
        actions: Collection[BaseAgentAction] = None,
    ):
        self.placements_left = placements_left
        self.terrs = terrs
        self._actions = [a for a in actions] if actions else []

    def get_current_player(self):
        return 1.0  # Maximise

    def get_possible_actions(self) -> List[PlacementAction]:
        options = []

        if self.placements_left == 0:
            options.append(NoPlacement())
        else:
            for terr in self.terrs:
                options.append(PlacementAction(terr, 1))
            options.append(NoPlacement())

        random.shuffle(options)
        return options

    def take_action(self, action: PlacementAction) -> "PlacementState":
        return action.execute(self)

    def is_terminal(self) -> bool:
        if len(self._actions) > 0:
            last = self._actions[-1]
            return last.is_terminal()
        return False

    def get_reward(self) -> float:
        return len(self._actions)


class RandomPlacements(Planner):
    """
    A planner that creates random placement plans.
    """

    def __init__(self, player: int, placements: int):
        super().__init__()
        self.player = player
        self.placements = placements

    def construct_plan(self, state: GameState) -> Plan:
        # Implementation of random placement plan construction
        plan = PlacementPlan(self.placements)
        terrs = set(terr.id for terr in state.get_territories_owned_by(self.player))
        max_runtime = 100  # milliseconds

        actions = []
        mcts_state = PlacementState(self.placements, terrs)
        for i in range(self.placements+1):
            debug(f"starting mcts for placement {i+1}/{self.placements}...")
            mcts = MCTS(time_limit=max(10, max_runtime // self.placements))
            action, reward = mcts.search(mcts_state, need_details=True)
            actions.append(action)
            mcts_state = mcts_state.take_action(action)
            debug(f"mcts finished, taking {action} with expected reward of {reward}")
            debug(extractStatistics(mcts, action))

        debug(f"Generated actions for placement plan: {actions}")

        # Convert actions to plan steps
        for action in actions:
            step = action.to_step()
            if step:
                plan.add_step(step)
        return plan


if __name__ == "__main__":
    from risk.utils.logging import setLevel
    from logging import DEBUG

    setLevel(DEBUG)

    state = GameState.create_new_game(25, 2, 50)
    state.initialise()
    state.update_player_statistics()

    for _ in range(10):
        pick = random.randint(1, 10)
        player = random.randint(0, 1)
        planner = RandomPlacements(player, pick)
        plan = planner.construct_plan(state)

        print(plan)
        assert len(plan.steps) == pick, f"Expected {pick} placements"
        for step in plan.steps:
            print(step)
            terr = state.get_territory(step.territory)
            assert terr.owner == player, f"Expected to pick territories for {player}"

        input("cotinue?")
