from ...plans import Planner, MovementPlan, RouteMovementStep, MovementStep
from risk.state import GameState
from risk.utils.logging import debug, info
from risk.utils.movement import find_movement_sequence
from risk.utils import map as mapping

import random
from typing import Set, Dict

from xdevs.models import Coupled, Port, Atomic
from xdevs.sim import Coordinator
from ..base import (
    Selector,
    Reworker,
    Builder,
    Filter,
    Computer,
    ComputeOnMany,
    SeenByFilter,
    ConditionalXor,
    Storage,
)


class ShouldBalance(ConditionalXor):
    """
    A conditional XOR that checks if balancing is needed.
    """

    def __init__(self, name, network_map: mapping.NetworkGraph):
        super().__init__(name)
        self.network_map = network_map

    def condition(self, input_data: map) -> bool:
        view = self.network_map.view(input_data)
        return view.size > 1


class SeenNetworks(SeenByFilter[int, int]):
    """
    A filter that only allows unseen networks from the given set.
    Returns a single random unseen network each time as a set.
    """

    def __init__(self, name=None):
        super().__init__(name)

    def filter(self, input_data: Set[int]) -> Set[int]:
        terr = random.choice(list(input_data))
        return set([terr])


class ComputeTargets(Computer[int, Dict[int, int]]):
    """
    A computer that considers a network and computes
    the ideal target for each territory in it.
    """

    def __init__(self, network_map: mapping.NetworkGraph, map: mapping.Graph):
        super().__init__("network-compute-targets")
        self.network_map = network_map
        self.map = map

    def compute(self, input_data: int) -> Set[int]:
        view = self.network_map.view(input_data)
        armies = {t.id: self.map.get_node(t.id).value for t in view.nodes}
        total_armies = sum(armies.values())
        fronts = {n.id for n in view.nodes if not n.safe}
        moveable = total_armies - (view.size - len(fronts))
        ideal_troops = moveable // len(fronts)
        missing = dict(
            (t, ideal_troops - armies[t]) for t in fronts if armies[t] < ideal_troops
        )

        return missing


class Passthrough(Computer[int, int]):
    """
    A computer that simply passes through the input.
    """

    def __init__(self, name=None):
        super().__init__(name)

    def compute(self, input_data: int) -> int:
        return input_data


class BalanceReworker(Atomic):
    """
    A reworker that waits for both an network and a mapping
    of terrs to target troop counts, and then triggers rework.
    """

    def __init__(self):
        super().__init__("balancer-reworker")

        for i_name, p_type in {"network": int, "targets": dict}.items():
            port = Port(p_type, f"i_{i_name}")
            setattr(self, f"i_{i_name}", port)
            setattr(self, i_name, None)
            self.add_in_port(port)

        self.i_trigger = Port(bool, "i_trigger")
        self.add_in_port(self.i_trigger)
        self.i_done = Port(bool, "i_done")
        self.add_out_port(self.i_done)

        self.o_network = Port(int, "o_network")
        self.add_out_port(self.o_network)
        self.o_targets = Port(dict, "o_targets")
        self.add_out_port(self.o_targets)
        self.o_work = Port(bool, "o_work")
        self.add_out_port(self.o_work)

        self._loop = False

    def initialize(self):
        self.passivate()

    def deltext(self, e):
        debug("BalancerReworker external transition")
        if self.i_network:
            self.network = self.i_network.get()
            debug(f"BalancerReworker received network: {self.network}")
            self.activate()
        if self.i_targets:
            self.targets = self.i_targets.get()
            debug(f"BalancerReworker received targets: {self.targets}")
            self.activate()
        if self.i_trigger:
            self.loop = True
            self.activate()
        if self.i_done:
            _ = self.i_done.get()
            debug(f"BalancerReworker received done signal")
            self.network = None
            self.targets = None
            self.sent = False
            self.loop = False
            self.passivate()

    def deltint(self):
        self.passivate()

    def lambdaf(self):
        if self.network is not None and self.targets is not None and not self.sent:
            self.o_network.add(self.network)
            self.o_targets.add(self.targets)
            self.sent = True
            self.i_trigger.put(True)
        elif self.loop:
            self.o_work.add(True)


class IsBalanced(ConditionalXor):
    """
    Checks that all targets have enough troops on the map.
    """

    def __init__(self, map: mapping.Graph):
        super().__init__("IsBalanced?")
        self._map = map
        self._targets = None

    def condition(self, item):
        balanced = True
        for node, target in self._targets:
            node = self._map.get_node(node)
            balanced = balanced and node.value >= target

        return balanced


class BalanceMovementBuilder(Builder[MovementStep]):
    """
    Builds a movement within a network to balance
    """

    def __init__(self):
        super().__init__("balance-build", {"source": int, "dest": int, "troops": int})

    def build(self, inputs):
        return MovementStep(
            source=inputs["source"], destination=inputs["dest"], troops=inputs["troops"]
        )


class ComputeTroops(ComputeOnMany[int]):
    """
    Computes the troops to move from the source.
    """

    def __init__(
        self,
    ):
        super().__init__("compute-troops",
            {"source" : int, "target" : int})

    def compute(self, values):
        return super().compute(values)


class ComputeTarget(ComputeOnMany[int]):
    """
    Computes what target needs balancing.
    """

    def __init__(self, map: mapping.Graph):
        super().__init__("balance-target", {"targets": dict})
        self._map = map

    def compute(self, item: dict) -> int:
        choices = []
        for key, target in item.items():
            node = self._map.get_node(key)
            if node.value < target:
                choices.append(key)

        return random.choce(choices)
    

class ComputeSources(ComputeOnMany[Set[int]]):
    """
    Computes the sources for movement
    """

    def __init__(self):
        super().__init__("balance-sources", {
            "target" : int, "targets" : dict
        })

    def compute(self, values):
        return super().compute(values)

class BalancerModel(Coupled):
    """
    Implements a balancer that balances troops within a network.
    """

    def __init__(self, map: mapping.Graph, network_map: mapping.NetworkGraph):
        super().__init__("NetworkBalancerModel")

        self.i_targets = Port(int, "i_targets")
        self.i_network = Port(int, "i_network")

        self.o_balanced = Port(bool, "o_balanced")
        self.o_step = Port(MovementStep, "o_step")

        self.add_in_port(self.i_targets)
        self.add_in_port(self.i_network)
        self.add_out_port(self.o_balanced)
        self.add_out_port(self.o_step)

        self.reworker = BalanceReworker()
        self.builder = BalanceMovementBuilder()
        self.is_balanced = IsBalanced(map)
        self.compute_target = ComputeTarget()
        self.compute_source = ComputeSources()
        self.compute_troops = ComputeTroops()

        self.add_component(self.reworker)
        self.add_component(self.is_balanced)
        self.add_component(self.builder)
        self.add_component(self.compute_source)
        self.add_component(self.compute_troops)

        self.add_coupling(self.i_network, self.reworker.i_network)
        self.add_coupling(self.i_targets, self.reworker.i_targets)
        self.add_coupling(self.reworker.o_targets, self.compute_target.i_targets)

        self.add_coupling(self.compute_source.o_output, self.builder.i_source)
        self.add_coupling(..., self.select_source.i_terrs)

        self.add_coupling(self.compute_target.o_output, self.builder.i_dest)
        self.add_coupling(self.select_source.o_terr, self.compute_troops.i_input)
        self.add_coupling(self.compute_troops.o_output, self.builder.i_troops)
        self.add_coupling(self.builder.o_step, self.o_step)
        self.add_coupling(self.builder.o_step, self.is_balanced.i_input)
        self.add_coupling(self.is_balanced.o_false, self.reworker.i_trigger)
        self.add_coupling(self.is_balanced.o_true, self.reworker.i_done)

        self.add_coupling(self.selector.o_output, self.o_balanced)

    def initialize(self):
        return super().initialize()


class MovementModel(Coupled):
    """
    Implements the defensive movement planner.
    """

    def __init__(self, player: int, map: mapping.Graph):
        super().__init__("DefensiveMovementModel")

        network_map = mapping.construct_network_view(map, player)
        networks = {net for net in network_map.networks}

        self.action_storage = Storage[MovementStep]("action-storage")

        self.reworker = Reworker[MovementStep](
            "reworker", networks, reworks=len(networks)
        )
        self.network_filter = SeenNetworks("network-filter")
        self.network_should_balance = ShouldBalance(
            "network-should-balance", network_map
        )
        self.network_select = Selector("network-select")
        self.network_targets = ComputeTargets(network_map, map)

        self.balancer = BalancerModel()

        self.add_component(self.reworker)
        self.add_component(self.network_filter)
        self.add_component(self.network_select)
        self.add_component(self.network_should_balance)
        self.add_component(self.network_targets)
        self.add_component(self.balancer)
        self.add_component(self.action_storage)

        self.add_coupling(self.reworker.o_request, self.network_filter.i_filter)
        self.add_coupling(self.network_filter.o_filtered, self.network_select.i_terrs)
        self.add_coupling(
            self.network_select.o_terr, self.network_should_balance.i_input
        )
        self.add_coupling(self.network_should_balance.o_false, self.reworker.i_action)
        self.add_coupling(
            self.network_should_balance.o_true, self.network_targets.i_input
        )
        self.add_coupling(self.network_should_balance.o_true, self.balancer.i_network)
        self.add_coupling(self.network_targets.o_output, self.balancer.i_targets)
        self.add_coupling(self.balancer.o_balanced, self.reworker.i_action)
        self.add_coupling(self.balancer.o_step, self.action_storage.i_input)

    def initialize(self):
        super().initialize()

    def start_planning(self):
        coordinator = Coordinator(self)
        coordinator.initialize()
        coordinator.simulate()
        done_steps = self.action_storage.storage
        return done_steps


class MovementPlanner(Planner):
    """
    A defensive movement planner.
    """

    def __init__(self, player: int):
        super().__init__()
        self.player = player

    def construct_plan(self, game_state: GameState) -> MovementPlan:

        model = MovementModel(
            self.player,
            game_state.map.clone(),
        )

        actions = model.start_planning()
        routes = []

        for action in actions:
            movements = find_movement_sequence(
                game_state.get_territory(action.source),
                game_state.get_territory(action.target),
                action.troops,
            )
            route = []
            for move in movements:
                route.append(
                    MovementStep(
                        source=move.src.id,
                        target=move.tgt.id,
                        troops=move.amount,
                    )
                )

            if route:
                routes.append(RouteMovementStep(route))

        plan = MovementPlan(len(routes))
        for route in reversed(routes):
            plan.add_step(route)

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

    planner = MovementPlanner(0)
    plan = planner.construct_plan(state)

    info("Constructed Plan: {}".format(plan))
    assert len(plan.steps) > 0, "Expected at least a movement in the plan."
    for step in plan.steps:
        info(" - Step: {}".format(step))
