from risk.agents.agent import BaseAgent
from risk.agents.simple import RandomAgent
from risk.engine import Engine
from risk.state.event_stack import (
    AgentTurnEndEvent,
    AttackPhase,
    Event,
    MovementPhase,
    PauseProcessingEvent,
    PlacementPhase,
)
from risk.state.game_state import GameState

from .finder import AgentStrategies, AgentTypes
from os.path import exists, join
from json import loads

from typing import Dict, List, Optional


class AiEngine(Engine):
    """
    Handles the integration of AI agents within the game engine.
    """

    allowed_elements = [MovementPhase, AttackPhase, PlacementPhase]

    def __init__(self, engine_id):
        super().__init__(engine_id)
        self._agents: Dict[int, BaseAgent] = {}

    def process(self, state: GameState, element: Event) -> Optional[List[Event]]:

        if state.current_player_id in self._agents:
            agent: BaseAgent = self._agents[state.current_player_id]
        else:
            return super().process(state, element)

        if isinstance(element, MovementPhase):
            # Process movement phase with AI logic
            return agent.decide_movement(state, goal=None)
        elif isinstance(element, AttackPhase):
            # Process attack phase with AI logic
            return agent.decide_attack(state, goal=None)
        elif isinstance(element, PlacementPhase):
            # Process placement phase with AI logic
            return agent.decide_placement(state, goal=None)

        return super().process(state, element)

    def add_ai_for_player(self, agent: BaseAgent, player_id: int) -> None:
        """
        Associate an AI agent with a specific player in the game.

        :param agent: AI agent instance
        :param player_id: ID of the player to associate with the agent
        """
        self._agents[player_id] = agent


class AiDelayEngine(Engine):
    """
    Adds a delay before processing AI turns to improve visibility.
    """

    allowed_elements = [AgentTurnEndEvent]

    def __init__(self, engine_id, ai_turn_delay: float = 1.0):
        super().__init__(engine_id)
        self.ai_turn_delay = ai_turn_delay

    def process(self, state: GameState, element: Event) -> Optional[List[Event]]:
        return [PauseProcessingEvent(self.ai_turn_delay)]


def create_ai_setup(
    ai_player_ids: List[int],
    attack_probability: float = 0.5,
    ai_delay: float = 1.0,
    configure_from_file: bool = True,
    with_delay_engine: bool = True,
) -> List[Engine]:
    """
    Factory function to create AI engines for the game.

    :param ai_player_ids: List of player IDs to be controlled by AI agents
    :param attack_probability: Probability of attacking during the attack phase
    :param ai_delay: Delay in seconds before processing AI turns
    :return: List of configured AI engines
    """
    ai_engines = []

    ai_engine = AiEngine("AI Engine")
    for player_id in ai_player_ids:
        print(f"Configuring AI for player {player_id}")
        if configure_from_file:
            if not determine_ai_policy(player_id, ai_engine):
                add_random_ai_policy(player_id, attack_probability, ai_engine)
        else:
            add_random_ai_policy(player_id, attack_probability, ai_engine)
    ai_engines.append(ai_engine)

    if with_delay_engine:
        ai_delay_engine = AiDelayEngine("AI Delay Engine", ai_turn_delay=ai_delay)
        ai_engines.append(ai_delay_engine)

    return ai_engines


def add_random_ai_policy(
    player_id: int, attack_probability: float, engine: AiEngine
) -> None:
    """
    Add a random AI policy to the specified player in the AI engine.

    :param player_id: ID of the player to add the AI policy for
    :param engine: AiEngine instance to add the AI policy to
    """
    agent = RandomAgent(
        player_id,
        attack_probability=attack_probability,
    )
    print(
        f"Add random agent policy for player {player_id} with attack probability {attack_probability}"
    )
    engine.add_ai_for_player(agent, player_id)


def determine_ai_policy(player_id: int, engine: AiEngine) -> bool:
    """
    Determine the AI policy for a given player ID from a configuration file.
    Looks locally for an 'ai.config' file in JSON format.

    :param player_id: ID of the player
    :return: whether the AI policy was successfully determined
    """
    if exists(join(".", "ai.config")):
        print("ai.config file found, configuring AI agents accordingly.")
        config = loads(open(join(".", "ai.config"), "r").read())

        player_setup = config.get(str(player_id), None)
        if player_setup:
            agent_type = player_setup.get("type", "bt")
            attack_probability = player_setup.get("attack_probability", 0.5)
            agent_family = AgentTypes.get_selector(agent_type)
            strat = AgentStrategies.find(player_setup.get("strat", "random"))
            agent_class = agent_family.get_agent(strat)
            agent = agent_class(
                player_id=player_id, attack_probability=attack_probability
            )
            print(
                (
                    f"Configured AI Agent for player {player_id}: "
                    f"Type={agent_type}, "
                    f"Strategy={strat}, "
                    f"Attack Probability={attack_probability}"
                )
            )
            engine.add_ai_for_player(agent, player_id)
            return True
        else:
            return False
    return False
