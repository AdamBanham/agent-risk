from ...plans import Planner, PlacementPlan, TroopPlacementStep
from risk.state import GameState

from typing import Set
import random

from simpn.helpers import BPMN, Place
from simpn.simulator import SimTokenValue, SimToken
from risk.utils.logging import debug
from risk.utils import map as mapping
from ..bases import ExpressiveSimProblem as SimProblem


def create_simulator(terrs: Set[int], placements: int):

    problem = SimProblem()

    class Start(BPMN):
        model = problem
        type = "resource-pool"
        name = "planning-started"
        amount = 1

    class Planner(BPMN):
        model = problem
        name = "planner"
        type = "resource-pool"
        amount = 0

    start = problem.var("planner")
    start.set_invisible_edges()
    planning_tok = SimTokenValue("plan", terrs=terrs, placements=placements, actions=[])
    start.put(planning_tok)

    class CheckingJoin(BPMN):
        model = problem
        type = "gat-ex-join"
        name = "Rejoin checking"
        incoming = ["planning-started", "rejoin"]
        outgoing = ["checking"]

    class Planning(BPMN):
        model = problem
        type = "task"
        name = "check for planning"
        incoming = ["checking", "planner"]
        outgoing = ["checked", "planner"]

        def behaviour(tok_val, planner: SimTokenValue):
            new_planner = planner.clone()
            new_planner.planning = new_planner.placements > 0
            if isinstance(tok_val, SimTokenValue):
                new_tok_val = tok_val.clone()
                new_tok_val.planning = new_planner.planning
            else:
                new_tok_val = SimTokenValue(tok_val, planning=new_planner.planning)
            return [SimToken((new_tok_val, new_planner))]

    class NeedsPlacementSplit(BPMN):
        model = problem
        type = "gat-ex-split"
        name = "needs placement?"
        incoming = ["checked"]
        outgoing = ["placing-troops", "end"]

        def choice(tok_val):
            if tok_val.planning:
                return [SimToken(tok_val), None]
            else:
                return [None, SimToken(tok_val)]

    class PlaceTroops(BPMN):
        model = problem
        type = "task"
        name = "place troops"
        incoming = ["placing-troops", "planner"]
        outgoing = ["rejoin", "planner"]

        def behaviour(tok_val, planner: SimTokenValue):
            new_planner = planner.clone()

            terrs = planner.terrs

            chosen_terr = random.choice(list(terrs))
            pick_placements = 1
            step = TroopPlacementStep(chosen_terr, pick_placements)

            new_planner.actions.append(step)
            new_planner.placements -= pick_placements

            return [SimToken((tok_val, new_planner))]

    class End(BPMN):
        model = problem
        type = "end"
        name = "plan-finished"
        incoming = ["end"]

    return problem


class RandomPlacement(Planner):
    """
    A planner that generates random placement plans.
    """

    def __init__(self, player_id: int, placements_left: int):
        super().__init__()
        self.player_id = player_id
        self.placements_left = placements_left
        self._sim = None

    def construct_plan(self, game_state: GameState) -> PlacementPlan:
        plan = PlacementPlan(self.placements_left)

        terrs = set(t.id for t in game_state.get_territories_owned_by(self.player_id))
        sim = create_simulator(terrs, self.placements_left)

        while sim.step():
            pass

        final = sim.var("planner").marking[0]

        for step in final.value.actions:
            plan.add_step(step)

        self._sim = sim

        return plan


if __name__ == "__main__":
    from risk.utils.logging import setLevel 
    from logging import DEBUG
    setLevel(DEBUG)

    state = GameState.create_new_game(52, 2, 50)
    state.initialise()
    state.update_player_statistics()

    planner = RandomPlacement(0, 5)
    plan = planner.construct_plan(state)

    debug(plan)
    assert len(plan.steps) == 5, "Expected 5 placement steps"
    for step in plan.steps:
        debug(step)
        node = state.map.get_node(step.territory)
        assert node.owner == 0, "Expected territory to be owned by player 0"

    from simpn.visualisation import Visualisation

    vis = Visualisation(planner._sim)
    vis.show()
