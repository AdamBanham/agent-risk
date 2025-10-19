
from risk.state.event_stack import PlacementPhase
from risk.state.event_stack import TroopPlacementEvent, PlacementPhaseEndEvent

from risk.state.event_stack import AttackPhase
from risk.state.event_stack import AttackOnTerritoryEvent, CasualtyEvent
from risk.state.event_stack import CaptureTerritoryEvent, AttackPhaseEndEvent

from risk.state.event_stack import MovementPhase
from risk.state.event_stack import MovementOfTroopsEvent, MovementPhaseEndEvent

from risk.state.event_stack import EventStack, Level, Event
from risk.state import Territory, TerritoryState

import unittest

class TestPlacementPhase(unittest.TestCase):

    def setUp(self):
        self.stack = EventStack("game loop")
        self.stack.push(Level("game"))
        self.stack.push(Event("game start"))

        self.turn = 1
        self.player = 1 

    def tearDown(self):
        pass

    def test_create(self):

        phase = PlacementPhase(self.turn, self.player)
        self.assertEqual(
            phase,
            eval(repr(phase))
        )
        self.stack.push(phase)

        self.assertNotEqual(
            self.stack.substack(-1).current_level,
            self.stack.current_level
        )
        self.assertEqual(
            self.stack.current_level,
            phase
        )
        self.assertEqual(
            self.stack.depth,
            2
        )

        # print()
        # print(str(self.stack))


        placement = TroopPlacementEvent(
            self.turn, self.player,
            1, 2
        )
        self.assertEqual(
            placement,
            eval(repr(placement))
        )

        self.stack.push(placement)
        self.stack.push(TroopPlacementEvent(
            self.turn, self.player,
            1, 1
        ))
        ender = PlacementPhaseEndEvent(
            self.turn, self.player
        )
        self.assertEqual(
            ender,
            eval(repr(ender))
        )
        self.stack.push(ender)

        self.player += 1

        phase = PlacementPhase(self.turn,self.player)
        self.stack.push(phase)

        self.assertNotEqual(
            self.stack.substack(-1).current_level,
            self.stack.current_level
        )
        self.assertEqual(
            self.stack.current_level,
            phase
        )
        self.assertEqual(
            self.stack.depth,
            3
        )

        ender = PlacementPhaseEndEvent(
            self.turn, self.player
        )
        self.assertEqual(
            ender,
            eval(repr(ender))
        )
        self.stack.push(ender)

        # print()
        # print(str(self.stack))

    def test_engine(self):
        pass 

class TestAttackPhase(unittest.TestCase):

    def setUp(self):
        self.stack = EventStack("game loop")
        self.stack.push(Level("game"))
        self.stack.push(Event("game start"))
        self.attacking = Territory(
            1,
            "attacking",
            (0,0),
            []
        )
        self.defending = Territory(
            2,
            "defending",
            (0,0),
            []
        )

        self.turn = 1
        self.player = 1 

    def tearDown(self):
        pass

    def test_create(self):
        
        phase = AttackPhase(
            self.turn,
            self.player
        )
        self.assertEqual(phase, eval(repr(phase)))

        self.stack.push(phase)
        self.assertEqual(self.stack.current_level, phase)

        # print()
        # print(self.stack)

        attack = AttackOnTerritoryEvent(
            self.player, self.turn,
            self.attacking.id, self.defending.id,
            5
        )
        self.assertEqual(attack, eval(repr(attack)))

        self.stack.push(attack)

        # print()
        # print(self.stack)

        atk_casualty = CasualtyEvent(
            self.turn,
            self.attacking.id, 1
        )
        def_casualty =  CasualtyEvent(
            self.turn,
            self.defending.id, 2
        )
        self.assertEqual(atk_casualty, eval(repr(atk_casualty)))
        self.assertEqual(def_casualty, eval(repr(def_casualty)))       

        self.stack.push(atk_casualty)
        self.stack.push(def_casualty)

        # print()
        # print(self.stack)

        capture = CaptureTerritoryEvent(
            self.player,
            self.turn,
            self.defending.id,
            self.attacking.id,
            3
        )
        self.assertEqual(capture, eval(repr(capture)))

        self.stack.push(capture)

        # print()
        # print(self.stack)

        ender = AttackPhaseEndEvent(
            self.turn,
            self.player
        )
        self.assertEqual(ender, eval(repr(ender)))

        self.stack.push(ender)

        # print()
        # print(self.stack)

    def test_engine(self):
        pass

class TestMovementPhase(unittest.TestCase):

    def setUp(self):
        self.stack = EventStack("game loop")
        self.stack.push(Level("game"))
        self.stack.push(Event("game start"))

        self.attacking = Territory(
            1,
            "attacking",
            (0,0),
            []
        )
        self.defending = Territory(
            2,
            "defending",
            (0,0),
            []
        )

        self.turn = 1
        self.player = 1 

    def tearDown(self):
        pass

    def test_create(self):
        
        phase = MovementPhase(
            self.turn,
            self.player
        )
        self.assertEqual(
            phase, 
            eval(repr(phase))
        )

        self.stack.push(phase)

        # print()
        # print(self.stack)

        movement = MovementOfTroopsEvent(
            self.player, self.turn,
            self.attacking.id, self.defending.id,
            3
        )
        self.assertEqual(movement, eval(repr(movement)) )

        self.stack.push(movement)
        self.stack.push(MovementOfTroopsEvent(
            self.player, self.turn,
            self.attacking.id, self.defending.id,
            5
        ))

        # print()
        # print(self.stack)

        ender = MovementPhaseEndEvent(
            self.turn, self.player
        )
        self.assertEqual(ender, eval(repr(ender)))

        self.stack.push(ender)

        # print()
        # print(self.stack)

    def test_engine(self):
        pass


