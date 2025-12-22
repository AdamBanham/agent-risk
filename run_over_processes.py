"""
This testings the option of having the visualisation be an observer of the
simulation rather than being coupled on the same process as the simulation.

The benefits of this approach is that we can get a more responsive UI
without hangs where the agents hog the processing thread when performing
decision making.
"""

from risk.state import GameState
from risk.utils.loading import load_game_state_from_file
from risk.engine.risk import RiskSimulationController
from risk.agents import create_ai_setup
from risk.game.loop_process import GameLoop
from risk.utils.logging import setLevel, info
from logging import DEBUG

from multiprocessing import Queue, Process, Event
from multiprocessing.queues import Queue as TQueue
from multiprocessing.synchronize import Event as TEvent

import pygame


def run_simulation(
    event_queue: TQueue, control_queue: TQueue, game_state: str, stop_event: TEvent
):
    """
    Simulation process - runs the Risk engine.

    :param event_queue: Queue for sending events to visualization
    :param control_queue: Queue for receiving control commands
    :param game_state: Initial game state
    """

    # setLevel(DEBUG)

    game_state: GameState = load_game_state_from_file(game_state)
    game_state.initialise(False)
    game_state.update_player_statistics()

    event_queue.put(game_state.starting_player)

    while control_queue.empty():
        pass
    control_queue.get()

    sim_controller = RiskSimulationController(game_state)

    for engine in create_ai_setup(range(game_state.num_players), 0.85):
        sim_controller.add_engine(engine)

    while not stop_event.is_set():
        # Check for control commands (pause, speed change, etc.)
        if not control_queue.empty():
            command = control_queue.get()
            sim_controller.stack.push(command)

        # Process simulation step
        action = sim_controller.step()
        if action:
            # Send event to visualization process
            event_queue.put(sim_controller._last)

        # info("simulation::stepped..")

    with open("communication_a.stack", "w") as f:
        f.write(str(sim_controller.tape.stack))


def run_visualization(
    event_queue: TQueue, control_queue: TQueue, initial_state: str, stop_event: TEvent
):
    """
    Visualization process - runs the pygame UI.

    :param event_queue: Queue for receiving events from simulation
    :param control_queue: Queue for sending control commands
    :param initial_state: Initial game state
    """
    pygame.init()
    setLevel(DEBUG)
    # Local copy of game state
    game_state: GameState = load_game_state_from_file(initial_state)
    game_state.initialise(False)
    game_state.update_player_statistics()

    while event_queue.empty():
        pass

    starting = event_queue.get()
    assert (
        game_state.starting_player == starting
    ), "expected the starting players to be same"
    
    loop = GameLoop(
        regions=game_state.regions,
        num_players=game_state.num_players,
        starting_armies=game_state.starting_armies,
        play_from_state=game_state,
        event_que=event_queue,
        control_que=control_queue,
    )

    loop.run()

    stop_event.set()

    with open("communication_b.stack", "w") as f:
        f.write(str(loop.stack))


def main():
    """
    Entry point - spawns simulation and visualization processes.
    """
    # Create communication queues
    event_queue = Queue()  # Sim -> Viz
    control_queue = Queue()  # Viz -> Sim
    stop_event = Event()

    # Create initial game state
    game_state = GameState.create_new_game(42, 8, 50)
    game_state.initialise()
    game_state.update_player_statistics()

    with open("communication.state", "w") as f:
        f.write(repr(game_state))

    try:
        # Spawn processes
        sim_process = Process(
            target=run_simulation,
            args=(event_queue, control_queue, "communication.state", stop_event),
        )
        viz_process = Process(
            target=run_visualization,
            args=(event_queue, control_queue, "communication.state", stop_event),
        )

        sim_process.start()
        viz_process.start()

        # Wait for processes to complete
        while True:
            viz_process.join(timeout=1.0)
            sim_process.join(timeout=1.0)

            if stop_event.is_set():
                raise RuntimeError("User triggered end of simulation")
    except:
        # handling for either the stop event or the user canning the process
        if viz_process.is_alive():
            viz_process.terminate()
            viz_process.join(timeout=2.0)

        if sim_process.is_alive():
            sim_process.terminate()
            sim_process.join(timeout=2.0)

        event_queue.close()
        control_queue.close()

        info("finished clean up")

    finally:
        import unittest

        caser = unittest.TestCase()
        tape_a = open("communication_a.stack", "r").readlines()[1:]
        tape_b = open("communication_b.stack", "r").readlines()[1:]

        caser.assertListEqual(
            tape_b[::-1],
            tape_a[-1 * len(tape_b) :][::-1],
            "the worlds beween processes was different",
        )

        print("the worlds agreed on the history that they shared.")
        print(f"the length of the simulation stack was :: {len(tape_a)}")
        print(f"the length of the visualisation stack was :: {len(tape_b)}")


if __name__ == "__main__":
    main()
