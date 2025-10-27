"""
Extended game loop with AI agent integration.
Enhances the base GameLoop to support automatic AI turn execution.
"""

from typing import Dict, List, Optional
from os.path import exists, join
from json import loads

from ..game.loop import GameLoop as BaseGameLoop
from ..state.game_state import GameState
from .agent import BaseAgent
from .finder import AgentStrategies, AgentTypes
from .simple.random import RandomAgent
from ..engine import Engine
from ..state.event_stack import MovementPhase, AttackPhase, PlacementPhase, Event
from ..state.event_stack import AgentTurnEndEvent
from ..state.event_stack import PauseProcessingEvent


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
            agent = self._agents[state.current_player_id]
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

    def process(self, state, element):
        return [PauseProcessingEvent(self.ai_turn_delay)]


class AIGameLoop(BaseGameLoop):
    """
    Extended game loop that supports AI agent turn execution. Automatically
    executes turns for AI players while maintaining human interaction for
    human players.
    """

    def __init__(
        self,
        width: int = 1800,
        height: int = 1028,
        regions: int = 27,
        num_players: int = 3,
        starting_armies: int = 10,
        play_from_state: Optional[GameState] = None,
        ai_turn_delay: float = 1.0,
        sim_delay: float = 1.0,
        sim_speed: int = 5,
    ) -> None:
        """
        Initialize the AI-enabled game loop. Extends base GameLoop with agent
        controller support.

        :param args: Arguments passed to base GameLoop
        :param kwargs: Keyword arguments passed to base GameLoop
        """
        super().__init__(
            width=width,
            height=height,
            regions=regions,
            num_players=num_players,
            starting_armies=starting_armies,
            play_from_state=play_from_state,
            sim_delay=sim_delay,
            sim_speed=sim_speed,
        )
        self.ai_turn_delay = (
            ai_turn_delay  # Seconds to wait between AI actions for visibility
        )
        self.last_ai_action_time = 0.0
        self.ai_turn_in_progress = False
        self._ai_engine = AiEngine("AI Engine")
        self.sim_controller.add_engine(self._ai_engine)
        self.sim_controller.add_engine(
            AiDelayEngine("AI Delay Engine", self.ai_turn_delay)
        )

    def add_ai_to_player(self, agent, player_id: int) -> None:
        """
        Add an AI agent to control a specific player in the game.

        :param agent: AI agent instance
        :param player_id: ID of the player to be controlled by the agent
        """
        self._ai_engine.add_ai_for_player(agent, player_id)


def create_ai_game(
    regions: int = 15,
    num_players: int = 3,
    starting_armies: int = 20,
    ai_player_ids: list = None,
    attack_probability: float = 0.5,
    ai_delay: float = 1.0,
    play_from_state: GameState = None,
    sim_delay: float = 1.0,
    sim_speed: int = 5,
) -> AIGameLoop:
    """
    Factory function to create a complete AI-enabled game setup. Creates game
    loop, agent controller, and configures AI players.

    :param regions: Number of territories to generate (g parameter)
    :param num_players: Number of players in the simulation (p parameter)
    :param starting_armies: Starting army size per player (s parameter)
    :param ai_player_ids: List of player IDs to be controlled by AI agents
    :param attack_probability: Probability that AI agents will attack when
                              opportunities arise
    :param ai_delay: Delay in seconds between AI actions for visibility
    :returns: Configured AIGameLoop ready to run with AI agents
    """
    if ai_player_ids is None:
        ai_player_ids = list(range(1, num_players))  # Default: all except player 0

    humans = [pid for pid in range(num_players) if pid not in ai_player_ids]

    # Create the enhanced game loop
    game_loop = AIGameLoop(
        width=1800,
        height=1028,
        regions=regions,
        num_players=num_players,
        starting_armies=starting_armies,
        play_from_state=play_from_state,
        ai_turn_delay=ai_delay,
        sim_delay=sim_delay,
        sim_speed=sim_speed,
    )

    # Set up AI agents if specified
    if ai_player_ids:

        # check for config file for the agents ('ai.config')
        if exists(join(".", "ai.config")):
            print("ai.config file found, configuring AI agents accordingly.")
            config = loads(open(join(".", "ai.config"), "r").read())

            for player_id in ai_player_ids:
                player_setup = config.get(str(player_id), None)
                if player_setup:
                    agent_type = player_setup.get("type", "bt")
                    attack_probability = player_setup.get(
                        "attack_probability", attack_probability
                    )
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
                    game_loop.add_ai_to_player(agent, player_id)
                else:
                    print(
                        f"No configuration found for player {player_id}, using default RandomAgent."
                    )
                    agent = RandomAgent(
                        player_id=player_id, attack_probability=attack_probability
                    )
                    game_loop.add_ai_to_player(agent, player_id)
        else:
            print(
                "No ai.config file found, defaulting to RandomAgents for all AI players."
            )
            for player_id in ai_player_ids:
                agent = RandomAgent(
                    player_id=player_id, attack_probability=attack_probability
                )
                game_loop.add_ai_to_player(agent, player_id)

    # Mark human players in the game state
    for human in humans:
        game_loop.game_state.get_player(human).is_human = True

    return game_loop
