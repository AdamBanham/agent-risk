from py_trees.behaviour import Behaviour
from py_trees.composites import Sequence
from py_trees.decorators import Inverter, Retry
from py_trees.common import Status
import py_trees
import inspect

from dataclasses import dataclass, field
from typing import Set
import random

from risk.state.territory import Territory
from risk.agents.plans import PlacementPlan, TroopPlacementStep


def func_name():
    return inspect.stack()[1].function


@dataclass
class PlacementState:
    player: int
    placements: int
    territories: Set[int] = field(default_factory=Set)
    placed: int = 0
    terr: Territory = None
    troops: int = 0
    plan: PlacementPlan = None


class CheckPlan(Behaviour):

    def __init__(self, game_state):
        super().__init__("Check Plan")
        self.game_state = game_state

    def initialise(self):
        self.logger.debug(f"{self.__class__.__name__}::{self.name}::{func_name()}")
        self.placement = self.attach_blackboard_client("placement")
        self.placement.register_key(key="state", access=py_trees.common.Access.READ)

    def update(self):
        self.logger.debug(f"{self.__class__.__name__}::{self.name}::{func_name()}")
        # Check if we have placements remaining
        state: PlacementState = self.placement.state
        if not state.plan.goal_achieved(self.game_state):
            remaining = state.placements - state.placed
            self.logger.debug(f"Placements remaining: {remaining}")
            return Status.SUCCESS
        else:
            self.logger.debug("Plan Acheived.")
            return Status.FAILURE

    def terminate(self, new_status):
        self.logger.debug(f"{self.__class__.__name__}::{self.name}::{func_name()}")
        return super().terminate(new_status)


class SelectTerritory(Behaviour):
    """
    Selects a random territory.
    """

    def __init__(self):
        super().__init__("Select Territory")

    def initialise(self):
        self.logger.debug(f"{self.__class__.__name__}::{self.name}::{func_name()}")
        self._ticks = 0
        self.placement = self.attach_blackboard_client("placement")
        self.placement.register_key(key="state", access=py_trees.common.Access.WRITE)
        return super().initialise()

    def update(self):
        state: PlacementState = self.placement.state
        state.terr = random.choice(state.territories)
        return Status.SUCCESS

    def terminate(self, new_status):
        return super().terminate(new_status)


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
        state.troops = random.choice(
            list(range(1, 1 + state.placements - state.placed))
        )
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


class Placement(Sequence):

    def __init__(self, player: int, placements: int, territories: Set[int], game_state):
        super().__init__(name="Placement Decision Making", memory=False)

        # Initialize the placement state for the blackboard
        self.placement_state = PlacementState(
            player=player, placements=placements, territories=territories
        )
        self.placement_state.plan = PlacementPlan(placements)

        checker = CheckPlan(game_state)
        select_terr = SelectTerritory()
        select_troops = SelectTroops()
        add_to_plan = AddToPlan()

        # Add children directly to this sequence
        self.add_children(
            [
                Retry(
                    "Keep Building Plan",
                    Inverter(
                        "Until all placements occur",
                        Sequence(
                            "Find a step",
                            False,
                            [
                                checker,
                                select_terr,
                                select_troops,
                                add_to_plan,
                                Inverter("keep going?", CheckPlan(game_state)),
                            ],
                        ),
                    ),
                    -1,
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
        self.logger.debug(f"Total placements needed: {self.placement_state.placements}")

        return super().initialise()

    def update(self):
        # Let the sequence handle the child execution
        return super().update()

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

    def construct_plan(self):
        """
        Constructs a plan for the phasement phase.
        """
        while self.status != Status.FAILURE:
            print("... building ...")
            self.tick_once()
            print("... added step ...")

    def __str__(self):
        from py_trees.display import ascii_tree

        return ascii_tree(self)


if __name__ == "__main__":
    from risk.state import GameState

    state = GameState.create_new_game(10, 2, 10)
    state.initialise()

    terrs = [t.id for t in state.get_territories_owned_by(1)]

    print(f"territories :: {terrs}")

    root = Placement(1, 10, terrs, state)

    print(root)

    root.construct_plan()

    print(str(root.plan))
