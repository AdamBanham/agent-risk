from ...plans import Planner, AttackPlan, AttackStep
from risk.state import GameState
from risk.utils.logging import debug

from typing import Set, Dict
import random

from xdevs.models import Atomic, Coupled, Port
from xdevs.sim import Coordinator
from ..base import Selector, Reworker, SelectFrom


class Builder(Atomic):
    """
    An atomic model that builds a TroopPlacementStep from a territory ID.
    """

    def __init__(self, name: str):
        super().__init__(name)

        self.i_terr = Port(int, "i_terr")
        self.i_defender = Port(int, "i_defender")
        self.i_troops = Port(int, "i_troops")
        self.o_step = Port(AttackStep, "o_step")

        self._attacker = None
        self._defender = None
        self._troops = None
        self._step = None

        self.add_in_port(self.i_terr)
        self.add_in_port(self.i_defender)
        self.add_in_port(self.i_troops)
        self.add_out_port(self.o_step)

    def initialize(self):
        self.passivate()

    def deltint(self):
        debug("Builder internal transition")
        if self._step is not None:
            self._attacker = None
            self._defender = None
            self._troops = None
            self._step = None
            self.passivate()

    def deltext(self, e):
        debug("Builder external transition")
        if self.i_terr:
            self._attacker = self.i_terr.get()
        if self.i_defender:
            self._defender = self.i_defender.get()
        if self.i_troops:
            self._troops = self.i_troops.get()
        self.activate()

    def lambdaf(self):
        debug("Builder output function")
        if (
            self._attacker is not None
            and self._defender is not None
            and self._troops is not None
        ):
            self._step = AttackStep(
                attacker=self._attacker,
                defender=self._defender,
                troops=self._troops,
            )
            debug(f"Builder created step: {self._step}")
            self.o_step.add(self._step)

    def exit(self):
        return super().exit()


class AtackModel(Coupled):
    """
    A coupled model that implements a random attack planner.
    """

    def __init__(
        self,
        name: str,
        attacks: int,
        terrs: Set[int],
        adjacents: Dict[int, Set[int]],
        armies: Dict[int, int],
    ):
        super().__init__(name)

        self.attacks = attacks

        self.selector = Selector("selector")
        self.select_adj = SelectFrom[int, Set[int]]("select_adj", adjacents)
        self.select_armies = SelectFrom[int, Set[int]]("select_armies", armies)
        self.builder = Builder("builder")
        self.reworker = Reworker[AttackStep]("reworker", terrs, reworks=attacks)

        self.add_component(self.selector)
        self.add_component(self.select_adj)
        self.add_component(self.select_armies)
        self.add_component(self.builder)
        self.add_component(self.reworker)

        self.add_coupling(self.reworker.o_request, self.selector.i_terrs)
        self.add_coupling(self.selector.o_terr, self.select_adj.i_terrs)
        self.add_coupling(self.selector.o_terr, self.select_armies.i_terrs)
        self.add_coupling(self.selector.o_terr, self.builder.i_terr)
        self.add_coupling(self.select_adj.o_terr, self.builder.i_defender)
        self.add_coupling(self.select_armies.o_terr, self.builder.i_troops)
        self.add_coupling(self.builder.o_step, self.reworker.i_action)

    def initialize(self):
        super().initialize()

    def start_planning(self):
        coordinator = Coordinator(self)
        coordinator.initialize()
        coordinator.simulate()
        done_steps = self.reworker.get_actions()
        return done_steps


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
        max_attacks = 1
        pick = random.uniform(0, 1)
        while pick <= self.attack_prob and max_attacks < self.max_attacks:
            max_attacks += 1
            pick = random.uniform(0, 1)

        plan = AttackPlan(self.max_attacks)

        terrs = {
            t.id 
            for t in game_state.get_territories_owned_by(self.player_id)
            if t.armies > 1
        }
        adjacents = {
            t.id: {adj.id for adj in t.adjacent_territories}
            for t in game_state.get_territories_owned_by(self.player_id)
        }
        armies = {
            t.id: list(range(1, t.armies))
            for t in game_state.get_territories_owned_by(self.player_id)
        }
        planner = AtackModel(
            "random_attack_model", max_attacks, terrs, adjacents, armies
        )
        steps = planner.start_planning()

        for step in steps:
            plan.add_step(step)

        return plan


if __name__ == "__main__":
    from logging import DEBUG
    from risk.utils.logging import setLevel

    setLevel(DEBUG)

    state = GameState.create_new_game(52, 2, 50)
    state.initialise()
    state.update_player_statistics()

    planner = RandomAttack(0, 5)
    plan = planner.construct_plan(state)

    print(plan)
    for step in plan.steps:
        print(step)
