"""
Extended game loop with AI agent integration.
Enhances the base GameLoop to support automatic AI turn execution.
"""

from typing import Optional, List
from ..game.loop import GameLoop as BaseGameLoop
from ..state.game_state import GameState
from .ai import create_ai_setup


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

    def _setup_ai(
        self,
        ai_player_ids: List[int],
        default_attack_prob: float,
        ai_delay: float = 1.0,
        configured_from_file: bool = True,
    ) -> None:
        """
        Add the appropriate AI engines to the simulation controller.
        Agent policies are determined from 'ai.config' file if present,
        otherwise default to RandomAgent.

        :param agent: AI agent instance
        :param player_id: ID of the player to be controlled by the agent
        """
        for engine in create_ai_setup(
            ai_player_ids,
            default_attack_prob,
            ai_delay,
            configured_from_file,
        ):
            self.sim_controller.add_engine(engine)


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
        game_loop._setup_ai(
            ai_player_ids,
            attack_probability,
            ai_delay,
        )
    input("Press Enter to start the game...")

    # Mark human players in the game state
    for human in humans:
        game_loop.game_state.get_player(human).is_human = True

    return game_loop
