from ...plans import Planner, MovementPlan, RouteMovementStep, MovementStep
from risk.state import GameState
from risk.utils.movement import find_movement_sequence
from risk.utils.logging import debug

from risk.utils import map as mapping
from risk.utils.map import Graph
from dataclasses import dataclass, field
from typing import Set, Dict

from py_trees.composites import Sequence
from py_trees.decorators import Retry
from py_trees.common import Status
from ..bases import Selector, Checker, BuildAction
import py_trees


@dataclass
class MovementState:
    player: int
    networks: Set[int] = field(default_factory=set)
    network: int = None
    armies: Dict[int, int] = field(default_factory=dict)
    network_target: int = None
    map: mapping.NetworkGraph = None
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
        return MovementStep(
            source=state.src,
            destination=state.tgt,
            troops=state.amount
        )


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
            map=network_map,
            networks=set(network_map.networks),
            actions=[],
        )

        self.add_children(
            [
                Retry(
                    "Keep Placing",
                    Sequence(
                        "Check network",
                        False,
                        [
                            Selector(
                                "movements", "networks",
                                "network", with_replacement=False
                            ),
                            # balancer needs to go here
                            Checker(
                                "movements",
                                "networks",
                                lambda s: len(s) == 0,
                            ),
                        ],
                    ),
                    -1,
                )
            ]
        )

    def initialise(self):
        self.logger.debug(f"{self.__class__.__name__}::{self.name}")

        # Initialize blackboard with placement state
        self.placement = self.attach_blackboard_client("movements")
        self.placement.register_key(key="state", access=py_trees.common.Access.WRITE)
        self.placement.state = self.state

        player_id = self.state.player
        msg = f"Initialized blackboard with MovementState for player {player_id}"
        self.logger.debug(msg)
        msg = f"Total networks to process: {len(self.state.networks)}"
        self.logger.debug(msg)
        return super().initialise()

    def terminate(self, new_status):
        self.logger.debug(f"Movement completed with status: {new_status}")
        self.logger.debug(
            f"Final movement count: {len(self.state.actions)}"
        )
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

        for move in actions:
            debug(f"Planned movement: {move}")

            movements = find_movement_sequence(
                state.get_territory(move.source),
                state.get_territory(move.destination),
                move.troops
            )

            movements = [
                MovementStep(
                    source=move.src.id,
                    destination=move.tgt.id,
                    troops=move.troops
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