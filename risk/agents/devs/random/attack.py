from ...plans import Planner, AttackPlan, AttackStep
from risk.state import GameState
from risk.utils.logging import debug
from risk.utils import map as mapping

from typing import Set, Dict
import random

from xdevs.models import Atomic, Coupled, Port
from xdevs.sim import Coordinator
from ..base import Selector, Reworker, SelectFrom, SeenByFilter


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


class SeenAttackers(SeenByFilter[int, int]):
    """
    Filters out already selected attackers.
    """

    def __init__(self):
        super().__init__("attack-filter", set())

    def filter(self, items: Set[int]):
        if items:
            terr = random.choice(list(items))
            return set([terr])
        return items


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
        self.filter = SeenAttackers()

        self.add_component(self.selector)
        self.add_component(self.select_adj)
        self.add_component(self.select_armies)
        self.add_component(self.builder)
        self.add_component(self.reworker)
        self.add_component(self.filter)

        self.add_coupling(self.reworker.o_request, self.filter.i_filter)
        self.add_coupling(self.filter.o_filtered, self.selector.i_terrs)
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

        map = game_state.map.clone()
        smap = mapping.construct_safe_view(map, self.player_id)

        terrs = {t.id for t in smap.frontline_nodes if mapping.get_value(map, t.id) > 1}
        adjacents = {
            t: {
                adj.id for adj in map.get_adjacent_nodes(t) if adj.owner != self.player_id
            }
            for t in terrs
        }
        armies = {
            t: list(range(1, mapping.get_value(map, t)))
            for t in terrs
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

    state = GameState.create_new_game(20, 2, 200)
    state.initialise()
    state.update_player_statistics()

    for _ in range(10):
        planner = RandomAttack(0, 5, 0.85)
        plan = planner.construct_plan(state)

        debug(plan)
        assert len(plan.steps) <= 5, "Expected no more than 5 attacks"
        for step in plan.steps:
            debug(step)
            atk_node = state.map.get_node(step.attacker)
            assert atk_node.owner == 0, "Expected attacker to be owned by player"
            assert (
                atk_node.value > step.troops
            ), "Expected that attacking troops is less than territories armies"
