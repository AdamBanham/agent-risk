from ...plans import Planner, MovementStep, RouteMovementStep, MovementPlan
from risk.utils.logging import info
from risk.utils import map as mapping
from risk.utils.movement import find_movement_sequence
from ..bases import ExpressiveSimProblem

import random

from simpn.simulator import SimTokenValue, SimToken
from simpn.helpers import Place, BPMN


def construct_problem(player: int, map: mapping.Graph):

    problem = ExpressiveSimProblem()

    network_map = mapping.construct_network_view(map, player)

    class Start(Place):
        model = problem
        name = "start"
        amount = 0

    start = problem.var("start")
    start.put(
        SimTokenValue(
            "start-0",
            map=map.clone(),
            network_map=network_map,
            networks=set(network_map.networks),
            targets=None,
        )
    )

    class Planner(BPMN):
        model = problem
        type = "resource-pool"
        name = "planner"
        amount = 0

    planner = problem.var("planner")
    planner.put(SimTokenValue("planner-0", actions=[]))

    class NetworkReworkXorJoin(BPMN):
        model = problem
        type = "gat-ex-join"
        incoming = ["start", "network-rework"]
        outgoing = ["network-start"]
        name = "Network Rework Join"

    class SelectNetwork(BPMN):
        model = problem
        type = "task"
        incoming = ["network-start", "planner"]
        outgoing = ["targetting", "planner"]
        name = "Select Network"

        def behaviour(val, res):
            val = val.clone()
            network = random.choice(list(val.networks))
            val.network = network
            val.networks = val.networks.difference(set([network]))
            return [SimToken((val, res))]

    class BuildTargets(BPMN):
        model = problem
        type = "task"
        incoming = ["targetting", "planner"]
        outgoing = ["balance-start", "planner"]
        name = "Build Targets"

        def behaviour(val, res):
            val = val.clone()
            val.targets = {}
            view = val.network_map.view(val.network)
            val.view = view

            if view.size > 1:
                nodes = view.nodes
                armies = {t.id: val.map.get_node(t.id).value for t in nodes}
                total_armies = sum(armies.values())
                fronts = list(n for n in nodes if not n.safe)
                moveable = total_armies - (view.size - len(fronts))
                ideal_troops = moveable // len(fronts)
                targets = dict((t.id, ideal_troops) for t in fronts)
                val.targets = targets

            return [SimToken((val, res))]

    class NeedsBalancingXorSplit(BPMN):
        model = problem
        type = "gat-ex-split"
        incoming = ["balance-start"]
        outgoing = ["balance-needed", "adjusted"]
        name = "Network needs balancing?"

        def choice(token: SimTokenValue):
            if len(token.targets.keys()) > 0:
                return [SimToken(token), None]
            else:
                return [None, SimToken(token)]

    class BalanceReworkXorJoin(BPMN):
        model = problem
        type = "gat-ex-join"
        incoming = ["balance-needed", "balance-rework"]
        outgoing = ["balance-select"]
        name = "Balance Rework Join"

    class SelectMissing(BPMN):
        model = problem
        type = "task"
        incoming = ["balance-select", "planner"]
        outgoing = ["balance-move", "planner"]
        name = "Select Balancing Target"

        def behaviour(val, res):

            missing = [
                t
                for t in val.targets.keys()
                if val.map.get_node(t).value < val.targets.get(t, 1)
            ]

            val.missing = random.choice(missing) if len(missing) > 0 else None

            return [SimToken((val, res))]

    class BalanceTroops(BPMN):
        model = problem
        type = "task"
        incoming = ["balance-move", "planner"]
        outgoing = ["adjusted", "planner"]
        name = "Move Balancing Troops"

        def behaviour(val, res):
            res = res.clone()
            val = val.clone()
            target = val.targets.get(val.missing, 1)
            node = val.map.get_node(val.missing)

            if node is not None and node.value < target:
                others = [
                    o.id
                    for o in val.view.nodes
                    if val.map.get_node(o.id).value > 1
                    and val.map.get_node(o.id).id != node.id
                    and val.map.get_node(o.id).value > val.targets.get(o.id, 1)
                ]
                others = sorted(
                    others, key=lambda x: val.map.get_node(x).value, reverse=True
                )
                for other in others:
                    other_node = val.map.get_node(other)
                    can_move = other_node.value - 1
                    need = target - node.value
                    move_troops = min(can_move, need)

                    val.map.get_node(other).value -= move_troops
                    val.map.get_node(node.id).value += move_troops

                    res.actions.append(
                        MovementStep(
                            source=other_node.id,
                            destination=node.id,
                            troops=move_troops,
                        )
                    )

                    if val.map.get_node(node.id).value >= target:
                        break

            return [SimToken((val, res))]

    class CheckNetwork(BPMN):
        model = problem
        type = "task"
        incoming = ["adjusted", "planner"]
        outgoing = ["checked-network", "planner"]
        name = "Check if Network is Balanced"

        def behaviour(val, res):
            balanced = True
            for node in val.targets.keys():
                if val.map.get_node(node).value < val.targets.get(node, 1):
                    balanced = False
                    break
            val = val.clone()
            val.is_balanced = balanced
            return [SimToken((val, res))]

    class ReworkBalanceXorSplit(BPMN):
        model = problem
        type = "gat-ex-split"
        incoming = ["checked-network"]
        outgoing = ["balance-rework", "next-network"]
        name = "Rework until Balanceed"

        def choice(token: SimTokenValue):
            if not token.is_balanced:
                return [SimToken(token), None]
            else:
                return [None, SimToken(token)]

    class CheckForMoreNetworks(BPMN):
        model = problem
        type = "task"
        incoming = ["next-network", "planner"]
        outgoing = ["loop", "planner"]
        name = "Check for more networks"

        def behaviour(val, res):

            val = val.clone()
            val.more_networks = len(val.networks) > 0
            return [SimToken((val, res))]

    class FinishedXorSplit(BPMN):
        model = problem
        type = "gat-ex-split"
        incoming = ["loop"]
        outgoing = ["network-rework", "finishing"]
        name = "Finished with Network Balancing"

        def choice(token: SimTokenValue):
            if token.more_networks:
                return [SimToken(token), None]
            else:
                return [None, SimToken(token)]

    class End(BPMN):
        model = problem
        type = "end"
        incoming = ["finishing"]
        name = "end"

    return problem


class MovementPlanner(Planner):
    """
    Planner for aggressive moving troops.
    """

    def __init__(
        self,
        player: int,
    ):
        super().__init__()
        self.player = player

    def construct_plan(self, state):

        sim = construct_problem(
            self.player,
            state.map,
        )

        while sim.step():
            pass

        actions = sim.var("planner").marking[0].value.actions
        plan = MovementPlan(len(actions))
        for action in reversed(actions):
            step: MovementStep = action

            route = find_movement_sequence(
                state.get_territory(step.source),
                state.get_territory(step.destination),
                step.troops,
            )

            step = RouteMovementStep(
                [MovementStep(move.src.id, move.tgt.id, move.amount) for move in route],
                step.troops,
            )

            plan.add_step(step)

        return plan


if __name__ == "__main__":
    from risk.utils.logging import setLevel
    from risk.utils.copy import copy_game_state
    from risk.state import GameState
    from logging import DEBUG

    setLevel(DEBUG)

    from simpn.visualisation import Visualisation

    state = GameState.create_new_game(20, 2, 100)
    state.initialise()
    state.update_player_statistics()

    safemap = mapping.construct_safe_view(state.map, 0)
    fronts = safemap.frontline_nodes

    problem = construct_problem(0, state.map.clone())

    vis = Visualisation(problem)
    vis.show()

    for _ in range(10):
        new_state = copy_game_state(state)
        terrs = list(fronts)
        terr = random.choice(terrs)
        new_state.get_territory(terr.id).armies += 100
        info("Increased troops in territory {}".format(terr.id))
        new_state.update_player_statistics()

        pick = random.randint(1, 5)
        planner = MovementPlanner(0)
        plan = planner.construct_plan(new_state)

        info(plan)
        assert len(plan.steps) > 0, "Expected one movement in the plan."
        for step in plan.steps:
            info(step)
        input("Press Enter to continue...")
