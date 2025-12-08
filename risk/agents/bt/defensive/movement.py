from ...plans import Planner, MovementPlan, RouteMovementStep, MovementStep
from risk.state import GameState
from risk.utils.movement import find_movement_sequence
from risk.utils.logging import debug

from risk.utils import map as mapping
from risk.utils.map import Graph
from dataclasses import dataclass, field
from typing import Set, Dict

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
    armies: Dict[int, int] = field(default_factory=dict)
    network_target: int = None
    map: mapping.NetworkGraph = None
    nodes: Set[int] = field(default_factory=set)
    missing: Set[int] = field(default_factory=set)
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
        state.armies[state.src] -= state.amount
        state.armies[state.tgt] += state.amount
        if state.armies[state.tgt] >= state.network_target:
            state.missing.discard(state.src)
        if state.armies[state.src] <= 1:
            state.nodes.discard(state.src)
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

        if src in state.missing:
            debug("src is missing troops, cannot move from it!!!")
            return Status.FAILURE

        if not state.map.get_node(src).safe:
            moveable = state.armies[state.src] - state.network_target
        else:
            moveable = state.armies[state.src] - 1

        if moveable <= 0:
            debug("no moveable troops!!!")
            state.nodes.discard(src)
            return Status.FAILURE

        needed = state.network_target - state.armies[state.tgt]

        if needed <= 0:
            debug("the tgt already has enough troops!!!")
            state.missing.discard(state.tgt)
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
        network = state.map.view(state.network)

        moveable = sum(state.armies[t.id] for t in network.nodes) - network.size
        fronts = network.frontlines_in_network(state.network)
        ideal_troops = moveable // len(fronts)

        state.network_target = ideal_troops

        state.missing = set(
            t.id for t in fronts if state.armies[t.id] < ideal_troops
        )
        state.nodes = set(t.id for t in network.nodes).difference(state.missing)
        unmoveable = set(t for t in state.nodes if state.armies[t] <= 1)
        state.nodes = state.nodes.difference(unmoveable)

        return Status.SUCCESS

    def terminate(self, new_status):
        debug(
            f"Balance target selection completed with status: {new_status}"
        )
        state: MovementState = self.blackboard.state
        return super().terminate(new_status)


class Balancer(Sequence):
    """
    Balances troops among frontlines in the selected network.
    """

    def __init__(self):
        super().__init__("Balance Troops", True)

        self.add_children(
            [
                BalanceTarget(),
                Retry(
                    "Keep Balancing?",
                    ExecuteIf(
                        "Needs Balancing?",
                        [
                            Checker(
                                "movements",
                                "missing",
                                lambda s: len(s) == 0,
                            ),
                            Checker(
                                "movements",
                                "nodes",
                                lambda s: len(s) == 0,
                            )
                        ],
                        Sequence(
                            "Balance Network",
                            True,
                            [
                                Selector(
                                    "movements",
                                    "missing",
                                    "tgt",
                                ),
                                Selector(
                                    "movements",
                                    "nodes",
                                    "src",
                                ),
                                BalanceAmount(),
                                BuildMovementAction(),
                                Checker(
                                    "movements",
                                    "missing",
                                    lambda s: len(s) == 0,
                                ),
                            ],
                        ),
                    ),
                    10000,
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
        super().__init__("Defensive movements", True)

        network_map = mapping.construct_network_view(map, player)
        networks = set(network_map.networks)

        self.state = MovementState(
            player=player,
            map=network_map,
            networks=networks,
            armies={t.id: map.get_node(t.id).value for t in map.nodes},
            actions=[],
        )

        self.add_children(
            [
                ExecuteIf(
                    "Networks left?",
                    [
                        Checker(
                            "movements",
                            "networks",
                            lambda s: len(s) == 0,
                        ),
                    ],
                    Retry(
                        "Check other networks?",
                        Sequence(
                            "Checking network",
                            True,
                            [
                                Selector(
                                    "movements",
                                    "networks",
                                    "network",
                                    with_replacement=False,
                                ),
                                Balancer(),
                                Checker(
                                    "movements",
                                    "networks",
                                    lambda s: len(s) == 0,
                                ),
                            ],
                        ),
                        len(networks),
                    )
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
        while self.status not in [Status.SUCCESS, Status.FAILURE]:
            debug(f"{self.name} ticking...")
            for _ in self.tick():
                debug("\n" + str(self))
        return self.state.actions
    
    def __str__(self):
        from py_trees.display import ascii_tree

        return ascii_tree(self, show_status=True)


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

    state = GameState.create_new_game(200, 2, 400)
    state.initialise()

    planner = MovementPlanner(player_id=1)
    plan = planner.construct_plan(state)
    debug(f"Constructed movement plan: {plan}")

    while not plan.is_done():
        step = plan.pop_step()
        debug(f"Executing movement step: {step}")
