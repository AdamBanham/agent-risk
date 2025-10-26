"""
Contains the template for what an agent is in the Risk game.
"""

from abc import ABC, abstractmethod
from typing import List
from risk.state.game_state import GameState

from risk.state.plan import Goal
from risk.state.event_stack import Event


class BaseAgent(ABC):
    """
    Abstract base class for all AI agents. Defines the interface that agents
    must implement to participate in the Risk simulation.
    """

    def __init__(
        self, player_id: int, name: str = "AI Agent", attack_probability: float = 0.5
    ):
        """
        Initialize the base agent. Sets up player identification and
        configuration.

        :param player_id: ID of the player this agent controls
        :param name: Display name for the agent
        """
        self.player_id = player_id
        self.name = name
        self.attack_probability = max(0.0, min(1.0, attack_probability))

    @abstractmethod
    def decide_placement(self, game_state: GameState, goal: Goal) -> List[Event]:
        """
        Decide where to place a reinforcement army. Called during the
        placement phase when the agent has reinforcements available.

        :param game_state: Current state of the game including all
                          territories and players
        :param goal: describes the goal of the plan to return

        returns: a plan of events to place armies
        """
        pass

    @abstractmethod
    def decide_attack(self, game_state: GameState, goal: Goal) -> List[Event]:
        """
        Decide whether to attack and which territories to use. Called during
        the attacking phase to determine if agent wants to initiate combat.

        :param game_state: Current state of the game including all
                          territories and players

        :param goal: describes the goal of the plan to return

        returns: a plan of events to attack other armies
        """
        pass

    @abstractmethod
    def decide_movement(self, game_state: GameState, goal: Goal) -> List[Event]:
        """
        Decide whether to move armies between territories. Called during the
        movement phase to determine if agent wants to relocate forces.

        :param game_state: Current state of the game including all
                          territories and players
        :param goal: describes the goal of the plan to return

        returns: a plan of events to move armies
        """
        pass
