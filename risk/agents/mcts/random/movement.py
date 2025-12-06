import random
from risk.agents.plans import Planner
from risk.state.game_state import GameState
from risk.state.plan import Plan
from risk.utils.movement import (
    find_connected_frontline_territories,
    find_movement_sequence,
    find_safe_frontline_territories,
)
from risk.utils.logging import debug, info
from risk.utils import map as mapping
from risk.agents.plans import MovementPlan, RouteMovementStep, MovementStep

from typing import List, Set, Collection
from copy import deepcopy

from mcts.base.base import BaseState, BaseAction
from mcts.searcher.mcts import MCTS
from ..base import NoAction, BaseAgentAction
from ..base import extractStatistics


class NoMove(NoAction):
    """
    Noop for movement.
    """

    def __init__(self):
        super().__init__()

    def execute(self, state: "MovementState"):
        return MovementState(
            state.moves, state.terrs, state.map, state.networks, state._actions + [self]
        )


class MovementAction(BaseAgentAction):

    def __init__(
        self,
        from_territory_id: int,
        to_territory_id: int,
        num_armies: int,
    ):
        super().__init__(False)
        self.src = from_territory_id
        self.tgt = to_territory_id
        self.troops = num_armies

    def execute(self, state: "MovementState") -> "MovementState":
        return MovementState(
            state.moves - 1,
            state.terrs,
            state.map,
            state.networks,
            state._actions + [self],
        )

    def to_step(self, game_state: GameState):
        return MovementStep(self.src, self.tgt, self.troops)

    def __str__(self):
        return str((self.src, self.tgt, self.troops))

    def __repr__(self):
        return str(self)

    def __eq__(self, other):
        if isinstance(other, MovementAction):
            return (
                self.src == other.src
                and self.tgt == other.tgt
                and self.troops == other.troops
            )
        return False

    def __hash__(self):
        return hash((self.id, self.src, self.tgt, self.troops))


class MovementState(BaseState):
    """
    A state representing the movement phase for MCTS.
    """

    def __init__(
        self,
        moves: int,
        terrs: Set[int],
        map: mapping.Graph,
        networks: mapping.NetworkGraph,
        actions: Collection[BaseAgentAction] = None,
    ):
        self.terrs = terrs
        self.moves = moves
        self.map = map.clone()
        self.networks = networks
        self._actions = [a for a in actions] if actions else []

    def get_current_player(self):
        return 1  # Maximise

    def get_possible_actions(self):
        options = []

        if self.moves > 0:
            # for each safe, make an action to one of its
            # connected frontlines
            for terr in self.terrs:
                troops = mapping.get_value(self.map, terr) - 1

                if troops > 0:
                    network = mapping.get_value(self.networks, terr)
                    for front in self.networks.frontlines_in_network(network):
                        options.append(MovementAction(terr, front.id, troops))

        options.append(NoMove())
        random.shuffle(options)
        debug(f"Produced action set of size: {len(options)}")
        return options

    def take_action(self, action):
        return action.execute(self)

    def is_terminal(self):
        if len(self._actions) > 0:
            last = self._actions[-1]
            return last.is_terminal()
        return False

    def get_reward(self):
        return len(self._actions)


class RandomMovements(Planner):
    """
    A planner that creates random movement plans.
    """

    def __init__(self, moves: int = 1, player: int = 0):
        super().__init__()
        self.moves = moves
        self.player = player

    def construct_plan(self, state: GameState) -> Plan:
        # Implementation of random movement plan construction
        # Get all territories owned by this agent
        map = state.map
        safe_map = mapping.construct_safe_view(map, self.player)
        network_map = mapping.construct_network_view(map, self.player)
        safes = safe_map.safe_nodes

        max_runtime = 100  # milliseconds
        plan = MovementPlan(self.moves)

        if len(safes) < 1:
            return plan

        actions = []
        mcts_state = MovementState(self.moves, {n.id for n in safes}, map, network_map)

        for i in range(self.moves + 1):
            if mcts_state.is_terminal():
                break

            debug(f"starting mcts for attacking {i+1}/{self.moves+1}...")
            mcts = MCTS(time_limit=max(10, max_runtime // self.moves + 1))
            action, reward = mcts.search(mcts_state, need_details=True)
            actions.append(action)
            mcts_state = mcts_state.take_action(action)
            debug(f"mcts finished, taking {action} with expected reward of {reward}")
            debug(extractStatistics(mcts, action))

        debug(f"Generated actions for attacks plan: {actions}")

        # Convert actions to plan steps
        for action in reversed(actions):
            step = action.to_step(state)
            if step:
                route = find_movement_sequence(
                    state.get_territory(step.source),
                    state.get_territory(step.destination),
                    step.troops,
                )

                if route:
                    route = [
                        MovementStep(move.src.id, move.tgt.id, step.troops)
                        for move in route
                    ]

                    plan.add_step(RouteMovementStep(route, step.troops))
                else:
                    raise ValueError(
                        f"No route found for movement from {action.src.id} to {action.tgt.id} of {action.amount} troops."
                    )
        return plan


if __name__ == "__main__":
    from risk.utils.logging import setLevel
    from logging import DEBUG

    setLevel(DEBUG)

    for _ in range(10):
        state = GameState.create_new_game(50, 2, 250)
        state.initialise()
        state.update_player_statistics()

        moves = 1
        player = random.randint(0, 1)
        planner = RandomMovements(moves, player)
        plan = planner.construct_plan(state)

        map = state.map
        networks = mapping.construct_network_view(map, player)

        debug(f"Constructed Plan: {plan}")
        assert len(plan.steps) <= moves, f"Expected no more than {moves} movements"
        seen = set()
        for step in plan.steps:
            debug(step)

        input("continue?")
