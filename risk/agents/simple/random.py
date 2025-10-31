"""
Simple random AI agent for the Risk simulation.
Makes random decisions for placement, attacking, and movement phases.
"""

import random
from typing import List

from ...state.game_state import GameState
from ...utils.movement import find_movement_sequence, Movement
from ...utils.movement import find_safe_frontline_territories
from ...utils.movement import find_connected_frontline_territories


from ..agent import BaseAgent
from risk.state.plan import Goal
from risk.state.event_stack import (
    TroopPlacementEvent,
    AttackOnTerritoryEvent,
    MovementOfTroopsEvent,
    Event,
)


class RandomAgent(BaseAgent):
    """
    A simple random AI agent that makes decisions for placement, attacking,
    and movement phases in the Risk simulation.

    :param player_id: ID of the player this agent controls
    :param attack_probability: Probability (0.0-1.0) that agent will attack
                               when it has the opportunity
    """

    def __init__(self, player_id: int, attack_probability: float = 0.5):
        super().__init__(
            player_id, "Random-Agent-{}".format(player_id), attack_probability
        )

    def decide_placement(self, game_state: GameState, goal: Goal) -> List[Event]:
        # print(f"simple-random-agent-{self.player_id} planning for placement")
        owned_territories = game_state.get_territories_owned_by(self.player_id)
        placements = game_state.placements_left

        # Place one army at a time randomly
        events = []
        for _ in range(placements):
            if owned_territories:
                selected_territory = random.choice(owned_territories)
                event = TroopPlacementEvent(
                    turn=game_state.total_turns,
                    player=self.player_id,
                    territory=selected_territory.id,
                    num_troops=1,
                )
                events.append(event)

        return events

    def decide_attack(self, game_state: GameState, goal: Goal) -> List[Event]:
        # print(f"simple-random-agent-{self.player_id} planning for attack")
        owned_territories = game_state.get_territories_owned_by(self.player_id)
        attack_events = []

        # try to pick for ten attacks
        # (should be possible at all times)
        pick = random.uniform(0, 1)
        while pick <= self.attack_probability and len(attack_events) < 10:

            territory = random.choice(owned_territories)
            adjacents = list(territory.adjacent_territories)
            adjacent = random.choice(adjacents)

            attack_events.append(
                AttackOnTerritoryEvent(
                    player=self.player_id,
                    turn=game_state.total_turns,
                    from_territory=territory.id,
                    to_territory=adjacent.id,
                    attacking_troops=random.choice(range(0, max(territory.armies, 1))),
                )
            )

            pick = random.uniform(0, 1)

        return attack_events

    def decide_movement(self, game_state: GameState, goal: Goal) -> List[Event]:
        """
        This agent tries to move armies if and only if it has safe territories.
        A safe territory is defined as one that has no adjacent enemy territories.
        It will then attempt to move armies from safe territories to front-line
        territories (those adjacent to enemy territories) using connected paths.

        It will only make one of these routes per turn, chosen at random, if
        possible.
        """
        # print(f"simple-random-agent-{self.player_id} planning for movement")
        # Get all territories owned by this agent
        safe, frontline = find_safe_frontline_territories(
            game_state=game_state, player_id=self.player_id
        )

        # Only move if we have safe territories
        if not safe:
            return []

        # Find safe territories that can move armies (have more than 1 army)
        moveable = [t for t in safe if t.armies > 1]
        if not moveable:
            return None

        # Find connected paths from safe territories to front-line territories
        valid_movements = []

        for safe_territory in moveable:
            reachable_frontline = find_connected_frontline_territories(
                safe_territory, frontline, safe + frontline
            )

            for target_territory in reachable_frontline:
                # Calculate how many armies to move (all but one)
                armies_to_move = safe_territory.armies - 1
                if armies_to_move > 0:
                    valid_movements.append(
                        find_movement_sequence(
                            safe_territory, target_territory, armies_to_move
                        )
                    )

        # Randomly select a movement if any are available
        events = []
        if valid_movements:
            route: List[Movement] = random.choice(valid_movements)

            for move in route:
                events.append(
                    MovementOfTroopsEvent(
                        player=self.player_id,
                        turn=game_state.total_turns,
                        from_territory=move.src.id,
                        to_territory=move.tgt.id,
                        moving_troops=move.amount,
                    )
                )

        return events
