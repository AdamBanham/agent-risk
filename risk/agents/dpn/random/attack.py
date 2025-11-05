from ...plans import Planner, AttackPlan, AttackStep
from risk.state import GameState

from simpn.helpers import Place, Transition
from simpn.simulator import SimTokenValue, SimToken
from .base import ExpressiveSimProblem as SimProblem
from .base import GuardedTransition

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
        amount = 1

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

    class Attacks(Place):
        model = problem
        name = "attacks"

    attacks_place = problem.var("attacks")
    for i in range(attacks):
        attacks_place.put(SimTokenValue(f"attack-{i}"))

    class Actions(Place):
        model = problem
        name = "actions"

    class Complete(Place):
        model = problem
        name = "complete"

    class InitatePlan(Transition):
        model = problem
        name = "initiate-plan"
        incoming = ["start"]
        outgoing = ["planning"]

        def behaviour(tok_val):
            return [SimToken(tok_val)]

    class PickTerritory(GuardedTransition):
        model = problem
        name = "pick-territory"
        incoming = ["planning", "territories", "attacks"]
        outgoing = ["planning", "territories", "actions"]

        def guard(
            tok_val: SimTokenValue,
            terr_val: SimTokenValue,
            attack_val: SimTokenValue,
        ):
            if terr_val.armies >= 2 and len(terr_val.adjacents) > 0:
                return True
            return False

        def behaviour(
            tok_val: SimTokenValue,
            terr_val: SimTokenValue,
            attack_val: SimTokenValue,
        ):
            pick = random.choice(list(terr_val.adjacents))
            army = random.choice(range(1, terr_val.armies))
            new_terr_val = terr_val.clone()
            new_terr_val.armies -= army
            return [
                SimToken(tok_val),
                SimToken(new_terr_val),
                SimToken(
                    SimTokenValue(
                        f"attack-from-{terr_val.territory}-to-{pick}",
                        attack=attack_val.id,
                        from_terr=terr_val.territory,
                        to_terr=pick,
                        troops=army,
                    )
                ),
            ]

    class CompletePlan(GuardedTransition):
        model = problem
        name = "complete-plan"
        incoming = ["planning"]
        outgoing = ["complete"]

        def guard(tok_val: SimTokenValue):
            if len(attacks_place.marking) > 0:
                return False
            return True

        def behaviour(tok_val: SimTokenValue):
            return [SimToken(tok_val)]

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
        pick = random.random()
        while pick < self.attack_prob and attacks <= self.max_attacks:
            attacks += 1
            pick = random.random()

        terrs = state.get_territories_owned_by(self.player_id)
        adjacents = dict(
            (terr.id, set(o.id for o in terr.adjacent_territories)) 
            for terr in terrs
        )
        armies = dict((terr.id, terr.armies) for terr in terrs)
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
    state = GameState.create_new_game(52, 2, 50)
    state.initialise()
    state.update_player_statistics()

    planner = RandomAttacks(player_id=0, max_attacks=5, attack_prob=0.7)
    plan = planner.construct_plan(state)

    print(f"Generated Attack Plan: {plan}")
    for step in plan.steps:
        print(step)

