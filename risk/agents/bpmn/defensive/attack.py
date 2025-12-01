from ...plans import Planner, AttackPlan, AttackStep
from risk.utils.logging import info
from risk.utils import map as mapping
from ..bases import ExpressiveSimProblem

import random
from typing import Set

from simpn.simulator import SimTokenValue, SimToken
from simpn.helpers import Place, BPMN


def construct_problem(fronts: Set[int], map: mapping.Graph, attacks: int):

    problem = ExpressiveSimProblem()

    class Start(Place):
        model = problem
        name = "start"
        amount = 0

    start = problem.var("start")
    start.put(
        SimTokenValue(
            "start-1",
            fronts=fronts,
            map=map,
            attack_left=attacks,
            front=None,
            attacks=set(),
        )
    )

    class Planner(BPMN):
        model = problem
        type = "resource-pool"
        name = "planner"
        amount = 0

    planner = problem.var("planner")
    planner.put(SimTokenValue("planner-0", actions=[]))

    class HasFrontsXorSplit(BPMN):
        model = problem
        type = "gat-ex-split"
        incoming = ["start"]
        outgoing = ["ready", "finishing"]
        name = "Has Fronts"

        def choice(token: SimTokenValue):
            if len(token.fronts) > 0:
                return [SimToken(token), None]
            else:
                return [None, SimToken(token)]

    class ReworkXorJoin(BPMN):
        model = problem
        type = "gat-ex-join"
        incoming = ["ready", "rework"]
        outgoing = ["selecting"]
        name = "Rework Join"

    class Pick(BPMN):
        model = problem
        type = "task"
        incoming = ["selecting", "planner"]
        outgoing = ["checking", "planner"]
        name = "Pick a Front"

        def behaviour(val: SimTokenValue, res):
            val = val.clone()

            val.front = random.choice(list(val.fronts))
            return [SimToken((val, res))]

    class Checking(BPMN):
        model = problem
        type = "task"
        incoming = ["checking", "planner"]
        outgoing = ["checked", "planner"]
        name = "Check Front"

        def behaviour(val, res):
            fnode = val.map.get_node(val.front)
            has_attack = False
            attacks = set()
            for adj in val.map.get_adjacent_nodes(val.front):
                if adj.owner != fnode.owner:
                    safe_troop_count = max(adj.value + 5, adj.value * 3)
                    if (fnode.value - 1) > safe_troop_count:
                        has_attack = True
                        attacks.add(adj.id)
            if has_attack:
                val = val.clone()
                val.attacks = attacks
            return [SimToken((val, res))]

    class AttackXorSplit(BPMN):
        model = problem
        type = "gat-ex-split"
        incoming = ["checked"]
        outgoing = ["filter", "attack"]
        name = "Attack Split"

        def choice(token: SimTokenValue):
            if len(token.attacks) > 0:
                return [None, SimToken(token)]
            else:
                return [SimToken(token), None]

    class Filter(BPMN):
        model = problem
        type = "task"
        incoming = ["filter", "planner"]
        outgoing = ["join-1-a", "planner"]
        name = "Filter Front"

        def behaviour(val, res):
            val = val.clone()
            val.fronts = val.fronts.difference(set([val.front]))
            val.front = None
            return [SimToken((val, res))]

    class Attack(BPMN):
        model = problem
        type = "task"
        incoming = ["attack", "planner"]
        outgoing = ["join-1-b", "planner"]
        name = "Build Attack"

        def behaviour(val, res):
            res = res.clone()
            defender = random.choice(list(val.attacks))
            defender = val.map.get_node(defender)
            safe_troop_count = max(defender.value + 5, defender.value * 3)
            res.actions.append(
                AttackStep(
                    attacker=val.front,
                    defender=defender.id,
                    troops=safe_troop_count,
                )
            )
            info(f"Added attack")

            val = val.clone()
            val.attacks = set()
            val.fronts = val.fronts.difference(set([val.front]))
            val.front = None
            val.attack_left -= 1
            return [SimToken((val, res))]

    class ActionXorJoin(BPMN):
        model = problem
        type = "gat-ex-join"
        incoming = ["join-1-a", "join-1-b"]
        outgoing = ["stepped"]
        name = "Join after Action"

    class ReworkXorSplit(BPMN):
        model = problem
        type = "gat-ex-split"
        incoming = ["stepped"]
        outgoing = ["rework", "finishing"]
        name = "Rework?"

        def choice(token: SimTokenValue):
            if len(token.fronts) > 0 and token.attack_left > 0:
                return [SimToken(token), None]
            else:
                return [None, SimToken(token)]

    class End(BPMN):
        model = problem
        type = "end"
        name = "end"
        incoming = ["finishing"]

    return problem


class AttackPlanner(Planner):
    """
    Planner for aggressive deploying attacks.
    """

    def __init__(self, player: int, max_attacks: int):
        super().__init__()
        self.player = player
        self.max_attacks = max_attacks

    def construct_plan(self, state):
        plan = AttackPlan(self.max_attacks)

        safemap = mapping.construct_safe_view(state.map, self.player)

        problem = construct_problem(
            set(f.id for f in safemap.frontline_nodes),
            state.map.clone(),
            self.max_attacks,
        )

        while problem.step():
            pass

        planner = problem.var("planner")
        actions = planner.marking[0].value.actions
        for step in actions:
            plan.add_step(step)

        return plan


if __name__ == "__main__":
    from risk.utils.logging import setLevel
    from risk.utils.copy import copy_game_state
    from risk.state import GameState
    from os import path
    from logging import DEBUG

    setLevel(DEBUG)

    from simpn.visualisation import Visualisation

    state = GameState.create_new_game(20, 2, 100)
    state.initialise()
    state.update_player_statistics()

    safemap = mapping.construct_safe_view(state.map, 0)
    fronts = safemap.frontline_nodes

    problem = construct_problem(set(f.id for f in fronts), state.map.clone(), 2)

    if path.exists("test.layout"):
        vis = Visualisation(problem, layout_file="test.layout")
    else:
        vis = Visualisation(problem)
    vis.show()

    vis.save_layout("test.layout")

    for _ in range(10):
        new_state = copy_game_state(state)
        terrs = list(fronts)
        terr = random.choice(terrs)
        new_state.get_territory(terr.id).armies += 100
        info("Increased troops in territory {}".format(terr.id))
        new_state.update_player_statistics()

        pick = random.randint(1, 5)
        planner = AttackPlanner(0, pick)
        plan = planner.construct_plan(new_state)

        info(plan)
        assert len(plan.steps) > 0, "Expected one attack in the plan."
        assert (
            len(plan.steps) <= pick
        ), "Expected at most {} attacks in the plan.".format(pick)
        for step in plan.steps:
            info(step)
        input("Press Enter to continue...")
