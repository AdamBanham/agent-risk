from py_trees.behaviour import Behaviour
from py_trees.composites import Sequence
from py_trees.decorators import Retry
from py_trees.common import Status
import py_trees

from dataclasses import dataclass, field
from typing import Set

from risk.agents.plans import PlacementPlan, TroopPlacementStep, Planner
from risk.state import GameState
from risk.utils.logging import debug
from ..bases import (
    StateWithPlan, func_name,
    CheckPlan, Selector
)


@dataclass
class PlacementState(StateWithPlan):
    placements: int = 0
    territories: Set[int] = field(default_factory=Set)
    placed: int = 0
    terr: int = None
    troops: int = 0


class SelectTroops(Behaviour):
    """
    Selects a random amount of troops.
    """

    def __init__(self):
        super().__init__("Select Troops")

    def initialise(self):
        self.logger.debug(f"{self.__class__.__name__}::{self.name}::{func_name()}")
        self._ticks = 0
        self.placement = self.attach_blackboard_client("placement")
        self.placement.register_key(key="state", access=py_trees.common.Access.WRITE)
        return super().initialise()

    def update(self):
        state: PlacementState = self.placement.state
        state.troops = 1
        return Status.SUCCESS

    def terminate(self, new_status):
        return super().terminate(new_status)


class AddToPlan(Behaviour):
    """
    Adds a new step to the plan and updates internal state.
    """

    def __init__(self):
        super().__init__("Add to Plan")

    def initialise(self):
        self.logger.debug(f"{self.__class__.__name__}::{self.name}::{func_name()}")
        self._ticks = 0
        self.placement = self.attach_blackboard_client("placement")
        self.placement.register_key(key="state", access=py_trees.common.Access.WRITE)
        return super().initialise()

    def update(self):
        self.logger.debug(f"{self.__class__.__name__}::{self.name}::{func_name()}")
        state: PlacementState = self.placement.state
        step = TroopPlacementStep(state.terr, state.troops)
        state.placed += state.troops
        self.logger.debug(f"added:: {step}")
        state.plan.add_step(step)
        return Status.SUCCESS

    def terminate(self, new_status):
        return super().terminate(new_status)


class RandomPlacements(Sequence):

    def __init__(
        self, player: int,
        placements: int,
        territories: Set[int],
        game_state: GameState
    ):
        super().__init__(name="Placement Decision Making", memory=True)

        # Initialize the placement state for the blackboard
        self.placement_state = PlacementState(
            player=player, placements=placements, territories=territories
        )
        self.placement_state.plan = PlacementPlan(placements)

        checker = CheckPlan(game_state, "placements")
        select_terr = Selector("placements", "territories")
        select_troops = SelectTroops()
        add_to_plan = AddToPlan()

        # Add children directly to this sequence
        self.add_children(
            [
                Retry(
                    "Keep Building Plan",
                    Sequence(
                        "Find a step",
                        True,
                        [
                            select_terr,
                            select_troops,
                            add_to_plan,
                            checker,
                        ],
                    ),
                    placements,
                )
            ]
        )

    def initialise(self):
        self.logger.debug(f"{self.__class__.__name__}::{self.name}::{func_name()}")

        # Initialize blackboard with placement state
        self.placement = self.attach_blackboard_client("placement")
        self.placement.register_key(key="state", access=py_trees.common.Access.WRITE)
        self.placement.state = self.placement_state

        player_id = self.placement_state.player
        msg = f"Initialized blackboard with PlacementState for player {player_id}"
        self.logger.debug(msg)
        self.logger.debug(
            f"Total placements needed: {self.placement_state.placements - self.placement_state.placed}"
        )

        return super().initialise()

    def terminate(self, new_status):
        self.logger.debug(f"Placement completed with status: {new_status}")
        if hasattr(self, "placement_state") and self.placement_state:
            final_placed = self.placement_state.placed
            total_needed = self.placement_state.placements
            self.logger.debug(f"Final placement count: {final_placed}/{total_needed}")
        return super().terminate(new_status)

    @property
    def plan(self):
        """
        The current plan.
        """
        return self.placement_state.plan

    def construct_plan(self) -> PlacementPlan:
        """
        Constructs a plan for the phasement phase.
        """
        while self.status not in [Status.SUCCESS, Status.FAILURE]:
            debug(f"{self.name} ticking...")
            for _ in self.tick():
                debug("\n" + str(self))

        debug(str(self.plan))
        return self.plan

    def __str__(self):
        from py_trees.display import ascii_tree

        return ascii_tree(self, show_status=True)


class PlacementPlanner(Planner):
    """
    Implements random placement.
    """

    def __init__(self, player: int, placements: int):
        super().__init__()
        self.player = player 
        self.placements = placements

    def construct_plan(self, state):

        terrs = state.get_territories_owned_by(self.player)
        terrs = [t.id for t in terrs]

        placer = RandomPlacements(self.player, self.placements, terrs, state)
        plan = placer.construct_plan()

        return plan
    

if __name__ == "__main__":
    from py_trees import logging
    from risk.utils.logging import setLevel
    import random
    from logging import DEBUG
    setLevel(DEBUG)

    logging.level = logging.Level.DEBUG
    state = GameState.create_new_game(10, 2, 30)
    state.initialise()
    state.update_player_statistics()

    terrs = [t.id for t in state.get_territories_owned_by(0)]

    for _ in range(5):
        pick = random.randint(1, 5)
        placer = PlacementPlanner(0, pick)
        plan = placer.construct_plan(state)

        debug(str(plan))
        assert len(plan.steps) == pick, f"Expected plan to have {pick} placements"
        for step in plan.steps:
            debug(step) 

        input("continue?")