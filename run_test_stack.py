
import random
import sys
from risk.engine.controller import RiskSimulationController
from risk.engine.base import RecordStackEngine, Engine
from risk.state.event_stack import GameEvent
from risk.state.game_state import GameState

from time import time, sleep

state = GameState.create_new_game(
    regions=10,
    num_players=2,
    starting_armies=20
)
state.initialise()

from risk.state.event_stack import PlacementPhase, TroopPlacementEvent
class MockPlacements(Engine):
    """
    Mock engine for handling troop placements.
    """

    allowed_elements = [
        PlacementPhase
    ]

    def __init__(self):
        super().__init__("MockPlacementsEngine")
    
    def process(self, game_state: GameState, element: PlacementPhase) -> None:
        # For each player, place 1 troop in the first territory they own
        placement = []

        territories = list(game_state.get_territories_owned_by(
            game_state.current_player_id 
        ))
        other_territories = list(game_state.get_territories_owned_by(
            (game_state.current_player_id + 1) % game_state.num_players
        ))

        placer = territories[0]
        other = other_territories[0]

        # simulate adding troops for non current player
        placement.append(
            TroopPlacementEvent(
                turn=game_state.total_turns,
                player=game_state.current_player_id,
                territory=other.id,
                num_troops=1
            )
        )
        # simulate adding troops for non current player
        placement.append(
            TroopPlacementEvent(
                turn=game_state.total_turns,
                player=(game_state.current_player_id + 1) % game_state.num_players,
                territory=placer.id,
                num_troops=3
            )
        )
        # simulate undo by placing another troop placement
        placement.append(
            TroopPlacementEvent(
                turn=game_state.total_turns,
                player=game_state.current_player_id,
                territory=placer.id,
                num_troops= -1
            )
        )
        # simulate adding troops
        placement.append(
            TroopPlacementEvent(
                turn=game_state.total_turns,
                player=game_state.current_player_id,
                territory=placer.id,
                num_troops=2
            )
        )

        return [random.choice(placement)]

from risk.state.event_stack import (
    AttackPhase,
    AttackOnTerritoryEvent,
)

class MockFights(Engine):
    """
    Mock engine for placing fights on the stack.
    """

    allowed_elements = [
        AttackPhase
    ]

    def __init__(self):
        super().__init__("MockFightsEngine")
    
    def process(self, 
                game_state: GameState, 
                element: AttackPhase) -> None:
        # For each player, place 1 troop in the first territory they own
        placement = []

        territories = list(game_state.get_territories_owned_by(
            game_state.current_player_id 
        ))
        other_territories = list(game_state.get_territories_owned_by(
            (game_state.current_player_id + 1) % game_state.num_players
        ))

        placer = random.choice(territories)
        other = random.choice(other_territories)

        # simulate an attack
        for adjacent in placer.adjacent_territories:
            placement.append(
                AttackOnTerritoryEvent(
                    turn=game_state.total_turns,
                    player=game_state.current_player_id,
                    from_territory=placer.id,
                    to_territory=adjacent.id,
                    attacking_troops=1
                )
            )

        # add some fail cases
        fails = []
        ## not your turn
        fails.append(
            AttackOnTerritoryEvent(
                turn=game_state.total_turns,
                player=(game_state.current_player_id + 1) % game_state.num_players, 
                from_territory=placer.id,
                to_territory=adjacent.id,
                attacking_troops=1
            )
        )
        ## not your territory
        fails.append(
            AttackOnTerritoryEvent(
                turn=game_state.total_turns,
                player=game_state.current_player_id,
                from_territory=other.id,
                to_territory=adjacent.id,
                attacking_troops=1
            )
        )
        ## no adjacent territory
        fails.append(
            AttackOnTerritoryEvent(
                turn=game_state.total_turns,
                player=game_state.current_player_id,
                from_territory=placer.id,
                to_territory=[t.id for t in game_state.territories.values() if t.id not in [adj.id for adj in placer.adjacent_territories]][0],
                attacking_troops=1
            )
        )
        ## zero attacking troops
        fails.append(
            AttackOnTerritoryEvent(
                turn=game_state.total_turns,
                player=game_state.current_player_id,
                from_territory=placer.id,
                to_territory=adjacent.id,
                attacking_troops=0
            )
        )
        ## too many attacking troops
        fails.append(
            AttackOnTerritoryEvent(
                turn=game_state.total_turns,
                player=game_state.current_player_id,
                from_territory=placer.id,
                to_territory=adjacent.id,
                attacking_troops=placer.armies + 5
            )
        )

        return placement + [random.choice(fails)]

recorder = RecordStackEngine()
engine = RiskSimulationController(
    game_state=state
)
engine.add_engine(MockPlacements())
engine.add_engine(MockFights())
engine.add_engine(recorder)

engine.event_stack.push(
    GameEvent()
)

delay = 0.5

original_stdout = sys.stdout
try :
    with open("test.out", "w") as f:
        # Redirect stdout to the file
        sys.stdout = f
        try:
            f.flush()
            print("Initial Event Stack:")
            print(str(engine.event_stack))
            print()

            # Process the event stack until empty
            while not engine.event_stack.is_empty:
                touched = engine.step()
                print(f"Engine processed something: {touched}")
                print("Current Event Stack:")
                print(str(engine.event_stack))
                print()
                sleep(delay)

                original_stdout.write('\033c')
                original_stdout.write(str(recorder.stack) + "\n")
        finally:
            # Restore original stdout
            sys.stdout = original_stdout
except KeyboardInterrupt:
    sys.stdout = original_stdout
    f.close()
    print('\033c')
    print("Test interrupted by user.")
    print(recorder.stack)
    with open("test.stack", "w") as f:
        f.write(str(recorder.stack))
    with open("test.state", "w") as f:
        f.write(repr(state))
    sys.exit(1)

