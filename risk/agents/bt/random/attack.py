from py_trees.behaviour import Behaviour
from py_trees.composites import Sequence
from py_trees.decorators import Inverter, Retry
from py_trees.common import Status
import py_trees

from dataclasses import dataclass, field
from typing import Set
import random

from risk.agents.plans import AttackStep, AttackPlan, Planner
from risk.state import GameState
from risk.utils import map as mapping
from risk.utils.logging import debug

from ..bases import (
    StateWithPlan,
    func_name,
    CheckPlan,
    Selector,
    ExecuteIf,
    Checker
)


@dataclass
class AttackState(StateWithPlan):
    pos_attacks: int = 0
    territories: Set[int] = field(default_factory=set)
    adjacents: Set[int] = field(default_factory=set)
    terr: int = None
    adjacent: int = None
    troops: int = 0
    attack_prob: float = 0.5
    keep_going: bool = True


class ShouldAttack(CheckPlan):
    """
    Decides whether to add another attack to the plan.
    """

    def __init__(self, game_state, state_name):
        super().__init__(game_state, state_name)

    def update(self):
        state: AttackState = self.bd.state
        has_more_attacks = len(state.plan.steps) < state.pos_attacks
        if has_more_attacks:
            # plan was not acheived, i.e. there are more possible attacks
            pick = random.uniform(0.0, 1.0)
            state.keep_going = pick <= state.attack_prob
            if state.keep_going:
                return Status.FAILURE
        return Status.SUCCESS


class FindsAdjacent(Behaviour):
    """
    Finds adjacent territories for a given territory.
    """

    def __init__(self, map: mapping.Graph, attr_name):
        super().__init__("Select Adjacent")
        self.map = map
        self.attr_name = attr_name

    def initialise(self):
        self.logger.debug(f"{self.__class__.__name__}::{self.name}::{func_name()}")
        self._ticks = 0
        self.bd = self.attach_blackboard_client("attack")
        self.bd.register_key(key="state", access=py_trees.common.Access.WRITE)
        return super().initialise()

    def update(self):
        state: AttackState = self.bd.state
        terr = getattr(state, self.attr_name)
        state.adjacents = set(
            t.id
            for t in self.map.get_adjacent_nodes(terr)
            if t.owner != self.map.get_node(terr).owner
        )
        return Status.SUCCESS


class SelectTroops(Behaviour):
    """
    Selects a random amount of troops.
    """

    def __init__(self, map: mapping.Graph):
        super().__init__("Select Troops")
        self.map = map

    def initialise(self):
        self.logger.debug(f"{self.__class__.__name__}::{self.name}::{func_name()}")
        self._ticks = 0
        self.bd = self.attach_blackboard_client("attack")
        self.bd.register_key(key="state", access=py_trees.common.Access.WRITE)
        return super().initialise()

    def update(self):
        state: AttackState = self.bd.state
        terr = self.map.get_node(state.terr)
        troops = terr.value - 1
        if troops > 1:
            troops = random.randint(1, troops)
        state.troops = troops
        return Status.SUCCESS


class AddToPlan(Behaviour):
    """
    Adds a new step to the plan and updates internal state.
    """

    def __init__(self):
        super().__init__("Add to Plan")

    def initialise(self):
        self.logger.debug(f"{self.__class__.__name__}::{self.name}::{func_name()}")
        self._ticks = 0
        self.placement = self.attach_blackboard_client("attack")
        self.placement.register_key(key="state", access=py_trees.common.Access.WRITE)
        return super().initialise()

    def update(self):
        self.logger.debug(f"{self.__class__.__name__}::{self.name}::{func_name()}")
        state: AttackState = self.placement.state
        step = AttackStep(state.terr, state.adjacent, state.troops)
        self.logger.debug(f"added:: {step}")
        state.plan.add_step(step)
        return Status.SUCCESS

    def terminate(self, new_status):
        return super().terminate(new_status)


class RandomAttacks(Sequence):

    def __init__(
        self,
        player: int,
        pos_attacks: int,
        territories: Set[int],
        game_state: GameState,
        attack_prob: float = 0.5,
    ):
        super().__init__(name="Attack Decision Making", memory=True)

        # Initialize the placement state for the blackboard
        self.state = AttackState(
            player=player,
            pos_attacks=pos_attacks,
            territories=territories,
            attack_prob=attack_prob,
        )
        self.state.plan = AttackPlan(pos_attacks)
        self.state.keep_going = random.uniform(0, 1) <= attack_prob
        map = game_state.map.clone()

        checker = ShouldAttack(game_state, "attacks")
        select_terr = Selector(
            "attacks", "territories",
            condition=lambda n: mapping.get_value(map, n) > 2,
            with_replacement=False
        )
        find_adj = FindsAdjacent(map, "terr")
        select_adj = Selector("attacks", "adjacents", "adjacent")
        select_troops = SelectTroops(map)
        add_to_plan = AddToPlan()

        # Add children directly to this sequence
        self.add_children(
            [
                Retry(
                    "Keep Building Plan",
                    ExecuteIf(
                        "has terrs left",
                        [
                            Checker(
                                "attacks", "territories",
                                lambda terrs: len(terrs) == 0
                            ),
                            Checker(
                                "attacks", "keep_going",
                                lambda k: not k
                            )
                        ],
                        Sequence(
                            "Find a step",
                            True,
                            [
                                select_terr,
                                find_adj,
                                select_adj,
                                select_troops,
                                add_to_plan,
                                checker,
                            ],
                        )
                    ),
                    pos_attacks,
                )
            ]
        )

    def initialise(self):
        self.logger.debug(f"{self.__class__.__name__}::{self.name}::{func_name()}")

        # Initialize blackboard with placement state
        self.bd = self.attach_blackboard_client("attack")
        self.bd.register_key(key="state", access=py_trees.common.Access.WRITE)
        self.bd.state = self.state

        player_id = self.state.player
        msg = f"Initialized blackboard with PlacementState for player {player_id}"
        self.logger.debug(msg)
        self.logger.debug(f"Maximum attacks: {self.state.pos_attacks}")

        return super().initialise()

    def terminate(self, new_status):
        self.logger.debug(f"Placement completed with status: {new_status}")
        self.logger.debug(f"Final attack count: {len(self.state.plan)}")
        return super().terminate(new_status)

    @property
    def plan(self):
        """
        The current plan.
        """
        return self.state.plan

    def construct_plan(self) -> AttackPlan:
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
    

class AttackPlanner(Planner):
    """
    Planner for random attacks.
    """

    def __init__(self, player: int, max_attack: int, attack_prob):
        super().__init__()
        self.player = player
        self.max_attacks = max_attack
        self.attack_prob = attack_prob

    def construct_plan(self, state):
        map = state.map.clone()
        safe_map = mapping.construct_safe_view(map, self.player)

        planner = RandomAttacks(
            self.player,
            self.max_attacks,
            [
                t.id
                for t in safe_map.frontline_nodes
                if mapping.get_value(map, t.id) > 1
            ],
            state,
            self.attack_prob,
        )

        return planner.construct_plan()


if __name__ == "__main__":
    from py_trees import logging
    from risk.utils.logging import setLevel
    from logging import DEBUG
    setLevel(DEBUG)

    logging.level = logging.Level.DEBUG
    state = GameState.create_new_game(10, 2, 30)
    state.initialise()
    state.update_player_statistics()

    map = state.map 
    safe_map = mapping.construct_safe_view(map, 0)


    for _ in range(10):
        pick = random.randint(1, 10)
        placer = AttackPlanner(
            0,
            pick,
            0.85
        )
        plan = placer.construct_plan(state)

        assert len(plan.steps) <= pick, f"Expected less than {pick} steps"
        for step in plan.steps:
            print(step)

        input("continue?")
