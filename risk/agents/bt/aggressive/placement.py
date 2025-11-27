from ...plans import Planner, PlacementPlan, TroopPlacementStep
from risk.state import GameState
from risk.utils.logging import debug
from risk.utils import map as mapping
from risk.utils.map import Graph
from dataclasses import dataclass, field
from typing import Set, Dict

from py_trees.composites import Sequence
from py_trees.decorators import Retry
from py_trees.common import Status
from ..bases import (
    Checker,
    BuildAction,
)
from .bases import BuildAndFindBestPotential
import py_trees


@dataclass
class PlacementState:
    player: int
    terr: int = None
    frontlines: Set[int] = field(default_factory=set)
    front: int = None
    potential: float = 0.0
    attack_potential: Dict[int, float] = field(default_factory=dict)
    actions: list = field(default_factory=list)


class BuildPlacementAction(BuildAction):
    """
    Builds a placement action from selected territory and troops.
    """

    def __init__(self):
        super().__init__("Build Placement Action", "placements", "actions")

    def build_step(self, state: PlacementState) -> TroopPlacementStep:
        return TroopPlacementStep(territory=state.terr, troops=1)


class Placements(Sequence):
    """
    Behaviour tree for deciding placements. Selects from
    the top n strongest frontlines to place troops.
    """

    def __init__(self, player: int, placements: int, map: Graph):
        super().__init__("Defensive Placement", True)

        self.placements_req = placements
        safe_map = mapping.construct_safe_view(map, player)

        self.state = PlacementState(
            player=player,
            frontlines=set(t.id for t in safe_map.frontline_nodes),
            actions=[],
        )

        self.add_children(
            [
                BuildAndFindBestPotential(
                    "placements",
                    "terr",
                    map
                ),
                Retry(
                    "Placing",
                    Sequence(
                        "Placement",
                        False,
                        [
                            BuildPlacementAction(),
                            Checker(
                                "placements",
                                "actions",
                                lambda s: len(s) == self.placements_req,
                            ),
                        ],
                    ),
                    placements,
                ),
            ]
        )

    def initialise(self):
        debug(f"{self.__class__.__name__}::{self.name}")

        # Initialize blackboard with placement state
        self.placement = self.attach_blackboard_client("placements")
        self.placement.register_key(key="state", access=py_trees.common.Access.WRITE)
        self.placement.state = self.state

        player_id = self.state.player
        msg = f"Initialized blackboard with PlacementState for player {player_id}"
        debug(msg)
        debug(
            f"Total placements needed: {self.placements_req - len(self.state.actions)}"
        )

        return super().initialise()

    def terminate(self, new_status):
        debug(f"Placement completed with status: {new_status}")
        debug(
            f"Final placement count: {len(self.state.actions)}/{self.placements_req}"
        )
        return super().terminate(new_status)

    def construct(self) -> PlacementPlan:
        """
        Constructs a plan for the phasement phase.
        """
        from time import sleep

        while self.status != Status.SUCCESS:
            self.tick_once()
            # sleep(2)
        return self.state.actions


class PlacementPlanner(Planner):
    """
    A planner that creates an attack plan based on the current game state.
    """

    def __init__(
        self,
        player_id: int,
        placements: int = None,
    ):
        super().__init__()
        self.player_id = player_id
        self.placements = placements

    def construct_plan(self, state: GameState) -> PlacementPlan:

        if self.placements is None:
            placements = state.placements_left
        else:
            placements = self.placements

        current_map = state.map
        constructor = Placements(
            player=self.player_id,
            placements=placements,
            map=current_map,
        )

        plan = PlacementPlan(state.placements_left)

        for action in constructor.construct():
            plan.add_step(action)

        return plan


if __name__ == "__main__":
    from logging import DEBUG
    from risk.utils.logging import setLevel

    setLevel(DEBUG)

    from py_trees import logging

    logging.level = logging.Level.DEBUG

    state = GameState.create_new_game(10, 2, 30)
    state.initialise()

    safe_map = mapping.construct_safe_view(state.map, state.current_player_id)

    planner = PlacementPlanner(player_id=state.current_player_id, placements=5)
    plan = planner.construct_plan(state)

    debug(f"Constructed Placement Plan: {plan}")
    terr = None
    while not plan.is_done():
        step = plan.pop_step()
        assert not safe_map.is_safe(step.territory), "Placed on safe territory"
        debug(f"Executing Step: {step}")

        if terr is None:
            terr = step.territory
        else:
            assert terr == step.territory, "Placed on multiple territories"
