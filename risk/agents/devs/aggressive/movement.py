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
    Computer,
    ComputeOnMany,
    SeenByFilter,
    ConditionalXor,
    Storage,
    ResetAll
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
        fronts = len(view.frontlines_in_network(input_data))
        return view.size > 1 and fronts > 0


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

    def __init__(self, network_map: mapping.NetworkGraph, map: mapping.Graph, player: int):
        super().__init__("network-compute-targets")
        self.network_map = network_map
        self.map = map
        self.player = player

    def compute_weights(self, node:int):
        total = 0
        for neighbor in self.map.get_adjacent_nodes(node):
            if neighbor.owner != self.player:
                total += (1.0 / neighbor.value) * 10
        return total

    def compute(self, input_data: int) -> Dict[int, int]:
        view = self.network_map.view(input_data)
        armies = {t.id: self.map.get_node(t.id).value for t in view.nodes}
        total_armies = sum(armies.values())
        fronts = {n.id for n in view.nodes if not n.safe}
        moveable = total_armies - view.size

        # compute the attack weight for each front
        weights = [self.compute_weights(node) for node in fronts]

        # sort them to keep only the top three positions
        top_most = random.randint(1, min(3, len(fronts)))
        options = sorted(
            zip(fronts, weights),
            key=lambda x: x[1],
            reverse=True,
        )[:top_most]

        # create targets for selected fronts
        total_weight = sum( w for f,w in options)
        targets = dict(
            (f, max(1, int((w / total_weight) * moveable)))
            for f, w 
            in options
        )

        return targets


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
        self._sent = False

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
            self._loop = True
            self.activate()
        if self.i_done:
            _ = self.i_done.get()
            debug(f"BalancerReworker received done signal")
            self.network = None
            self.targets = None
            self._sent = False
            self._loop = False
            self.passivate()

    def deltint(self):
        self.passivate()

    def lambdaf(self):
        if self.network is not None and self.targets is not None and not self._sent:
            self.o_network.add(self.network)
            self.o_targets.add(self.targets)
            self._sent = True
            self.i_trigger.add(True)
        elif self._loop:
            self.o_work.add(True)
            if self.network:
                self.o_network.add(self.network)
            if self.targets:
                self.o_targets.add(self.targets)

    def exit(self):
        return super().exit()


class IsBalanced(ConditionalXor):
    """
    Checks that all targets have enough troops on the map.
    """

    def __init__(self, map: mapping.Graph):
        super().__init__("IsBalanced?")
        self._map = map

        self.i_targets = Port(dict, "i_targets")
        self._targets = None

        self.add_in_port(self.i_targets)

    def condition(self, item):
        balanced = True
        for node, target in self._targets.items():
            node = self._map.get_node(node)
            balanced = balanced and node.value >= target

        return balanced

    def deltext(self, e):
        ret = super().deltext(e)

        if self.i_targets:
            value = self.i_targets.get()
            self._targets = value

        return ret

class IsNotBalanced(IsBalanced):
    """
    Negation of IsBalanced.
    """

    def __init__(self, map):
        super().__init__(map)
        self.name = "IsNotBalanced"

    def condition(self, item):
        self._targets = item
        return not super().condition(item)

class BalanceMovementBuilder(Builder[MovementStep]):
    """
    Builds a movement within a network to balance
    """

    def __init__(self, map: mapping.Graph):
        super().__init__("balance-build", {"source": int, "dest": int, "troops": int})
        self._map = map

    def build(self, inputs):
        step =  MovementStep(
            source=inputs["source"], destination=inputs["dest"], troops=inputs["troops"]
        )

        self._map.get_node(step.source).value -= step.troops
        self._map.get_node(step.destination).value += step.troops

        return step




class ComputeTroops(ComputeOnMany[int]):
    """
    Computes the troops to move from the source.
    """

    def __init__(self, map: mapping.Graph):
        super().__init__(
            "compute-troops", {"source": int, "target": int, "targets": dict}
        )

        self._map = map

    def compute(self, values):
        src = self._map.get_node(values["source"])
        tgt = self._map.get_node(values["target"])
        ideal_troops = values["targets"].get(tgt.id, 1)

        can_move = src.value - 1
        missing = ideal_troops - tgt.value
        selected = min(can_move, missing)

        if selected < 1:
            debug(f"[ERROR] {selected=}, {can_move=} {missing=} {ideal_troops=} {src=} {tgt=}")
            raise ValueError("something is wrong")

        return min(can_move, missing)


class ComputeTarget(ComputeOnMany[int]):
    """
    Computes what target needs balancing.
    """

    def __init__(self, map: mapping.Graph):
        super().__init__("balance-target", {"targets": dict})
        self._map = map

    def compute(self, values: dict) -> int:
        choices = []
        targets = values["targets"]
        for key, target in targets.items():
            node = self._map.get_node(key)
            if node is None:
                raise ValueError(f"Unable to find node for key {key} on map {self._map}")
            if node.value < target:
                choices.append(key)

        return random.choice(choices) if choices else None


class ComputeSource(ComputeOnMany[Set[int]]):
    """
    Computes the sources for movement
    """

    def __init__(self, map: mapping.Graph, network_map: mapping.NetworkGraph):
        super().__init__(
            "balance-sources", {"target": int, "network": int, "targets": dict}
        )
        self._map = map
        self._network_map = network_map

    def compute(self, values):
        choices = []
        tgt = values["target"]
        targets = values["targets"]
        network = self._network_map.get_node(tgt).value
        for node in self._network_map.nodes_in_network(network):
            if node.id == tgt:
                continue

            can_move = 0
            troops = self._map.get_node(node.id).value

            if node.safe:
                can_move = troops - 1
            else:
                can_move = troops - targets.get(node.id, 1)

            if can_move > 0:
                choices.append((node.id, can_move))

        choices = sorted(choices, key=lambda n: n[1], reverse=True)
        select = choices[0][0] if choices else None

        if select:
            source = self._network_map.get_node(select)
            dest = self._network_map.get_node(tgt)

            if source.value != dest.value:
                raise ValueError(
                    f"Attempting to build move from non-connected territories::"
                    f"{source=} {dest=} {tgt=} {select=}"
                )

        return select


class CheckSources(ConditionalXor):
    """
    Checks whether we have any sources left to balance with.
    """

    def __init__(self):
        super().__init__("balance-check-sources")

    def condition(self, item):
        return item is not None


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
        self.builder = BalanceMovementBuilder(map)
        self.is_balanced = IsBalanced(map)
        self.is_not_balanced = IsNotBalanced(map)
        self.compute_target = ComputeTarget(map)
        self.compute_source = ComputeSource(map, network_map)
        self.check_source = CheckSources()
        self.compute_troops = ComputeTroops(map)
        self.reset = ResetAll("balance-reset")

        self.add_component(self.reworker)
        self.add_component(self.is_balanced)
        self.add_component(self.is_not_balanced)
        self.add_component(self.builder)
        self.add_component(self.compute_source)
        self.add_component(self.compute_target)
        self.add_component(self.check_source)
        self.add_component(self.compute_troops)
        self.add_component(self.reset)

        self.reset.add_resetables(
            self,
            [
                self.compute_source, self.compute_target, self.compute_troops,
                self.builder, self.is_not_balanced, self.is_balanced
            ]
        )

        self.add_coupling(self.i_network, self.reworker.i_network)
        self.add_coupling(self.i_targets, self.reworker.i_targets)

        self.add_coupling(self.is_not_balanced.o_true, self.compute_target.i_targets)
        self.add_coupling(self.is_not_balanced.o_false, self.reworker.i_done)

        self.add_coupling(self.reworker.o_targets, self.is_not_balanced.i_input)
        self.add_coupling(self.reworker.o_targets, self.compute_source.i_targets)
        self.add_coupling(self.reworker.o_targets, self.is_balanced.i_targets)
        self.add_coupling(self.reworker.o_targets, self.compute_troops.i_targets)

        self.add_coupling(self.reworker.o_network, self.compute_source.i_network)

        self.add_coupling(self.compute_target.o_output, self.compute_source.i_target)
        self.add_coupling(self.compute_target.o_output, self.builder.i_dest)
        self.add_coupling(self.compute_target.o_output, self.compute_troops.i_target)

        self.add_coupling(self.compute_source.o_output, self.check_source.i_input)
        self.add_coupling(self.check_source.o_false, self.reworker.i_done)
        self.add_coupling(self.check_source.o_false, self.reset.i_reset)

        self.add_coupling(self.check_source.o_true, self.builder.i_source)
        self.add_coupling(self.check_source.o_true, self.compute_troops.i_source)

        self.add_coupling(self.compute_troops.o_output, self.builder.i_troops)

        self.add_coupling(self.builder.o_step, self.o_step)

        self.add_coupling(self.builder.o_step, self.is_balanced.i_input)
        self.add_coupling(self.is_balanced.o_false, self.reworker.i_trigger)
        self.add_coupling(self.is_balanced.o_true, self.reworker.i_done)

        self.add_coupling(self.reworker.i_done, self.reset.i_reset)
        self.add_coupling(self.reworker.i_done, self.o_balanced)

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
        self.network_targets = ComputeTargets(network_map, map, player)

        self.balancer = BalancerModel(map.clone(), network_map)

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
                game_state.get_territory(action.destination),
                action.troops,
            )
            route = []
            for move in movements:
                route.append(
                    MovementStep(
                        source=move.src.id,
                        destination=move.tgt.id,
                        troops=move.amount,
                    )
                )

            if route:
                routes.append(RouteMovementStep(route, action.troops))

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
