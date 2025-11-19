from py_trees.behaviour import Behaviour
from py_trees.composites import Sequence
from py_trees.decorators import Inverter, Retry
from py_trees.common import Status, Access
import py_trees

from dataclasses import dataclass, field
from typing import List, Set
import random

from risk.state.territory import Territory
from risk.agents.plans import MovementPlan, RouteMovementStep, MovementStep
from risk.state import GameState
from risk.utils.movement import Movement, find_movement_sequence
from risk.utils.movement import find_safe_frontline_territories
from risk.utils.movement import find_connected_frontline_territories
from ..bases import StateWithPlan, func_name, CheckPlan, Selector


@dataclass
class MovementState(StateWithPlan):
    moves: int = 0
    territories: Set[int] = field(default_factory=set)
    safes: Set[int] = field(default_factory=set)
    moveable: Set[int] = field(default_factory=set)
    frontlines: Set[int] = field(default_factory=set)
    routes: List[List[Movement]] = field(default_factory=list)
    route: List[Movement] = field(default_factory=list)
    route_prob: float = 1.0
    terr: Territory = None
    troops: int = 0


class ShouldRoute(CheckPlan):
    """
    Decides whether to add another attack to the plan.
    """

    def __init__(self, game_state, state_name):
        super().__init__(game_state, state_name)

    def update(self):
        status = super().update()
        if status == Status.FAILURE:
            state: Movement = self.bd.state
            current_chance = (100 / state.moves) * len(state.plan)
            current_chance = current_chance / 100
            current_chance = min(1, current_chance)
            current_chance = 1 - current_chance
            state.route_prob = current_chance
            if len(state.plan) < state.moves:
                pick = random.uniform(0.0, 1.0)
                if pick <= state.route_prob:
                    return Status.SUCCESS
        return status


class FindSafeFrontlines(Behaviour):
    """
    Finds safes and frontline territories for movement.
    """

    def __init__(self, game_state: GameState):
        super().__init__("find front and safe terrs")
        self.game_state = game_state

    def initialise(self):
        self.logger.debug(f"{self.__class__.__name__}::{self.name}::{func_name()}")
        self.bd = self.attach_blackboard_client("movements")
        self.bd.register_key(key="state", access=Access.READ)

    def update(self):
        state: MovementState = self.bd.state
        safe, frontline = find_safe_frontline_territories(
            game_state=self.game_state, player_id=state.player
        )
        state.safes = set(t for t in safe)
        state.frontlines = set(t for t in frontline)

        if not state.safes:
            return Status.FAILURE
        return Status.SUCCESS


class FilterForMoveable(Selector):
    """
    Filters safe territories for moveable ones.
    """

    def __init__(self, state_name, attr_name: str, put_name: str):
        super().__init__(state_name, attr_name, put_name)

    def update(self):
        state: MovementState = self.bd.state
        moveable = [t for t in state.safes if t.armies > 1]
        state.moveable = set(moveable)
        if not state.moveable:
            return Status.FAILURE
        return Status.SUCCESS


class PopMovable(Selector):
    """
    Pops a territory from moveable territories.
    """

    def __init__(self, state_name: str, attr_name: str, put_name: str = "terr"):
        super().__init__(state_name, attr_name, put_name)

    def initialise(self):
        super().initialise()
        self.logger.debug(
            f"{self.__class__.__name__}::{self.name}::{func_name()}::{len(self.bd.state.moveable)}"
        )

    def update(self):
        state: MovementState = self.bd.state
        if not state.moveable:
            return Status.FAILURE
        terr = random.choice(list(state.moveable))
        state.terr = terr
        state.moveable = state.moveable - {terr}
        return Status.SUCCESS


class GenerateMovementRoute(Behaviour):
    """
    Generates a movement route and adds it to the plan.
    """

    def __init__(self, game_state: GameState):
        super().__init__("generate movement route")
        self.game_state = game_state

    def initialise(self):
        self.logger.debug(f"{self.__class__.__name__}::{self.name}::{func_name()}")
        self.bd = self.attach_blackboard_client("movements")
        self.bd.register_key(key="state", access=Access.WRITE)
        self.logger.debug(
            f"{self.__class__.__name__}::{self.name}::{func_name()}::{len(self.bd.state.routes)}"
        )

    def update(self):
        state: MovementState = self.bd.state
        reachable_frontline = find_connected_frontline_territories(
            state.terr, state.frontlines, list(state.safes | state.frontlines)
        )
        routes = []
        for target in reachable_frontline:
            armies_to_move = state.terr.armies - 1
            if armies_to_move > 0:
                route = find_movement_sequence(state.terr, target, armies_to_move)
                if route:
                    routes.append(route)

        state.routes.extend(routes)
        return Status.SUCCESS

    def terminate(self, new_status):
        self.logger.debug(
            f"{self.__class__.__name__}::{self.name}::{func_name()}::{len(self.bd.state.routes)}"
        )
        return super().terminate(new_status)


class BuildMovementRoute(Sequence):
    """
    Finds a movement route from a safe territory to a frontline territory.
    """

    def __init__(self, game_state: GameState):
        super().__init__("find movement route", memory=False)
        self.game_state = game_state
        self.add_children(
            [
                Retry(
                    "building routes",
                    Inverter(
                        "while we have moveable terrs",
                        Sequence(
                            "routes for moveable",
                            False,
                            [
                                PopMovable("movements", "moveable", "terr"),
                                GenerateMovementRoute(game_state),
                            ],
                        ),
                    ),
                    -1,
                )
            ]
        )


class AddToPlan(Behaviour):
    """
    Adds a new step to the plan and updates internal state.
    """

    def __init__(self):
        super().__init__("Add to Plan")

    def initialise(self):
        self.logger.debug(f"{self.__class__.__name__}::{self.name}::{func_name()}")
        self._ticks = 0
        self.placement = self.attach_blackboard_client("movements")
        self.placement.register_key(key="state", access=py_trees.common.Access.WRITE)
        return super().initialise()

    def update(self):
        self.logger.debug(f"{self.__class__.__name__}::{self.name}::{func_name()}")
        state: MovementState = self.placement.state
        steps = []
        amount = state.route[0].amount
        for move in state.route:
            steps.append(
                MovementStep(
                    source=move.src.id,
                    destination=move.tgt.id,
                    troops=move.amount,
                )
            )
            if move.amount != amount:
                raise ValueError("Inconsistent troop amounts in movement route.")
        step = RouteMovementStep(steps, amount)
        self.logger.debug(f"added:: {step}")
        state.plan.add_step(step)
        return Status.SUCCESS

    def terminate(self, new_status):
        return super().terminate(new_status)


class RandomMovements(Sequence):

    def __init__(
        self, player: int, moves: int, territories: Set[int], game_state: GameState
    ):
        super().__init__(name="Movement Decision Making", memory=False)

        # Initialize the movement state for the blackboard
        self.movement_state = MovementState(
            player=player, moves=moves, territories=territories
        )
        self.movement_state.plan = MovementPlan(moves=moves)

        checker = ShouldRoute(game_state, "movements")
        finder = FindSafeFrontlines(game_state)
        filter = FilterForMoveable("movements", "safes", "moveable")
        builder = BuildMovementRoute(game_state)

        # Add children directly to this sequence
        self.add_children(
            [
                Retry(
                    "Keep Building Plan",
                    Inverter(
                        "while routing?",
                        Sequence(
                            "Create route",
                            False,
                            [
                                checker,
                                finder,
                                filter,
                                Inverter("found routes", builder),
                                Selector("movements", "routes", "route"),
                                AddToPlan(),
                            ],
                        ),
                    ),
                    -1,
                )
            ]
        )

    def initialise(self):
        self.logger.debug(f"{self.__class__.__name__}::{self.name}::{func_name()}")

        # Initialize blackboard with movement state
        self.movement = self.attach_blackboard_client("movements")
        self.movement.register_key(key="state", access=py_trees.common.Access.WRITE)
        self.movement.state = self.movement_state

        player_id = self.movement_state.player
        msg = f"Initialized blackboard with MovementState for player {player_id}"
        self.logger.debug(msg)
        self.logger.debug(f"Maximum movements needed: {self.movement_state.moves}")

        return super().initialise()

    def terminate(self, new_status):
        self.logger.debug(f"Movement completed with status: {new_status}")
        if hasattr(self, "movement_state") and self.movement_state:
            final_moved = len(self.movement_state.plan)
            self.logger.debug(f"Final movement count: {final_moved}")
        return super().terminate(new_status)

    @property
    def plan(self):
        """
        The current plan.
        """
        return self.movement_state.plan

    def construct_plan(self) -> MovementPlan:
        """
        Constructs a plan for the movement phase.
        """
        while self.status != Status.SUCCESS:
            self.tick_once()
        return self.plan

    def __str__(self):
        from py_trees.display import ascii_tree

        return ascii_tree(self)


if __name__ == "__main__":
    from py_trees import logging

    logging.level = logging.Level.DEBUG
    state = GameState.create_new_game(30, 2, 100)
    state.initialise()

    terrs = [t.id for t in state.get_territories_owned_by(0)]

    placer = RandomMovements(0, 3, terrs, state)

    print(str(placer))

    plan = placer.construct_plan()

    print(str(plan))
    print(str(repr(plan.steps)))
