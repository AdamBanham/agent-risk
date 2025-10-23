
import random
import sys
from risk.engine.controller import RiskSimulationController
from risk.engine.base import RecordStackEngine, Engine
from risk.state.event_stack import GameEvent
from risk.state.game_state import GameState

from time import time, sleep

state = GameState.create_new_game(
    regions=30,
    num_players=2,
    starting_armies=30
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
        fails = []

        territories = list(game_state.get_territories_owned_by(
            game_state.current_player_id 
        ))
        other_territories = list(game_state.get_territories_owned_by(
            (game_state.current_player_id + 1) % game_state.num_players
        ))

        placer = random.choice(territories)
        other = other_territories[0]

        for place in territories:
            # simulate adding troops
            placement.append(
                TroopPlacementEvent(
                    turn=game_state.total_turns,
                    player=game_state.current_player_id,
                    territory=place.id,
                    num_troops=random.choice(
                        range(1, game_state.placements_left)
                    )
                )
            )

        # simulate adding troops for non owned territory
        fails.append(
            TroopPlacementEvent(
                turn=game_state.total_turns,
                player=game_state.current_player_id,
                territory=other.id,
                num_troops=1
            )
        )
        # simulate adding troops for non current player
        fails.append(
            TroopPlacementEvent(
                turn=game_state.total_turns,
                player=(game_state.current_player_id + 1) % game_state.num_players,
                territory=placer.id,
                num_troops=3
            )
        )

        # simulate adding too many troops
        fails.append(
            TroopPlacementEvent(
                turn=game_state.total_turns,
                player=game_state.current_player_id,
                territory=placer.id,
                num_troops=game_state.placements_left + 1
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
                    attacking_troops=max(1 , placer.armies // 2)
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

        return [random.choice(placement)] #+ [random.choice(fails)]

from risk.state.event_stack import (
    MovementPhase,
    MovementOfTroopsEvent,
)
class MockMovements(Engine):
    """
    Mock engine for placing troop movements on the stack.
    """

    allowed_elements = [
        MovementPhase
    ]

    def __init__(self):
        super().__init__("MockMovementsEngine")
    
    def process(self, 
                game_state: GameState, 
                element) -> None:
        # For each player, place 1 troop in the first territory they own
        placement = []
        fails = []

        territories = list(game_state.get_territories_owned_by(
            game_state.current_player_id 
        ))
        other_territories = list(game_state.get_territories_owned_by(
            (game_state.current_player_id + 1) % game_state.num_players
        ))

        placer = random.choice(territories)
        other = random.choice(other_territories)
        
        for adjacent in placer.adjacent_territories:
            if adjacent.owner != game_state.current_player_id:
                continue
            placement.append(
                MovementOfTroopsEvent(
                    turn=game_state.total_turns,
                    player=game_state.current_player_id,
                    from_territory=placer.id,
                    to_territory=adjacent.id,
                    moving_troops=max(1 , placer.armies // 2)
                )
            )

        # add some fail cases
        ## not your turn
        fails.append(
            MovementOfTroopsEvent(
                turn=game_state.total_turns,
                player=(game_state.current_player_id + 1) % game_state.num_players,
                from_territory=placer.id,
                to_territory=adjacent.id,
                moving_troops=max(1 , placer.armies // 2)
            )
        )
        ## not your territory
        non_owned = [ adj for adj in placer.adjacent_territories if adj.owner != game_state.current_player_id ]
        if len(non_owned) > 0:
            fails.append(
                MovementOfTroopsEvent(
                    turn=game_state.total_turns,
                    player=game_state.current_player_id,
                    from_territory=non_owned[0].id,
                    to_territory=placer.id,
                    moving_troops=1
                )
            )
            fails.append(
                MovementOfTroopsEvent(
                    turn=game_state.total_turns,
                    player=game_state.current_player_id,
                    from_territory=placer.id,
                    to_territory=non_owned[0].id,
                    moving_troops=1
                )
            )
        ## zero troops
        fails.append(
            MovementOfTroopsEvent(
                turn=game_state.total_turns,
                player=game_state.current_player_id,
                from_territory=placer.id,
                to_territory=adjacent.id,
                moving_troops=0
            )
        )
        ## too many troops
        fails.append(
            MovementOfTroopsEvent(
                turn=game_state.total_turns,
                player=game_state.current_player_id,
                from_territory=placer.id,
                to_territory=adjacent.id,
                moving_troops=placer.armies + 5
            )
        )
        ## must leave one behind
        fails.append(
            MovementOfTroopsEvent(
                turn=game_state.total_turns,
                player=game_state.current_player_id,
                from_territory=placer.id,
                to_territory=adjacent.id,
                moving_troops=placer.armies
            )
        )

        if len(placement) == 0:
            return random.sample(fails, k=1)
        return [random.choice(placement), random.choice(fails)]

from risk.state.event_stack import (
    PlayingEvent,
    AgentTurnEndEvent,
    AgentTurnPhase,
    GameEvent,
    PlacementPhaseEndEvent,
    AttackPhaseEndEvent,
    MovementPhaseEndEvent
)

recorder = RecordStackEngine(
    pairs=[
        (PlayingEvent, AgentTurnEndEvent),
        (PlacementPhase, PlacementPhaseEndEvent),
        (AttackPhase, AttackPhaseEndEvent),
        (MovementPhase, MovementPhaseEndEvent)
    ]
)
engine = RiskSimulationController(
    game_state=state
)
engine.add_engine(MockPlacements())
engine.add_engine(MockFights())
engine.add_engine(MockMovements())
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

