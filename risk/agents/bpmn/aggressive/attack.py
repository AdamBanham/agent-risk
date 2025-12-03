from ...plans import Planner, AttackPlan, AttackStep
from risk.utils import map as mapping
from risk.utils.logging import info

import random
from typing import Set

from ..bases import ExpressiveSimProblem
from simpn.simulator import SimTokenValue, SimToken
from simpn.helpers import Place, BPMN


def sum_of_adjacents(node: int, map: mapping.Graph, player: int) -> int:
    total = 0
    armies = map.get_node(node).value
    for neighbor in map.get_adjacent_nodes(node):
        if neighbor.owner != player:
            total += armies / neighbor.value
    return total


def construct_problem(fronts: Set[int], map: mapping.Graph, player: int, attacks: int):
    problem = ExpressiveSimProblem()

    class Start(Place):
        model = problem
        name = "start"
        amount = 0

    start = problem.var("start")
    start.put(
        SimTokenValue(
            "start-0",
            fronts=fronts,
            map=map.clone(),
            attack_left=attacks,
            attacker=None,
            defender=None,
            troops=None,
        )
    )

    class Planner(Place):
        model = problem
        name = "planner"
        amount = 0

    planner = problem.var("planner")
    planner.put(SimTokenValue("planner-0", actions=[]))

    class FindFront(BPMN):
        model = problem
        type = "task"
        incoming = ["start", "planner"]
        outgoing = ["preselected", "planner"]
        name = "Find a Front"

        def behaviour(val, res):
            val.clone()
            sorted_fronts = sorted(
                val.fronts,
                key=lambda t: sum_of_adjacents(t, val.map, player=player),
                reverse=True,
            )
            front = sorted_fronts[0]

            if sum_of_adjacents(front, val.map, player=player) > 0.25:
                val.attacker = front
                val.troops = val.map.get_node(front).value - 1

            return [SimToken((val, res))]

    class HasAttackerXorSplit(BPMN):
        model = problem
        type = "gat-ex-split"
        incoming = ["preselected"]
        outgoing = ["finishing", "attacking"]
        name = "Has Attacker?"

        def choice(token: SimTokenValue):
            if token.attacker is None:
                return [SimToken(token), None]
            else:
                return [None, SimToken(token)]

    class FindAdjacent(BPMN):
        model = problem
        type = "task"
        incoming = ["attacking", "planner"]
        outgoing = ["selected", "planner"]
        name = "Find Adjacents to Attack"

        def behaviour(val, res):
            val = val.clone()

            adjacents = val.map.get_adjacent_nodes(val.attacker)
            adjacents = list(a for a in adjacents if a.owner != player)

            def strength(o: mapping.Node) -> float:
                return o.value

            adjacents = sorted(adjacents, key=strength)

            val.defender = adjacents[0].id if adjacents else None

            # check that the first attack is indeed safe
            if len(res.actions) == 0 and val.defender is not None:
                defender = val.map.get_node(val.defender)
                safe_troops = max( defender.value + 5, defender.value * 3)
                if val.troops < safe_troops:
                    val.defender = None

            return [SimToken((val, res))]

    class FoundDefenderXorSplit(BPMN):
        model = problem
        type = "gat-ex-split"
        incoming = ["selected"]
        outgoing = ["finishing", "building"]
        name = "Found Defender?"

        def choice(token: SimTokenValue):
            if token.defender is None:
                return [SimToken(token), None]
            else:
                return [None, SimToken(token)]

    class BuildAttack(BPMN):
        model = problem
        type = "task"
        incoming = ["building", "planner"]
        outgoing = ["attacked", "planner"]
        name = "Build Attack"

        def behaviour(val, res):

            val = val.clone()
            res = res.clone()

            res.actions.append(
                AttackStep(
                    attacker=val.attacker,
                    defender=val.defender,
                    troops=val.troops,
                )
            )

            val.map.get_node(val.attacker).value -= val.troops
            val.map.get_node(val.defender).value = val.troops // 2
            val.map.get_node(val.defender).owner = val.map.get_node(val.attacker).owner
            val.attack_left -= 1
            val.troops = val.troops // 2
            val.attacker = val.defender
            val.defender = None

            return [SimToken((val, res))]

    class Continue(BPMN):
        model = problem
        type = "task"
        incoming = ["attacked", "planner"]
        outgoing = ["preselected", "planner"]
        name = "Continue Attacks"

        def behaviour(val, res):
            val = val.clone()
            if val.attack_left < 1 or val.troops < 2:
                val.attacker = None

            return [SimToken((val, res))]

    class End(BPMN):
        model = problem
        type = "end"
        incoming = ["finishing"]
        name = "End"

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

        fronts = mapping.construct_safe_view(state.map, self.player).frontline_nodes
        problem = construct_problem(
            set(f.id for f in fronts), state.map.clone(), self.player, self.max_attacks
        )

        while problem.step():
            pass

        planner = problem.var("planner")
        actions = planner.marking[0].value.actions

        for step in reversed(actions):
            plan.add_step(step)

        return plan


if __name__ == "__main__":
    from risk.utils.logging import setLevel
    from risk.utils.copy import copy_game_state
    from risk.state import GameState
    from logging import DEBUG
    from os import path

    setLevel(DEBUG)

    from simpn.visualisation import Visualisation

    state = GameState.create_new_game(20, 2, 100)
    state.initialise()
    state.update_player_statistics()

    safemap = mapping.construct_safe_view(state.map, 0)
    fronts = safemap.frontline_nodes

    problem = construct_problem(set(f.id for f in fronts), state.map.clone(), 0, 2)

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
