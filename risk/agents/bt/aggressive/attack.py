from ...plans import Planner, AttackPlan, AttackStep
from risk.state import GameState
from risk.utils.logging import debug
from risk.utils import map as mapping

from ..bases import Checker, BuildAction, Compute, ExecuteIf
from .bases import BuildAndFindBestPotential
from py_trees.behaviour import Behaviour
from py_trees.composites import Sequence
from py_trees.decorators import Retry
from py_trees.common import Status, Access

from dataclasses import dataclass, field
from typing import Set, Collection, Dict
from copy import deepcopy


@dataclass
class AttackState:
    player: int
    frontlines: Set[int] = field(default_factory=set)
    front: int = None
    potential: float = 0.0
    attack_potential: Dict[int, float] = field(default_factory=dict)
    map: mapping.Graph[mapping.Node, mapping.Edge] = None
    actions: list = field(default_factory=list)
    attacker: int = None
    defender: int = None
    troops: int = -1
    attacked: Set[int] = field(default_factory=set)
    had_safe: bool = None


class ComputeTroops(Compute):
    """
    Computes the attacker territory for the selected front.
    """

    def __init__(self):
        super().__init__("attacker", "troops")
        self.map = map

    def compute(self, state) -> int:
        debug(f"Selected front for attack: {state.attacker}")
        if state.troops < 0:
            armies = state.map.get_node(state.attacker).value
            return armies - 1
        else:
            return state.troops // 2


class FindWeakest(Behaviour):
    """
    Finds the adjacent enemy territories for the selected attacker territory.
    """

    def __init__(self):
        super().__init__("Find Adjacent Enemies")

    def initialise(self):
        self.bd = self.attach_blackboard_client("attacks")
        self.bd.register_key(key="state", access=Access.WRITE)
        return super().initialise()

    def update(self):
        state: AttackState = self.bd.state
        adjacents = state.map.get_adjacent_nodes(state.attacker)
        adjacents = [o for o in adjacents if o.owner != state.player]

        if not adjacents:
            debug("No adjacent enemies found")
            return Status.INVALID

        adjacents = sorted(adjacents, key=lambda o: o.value)
        weakest = adjacents[0]
        state.defender = weakest.id
        debug(f"Found weakest: {weakest}")
        return Status.SUCCESS

    def terminate(self, new_status):
        return super().terminate(new_status)


class BuildAttackAction(BuildAction):
    """
    Builds an attack action from selected territory and target.
    """

    def __init__(self):
        super().__init__("Build Attack Action", "attacks", "actions")

    def build_step(self, state: AttackState) -> AttackStep:

        step = AttackStep(
            attacker=state.attacker,
            defender=state.defender,
            troops=state.troops,
        )

        state.map.get_node(state.attacker).value -= state.troops
        state.map.get_node(state.defender).value = state.troops
        state.map.get_node(state.defender).owner = state.player

        state.attacker = state.defender
        state.defender = None

        return step


class ComputeHasSafe(Compute):
    """
    Computes whether selected front has a safe attack.
    """

    def __init__(self):
        super().__init__("attacks", "had_safe")

    def compute(self, state: AttackState):

        attacker = state.troops
        had_safe = False
        for adj in state.map.get_adjacent_nodes(state.front):
            safe_troops = max(adj.value + 5, adj.value * 3)
            had_safe = had_safe or attacker >= safe_troops
        return had_safe
        

    

class Attacks(Sequence):
    """
    Decides what frontline territories should attack based on
    their strength against neighboring enemy territories.
    """

    def __init__(self, player: int, max_attacks: int, map: mapping.Graph):
        super().__init__(
            "Plan Attacks",
            True,
        )

        self.state = AttackState(
            player=player,
            frontlines=set(
                t.id for t in mapping.construct_safe_view(map, player).frontline_nodes
            ),
            map=deepcopy(map),
            actions=[],
        )

        self.add_children(
            [
                BuildAndFindBestPotential("attacks", "attacker", map),
                ComputeTroops(),
                ComputeHasSafe(),
                ExecuteIf(
                    "Execute only if first attack can be safe",
                    [
                        Checker(
                            "attacks",
                            "had_safe",
                            lambda c: not c
                        )
                    ],
                    Retry(
                        "Keep Attacking",
                        Sequence(
                            "Building Attack",
                            False,
                            [
                                FindWeakest(),
                                BuildAttackAction(),
                                ComputeTroops(),
                                Checker(
                                    "attacks",
                                    "troops",
                                    lambda s: s < 2,
                                ),
                            ],
                        ),
                        max_attacks,
                    ),
                )
            ]
        )

    def initialise(self):
        self.bd = self.attach_blackboard_client("attacks")
        self.bd.register_key(key="state", access=Access.WRITE)
        self.bd.state = self.state
        return super().initialise()

    def terminate(self, new_status):
        return super().terminate(new_status)

    def construct(self) -> Collection[AttackStep]:
        """
        Constructs a plan for the attack phase.
        """
        while self.status != Status.SUCCESS:
            self.tick_once()
        return reversed(self.state.actions)


class AttackPlanner(Planner):
    """
    A planner that creates an attack plan based on the current game state.
    """

    def __init__(
        self,
        player_id: int,
        max_attacks: int,
        attack_probability: float = 0.5,
    ):
        super().__init__()
        self.player_id = player_id
        self.max_attacks = max_attacks
        self.attack_probability = attack_probability

    def construct_plan(self, state: GameState) -> AttackPlan:
        attack_plan = AttackPlan(self.max_attacks)

        constructor = Attacks(
            player=self.player_id,
            max_attacks=self.max_attacks,
            map=state.map,
        )

        for step in constructor.construct():
            attack_plan.add_step(step)

        return attack_plan


if __name__ == "__main__":
    from logging import DEBUG
    from risk.utils.logging import setLevel

    setLevel(DEBUG)

    state = GameState.create_new_game(25, 2, 150)
    state.initialise()

    state.update_player_statistics()

    planner = AttackPlanner(
        state.current_player_id, max_attacks=5, attack_probability=0.5
    )
    plan = planner.construct_plan(state)

    debug(f"Constructed Placement Plan: {plan}")
    attacked = False
    armies = None
    while not plan.is_done():
        step: AttackStep = plan.pop_step()
        debug(f"Executing Step: {step}")

        if armies is None:
            armies = step.troops
        else:
            assert armies // 2 == step.troops, "Attack amounts are not halving"
            armies = step.troops
