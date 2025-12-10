from ...plans import Planner, AttackPlan, AttackStep
from risk.state import GameState
from risk.utils import map as mapping
from risk.utils.logging import debug

from simpn.helpers import Place, Transition
from simpn.simulator import SimTokenValue, SimToken
from ..bases import ExpressiveSimProblem as SimProblem
from ..bases import GuardedTransition

import random
from typing import Dict, Set


def create_simulator(
    attacks: int,
    terrs: Set[int],
    adjacents: Dict[int, Set[int]],
    armies: Dict[int, int],
) -> SimProblem:

    problem = SimProblem()

    class Start(Place):
        model = problem
        name = "start"
        amount = attacks

    class Territories(Place):
        model = problem
        name = "territories"

    territories = problem.var("territories")
    for terr in terrs:
        territories.put(
            SimTokenValue(
                f"terr-{terr}",
                territory=terr,
                adjacents=adjacents[terr],
                armies=armies[terr],
            )
        )

    class PickTerritory(GuardedTransition):
        model = problem
        name = "pick-territory"
        incoming = ["start", "territories", ]
        outgoing = [ "actions"]

        def guard(
            tok_val: SimTokenValue,
            terr_val: SimTokenValue,
        ):
            if terr_val.armies >= 2 and len(terr_val.adjacents) > 0:
                return True
            return False

        def behaviour(
            tok_val: SimTokenValue,
            terr_val: SimTokenValue,
        ):
            pick = random.choice(list(terr_val.adjacents))
            army = random.choice(range(1, terr_val.armies))
            return [
                SimToken(
                    SimTokenValue(
                        f"attack-from-{terr_val.territory}-to-{pick}",
                        from_terr=terr_val.territory,
                        to_terr=pick,
                        troops=army,
                    )
                ),
            ]

    return problem


class RandomAttacks(Planner):
    """
    A planner that generates random attack plans.
    """

    def __init__(self, player_id: int, max_attacks: int, attack_prob: float = 0.5):
        super().__init__()
        self.player_id = player_id
        self.max_attacks = max_attacks
        self.attack_prob = attack_prob

    def construct_plan(self, state: GameState) -> "AttackPlan":

        attacks = 1
        pick = random.uniform(0, 1)
        while pick < self.attack_prob and attacks <= self.max_attacks:
            attacks += 1
            pick = random.uniform(0, 1)

        terrs = mapping.construct_safe_view(state.map, self.player_id).frontline_nodes 
        adjacents = dict(
            (terr.id, set(o.id for o in state.map.get_adjacent_nodes(terr.id) if o.owner != self.player_id)) 
            for terr in terrs
        )
        armies = dict((terr.id, mapping.get_value(state.map, terr.id)) for terr in terrs)
        terrs = set(terr.id for terr in terrs)

        sim = create_simulator(
            attacks,
            terrs,
            adjacents,
            armies,
        )

        while sim.step():
            pass

        plan = AttackPlan(self.max_attacks)
        for tok in sim.var("actions").marking:
            val:SimTokenValue = tok.value
            step = AttackStep(
                attacker=val.from_terr,
                defender=val.to_terr,
                troops=val.troops,
            )
            plan.add_step(step)

        return plan


if __name__ == "__main__":
    from logging import DEBUG
    from risk.utils.logging import setLevel
    from simpn.visualisation import Visualisation
    setLevel(DEBUG)

    state = GameState.create_new_game(52, 2, 250)
    state.initialise()
    state.update_player_statistics()

    for _ in range(5):
        player = random.randint(0, 1)
        attacks = random.randint(1, 10)
        planner = RandomAttacks(player_id=player, max_attacks=attacks, attack_prob=0.7)
        plan = planner.construct_plan(state)

        ## uncomment to show the conceptual model emulator
        # terrs = mapping.construct_safe_view(state.map, player).frontline_nodes 
        # adjacents = dict(
        #     (terr.id, set(o.id for o in state.map.get_adjacent_nodes(terr.id) if o.owner != player)) 
        #     for terr in terrs
        # )
        # armies = dict((terr.id, mapping.get_value(state.map, terr.id)) for terr in terrs)
        # terrs = set(terr.id for terr in terrs)

        # sim = create_simulator(
        #     attacks,
        #     terrs,
        #     adjacents,
        #     armies,
        # )
        # vis = Visualisation(sim)
        # vis.show()

        map = state.map

        debug(f"Generated Attack Plan: {plan}")
        assert len(plan.steps) <= attacks, \
            "Expected at most {} attacks, got {}".format(
                attacks, len(plan.steps)
            )
        for step in plan.steps:
            debug(step)
            atk_node = map.get_node(step.attacker)
            def_node = map.get_node(step.defender)
            assert atk_node.owner == player, \
                "Attacking territory {} not owned by player {}".format(
                    step.attacker, player
                )
            assert def_node.owner != player, \
                "Defending territory {} owned by player {}".format(
                    step.defender, player
                )
            assert atk_node.value > step.troops, \
                "Attacking territory {} does not have enough armies for attacking with {}".format(
                    step.attacker, step.troops
                )
            

