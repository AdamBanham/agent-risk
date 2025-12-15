from ...plans import Planner, AttackPlan, AttackStep
from risk.state import GameState
from risk.utils.logging import debug 
from risk.utils import map as mapping

from typing import Set, Dict
import random

from simpn.helpers import BPMN, Place
from simpn.simulator import SimTokenValue, SimToken
from ..bases import ExpressiveSimProblem as SimProblem


def construct_simulator(
    terrs: Set[int],
    armies: Dict[int, int],
    adjacents: Dict[int, Set[int]],
    max_attacks: int,
):

    problem = SimProblem()

    class Start(BPMN):
        model = problem
        type = "resource-pool"
        name = "planning-started"
        amount = 1

    class Finish(BPMN):
        model = problem
        type = "end"
        name = "finished"
        incoming = ["finish"]

    class Planner(BPMN):
        model = problem
        name = "planner"
        type = "resource-pool"
        amount = 0

    start = problem.var("planner")
    start.set_invisible_edges()
    attack_tok = SimTokenValue(
        "attack",
        terrs=terrs,
        armies=armies,
        adjacents=adjacents,
        attacks_left=max_attacks,
        actions=[],
    )
    start.put(attack_tok)

    class AttackCheck(BPMN):
        model = problem
        type = "task"
        name = "check for attacks"
        incoming = ["checking", "planner"]
        outgoing = ["attacking", "planner"]

        def behaviour(tok_val, planner: SimTokenValue):
            new_planner = planner.clone()
            new_planner.attacking = new_planner.attacks_left > 0

            # check for armies
            can_attack = False
            for terr in new_planner.terrs:
                if new_planner.armies[terr] > 1:
                    can_attack = True
                    break

            if not can_attack:
                new_planner.attacking = False

            if isinstance(tok_val, SimTokenValue):
                new_tok_val = tok_val.clone()
                new_tok_val.attacking = new_planner.attacking
            else:
                new_tok_val = SimTokenValue(tok_val, attacking=new_planner.attacking)
            return [SimToken((new_tok_val, new_planner))]

    class AttackSplit(BPMN):
        model = problem
        type = "gat-ex-split"
        name = "Needs Attack?"
        incoming = [
            "attacking",
        ]
        outgoing = ["attack", "finish"]

        def choice(tok_val: SimTokenValue):
            if tok_val.attacking:
                return [SimToken(tok_val), None]
            else:
                return [None, SimToken(tok_val)]

    class SelectAttack(BPMN):
        model = problem
        type = "task"
        name = "select attack"
        incoming = ["attack", "planner"]
        outgoing = ["selected", "planner"]

        def behaviour(tok_val, planner: SimTokenValue):
            new_planner = planner.clone()

            terr = random.choice(
                [t for t in planner.terrs if planner.armies[t] > 1]
            )
            adjacent = random.choice(list(planner.adjacents[terr]))
            army = planner.armies[terr] - 1
            if army > 1:
                army = random.randint(1, army)

            new_planner.selected = {
                "from": terr,
                "to": adjacent,
                "troops": army,
            }

            new_tok_val = tok_val.clone()
            execute = True

            if planner.armies[terr] < 2:
                execute = False

            new_tok_val.execute_attack = execute

            return [SimToken((new_tok_val, new_planner))]

    class ExecuteAttackSplit(BPMN):
        model = problem
        type = "gat-ex-split"
        name = "execute attack?"
        incoming = ["selected"]
        outgoing = ["executed", "finish"]

        def choice(tok_val: SimTokenValue):
            # Placeholder for decision to execute or skip the attack
            if tok_val.execute_attack:
                return [SimToken(tok_val), None]
            else:
                return [None, SimToken(tok_val)]

    class BuildAttackAction(BPMN):
        model = problem
        type = "task"
        name = "build attack action"
        incoming = ["executed", "planner"]
        outgoing = ["rejoin", "planner"]

        def behaviour(tok_val, planner: SimTokenValue):
            new_tok_val = planner.clone()
            new_tok_val.actions.append(
                AttackStep(
                    attacker=planner.selected["from"],
                    defender=planner.selected["to"],
                    troops=planner.selected["troops"],
                )
            )
            new_tok_val.attacks_left -= 1
            new_tok_val.terrs = new_tok_val.terrs.difference(
                set([planner.selected["from"]])
            )
            return [SimToken((tok_val, new_tok_val))]

    class Rejoin(BPMN):
        model = problem
        type = "gat-ex-join"
        name = "Rejoin checking"
        incoming = ["planning-started", "rejoin"]
        outgoing = ["checking"]

    return problem


class RandomAttack(Planner):
    """
    A planner that generates random attack plans.
    """

    def __init__(self, player_id: int, max_attacks: int, attack_prob: float = 0.5):
        super().__init__()
        self.player_id = player_id
        self.max_attacks = max_attacks
        self.attack_prob = attack_prob

    def construct_plan(self, game_state: GameState) -> AttackPlan:
        # Implementation of random attack plan generation
        max_attacks = 0
        pick = random.uniform(0, 1)
        while pick <= self.attack_prob and max_attacks < self.max_attacks:
            max_attacks += 1
            pick = random.uniform(0, 1)

        map = game_state.map
        smap = mapping.construct_safe_view(game_state.map, self.player_id)
        fronts = set(n.id for n in smap.frontline_nodes)
        terrs = [ n for n in map.nodes if n.id in fronts and n.owner == self.player_id ]
        terr_ids = set(t.id for t in terrs)
        armies = {t.id: t.value for t in terrs}
        adjacents = {t.id: set(adj.id for adj in map.get_adjacent_nodes(t.id) if adj.owner != t.owner) for t in terrs}
        sim_problem = construct_simulator(terr_ids, armies, adjacents, max_attacks)

        while sim_problem.step():
            pass

        plan = AttackPlan(self.max_attacks)
        planner_token = sim_problem.var("planner").marking[0]
        for action in planner_token.value.actions:
            plan.add_step(action)

        self._sim = sim_problem

        return plan


if __name__ == "__main__":
    from risk.utils.logging import setLevel 
    from logging import DEBUG
    setLevel(DEBUG)
    
    game_state = GameState.create_new_game(20, 2, 200)
    game_state.initialise()
    game_state.update_player_statistics()

    planner = RandomAttack(1, 10, 0.9)
    plan = planner.construct_plan(game_state)

    debug("Generated Attack Plan:" + str(plan))
    assert len(plan.steps) <= 10, "Expected no more than ten attacks"
    for step in plan.steps:
        debug(step)
        atk_node = game_state.map.get_node(step.attacker)
        assert atk_node.owner == 1, "Expected attacker to be owned by player"
        assert (
            atk_node.value > step.troops
        ), "Expected attacking troops to be less than territory"

    from simpn.visualisation import Visualisation
    vis = Visualisation(planner._sim)
    vis.show()
