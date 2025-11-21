"""
Simple random AI agent for the Risk simulation.
Makes aggressive decisions for placement, attacking, and movement phases.
"""

from typing import List
from copy import deepcopy

from ...state.game_state import GameState
from ...utils.movement import find_movement_sequence
from risk.utils import map as mapping
from risk.utils.logging import debug, info


from ..agent import BaseAgent
from risk.state.plan import Goal
from risk.state.event_stack import (
    TroopPlacementEvent,
    AttackOnTerritoryEvent,
    MovementOfTroopsEvent,
    Event,
)


class AggressiveAgent(BaseAgent):
    """
    A simple aggressive AI agent that makes decisions for placement, attacking,
    and movement phases in the Risk simulation.

    :param player_id: ID of the player this agent controls
    :param attack_probability: Unused parameter for compatibility
    """

    def __init__(self, player_id: int, attack_probability: float = 0.5):
        super().__init__(
            player_id,
            "simple-aggressive-agent-{}".format(player_id),
            attack_probability,
        )
        self.front = None

    def decide_placement(self, game_state: GameState, goal: Goal) -> List[Event]:
        info(f"{self.name} deciding placements...")
        # find frontline territories with attack potential
        map = game_state.map
        safe_map = mapping.construct_safe_view(map, self.player_id)
        fronts = safe_map.frontline_nodes

        def sum_of_adjacents(node: mapping.SafeNode) -> int:
            total = 0
            armies = map.get_node(node.id).value
            for neighbor in map.get_adjacent_nodes(node.id):
                if neighbor.owner != self.player_id:
                    total += armies / neighbor.value
            return total

        fronts = sorted(fronts, key=sum_of_adjacents, reverse=True)
        self.front = fronts[0]

        if sum_of_adjacents(self.front) < 0.25:
            self.front = None
            return []

        events = [
            TroopPlacementEvent(
                turn=game_state.current_turn,
                player=self.player_id,
                territory=self.front.id,
                num_troops=game_state.placements_left,
            )
        ]

        return events

    def decide_attack(self, game_state: GameState, goal: Goal) -> List[Event]:
        info(f"{self.name} deciding attacks...")
        if self.front is None:
            return []

        # find the weakest adjacent enemy territory to attack
        map = game_state.map
        adjacents = map.get_adjacent_nodes(self.front.id)
        adjacents = [o for o in adjacents if o.owner != self.player_id]

        def strength(o: mapping.Node) -> float:
            return o.value

        adjacents = sorted(adjacents, key=strength)

        # build chain of attacks, starting with the first
        target = adjacents[0]
        attacking = map.get_node(self.front.id).value - 1
        events = [
            AttackOnTerritoryEvent(
                turn=game_state.current_turn,
                player=self.player_id,
                from_territory=self.front.id,
                to_territory=target.id,
                attacking_troops=attacking,
            )
        ]
        ## it would be nice if we had a way to connect future attacks
        ## with the outcomes of the previous
        ## this is likely future work though...
        attacking = attacking // 2
        last = target.id
        while attacking > 1:
            adjacents = map.get_adjacent_nodes(last)
            adjacents = [o for o in adjacents if o.owner != self.player_id]
            if not adjacents:
                break
            adjacents = sorted(adjacents, key=strength)
            target = adjacents[0]
            events.append(
                AttackOnTerritoryEvent(
                    turn=game_state.current_turn,
                    player=self.player_id,
                    from_territory=last,
                    to_territory=target.id,
                    attacking_troops=attacking,
                )
            )
            last = target.id
            attacking = attacking // 2

        debug(f"{self.name} planned attacks: {events}")
        return list(reversed(events))

    def decide_movement(self, game_state: GameState, goal: Goal) -> List[Event]:
        info(f"{self.name} deciding movement...")
        events = []

        def sum_of_adjacents(node: mapping.SafeNode) -> int:
            total = 0
            armies = map.get_node(node.id).value
            for neighbor in map.get_adjacent_nodes(node.id):
                if neighbor.owner != self.player_id:
                    total += armies / neighbor.value
            return total

        # distribute within network based on possible next attacks
        map = game_state.map
        network_map = mapping.construct_network_view(map, self.player_id)

        for network in network_map.networks:
            network_view = network_map.view(network)

            # work out the distribution of troops to each frontline territory
            fronts = network_view.frontlines_in_network(network)
            movable_armies = sum(node.value for node in network_view.nodes)
            movable_armies -= network_view.size
            weights = [sum_of_adjacents(node) for node in fronts]
            total_weight = sum(weights)
            weights = [w / total_weight for w in weights]
            troops = [min(1, int(movable_armies * w)) for w in weights]

            ordered_fronts = sorted(
                zip(fronts, troops),
                key=lambda x: x[1],
                reverse=True,
            )

            # fill frontline territories from most to least important
            secured_terrs = set()
            move_map = deepcopy(map)
            for front, num_troops in ordered_fronts:
                for node in network_view.nodes:
                    if (
                        node.id != front.id
                        and node.id not in secured_terrs
                        and move_map.get_node(node.id).value > 1
                    ):
                        movable = min(
                            num_troops,
                            move_map.get_node(node.id).value - 1,
                        )

                        if movable <= 0:
                            continue

                        path = find_movement_sequence(
                            game_state.get_territory(node.id),
                            game_state.get_territory(front.id),
                            movable,
                        )
                        if path is not None:
                            route = []
                            for move in path:
                                route.append(
                                    MovementOfTroopsEvent(
                                        player=self.player_id,
                                        turn=game_state.current_turn,
                                        from_territory=move.src.id,
                                        to_territory=move.tgt.id,
                                        moving_troops=move.amount,
                                    )
                                )
                            events.extend(reversed(route))
                            move_map.get_node(node.id).value -= movable
                            move_map.get_node(front.id).value += movable

                    if num_troops <= 0:
                        secured_terrs.add(front.id)
                        break

        return events
