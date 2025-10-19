#!/usr/bin/env python3
"""
Test script to verify AI movement animations are working correctly.
Creates a specific game scenario that will definitely trigger movements and animations.
"""

import pygame
import time
from risk.agents.simple.ai_game_loop import AIGameLoop
from risk.agents.simple.random_agent import AgentController, RandomAgent
from risk.state.game_state import GameState
from risk.state.turn_manager import TurnManager, TurnPhase
from risk.state.territory import Territory


def create_movement_test_scenario():
    """Create a game with guaranteed movement opportunities."""
    print("Creating test scenario with guaranteed movements...")
    
    # Initialize pygame
    pygame.init()
    
    # Create AI game loop
    game_loop = AIGameLoop(
        width=1200,
        height=800,
        regions=4,
        num_players=2,
        starting_armies=20
    )
    
    # Clear the auto-generated territories and create custom ones
    game_loop.game_state.territories.clear()
    
    # Territory 1: Safe territory (player 0, many armies, no enemies nearby)
    territory1 = Territory(id=1, name='Safe Base', center=(200, 300), 
                          vertices=[(150,250), (250,250), (250,350), (150,350)])
    territory1.set_owner(0, 15)
    
    # Territory 2: Front-line territory (player 0, few armies, has adjacent enemy)
    territory2 = Territory(id=2, name='Front Line', center=(400, 300),
                          vertices=[(350,250), (450,250), (450,350), (350,350)])
    territory2.set_owner(0, 3)
    
    # Territory 3: Enemy territory (player 1)
    territory3 = Territory(id=3, name='Enemy Outpost', center=(600, 300),
                          vertices=[(550,250), (650,250), (650,350), (550,350)])
    territory3.set_owner(1, 8)
    
    # Territory 4: Another safe territory (player 0, separate from front-line)
    territory4 = Territory(id=4, name='Safe Rear', center=(200, 500),
                          vertices=[(150,450), (250,450), (250,550), (150,550)])
    territory4.set_owner(0, 10)
    
    # Set up adjacencies to create the movement scenario
    # 1 (safe) -> 2 (front-line) -> 3 (enemy)
    # 4 (safe) -> 2 (front-line)
    territory1.add_adjacent_territory(2)
    territory2.add_adjacent_territory(1)
    territory2.add_adjacent_territory(3)
    territory2.add_adjacent_territory(4)
    territory3.add_adjacent_territory(2)
    territory4.add_adjacent_territory(2)
    
    # Add territories to game state
    for territory in [territory1, territory2, territory3, territory4]:
        game_loop.game_state.add_territory(territory)
    
    # Update player statistics
    game_loop.game_state.update_player_statistics()
    
    # Create AI agents with low attack probability to encourage movement
    controller = AgentController()
    agent1 = RandomAgent(player_id=0, attack_probability=0.2)  # Low attack rate
    agent2 = RandomAgent(player_id=1, attack_probability=0.2)  # Low attack rate
    controller.register_agent(agent1)
    controller.register_agent(agent2)
    
    # Set agent controller and timing
    game_loop.set_agent_controller(controller)
    game_loop.set_ai_turn_delay(2.0)  # Slower for visibility
    
    print("Test scenario created:")
    print("  Territory 1 (Safe Base): 15 armies, no adjacent enemies")
    print("  Territory 2 (Front Line): 3 armies, adjacent to enemy territory 3")
    print("  Territory 3 (Enemy Outpost): 8 armies, player 1")
    print("  Territory 4 (Safe Rear): 10 armies, no adjacent enemies")
    print("  Expected: Agents should move armies from territories 1&4 to territory 2")
    
    return game_loop


def run_movement_test():
    """Run the movement animation test."""
    game_loop = create_movement_test_scenario()
    
    # Initialize game components
    if not game_loop.initialize():
        print("Failed to initialize game loop")
        return
    
    # Start the first turn
    game_loop.turn_manager.start_player_turn(0)
    
    print("\nStarting movement animation test...")
    print("Watch for movement animations (black random walk paths) between territories")
    print("Press ESC to exit")
    
    clock = pygame.time.Clock()
    running = True
    start_time = time.time()
    
    while running and time.time() - start_time < 30:  # Run for 30 seconds max
        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
        
        # Update game
        game_loop.update()
        
        # Calculate delta time for animations
        delta_time = clock.tick(60) / 1000.0
        
        # Render
        game_loop.render(delta_time)
        
        # Check for game end
        if game_loop.game_state.winner_id is not None:
            winner = game_loop.game_state.get_player(game_loop.game_state.winner_id)
            print(f"\nGame ended! Winner: {winner.name if winner else 'Unknown'}")
            time.sleep(2)  # Show final state
            break
    
    pygame.quit()
    print("Movement animation test complete!")


if __name__ == "__main__":
    run_movement_test()