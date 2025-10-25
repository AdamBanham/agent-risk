import unittest

from risk.state import GameState
import random


class TestAdvanceTurn(unittest.TestCase):

    def setUp(self):
        self.state = GameState.create_new_game(5, 5, 10)
        self.state.initialise()

    def test_simple_advance(self):
        
        turn = self.state.current_turn
        for _ in range(5):
            current_player = self.state.current_player_id

            self.state.advance_turn()

            self.assertEqual(
                self.state.current_player_id, 
                (current_player + 1) % len(self.state.players)
            )

        self.assertEqual(
            self.state.current_turn,
            turn + 1
        )

    def test_starting_dead(self):

        starting = self.state.get_player(
            self.state.starting_player
        )
        starting.is_active = False
        for territory in starting.territories_controlled:
            territory = self.state.get_territory(territory)
            territory.set_owner(None)

        self.state.update_player_statistics()

        turn = self.state.current_turn
        for _ in range(5):
            self.state.advance_turn()

        self.assertGreater(
            self.state.current_turn,
            turn
        )

    def test_several_dead_players(self):
        seen = set()
        options = set(range(5))
        for _ in range(3):
            pick = random.choice(list(options.difference(seen)))
            seen.add(pick)
            player = self.state.get_player(
                pick
            )
            player.is_active = False
            for territory in player.territories_controlled:
                territory = self.state.get_territory(territory)
                territory.set_owner(None)

        turn = self.state.current_turn
        for _ in range(5):
            self.state.advance_turn()

        self.assertGreater(
            self.state.current_turn,
            turn
        )
