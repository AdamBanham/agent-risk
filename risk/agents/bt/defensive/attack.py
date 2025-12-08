from ...plans import Planner, AttackPlan, AttackStep
from risk.state import GameState
from risk.utils.logging import debug
from risk.utils import map as mapping

from ..bases import Checker, Selector, BuildAction, ExecuteIf
from py_trees.behaviour import Behaviour
from py_trees.composites import Sequence
from py_trees.decorators import Retry
from py_trees.common import Status, Access

from dataclasses import dataclass, field
from typing import Set, Collection


@dataclass
class AttackState:
    player: int
    fronts: Set[int] = field(default_factory=set)
    adjacents: Set[int] = None
    map: mapping.Graph[mapping.Node, mapping.Edge] = None
    actions: list = field(default_factory=list)
    attacker: int = None
    defender: int = None
    troops: int = 0


class FindAdjacents(Behaviour):
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
        atk = state.map.get_node(state.attacker)
        atk_army = state.map.get_node(state.attacker).value
        debug(f"Attacker armies: {atk_army}")

        # Find adjacent enemy territories that are consider to be
        # safe attacks
        def safe(o: mapping.Node):
            return (atk_army - 1) > max(o.value + 5, o.value * 3)

        adjacents = set(
            o.id
            for o in state.map.get_adjacent_nodes(state.attacker)
            if o.owner != atk.owner and safe(o)
        )
        state.adjacents = adjacents
        debug(f"Found adjacents: {adjacents}")
        return Status.SUCCESS

    def terminate(self, new_status):
        return super().terminate(new_status)


class FindArmies(Behaviour):
    """
    Attempts to find a safe number of armies to attack with.
    """

    def __init__(self):
        super().__init__("Find Armies")

    def initialise(self):
        self.bd = self.attach_blackboard_client("attacks")
        self.bd.register_key(key="state", access=Access.WRITE)
        return super().initialise()

    def update(self):
        state: AttackState = self.bd.state
        adj = state.map.get_node(state.defender)
        adj_army = adj.value
        debug(f"Defender armies: {adj_army}")
        # For simplicity, we just set a fixed number of troops to attack with
        state.troops = max(adj_army + 5, adj_army * 3)
        debug(f"Selected {state.troops} troops for attack")
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
        # For simplicity, we just pick the first adjacent enemy territory
        return AttackStep(
            attacker=state.attacker,
            defender=state.defender,
            troops=state.troops,
        )


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

        fronts = mapping.construct_safe_view(map, player).frontline_nodes

        self.state = AttackState(
            player=player,
            fronts=set(
                t.id for t in fronts
            ),
            map=map,
            actions=[],
        )

        self.add_children(
            [
                Retry(
                    "Keep Attacking",
                    Sequence(
                        "Find Attack",
                        True,
                        [
                            ExecuteIf(
                                "No Fronts Left",
                                [
                                    Checker(
                                        "attacks",
                                        "fronts",
                                        lambda s: len(s) == 0,
                                    )
                                ],
                                Sequence(
                                    "Build Attack",
                                    True,
                                    [
                                        Selector(
                                            "attacks",
                                            "fronts",
                                            "attacker",
                                            with_replacement=False,
                                        ),
                                        FindAdjacents(),
                                        Selector("attacks", "adjacents", "defender"),
                                        FindArmies(),
                                        BuildAttackAction(),
                                        Checker(
                                            "attacks",
                                            "actions",
                                            lambda s: len(s) != max_attacks,
                                        ),
                                        Checker(
                                            "attacks",
                                            "fronts",
                                            lambda s: len(s) == 0,
                                        ),
                                    ],
                                ),
                            )
                        ],
                    ),
                    len(fronts),
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
        while self.status not in [Status.SUCCESS, Status.FAILURE]:
            debug(f"{self.name} ticking...")
            for _ in self.tick():
                debug("\n" + str(self))
        return self.state.actions
    
    def __str__(self):
        from py_trees.display import ascii_tree

        return ascii_tree(self, show_status=True)


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
    from logging import DEBUG, INFO
    from risk.utils.logging import setLevel, info
    import random

    setLevel(INFO)

    state = GameState.create_new_game(50, 2, 150)
    state.initialise()

    nodes = state.get_territories_owned_by(state.current_player_id)
    terr = random.choice(nodes)
    terr.armies += 20

    state.update_player_statistics()

    info("Current Game State:")
    info(state.map)

    planner = AttackPlanner(
        state.current_player_id, max_attacks=5, attack_probability=0.8
    )
    plan = planner.construct_plan(state)

    def safe(attacker, defender):
        attacker = state.get_territory(attacker)
        defender = state.get_territory(defender)
        return (attacker.armies - 1) > max(defender.armies + 5, defender.armies * 3)

    info(f"Constructed Placement Plan: {plan}")
    attacked = False
    while not plan.is_done():
        step: AttackStep = plan.pop_step()
        attacked = attacked or terr.id == step.attacker
        info(f"Executing Step: {step}")
        assert safe(step.attacker, step.defender), "Attack is not safe"

    assert attacked, "No attacks were planned from the selected territory"
