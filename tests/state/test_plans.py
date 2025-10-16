from risk.state.plan import Plan, Step, Goal
from risk.state.game_state import GameState, GamePhase
from risk.state.territory import Territory, TerritoryState

import unittest
from unittest.mock import Mock


class TestSteps(unittest.TestCase):
    """Test suite for Step class functionality."""
    
    def setUp(self):
        """Set up test fixtures with sample steps."""
        self.step1 = Step("Attack territory 5")
        self.step2 = Step("Move armies from 1 to 2")
        self.step3 = Step("Attack territory 5")  # Same description as step1
        self.step4 = Step("")  # Empty description
        
    def test_step_initialization(self):
        """Test Step object creation and basic attributes."""
        step = Step("Test action")
        self.assertEqual(step.description, "Test action")
        
    def test_step_str_representation(self):
        """Test __str__ method returns correct format."""
        expected = "Step: Attack territory 5"
        self.assertEqual(str(self.step1), expected)
        
        # Test with empty description
        expected_empty = "Step: "
        self.assertEqual(str(self.step4), expected_empty)
        
    def test_step_repr_representation(self):
        """Test __repr__ method returns correct format."""
        expected = "Step('Attack territory 5')"
        self.assertEqual(repr(self.step1), expected)
        
        # Test with empty description
        expected_empty = "Step('')"
        self.assertEqual(repr(self.step4), expected_empty)
        
    def test_step_equality(self):
        """Test Step equality based on description."""
        self.assertEqual(self.step1, self.step3)  # Same description
        self.assertNotEqual(self.step1, self.step2)  # Different descriptions
        self.assertNotEqual(self.step1, "not a step")  # Different type
        
    def test_step_hash(self):
        """Test Step objects can be hashed and used in sets/dicts."""
        step_set = {self.step1, self.step2, self.step3}
        self.assertEqual(len(step_set), 2)  # step1 and step3 are identical
        
        step_dict = {self.step1: "value1", self.step2: "value2"}
        self.assertEqual(len(step_dict), 2)
        self.assertEqual(step_dict[self.step1], "value1")
        self.assertEqual(step_dict[self.step2], "value2")
        
    def test_step_execute(self):
        """Test default execute method returns None."""
        game_state = GameState.create_new_game(5, 2, 10)
        result = self.step1.execute(game_state)
        self.assertIsNone(result)


class TestGoals(unittest.TestCase):
    """Test suite for Goal class functionality."""
    
    def setUp(self):
        """Set up test fixtures with sample goals and game states."""
        self.goal1 = Goal("Control 3 territories")
        self.goal2 = Goal("Eliminate player 1")
        self.goal3 = Goal("Control 3 territories")  # Same as goal1
        self.goal4 = Goal("")  # Empty description
        
        # Create test game states
        self.game_state = GameState.create_new_game(5, 3, 15)
        
        # Add territories to game state
        for i in range(5):
            territory = Territory(
                id=i,
                name=f"Territory {i}",
                center=Mock(),
                vertices=Mock(),
                state=TerritoryState.OWNED,
                owner=i % 3,  # Distribute among players
                armies=3
            )
            self.game_state.add_territory(territory)
        
        # Update player statistics
        self.game_state.update_player_statistics()
        
    def test_goal_initialization(self):
        """Test Goal object creation and basic attributes."""
        goal = Goal("Test objective")
        self.assertEqual(goal.description, "Test objective")
        
    def test_goal_str_representation(self):
        """Test __str__ method returns correct format."""
        expected = "Goal: Control 3 territories"
        self.assertEqual(str(self.goal1), expected)
        
        # Test with empty description
        expected_empty = "Goal: "
        self.assertEqual(str(self.goal4), expected_empty)
        
    def test_goal_repr_representation(self):
        """Test __repr__ method returns correct format."""
        expected = "Goal('Control 3 territories')"
        self.assertEqual(repr(self.goal1), expected)
        
        # Test with empty description  
        expected_empty = "Goal('')"
        self.assertEqual(repr(self.goal4), expected_empty)
        
    def test_goal_equality(self):
        """Test Goal equality based on description."""
        self.assertEqual(self.goal1, self.goal3)  # Same description
        self.assertNotEqual(self.goal1, self.goal2)  # Different descriptions
        self.assertNotEqual(self.goal1, "not a goal")  # Different type
        
    def test_goal_hash(self):
        """Test Goal objects can be hashed and used in sets/dicts."""
        goal_set = {self.goal1, self.goal2, self.goal3}
        self.assertEqual(len(goal_set), 2)  # goal1 and goal3 are identical
        
        goal_dict = {self.goal1: "value1", self.goal2: "value2"}
        self.assertEqual(len(goal_dict), 2)
        
    def test_goal_achieved_default(self):
        """Test default achieved method returns False."""
        result = self.goal1.achieved(self.game_state)
        self.assertFalse(result)
        
    def test_goal_achieved_with_different_states(self):
        """Test achieved method with various game states."""
        # Test with empty game state
        empty_state = GameState.create_new_game(0, 2, 5)
        self.assertFalse(self.goal1.achieved(empty_state))
        
        # Test with initialized game state
        self.assertFalse(self.goal1.achieved(self.game_state))
        
        # Test with game end state
        end_state = GameState.create_new_game(3, 2, 10)
        end_state.phase = GamePhase.GAME_END
        end_state.winner_id = 0
        self.assertFalse(self.goal1.achieved(end_state))


class TestConcreteGoal(Goal):
    """Concrete Goal subclass for testing achieved() method."""
    
    def __init__(self, description: str, target_territories: int):
        super().__init__(description)
        self.target_territories = target_territories
        
    def achieved(self, state: GameState) -> bool:
        """Check if any player controls target number of territories."""
        for player in state.players.values():
            if player.get_territory_count() >= self.target_territories:
                return True
        return False


class TestGoalsWithConcreteImplementation(unittest.TestCase):
    """Test Goal functionality with concrete implementation."""
    
    def setUp(self):
        """Set up test fixtures with concrete goals."""
        self.goal = TestConcreteGoal("Control 2+ territories", 2)
        
    def test_concrete_goal_achieved_true(self):
        """Test achieved method returns True when condition is met."""
        # Create game state where player controls 2 territories
        game_state = GameState.create_new_game(4, 2, 10)
        
        # Add territories with player 0 controlling 2 territories
        territory1 = Territory(id=0, name="T1", center=Mock(),
                              vertices=Mock(),
                              state=TerritoryState.OWNED, 
                              owner=0, armies=5)
        territory2 = Territory(id=1, name="T2", center=Mock(),
                              vertices=Mock(),  
                              state=TerritoryState.OWNED,
                              owner=0, armies=3)
        territory3 = Territory(id=2, name="T3", center=Mock(),
                              vertices=Mock(),
                              state=TerritoryState.OWNED,
                              owner=1, armies=2)
        territory4 = Territory(id=3, name="T4", center=Mock(),
                              vertices=Mock(),
                              state=TerritoryState.FREE,
                              armies=0)
        
        game_state.add_territory(territory1)
        game_state.add_territory(territory2)
        game_state.add_territory(territory3)
        game_state.add_territory(territory4)
        game_state.update_player_statistics()
        
        self.assertTrue(self.goal.achieved(game_state))
        
    def test_concrete_goal_achieved_false(self):
        """Test achieved method returns False when condition is not met."""
        # Create game state where no player controls 2+ territories
        game_state = GameState.create_new_game(4, 3, 8)
        
        # Each player controls only 1 territory
        territory1 = Territory(id=0, name="T1", center=Mock(),
                              vertices=Mock(),
                              state=TerritoryState.OWNED,
                              owner=0, armies=3)
        territory2 = Territory(id=1, name="T2", center=Mock(),
                              vertices=Mock(),
                              state=TerritoryState.OWNED,
                              owner=1, armies=3)
        territory3 = Territory(id=2, name="T3", center=Mock(),
                              vertices=Mock(),
                              state=TerritoryState.OWNED,
                              owner=2, armies=2)
        territory4 = Territory(id=3, name="T4", center=Mock(),
                              vertices=Mock(),
                              state=TerritoryState.FREE,
                              armies=0)
        
        game_state.add_territory(territory1)
        game_state.add_territory(territory2)
        game_state.add_territory(territory3)
        game_state.add_territory(territory4)
        game_state.update_player_statistics()
        
        self.assertFalse(self.goal.achieved(game_state))


class TestPlans(unittest.TestCase):
    """Test suite for Plan class functionality."""
    
    def setUp(self):
        """Set up test fixtures with sample plans, goals, and steps."""
        self.goal1 = Goal("Conquer the world")
        self.goal2 = Goal("Defend territory")
        
        self.step1 = Step("Attack territory A")
        self.step2 = Step("Move armies to B")
        self.step3 = Step("Fortify position")
        self.step4 = Step("Scout enemy")
        
        self.plan1 = Plan("World Domination", self.goal1)
        self.plan2 = Plan("Defense Strategy", self.goal2)
        self.plan3 = Plan("World Domination", self.goal1)  # Same as plan1
        
    def test_plan_initialization(self):
        """Test Plan object creation and basic attributes."""
        plan = Plan("Test Plan", self.goal1)
        self.assertEqual(plan.name, "Test Plan")
        self.assertEqual(plan.goal, self.goal1)
        self.assertEqual(len(plan.steps), 0)
        
    def test_plan_add_single_step(self):
        """Test adding a single step to a plan."""
        original_length = len(self.plan1)
        result = self.plan1.add_step(self.step1)
        
        # Check fluent interface returns plan
        self.assertIs(result, self.plan1)
        
        # Check step was added
        self.assertEqual(len(self.plan1), original_length + 1)
        self.assertIn(self.step1, self.plan1.steps)
        
    def test_plan_add_multiple_steps(self):
        """Test adding multiple steps to a plan."""
        steps = [self.step1, self.step2, self.step3]
        original_length = len(self.plan2)
        result = self.plan2.add_steps(steps)
        
        # Check fluent interface returns plan
        self.assertIs(result, self.plan2)
        
        # Check all steps were added
        self.assertEqual(len(self.plan2), original_length + 3)
        for step in steps:
            self.assertIn(step, self.plan2.steps)
            
    def test_plan_peek_step(self):
        """Test peeking at next step without removing it."""
        # Empty plan
        self.assertIsNone(self.plan1.peek_step())
        
        # Plan with steps
        self.plan1.add_steps([self.step1, self.step2, self.step3])
        next_step = self.plan1.peek_step()
        
        self.assertEqual(next_step, self.step1)
        self.assertEqual(len(self.plan1), 3)  # Length unchanged
        self.assertEqual(self.plan1.steps[0], self.step1)  # Step still there
        
    def test_plan_pop_step(self):
        """Test popping next step and removing it from plan."""
        # Empty plan
        self.assertIsNone(self.plan1.pop_step())
        
        # Plan with steps
        self.plan1.add_steps([self.step1, self.step2, self.step3])
        original_length = len(self.plan1)
        
        popped_step = self.plan1.pop_step()
        
        self.assertEqual(popped_step, self.step1)
        self.assertEqual(len(self.plan1), original_length - 1)
        self.assertEqual(self.plan1.steps[0], self.step2)  # Next step is now first
        
    def test_plan_multiple_pops(self):
        """Test sequential pop operations."""
        steps = [self.step1, self.step2, self.step3, self.step4]
        self.plan1.add_steps(steps)
        
        # Pop all steps in order
        for i, expected_step in enumerate(steps):
            self.assertEqual(len(self.plan1), len(steps) - i)
            popped = self.plan1.pop_step()
            self.assertEqual(popped, expected_step)
            
        # Plan should be empty now
        self.assertEqual(len(self.plan1), 0)
        self.assertTrue(self.plan1.is_done())
        self.assertIsNone(self.plan1.pop_step())
        self.assertIsNone(self.plan1.peek_step())
        
    def test_plan_length(self):
        """Test plan length calculations."""
        self.assertEqual(len(self.plan1), 0)
        
        self.plan1.add_step(self.step1)
        self.assertEqual(len(self.plan1), 1)
        
        self.plan1.add_steps([self.step2, self.step3])
        self.assertEqual(len(self.plan1), 3)
        
        self.plan1.pop_step()
        self.assertEqual(len(self.plan1), 2)
        
    def test_plan_is_done(self):
        """Test is_done method for empty plans."""
        self.assertTrue(self.plan1.is_done())
        
        self.plan1.add_step(self.step1)
        self.assertFalse(self.plan1.is_done())
        
        self.plan1.pop_step()
        self.assertTrue(self.plan1.is_done())
        
    def test_plan_goal_achieved(self):
        """Test goal achievement checking through plan."""
        game_state = GameState.create_new_game(5, 2, 10)
        
        # Use default Goal implementation (always returns False)
        result = self.plan1.goal_achieved(game_state)
        self.assertFalse(result)
        
        # Test with concrete goal implementation
        concrete_goal = TestConcreteGoal("Control 1+ territories", 1)
        plan_with_concrete_goal = Plan("Test", concrete_goal)
        
        # Create state where goal is achieved
        territory = Territory(id=0, name="T1", center=Mock(),
                            vertices=Mock(),
                            state=TerritoryState.OWNED,
                            owner=0, armies=5)
        game_state.add_territory(territory)
        game_state.update_player_statistics()
        
        result = plan_with_concrete_goal.goal_achieved(game_state)
        self.assertTrue(result)
        
    def test_plan_str_representation(self):
        """Test __str__ method returns correct format."""
        expected = "Plan(World Domination, Goal: Conquer the world, Steps: 0)"
        self.assertEqual(str(self.plan1), expected)
        
        # Add steps and test again
        self.plan1.add_steps([self.step1, self.step2])
        expected = "Plan(World Domination, Goal: Conquer the world, Steps: 2)"
        self.assertEqual(str(self.plan1), expected)
        
    def test_plan_repr_representation(self):
        """Test __repr__ method returns correct format."""
        expected = ("Plan('World Domination', goal=Goal('Conquer the world'))"
                   ".add_steps([])")
        self.assertEqual(repr(self.plan1), expected)
        
        # Add steps and test again
        self.plan1.add_steps([self.step1, self.step2])
        expected = ("Plan('World Domination', goal=Goal('Conquer the world'))"
                   f".add_steps([{repr(self.step1)}, {repr(self.step2)}])")
        self.assertEqual(repr(self.plan1), expected)
        
    def test_plan_equality(self):
        """Test Plan equality based on name, goal, and steps."""
        # Initially equal (same name, goal, empty steps)
        self.assertEqual(self.plan1, self.plan3)
        
        # Different after adding steps to one
        self.plan1.add_step(self.step1)
        self.assertNotEqual(self.plan1, self.plan3)
        
        # Equal again after adding same step to both
        self.plan3.add_step(self.step1)
        self.assertEqual(self.plan1, self.plan3)
        
        # Different plans with different goals
        self.assertNotEqual(self.plan1, self.plan2)
        
        # Not equal to different type
        self.assertNotEqual(self.plan1, "not a plan")
        
    def test_plan_hash(self):
        """Test Plan objects can be hashed and used in sets/dicts."""
        plan_set = {self.plan1, self.plan2, self.plan3}
        self.assertEqual(len(plan_set), 2)  # plan1 and plan3 are identical
        
        plan_dict = {self.plan1: "value1", self.plan2: "value2"}
        self.assertEqual(len(plan_dict), 2)
        
        # Test hash changes when plan is modified
        original_hash = hash(self.plan1)
        self.plan1.add_step(self.step1)
        new_hash = hash(self.plan1)
        self.assertNotEqual(original_hash, new_hash)


if __name__ == '__main__':
    unittest.main() 

