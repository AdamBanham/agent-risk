"""
Simple random AI agent for the Risk simulation.
Makes random decisions for placement, attacking, and movement phases.
"""

import random
from typing import List

from ...state.game_state import GameState
from ...utils.movement import find_movement_sequence, Movement
from risk.utils import map as mapping
from risk.utils.logging import info


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
            player_id, "simnple-random-agent-{}".format(player_id), attack_probability
        )

    def decide_placement(self, game_state: GameState, goal: Goal) -> List[Event]:
        info(f"{self.name} planning for placement...")
        owned_territories = game_state.get_territories_owned_by(self.player_id)
        placements = game_state.placements_left

        # Place one army at a time randomly
        events = []
        for _ in range(placements):
            if owned_territories:
                selected_territory = random.choice(owned_territories)
                event = TroopPlacementEvent(
                    turn=game_state.current_turn,
                    player=self.player_id,
                    territory=selected_territory.id,
                    num_troops=1,
                )
                events.append(event)

        return events

    def decide_attack(self, game_state: GameState, goal: Goal) -> List[Event]:
        info(f"{self.name} planning for attack...")

        # pick a frontline territory with more than one troop
        map = game_state.map
        safe_map = mapping.construct_safe_view(map, self.player_id)
        terrs = set(
            n.id for n in safe_map.frontline_nodes if map.get_node(n.id).value > 2
        )
        attack_events = []

        # try to pick for ten attacks
        # (should be possible at all times)
        pick = random.uniform(0, 1)
        while (
            pick <= self.attack_probability
            and len(attack_events) < 10
            and len(terrs) > 0
        ):

            # select and remove terr
            territory = random.choice(list(terrs))
            terrs.remove(territory)
            adjacents = list(
                n.id
                for n in map.get_adjacent_nodes(territory)
                if n.owner != self.player_id
            )
            if not adjacents:
                continue
            adjacent = random.choice(adjacents)

            # compute parameters for attack
            troops = map.get_node(territory).value - 1
            if troops > 1:
                troops = random.randint(1, troops)
            attack_events.append(
                AttackOnTerritoryEvent(
                    player=self.player_id,
                    turn=game_state.current_turn,
                    from_territory=territory,
                    to_territory=adjacent,
                    attacking_troops=troops,
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
        info(f"{self.name} planning for movement...")
        # Get all territories owned by this agent
        map = game_state.map
        safe_map = mapping.construct_safe_view(map, self.player_id)
        network_map = mapping.construct_network_view(map, self.player_id)
        safes = safe_map.safe_nodes

        # Only move if we have safe territories
        if not safes:
            return []

        # Find safe territories that can move armies (have more than 1 army)
        moveable = [t for t in safes if mapping.get_value(map, t.id) > 1]
        if not moveable:
            return None

        # Find connected paths from safe territories to front-line territories
        valid_movements = []

        for sterr in moveable:
            network = mapping.get_value(network_map, sterr.id)
            reachable_frontline = network_map.frontlines_in_network(network)

            for tgt in reachable_frontline:
                # Calculate how many armies to move (all but one)
                armies_to_move = mapping.get_value(map, sterr.id) - 1
                if armies_to_move > 0:
                    valid_movements.append(
                        find_movement_sequence(
                            game_state.get_territory(sterr.id), 
                            game_state.get_territory(tgt.id), 
                            armies_to_move
                        )
                    )

        # Randomly select a movement if any are available
        events = []
        if valid_movements:
            route: List[Movement] = random.choice(valid_movements)

            for move in reversed(route):
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
