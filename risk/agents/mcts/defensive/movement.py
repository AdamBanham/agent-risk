from risk.agents.plans import Planner
from risk.state.game_state import GameState
from risk.utils.movement import (
    find_connected_frontline_territories,
    find_movement_sequence,
    find_safe_frontline_territories,
)
from risk.utils.logging import debug, info
from risk.agents.plans import MovementPlan, RouteMovementStep, MovementStep
from risk.utils import map as mapping
from ..base import extractStatistics

from typing import List, Set, Dict
from copy import deepcopy
import random

from mcts.base.base import BaseState, BaseAction
from mcts.searcher.mcts import MCTS


class NoMove(BaseAction):
    """
    An action for not moving troops.
    """

    def __init__(self):
        super().__init__()

    def __eq__(self, other):
        return isinstance(other, NoMove)

    def __hash__(self):
        return hash("noop")

    def __str__(self):
        return "no-move"

    def __repr__(self):
        return str(self)


class Movement(BaseAction):
    """
    An action for moving troops between territories.
    """

    def __init__(self, src: mapping.Node, tgt: mapping.Node, amount: int):
        super().__init__()
        self.src = src
        self.tgt = tgt
        self.amount = amount

    def optimal_amount(self, target: int):
        missing = target - self.tgt.value
        return min(self.amount, missing)

    def __eq__(self, other):
        if isinstance(other, Movement):
            return self.src == other.src and self.tgt == other.tgt
        return False

    def __hash__(self):
        return hash((self.src.id, self.tgt.id))

    def to_step(self, target: int):
        amount = self.optimal_amount(target)
        return MovementStep(self.src.id, self.tgt.id, amount)
    
    def __str__(self):
        return f"(#{self.src.id} -> #{self.tgt.id}, {self.amount})"
    
    def __repr__(self):
        return str(self)


class MovementState(BaseState):
    """
    State representing the movement phase.
    """

    def __init__(
        self,
        map: mapping.Graph,
        network_map: mapping.NetworkGraph,
        targets: Dict[int, Set[int]],
        moves: int = 0,
        max_moves: int = 20,

    ):
        self.map = map
        self.network_map = network_map
        self.targets = targets
        self.moves = moves
        self.max_moves = max_moves
        self._terminal = False

    def _set_terminal(self):
        self._terminal = True

    def get_current_player(self):
        return 1  # Maximizer

    def get_possible_actions(self) -> List[Movement]:
        actions = []

        for network in self.network_map.networks:
            target = self.targets.get(network)
            # add all possible moves to frontlines from safes
            for node in self.network_map.safes_in_network(network):
                node = self.map.get_node(node.id)
                if self.map.get_node(node.id).value > 1:
                    for tgt in self.network_map.frontlines_in_network(network):
                        tgt = self.map.get_node(tgt.id)
                        if tgt.id != node.id and tgt.value < target:
                            actions.append(
                                Movement(
                                    src=node,
                                    tgt=tgt,
                                    amount=self.map.get_node(node.id).value - 1,
                                )
                            )
            # add all possible moves between frontlines
            for node in self.network_map.frontlines_in_network(network):
                node = self.map.get_node(node.id)
                if self.map.get_node(node.id).value > target:
                    for tgt in self.network_map.frontlines_in_network(network):
                        tgt = self.map.get_node(tgt.id)
                        if (
                            tgt.id != node.id
                            and tgt.value < target
                        ):
                            actions.append(
                                Movement(
                                    src=node,
                                    tgt=tgt,
                                    amount=node.value - target,
                                )
                            )

        actions.append(NoMove())
        random.shuffle(actions)
        return actions

    def take_action(self, action):
        if isinstance(action, NoMove):
            state = MovementState(
                self.map.clone(),
                self.network_map,
                self.targets,
                self.moves + 1,
                self.max_moves,
            )
            state._set_terminal()
            return state
        new_map = self.map.clone()
        amount = action.optimal_amount(
            self.targets.get(self.network_map.get_node(action.tgt.id).value)
        )
        new_map.get_node(action.src.id).value -= amount
        new_map.get_node(action.tgt.id).value += amount

        return MovementState(
            new_map,
            self.network_map,
            self.targets,
            self.moves + 1,
            self.max_moves,
        )

    def is_terminal(self):
        return self._terminal or self.moves >= self.max_moves

    def get_reward(self):
        rewards = 0
        networks_balanced = 0
        for network in self.network_map.networks:
            all_balanced = True
            for tgt in self.network_map.frontlines_in_network(network):
                tgt = self.map.get_node(tgt.id)
                if tgt.value >= self.targets.get(network, 0):
                    rewards += 1
                else:
                    all_balanced = False
            if all_balanced:
                networks_balanced += 1

        return rewards * networks_balanced

class MovementPlanner(Planner):
    """
    A planner for moving troops defensively using MCTS.
    """

    def __init__(self, player: int, max_moves: int = 20):
        super().__init__()
        self.player = player
        self.max_moves = max_moves

    def construct_plan(self, state):

        max_runtime = 100  # milliseconds
        actions:List[Movement] = []
        network_map = mapping.construct_network_view(state.map, self.player)
        targets = {}

        for network in network_map.networks:
            group = network_map.view(network)
            total_armies = sum(
                state.map.get_node(t.id).value for t in group.nodes
            )
            fronts = group.frontlines_in_network(network)
            moveable = total_armies - (group.size - len(fronts))
            ideal_troops = moveable // len(fronts)
            targets[network] = ideal_troops


        mcts_state = MovementState(
            state.map.clone(),
            network_map,
            targets,
        )

        moves = self.max_moves
        for _ in range(moves):
            mcts = MCTS(time_limit=max(10, max_runtime // moves))
            action, reward = mcts.search(mcts_state, need_details=True)
            debug("Selected action: {}".format(action))
            debug(extractStatistics(mcts, action))

            if isinstance(action, NoMove):
                break

            mcts_state = mcts_state.take_action(action)
            actions.append(action)

        debug(f"Generated actions for attack plan: {actions}")

        plan = MovementPlan(len(actions))
        # Convert actions to plan steps
        for action in reversed(actions):
            step = action.to_step(targets.get(
                network_map.get_node(action.tgt.id).value
            ))

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

                plan.add_step(
                    RouteMovementStep(
                        route, step.troops
                    )
                )
            else:
                raise ValueError(f"No route found for movement from {action.src.id} to {action.tgt.id} of {action.amount} troops.")

        return plan


if __name__ == "__main__":
    from risk.state import GameState
    from risk.utils.logging import setLevel, info
    from logging import DEBUG

    setLevel(DEBUG)

    game_state = GameState.create_new_game(25, 2, 50)
    game_state.initialise()
    game_state.update_player_statistics()

    planner = MovementPlanner(player=0)
    plan = planner.construct_plan(game_state)

    terr = random.choice(game_state.map.nodes_for_player(0))
    game_state.get_territory(terr.id).armies += 50
    game_state.update_player_statistics()
    debug(f"Add extra armies to territory {terr.id} for testing.")

    info(f"Generated movement plan: {plan}")
    for step in plan.steps:
        info(f"  {step}")
