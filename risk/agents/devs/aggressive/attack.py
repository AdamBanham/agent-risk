from ...plans import Planner, AttackPlan, AttackStep
from risk.state import GameState
from risk.utils.logging import debug, info
from risk.utils import map as mapping

import random
from typing import Set

from xdevs.models import Coupled, Port
from xdevs.sim import Coordinator
from ..base import (
    Selector, Reworker, Builder, Filter, Computer,
    ComputeOnMany, SeenByFilter
)

class AttackFilter(Filter[Set[int], Set[int]]):
    """
    Filters fronts down to the a singleton set of containing the
    territory with the most attack potential.
    """

    def __init__(self, map: mapping.Graph, player: int):
        super().__init__("attack-filter")
        self._map = map 
        self._player = player

        self._next = None
        self.i_next = Port(int, "i_next")
        self.add_in_port(self.i_next)

    def sort_key(self, item) -> float:
        total = 0
        armies = self._map.get_node(item).value
        for neighbor in self._map.get_adjacent_nodes(item):
            if neighbor.owner != self._player:
                total += armies / neighbor.value
        return total

    def filter(self, item):
        if self._next:
            return [self._next]
        
        ret = list(item)
        ret = sorted(
            item, key=self.sort_key, reverse=True
        )

        selected = ret[0]
        if self.sort_key(selected) < 0.25:
            return []
        
        return set(ret[:1])
    
    def deltext(self, e):
        if self.i_next:
            value = self.i_next.get()
            self._next = value 
            debug(f"Filter {self.name} received next element to use")
            
        ret = super().deltext(e)
        return ret


class AttackBuilder(Builder[AttackStep]):
    """
    Builds attack steps from an attacker, defender, and a troop count.

    .. ports ::
         :port i_attacker: int
         :port i_defender: int
         :port i_troops: int
         :port o_step: AttackStep
    """

    def __init__(self, name, map: mapping.Graph):
        super().__init__(
            name,
            {
                "attacker": int,
                "defender": int,
                "troops": int,
            },
        )
        self._map = map

    def build(self, inputs):
        step =  AttackStep(
            attacker=inputs["attacker"],
            defender=inputs["defender"],
            troops=inputs["troops"],
        )

        attacker = self._map.get_node(inputs["attacker"])
        defender = self._map.get_node(inputs["defender"])
        attacker.value -= inputs["troops"]
        defender.owner = attacker.owner
        defender.value = inputs["troops"] // 2

        return step


class ComputeAdjacentDefenders(Computer[int, Set[int]]):
    """
    Computes the set of adjacent enemy territories for a given attacker territory.

    :param map: the current map of the game.
    :param player: the player ID of the agent.
    """

    def __init__(self, name: str, map: mapping.Graph, player: int):
        super().__init__(name)
        self.map = map
        self.player = player

    def compute(self, terr: int) -> Set[int]:
        adjs = self.map.get_adjacent_nodes(terr)
        enemy_adjs = {adj.id for adj in adjs if adj.owner != self.player}
        return enemy_adjs


class ComputeTroops(ComputeOnMany[int]):
    """
    Computes the number of troops to use in an attack.
    """

    def __init__(self, name: str, map: mapping.Graph):
        super().__init__(
            name,
            {
                "attacker": int,
                "defender": int,
            },
        )
        self.map = map

        self._last = None 

    def compute(self, values):
        if self._last == None:
            attacker = self.map.get_node(values["attacker"])
            self._last = attacker.value - 1
        else:
            self._last = self._last // 2 
        return self._last


class FilterToWeakest(Filter[Set[int], Set[int]]):
    """
    Filters out defenders down to a singleton set contain the 
    weakest defender.
    """

    def __init__(self, name, map: mapping.Graph, player: int):
        super().__init__(name)
        self.map = map
        self.player = player
        self._checked_first = False

        self.i_attacker = Port(int, "i_attacker")

        self.add_in_port(self.i_attacker)

    def filter(self, defenders: Set[int]) -> Set[int]:
        attacker = self.map.get_node(self._attacker)

        defenders = list( d for d in defenders if self.map.get_node(d).owner != self.player)
        if not defenders:
            return set()
        
        def strength(defender):
            return self.map.get_node(defender).value
        
        defenders = sorted(defenders, key=strength)
        defender = defenders[0]

        # check that first attack is safe.
        if not self._checked_first:
            self._checked_first = True
            def_str = strength(defender)
            safe_troops = max(def_str + 5, def_str * 3)
            if attacker.value - 1 < safe_troops:
                return set()

        return set(defenders[:1])

    def deltext(self, e):
        if self.i_attacker:
            self._attacker = self.i_attacker.get()
            debug(f"UnsafeFilter received attacker: {self._attacker}")
        super().deltext(e)


class AttackModel(Coupled):
    """
    Implements a defensive attack planner.
    """

    def __init__(self, player: int, map: mapping.Graph, max_attacks: int):
        super().__init__("DefensiveAttackModel")

        fronts = mapping.construct_safe_view(map, player).frontline_nodes

        n_most = min(random.randint(1, len(fronts)), max_attacks)
        top_most = sorted(
            fronts,
            key=lambda t: map.get_node(t.id).value,
            reverse=True,
        )[: int(n_most)]
        fronts = {node.id for node in top_most}

        self.reworker = Reworker[AttackStep]("reworker", fronts, reworks=n_most)
        self.builder = AttackBuilder("builder", map.clone())
        self.filter = AttackFilter(map, player)
        self.selector = Selector("attacker")
        self.adjs = ComputeAdjacentDefenders("adjacent_to", map, player)
        self.filter_ajs = FilterToWeakest("unsafe_filter", map, player)
        self.adj_selector = Selector("defender")
        self.troop_computer = ComputeTroops("troop_computer", map)

        self.add_component(self.reworker)
        self.add_component(self.builder)
        self.add_component(self.filter)
        self.add_component(self.selector)
        self.add_component(self.adjs)
        self.add_component(self.filter_ajs)
        self.add_component(self.adj_selector)
        self.add_component(self.troop_computer)

        self.add_coupling(self.reworker.o_request, self.filter.i_filter)
        self.add_coupling(self.filter.o_filtered, self.selector.i_terrs)
        self.add_coupling(self.selector.o_terr, self.builder.i_attacker)
        
        self.add_coupling(self.selector.o_terr, self.adjs.i_input)
        self.add_coupling(self.adjs.o_output, self.filter_ajs.i_filter)

        self.add_coupling(self.selector.o_terr, self.filter_ajs.i_attacker)
        self.add_coupling(self.filter_ajs.o_filtered, self.adj_selector.i_terrs)

        self.add_coupling(self.adj_selector.o_terr, self.builder.i_defender)
        self.add_coupling(self.adj_selector.o_terr, self.filter.i_next)

        self.add_coupling(self.selector.o_terr, self.troop_computer.i_attacker,)
        self.add_coupling(self.adj_selector.o_terr, self.troop_computer.i_defender)
        self.add_coupling(self.troop_computer.o_output, self.builder.i_troops)

        self.add_coupling(self.builder.o_step, self.reworker.i_action)

    def initialize(self):
        super().initialize()

    def start_planning(self):
        coordinator = Coordinator(self)
        coordinator.initialize()
        coordinator.simulate()
        done_steps = self.reworker.get_actions()
        return done_steps

class AttackPlanner(Planner):
    """
    A defensive attack planner.
    """

    def __init__(self, player: int, max_attacks: int):
        super().__init__()
        self.player = player
        self.max_attacks = max_attacks

    def construct_plan(self, game_state: GameState) -> AttackPlan:
        plan = AttackPlan(self.max_attacks)

        model = AttackModel(self.player, game_state.map, self.max_attacks)
        actions = model.start_planning()

        for action in reversed(actions):
            plan.add_step(action)

        return plan


if __name__ == "__main__":
    from risk.utils.logging import setLevel
    from logging import DEBUG

    setLevel(DEBUG)

    state = GameState.create_new_game(20, 2, 50)
    state.initialise()
    state.update_player_statistics()

    fronts = mapping.construct_safe_view(state.map, 0).frontline_nodes
    front = random.choice(list(fronts))
    terr = state.get_territory(front.id)
    terr.armies += 100

    state.update_player_statistics()

    planner = AttackPlanner(0, 2)
    plan = planner.construct_plan(state)

    info("Constructed Plan: {}".format(plan))
    assert len(plan.steps) > 0, "Expected at least an attack in the plan."
    for step in plan.steps:
        info(" - Step: {}".format(step))
