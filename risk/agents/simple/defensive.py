"""
Simple random AI agent for the Risk simulation.
Makes defensive decisions for placement, attacking, and movement phases.
"""

import random
from typing import List

from ...state.game_state import GameState
from ...utils.movement import find_movement_sequence
from risk.utils.logging import debug, info
from risk.utils import map

from ..agent import BaseAgent
from risk.state.plan import Goal
from risk.state.event_stack import (
    TroopPlacementEvent,
    AttackOnTerritoryEvent,
    MovementOfTroopsEvent,
    Event,
)


class DefensiveAgent(BaseAgent):
    """
    A simple defensive AI agent that makes decisions for placement, attacking,
    and movement phases in the Risk simulation.

    :param player_id: ID of the player this agent controls
    :param attack_probability: Unused parameter for compatibility
    """

    def __init__(self, player_id: int, attack_probability: float = 0.5):
        super().__init__(
            player_id, "simple-defensive-agent-{}".format(player_id), attack_probability
        )

    def decide_placement(self, game_state: GameState, goal: Goal) -> List[Event]:
        info(f"{self.name} deciding placements...")
        current_map = game_state.map
        safe_map = map.construct_safe_view(current_map, self.player_id)

        n_most = random.randint(1, len(safe_map.frontline_nodes))
        top_most = sorted(
            safe_map.frontline_nodes,
            key=lambda t: current_map.get_node(t.id).value,
            reverse=True,
        )[: int(n_most)]

        events = []
        for i in range(game_state.placements_left):
            if top_most:
                map_node = top_most[int(i % len(top_most))]
                selected_territory = game_state.get_territory(map_node.id)
                event = TroopPlacementEvent(
                    turn=game_state.total_turns,
                    player=self.player_id,
                    territory=selected_territory.id,
                    num_troops=1,
                )
                events.append(event)

        return events

    def decide_attack(self, game_state: GameState, goal: Goal) -> List[Event]:
        info(f"{self.name} deciding attacks...")
        current_map = game_state.map
        safe_map = map.construct_safe_view(current_map, self.player_id)

        events = []

        for front in safe_map.frontline_nodes:
            front_terr = current_map.get_node(front.id)
            for adjacent in current_map.get_adjacent_nodes(front.id):
                if adjacent.owner != self.player_id:
                    adj_terr = current_map.get_node(adjacent.id)
                    safe_troop_count = max(adj_terr.value + 5, adj_terr.value * 3)
                    if (front_terr.value - 1) > safe_troop_count:
                        event = AttackOnTerritoryEvent(
                            player=self.player_id,
                            turn=game_state.total_turns,
                            from_territory=front.id,
                            to_territory=adjacent.id,
                            attacking_troops=safe_troop_count,
                        )
                        events.append(event)
                        break

        if len(events) > 10:
            events = random.choices(events, k=10)

        return events

    def decide_movement(self, game_state: GameState, goal: Goal) -> List[Event]:
        info(f"{self.name} deciding movement...")
        current_map = game_state.map
        network_map = map.construct_network_view(current_map, self.player_id)

        all_events = []
        for network in network_map.networks:
            group = network_map.view(network)
            debug(f"Processing group: {set(g for g in group.nodes)}")

            if group.size <= 1:
                continue

            armies = {t.id: current_map.get_node(t.id).value for t in group.nodes}
            total_armies = sum(armies.values())
            fronts = group.frontlines_in_network(network)
            moveable = total_armies - (group.size - len(fronts))
            ideal_troops = moveable // len(fronts)
            missing = dict(
                (t, ideal_troops - armies[t.id])
                for t in fronts
                if armies[t.id] < ideal_troops
            )

            events = []
            for tgt, troops in missing.items():
                for src in group.nodes:
                    if src.id == tgt.id or src.id in missing:
                        continue

                    if src not in fronts:
                        can_move = armies[src.id] - 1
                    else:
                        can_move = armies[src.id] - ideal_troops

                    if can_move <= 0:
                        continue

                    path = find_movement_sequence(
                        game_state.get_territory(src.id),
                        game_state.get_territory(tgt.id),
                        can_move,
                    )

                    if path:
                        move_troops = min(can_move, troops)
                        armies[src.id] -= move_troops
                        armies[tgt.id] += move_troops
                        for move in reversed(path):
                            event = MovementOfTroopsEvent(
                                player=self.player_id,
                                turn=game_state.total_turns,
                                from_territory=move.src.id,
                                to_territory=move.tgt.id,
                                moving_troops=move_troops,
                            )
                            events.append(event)
                        troops -= move_troops

                    if troops <= 0:
                        break
            all_events.extend(reversed(events))

        return reversed(all_events)
