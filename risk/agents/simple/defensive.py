"""
Simple random AI agent for the Risk simulation.
Makes defensive decisions for placement, attacking, and movement phases.
"""

import random
from typing import List

from ...state.game_state import GameState
from ...utils.movement import find_movement_sequence
from ...utils.movement import find_safe_frontline_territories
from ...utils.groups import find_connected_groups
from risk.utils.logging import debug, info


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

        _, frontlines = find_safe_frontline_territories(
            game_state=game_state, player_id=self.player_id
        )

        n_most = random.uniform(1, len(frontlines))
        top_most = sorted(frontlines, key=lambda t: t.armies, reverse=True)[
            : int(n_most)
        ]
        events = []
        for i in range(game_state.placements_left):
            if top_most:
                selected_territory = top_most[int(i % len(top_most))]
                event = TroopPlacementEvent(
                    turn=game_state.total_turns,
                    player=self.player_id,
                    territory=selected_territory.id,
                    num_troops=1,
                )
                events.append(event)

        return events

    def decide_attack(self, game_state: GameState, goal: Goal) -> List[Event]:

        _, frontlines = find_safe_frontline_territories(
            game_state=game_state, player_id=self.player_id
        )

        events = []

        for front in frontlines:
            for adjacent in front.adjacent_territories:
                if adjacent.owner != self.player_id:
                    safe_troop_count = max(adjacent.armies + 5, adjacent.armies * 2)
                    if front.armies > safe_troop_count:
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
        elif len(events) < 1:
            debug(f"simple-defensive-agent-{self.player_id} did not find attack")

            strongest_front = max(
                frontlines, key=lambda t: t.armies, default=None
            )
            if strongest_front:
                enemies = [
                    adj
                    for adj in strongest_front.adjacent_territories
                    if adj.owner != self.player_id
                ]
                weakest_enemy = min(
                    enemies, key=lambda t: t.armies, default=None
                )
                if weakest_enemy:
                    event = AttackOnTerritoryEvent(
                        player=self.player_id,
                        turn=game_state.total_turns,
                        from_territory=strongest_front.id,
                        to_territory=weakest_enemy.id,
                        attacking_troops=strongest_front.armies // 2,
                    )
                    events.append(event)

        return events

    def decide_movement(self, game_state: GameState, goal: Goal) -> List[Event]:

        safes, frontlines = find_safe_frontline_territories(
            game_state=game_state, player_id=self.player_id
        )
        if len(safes) == 0 or len(frontlines) == 0:
            return []
        
        groups = find_connected_groups(safes + frontlines)
        events = []

        info(f"Found groups: {len(groups)}")
        for group in groups:
            info(f"Processing group: {set(g.id for g in group)}")

            if len(group) < 2:
                continue

            total_armies = sum(t.armies for t in group)
            armies = {t.id: t.armies for t in group}
            moveable = total_armies - len(group)
            fronts = [t for t in group if t in frontlines]
            ideal_troops = moveable // len(fronts)
            missing = dict(
                (t, ideal_troops - t.armies)
                for t in fronts if t.armies < ideal_troops
            )

            for tgt, troops in missing.items():
                for src in group:
                    if src.id == tgt.id or src.id in missing:
                        continue

                    if src not in fronts:
                        can_move = armies[src.id] - 1
                    else:
                        can_move = armies[src.id] - ideal_troops
                        
                    if can_move <= 0:
                        continue

                    path = find_movement_sequence(
                        src,
                        tgt,
                        can_move
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

        return events
