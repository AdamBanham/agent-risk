from py_trees.behaviour import Behaviour
from py_trees.composites import Sequence
from py_trees.common import Status, Access
import py_trees

from dataclasses import dataclass, field
from typing import List, Set

from risk.state.territory import Territory
from risk.agents.plans import MovementPlan, MovementStep, Planner
from risk.state import GameState
from ..bases import StateWithPlan, func_name, Selector
from risk.utils import map as mapping
from risk.utils.logging import debug


@dataclass
class MovementState(StateWithPlan):
    moves: int = 0
    territories: Set[int] = field(default_factory=set)
    safes: Set[int] = field(default_factory=set)
    moveable: Set[int] = field(default_factory=set)
    frontlines: Set[int] = field(default_factory=set)
    routes: List[MovementStep] = field(default_factory=list)
    route: MovementStep = field(default_factory=list)
    route_prob: float = 1.0
    terr: Territory = None
    troops: int = 0

class GenerateMovementRoute(Behaviour):
    """
    Generates a movement route and adds it to the plan.
    """

    def __init__(self, map: mapping.Graph, network_map: mapping.NetworkGraph):
        super().__init__("generate movement route")
        self.map = map
        self.network_map = network_map

    def initialise(self):
        self.logger.debug(f"{self.__class__.__name__}::{self.name}::{func_name()}")
        self.bd = self.attach_blackboard_client("movements")
        self.bd.register_key(key="state", access=Access.WRITE)
        self.logger.debug(
            f"{self.__class__.__name__}::{self.name}::{func_name()}::{len(self.bd.state.routes)}"
        )

    def update(self):
        state: MovementState = self.bd.state
        src = state.terr
        reachable_frontline = self.network_map.frontlines_in_network(
            mapping.get_value(self.network_map, src)
        )
        routes = []
        armies_to_move = mapping.get_value(self.map, src) - 1
        for target in reachable_frontline:
            if armies_to_move > 0:
                route = MovementStep(src, target.id, armies_to_move)
                if route:
                    routes.append(route)

        state.routes.extend(routes)
        return Status.SUCCESS

    def terminate(self, new_status):
        self.logger.debug(
            f"{self.__class__.__name__}::{self.name}::{func_name()}::{len(self.bd.state.routes)}"
        )
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
        self.placement = self.attach_blackboard_client("movements")
        self.placement.register_key(key="state", access=py_trees.common.Access.WRITE)
        return super().initialise()

    def update(self):
        self.logger.debug(f"{self.__class__.__name__}::{self.name}::{func_name()}")
        state: MovementState = self.placement.state
        step = state.route
        self.logger.debug(f"added:: {step}")
        state.plan.add_step(step)
        return Status.SUCCESS

    def terminate(self, new_status):
        return super().terminate(new_status)


class RandomMovements(Sequence):

    def __init__(
        self,
        player: int,
        moves: int,
        safes: Set[int],
        map: mapping.Graph,
        network_map: mapping.NetworkGraph,
    ):
        super().__init__(name="Movement Decision Making", memory=True)

        # Initialize the movement state for the blackboard
        self.movement_state = MovementState(
            player=player, moves=moves, territories=safes
        )
        self.movement_state.plan = MovementPlan(moves=moves)

        select_safe = Selector(
            "movements",
            "territories",
            condition=lambda t: mapping.get_value(map, t) > 1,
            with_replacement=False,
        )
        builder = GenerateMovementRoute(map, network_map)

        # Add children directly to this sequence
        self.add_children(
            [
                select_safe,
                builder,
                Selector("movements", "routes", "route"),
                AddToPlan(),
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
        while self.status not in [Status.SUCCESS, Status.FAILURE]:
            debug(f"{self.name} ticking...")
            for _ in self.tick():
                debug("\n" + str(self))

        debug(str(self.plan))
        return self.plan

    def __str__(self):
        from py_trees.display import ascii_tree

        return ascii_tree(self, show_status=True)
    

class MovementPlanner(Planner):
    """
    Implements random move from safe to frontline.
    """

    def __init__(self, player: int, moves: int):
        super().__init__()
        self.player = player 
        self.moves = moves

    def construct_plan(self, state):
        map = state.map.clone()
        network_map = mapping.construct_network_view(map, self.player)
        placer = RandomMovements(
            self.player, self.moves, 
            [t.id for t in network_map.nodes if t.safe],
            map, network_map
        )
        plan = placer.construct_plan()

        return plan


if __name__ == "__main__":
    from py_trees import logging
    from risk.utils.logging import setLevel
    from logging import DEBUG
    setLevel(DEBUG)

    logging.level = logging.Level.DEBUG

    for _ in range(10):
        state = GameState.create_new_game(30, 2, 100)
        state.initialise()
        state.update_player_statistics()

        map = state.map
        safe_map = mapping.construct_safe_view(map, 0)
        while len(safe_map.safe_nodes) < 1:
            state = GameState.create_new_game(30, 2, 100)
            state.initialise()
            state.update_player_statistics()
            map = state.map
            safe_map = mapping.construct_safe_view(map, 0)

        planner = MovementPlanner(
            0, 1
        )
        plan = planner.construct_plan(state)

        debug(plan)
        assert len(plan.steps) > 0, "Expected one movement"
        for step in plan.steps:
            debug(step)
            assert safe_map.get_node(step.source).value, "Expected move from safe node"
        
        input("continue?")
