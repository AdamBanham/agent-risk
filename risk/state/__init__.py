"""
This module contains the data structures to represent the state of the game.
The state includes information about the board, players, territories, and other
game elements.

The game state is immutable and can be serialized to and from JSON for easy storage
and transmission.
In order to make changes happen to the game state, a single action mutations 
occur to create a new immutable game state.
"""

from .territory import Territory, TerritoryState
from .game_state import GameState, Player, GamePhase
from .turn_manager import TurnManager, TurnState, TurnPhase, AttackState, MovementState
from .fight import Fight, FightPhase, FightResult, DiceRoll

__all__ = [
    'Territory',
    'TerritoryState', 
    'GameState',
    'Player',
    'GamePhase',
    'TurnManager',
    'TurnState', 
    'TurnPhase',
    'AttackState',
    'MovementState',
    'Fight',
    'FightPhase',
    'FightResult',
    'DiceRoll'
]