from ...plans import Planner, MovementPlan, RouteMovementStep, MovementStep
from risk.state import GameState
from risk.utils.movement import find_movement_sequence
from risk.utils.logging import debug

from risk.utils import map as mapping
from risk.utils.map import Graph
from dataclasses import dataclass, field
from typing import Set, Dict, List
from copy import deepcopy

from py_trees.behaviour import Behaviour
from py_trees.composites import Sequence
from py_trees.decorators import Retry
from py_trees.common import Status
from ..bases import Selector, Checker, BuildAction, ExecuteIf
import py_trees


@dataclass
class MovementState:
    player: int
    networks: Set[int] = field(default_factory=set)
    network: int = None
    network_target: int = None
    network_map: mapping.NetworkGraph = None
    map: mapping.Graph = None
    nodes: List[int] = field(default_factory=set)
    targets: Dict[int, int] = field(default_factory=dict)
    unchecked: Set[int] = field(default_factory=set)
    src: int = None
    tgt: int = None
    amount: int = None
    actions: list = field(default_factory=list)


class BuildMovementAction(BuildAction):
    """
    Builds a placement action from selected territory and troops.
    """

    def __init__(self):
        super().__init__("Build Movement Action", "movements", "actions")

    def build_step(self, state: MovementState) -> MovementStep:
        src_node = state.map.get_node(state.src)
        tgt_node = state.map.get_node(state.tgt)
        src_node.value -= state.amount
        tgt_node.value += state.amount

        if tgt_node.value >= state.targets[state.tgt]:
            state.unchecked.discard(state.tgt)
            debug(f"Target {state.tgt} been routed enough troops.")
            debug(f"Unchecked remaining: {state.unchecked}")

        return MovementStep(
            source=state.src, destination=state.tgt, troops=state.amount
        )


class BalanceAmount(Behaviour):
    """
    Determines the amount of troops to move from source to target.
    """

    def __init__(self):
        super().__init__("Determine Balance Amount")

    def initialise(self):
        debug(f"{self.__class__.__name__}::{self.name}")
        self.blackboard = self.attach_blackboard_client("movements")
        self.blackboard.register_key(key="state", access=py_trees.common.Access.WRITE)

    def update(self) -> Status:
        state: MovementState = self.blackboard.state
        src = state.src
        src_node = state.map.get_node(src)
        tgt_node = state.map.get_node(state.tgt)

        if state.tgt == state.src:
            debug("source and target are the same!!!")
            return Status.FAILURE

        if src_node.value < state.targets[src]:
            debug("source does not have enough troops to help tgt!!!")
            state.nodes.discard(state.src)
            debug(f"Remaining nodes to source from: {state.nodes}")
            return Status.FAILURE

        moveable = src_node.value - state.targets[src]

        if moveable <= 0:
            debug("no moveable troops!!!")
            return Status.FAILURE

        needed = state.targets[state.tgt] - tgt_node.value

        if needed <= 0:
            debug("the tgt already has enough troops!!!")
            state.unchecked.discard(state.tgt)
            debug(f"Unchecked targets remaining: {state.unchecked}")
            return Status.FAILURE

        amount = min(moveable, needed)

        state.amount = amount

        return Status.SUCCESS


class BalanceTarget(Behaviour):
    """
    Sets the goal army count for in network territories.
    """

    def __init__(self):
        super().__init__("Select Balance Target")

    def initialise(self):
        debug(f"{self.__class__.__name__}::{self.name}")
        self.blackboard = self.attach_blackboard_client("movements")
        self.blackboard.register_key(key="state", access=py_trees.common.Access.WRITE)

    def update(self) -> Status:
        state: MovementState = self.blackboard.state
        network = state.network_map.view(state.network)

        moveable = (
            sum(state.map.get_node(t.id).value for t in network.nodes) - network.size
        )
        fronts = network.frontlines_in_network(state.network)

        if not fronts:
            debug("No frontlines in network!")
            return Status.INVALID

        map = state.map

        def sum_of_adjacents(node: mapping.SafeNode) -> int:
            total = 0
            armies = map.get_node(node.id).value
            for neighbor in map.get_adjacent_nodes(node.id):
                if neighbor.owner != state.player:
                    total += armies / neighbor.value
            return total

        weights = [sum_of_adjacents(node) for node in fronts]
        total_weight = sum(weights)
        weights = [w / total_weight for w in weights]
        troops = [min(1, int(moveable * w)) for w in weights]

        ordered_fronts = sorted(
            zip(fronts, troops),
            key=lambda x: x[1],
            reverse=True,
        )

        state.targets = {t.id: n for t, n in ordered_fronts}
        state.unchecked = set(list(state.targets.keys()))
        state.nodes = list(t.id for t in network.nodes if map.get_node(t.id).value > 1)

        for node in network.nodes:
            if node.id not in state.targets:
                state.targets[node.id] = 1

        return Status.SUCCESS

    def terminate(self, new_status):
        debug(f"Balance target selection completed with status: {new_status}")
        state: MovementState = self.blackboard.state
        return super().terminate(new_status)


class Balancer(Sequence):
    """
    Balances troops among frontlines in the selected network.
    """

    def __init__(self):
        super().__init__("Balance Troops", False)

        self.add_children(
            [
                Retry(
                    "Keep Balancing?",
                    ExecuteIf(
                        "Nodes left to balance?",
                        [
                            Checker(
                                "movements",
                                "nodes",
                                lambda s: len(s) == 0,
                            ),
                            Checker(
                                "movements",
                                "unchecked",
                                lambda s: len(s) == 0,
                            ),
                        ],
                        Sequence(
                            "Balance Network",
                            False,
                            [
                                Selector(
                                    "movements",
                                    "unchecked",
                                    "tgt",
                                ),
                                Selector(
                                    "movements",
                                    "nodes",
                                    "src",
                                    lambda s: s != self.state.tgt,
                                ),
                                BalanceAmount(),
                                BuildMovementAction(),
                                Checker(
                                    "movements",
                                    "unchecked",
                                    lambda s: len(s) == 0,
                                ),
                            ],
                        ),
                    ),
                    -1,
                ),
            ]
        )

    def initialise(self):
        debug(f"{self.__class__.__name__}::{self.name}")

        # Initialize blackboard with movement state
        self.movement = self.attach_blackboard_client("movements")
        self.movement.register_key(key="state", access=py_trees.common.Access.WRITE)
        self.state: MovementState = self.movement.state

        return super().initialise()

    def update(self) -> Status:
        return super().update()

    def terminate(self, new_status):
        debug(f"Balancing completed with status: {new_status}")
        return super().terminate(new_status)


class Movements(Sequence):
    """
    Behaviour tree for deciding movements. For each network, balances troops
    among frontlines.
    """

    def __init__(self, player: int, map: Graph):
        super().__init__("Defensive movements", False)

        network_map = mapping.construct_network_view(map, player)

        self.state = MovementState(
            player=player,
            network_map=network_map,
            networks=set(network_map.networks),
            map=deepcopy(map),
            actions=[],
        )

        self.add_children(
            [
                Retry(
                    "Processing Networks",
                    ExecuteIf(
                        "Networks left?",
                        [
                            Checker(
                                "movements",
                                "networks",
                                lambda s: len(s) == 0,
                            ),
                        ],
                        Sequence(
                            "Process Network",
                            True,
                            [
                                Selector(
                                    "movements",
                                    "networks",
                                    "network",
                                    with_replacement=False,
                                ),
                                BalanceTarget(),
                                Balancer(),
                                Checker(
                                    "movements",
                                    "networks",
                                    lambda s: len(s) == 0,
                                )
                            ]
                        ),
                    ),
                    -1
                )
            ]
        )

    def initialise(self):
        debug(f"{self.__class__.__name__}::{self.name}")

        # Initialize blackboard with placement state
        self.placement = self.attach_blackboard_client("movements")
        self.placement.register_key(key="state", access=py_trees.common.Access.WRITE)
        self.placement.state = self.state

        player_id = self.state.player
        msg = f"Initialized blackboard with MovementState for player {player_id}"
        debug(msg)
        msg = f"Total networks to process: {len(self.state.networks)}"
        debug(msg)
        return super().initialise()

    def terminate(self, new_status):
        debug(f"Movement completed with status: {new_status}")
        debug(f"Final movement count: {len(self.state.actions)}")
        return super().terminate(new_status)

    def construct(self) -> list:
        """
        Constructs a plan for the phasement phase.
        """

        while self.status != Status.SUCCESS:
            self.tick_once()
        return self.state.actions


class MovementPlanner(Planner):
    """
    A planner that creates an attack plan based on the current game state.
    """

    def __init__(
        self,
        player_id: int,
    ):
        super().__init__()
        self.player_id = player_id

    def construct_plan(self, state: GameState) -> MovementPlan:

        constructor = Movements(self.player_id, state.map)
        actions = constructor.construct()

        plan = MovementPlan(len(actions))

        for move in reversed(actions):
            debug(f"Planned movement: {move}")

            movements = find_movement_sequence(
                state.get_territory(move.source),
                state.get_territory(move.destination),
                move.troops,
            )

            if not movements:
                raise ValueError(f"No movement path found from {move.source} to {move.destination}!!!!")

            movements = [
                MovementStep(
                    source=move.src.id, destination=move.tgt.id, troops=move.amount
                )
                for move in movements
            ]

            plan.add_step(RouteMovementStep(route=movements, troops=move.troops))

        return plan


if __name__ == "__main__":
    from logging import DEBUG
    from risk.utils.logging import setLevel

    setLevel(DEBUG)
    from py_trees import logging

    logging.level = logging.Level.DEBUG

    state = GameState.create_new_game(10, 2, 50)
    state.initialise()

    planner = MovementPlanner(player_id=1)
    plan = planner.construct_plan(state)
    debug(f"Constructed movement plan: {plan}")

    while not plan.is_done():
        step = plan.pop_step()
        debug(f"Executing movement step: {step}")
