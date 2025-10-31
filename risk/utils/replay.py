from typing import Callable, Tuple, Union
from risk.engine.controller import SimulationController
from risk.state.event_stack import Event, Level
from risk.state.game_state import GameState
from risk.agents.ai import create_ai_setup
from risk.engine.risk import RiskSimulationController
from risk.engine.risk import RiskForwardEngine
from risk.engine.risk import RiskRecordEngine
from dataclasses import dataclass


@dataclass
class SimulationConfiguration:
    attack_rate: float = 0.5
    load_ai_from_file: bool = False


def simulate_turns(
    game_state: GameState, turns: int, config: SimulationConfiguration = None
) -> Tuple[GameState, RiskRecordEngine]:
    """
    Runs a risk simulation forward for a specified number of turns.
    Uses a random policy for all player turns and will make a copy
    of the given game state to avoid modifying the original.

    :returns: A tuple of the final GameState and the RiskRecordEngine used
    to record the simulation events.
    """

    # import needed classes for the repr to work
    from risk.state.game_state import GameState, Player, Territory, GamePhase
    from risk.state.territory import TerritoryState

    if config is None:
        config = SimulationConfiguration()

    state: GameState = eval(repr(game_state))
    state.initialise(False)
    state.update_player_statistics()

    start = state.current_turn

    controller = RiskSimulationController(state)
    for engine in create_ai_setup(
        list(range(state.num_players)),
        config.attack_rate,
        0,
        config.load_ai_from_file,
        False,
    ):
        controller.add_engine(engine)

    controller.add_engine(
        RiskForwardEngine(turns, starting_turn=state.current_turn)
    )

    action = controller.step()
    while action:
        action = controller.step()

    print("Simulation complete.")
    print(f"Started from turn {start}.")
    print(f"Simulated until final turn of {controller.game_state.current_turn}")

    return state, controller.tape


def simulate_stack_until(
    controller: SimulationController, condition: Callable[Union[Event, Level], bool]
) -> GameState:
    """
    Simulates the event stack until a certain condition is met
    based on the next event or level on the stack.

    :param controller: The simulation controller managing the simulation.
    :param condition: A callable that takes an Event or Level and returns
    a boolean indicating whether to stop the simulation.
    :returns: The GameState after simulation.
    """
    pass
