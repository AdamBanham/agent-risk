"""
Simple random AI agent for the Risk simulation.
Makes random decisions for placement, attacking, and movement phases.
"""

import random
from typing import List, Optional, Tuple, Set
from abc import ABC, abstractmethod

from ...state.game_state import GameState, Player
from ...state.territory import Territory
from ...state.turn_manager import TurnManager, TurnState, TurnPhase


class BaseAgent(ABC):
    """
    Abstract base class for all AI agents. Defines the interface that agents 
    must implement to participate in the Risk simulation.
    """
    
    def __init__(self, player_id: int, name: str = "AI Agent"):
        """
        Initialize the base agent. Sets up player identification and 
        configuration.
        
        :param player_id: ID of the player this agent controls
        :param name: Display name for the agent
        """
        self.player_id = player_id
        self.name = name
    
    @abstractmethod
    def decide_placement(self, game_state: GameState, turn_state: TurnState) -> Optional[int]:
        """
        Decide where to place a reinforcement army. Called during the 
        placement phase when the agent has reinforcements available.
        
        :param game_state: Current state of the game including all 
                          territories and players
        :param turn_state: Current turn state including reinforcements 
                          remaining and phase information
        :returns: Territory ID where to place one army, or None to pass
        """
        pass
    
    @abstractmethod
    def decide_attack(self, game_state: GameState, turn_state: TurnState) -> Optional[Tuple[int, int]]:
        """
        Decide whether to attack and which territories to use. Called during 
        the attacking phase to determine if agent wants to initiate combat.
        
        :param game_state: Current state of the game including all 
                          territories and players
        :param turn_state: Current turn state including phase and attack 
                          history
        :returns: Tuple of (attacker_territory_id, defender_territory_id) 
                 for attack, or None to end attacking phase
        """
        pass
    
    @abstractmethod
    def decide_movement(self, game_state: GameState, turn_state: TurnState) -> Optional[Tuple[int, int, int]]:
        """
        Decide whether to move armies between territories. Called during the 
        movement phase to determine if agent wants to relocate forces.
        
        :param game_state: Current state of the game including all 
                          territories and players
        :param turn_state: Current turn state including phase and movement 
                          history
        :returns: Tuple of (source_territory_id, target_territory_id, 
                 army_count) for movement, or None to end movement phase
        """
        pass


class RandomAgent(BaseAgent):
    """
    Simple random AI agent that makes strategic decisions for placement, 
    attacking, and movement. Places troops randomly, attacks with configurable 
    probability, and moves troops from safe territories to front-line positions.
    
    This agent serves as a baseline for testing the game mechanics and 
    provides a simple opponent for other agents to compete against. Movement 
    strategy consolidates forces near enemy borders for better positioning.
    """
    
    def __init__(self, player_id: int, attack_probability: float = 0.5):
        """
        Initialize the random agent. Sets up random decision-making 
        parameters and behavior configuration.
        
        :param player_id: ID of the player this agent controls
        :param attack_probability: Probability (0.0-1.0) that agent will 
                                  attack when it has the opportunity
        """
        super().__init__(player_id, f"Random Agent {player_id + 1}")
        self.attack_probability = max(0.0, min(1.0, attack_probability))
    
    def decide_placement(self, game_state: GameState, turn_state: TurnState) -> Optional[int]:
        """
        Randomly place reinforcement armies on owned territories. Selects a 
        random territory from all territories owned by this agent.
        
        :param game_state: Current state of the game including all 
                          territories and players
        :param turn_state: Current turn state including reinforcements 
                          remaining and placement history
        :returns: Random territory ID where to place one army, or None if no 
                 owned territories available
        """
        # Get all territories owned by this agent
        owned_territories = []
        for territory in game_state.territories.values():
            if territory.is_owned_by(self.player_id):
                owned_territories.append(territory)
        
        # Return random territory if any owned, otherwise None
        if owned_territories:
            selected_territory = random.choice(owned_territories)
            return selected_territory.id
        
        return None
    
    def decide_attack(self, game_state: GameState, turn_state: TurnState) -> Optional[Tuple[int, int]]:
        """
        Randomly decide whether to attack adjacent enemy territories. Uses 
        attack probability to determine if agent should attack, then 
        randomly selects valid attack combinations.
        
        :param game_state: Current state of the game including all 
                          territories and players
        :param turn_state: Current turn state including phase and attack 
                          history
        :returns: Tuple of (attacker_territory_id, defender_territory_id) 
                 for random attack, or None if no attack possible or agent 
                 chooses not to attack
        """
        # First, decide if we want to attack at all
        if random.random() > self.attack_probability:
            return None
        
        # Find all possible attacks
        possible_attacks = []
        
        for territory in game_state.territories.values():
            # Can only attack from territories we own with more than 1 army
            if (territory.is_owned_by(self.player_id) and 
                territory.can_attack_from()):
                
                # Check all adjacent territories for valid targets
                for adjacent_id in territory.adjacent_territories:
                    adjacent_territory = game_state.get_territory(adjacent_id)
                    
                    # Can attack if adjacent territory is owned by someone else
                    if (adjacent_territory and 
                        not adjacent_territory.is_owned_by(self.player_id) and 
                        adjacent_territory.can_be_attacked()):
                        
                        possible_attacks.append((territory.id, adjacent_id))
        
        # Return random attack if any possible, otherwise None
        if possible_attacks:
            return random.choice(possible_attacks)
        
        return None
    
    def decide_movement(self, game_state: GameState, turn_state: TurnState) -> Optional[Tuple[int, int, int]]:
        """
        Move troops from safe territories to front-line territories that 
        border enemies. Finds connected groups and consolidates forces near 
        enemy positions.
        
        :param game_state: Current state of the game including all 
                          territories and players
        :param turn_state: Current turn state including phase and movement 
                          history
        :returns: Tuple of (source_territory_id, target_territory_id, 
                 army_count) for movement, or None if no beneficial movement 
                 found
        """
        # Get all territories owned by this agent
        owned_territories = []
        for territory in game_state.territories.values():
            if territory.is_owned_by(self.player_id):
                owned_territories.append(territory)
        
        if len(owned_territories) <= 1:
            return None  # Need at least 2 territories to move between
        
        # Find territories with and without adjacent enemies
        front_line_territories = []  # Territories with adjacent enemies
        safe_territories = []        # Territories without adjacent enemies
        
        for territory in owned_territories:
            has_enemy_neighbor = False
            
            for adjacent_id in territory.adjacent_territories:
                adjacent_territory = game_state.get_territory(adjacent_id)
                if (adjacent_territory and 
                    not adjacent_territory.is_owned_by(self.player_id)):
                    has_enemy_neighbor = True
                    break
            
            if has_enemy_neighbor:
                front_line_territories.append(territory)
            else:
                safe_territories.append(territory)
        
        # Only move if we have safe territories with extra armies and front-line targets
        if not safe_territories or not front_line_territories:
            return None
        
        # Find safe territories that can move armies (have more than 1 army)
        movable_safe_territories = [t for t in safe_territories if t.armies > 1]
        if not movable_safe_territories:
            return None
        
        # Find connected paths from safe territories to front-line territories
        valid_movements = []
        
        for safe_territory in movable_safe_territories:
            # Use breadth-first search to find connected front-line territories
            reachable_frontline = self._find_connected_frontline_territories(
                safe_territory, front_line_territories, owned_territories, game_state)
            
            for target_territory in reachable_frontline:
                # Calculate how many armies to move (all but one)
                armies_to_move = safe_territory.armies - 1
                if armies_to_move > 0:
                    valid_movements.append((safe_territory.id, target_territory.id, armies_to_move))
        
        # Randomly select a movement if any are available
        if valid_movements:
            return random.choice(valid_movements)
        
        return None
    
    def _find_connected_frontline_territories(self, source_territory: Territory, 
                                            front_line_territories: List[Territory],
                                            owned_territories: List[Territory],
                                            game_state: GameState) -> List[Territory]:
        """
        Find front-line territories reachable from source territory through 
        owned territory connections using breadth-first search.
        
        :param source_territory: Starting territory for pathfinding
        :param front_line_territories: List of target front-line territories
        :param owned_territories: List of all owned territories for pathfinding
        :param game_state: Game state for territory lookup
        :returns: List of reachable front-line territories
        """
        # Create sets for faster lookup
        owned_territory_ids = {t.id for t in owned_territories}
        front_line_ids = {t.id for t in front_line_territories}
        
        # Breadth-first search to find connected territories
        visited = set()
        queue = [source_territory.id]
        visited.add(source_territory.id)
        reachable_frontline = []
        
        while queue:
            current_id = queue.pop(0)
            current_territory = game_state.get_territory(current_id)
            
            if not current_territory:
                continue
            
            # Check if this is a front-line territory
            if current_id in front_line_ids:
                # Find the actual territory object
                for frontline_territory in front_line_territories:
                    if frontline_territory.id == current_id:
                        reachable_frontline.append(frontline_territory)
                        break
            
            # Add adjacent owned territories to search queue
            for adjacent_id in current_territory.adjacent_territories:
                if (adjacent_id in owned_territory_ids and 
                    adjacent_id not in visited):
                    visited.add(adjacent_id)
                    queue.append(adjacent_id)
        
        return reachable_frontline
    
    def get_status(self) -> str:
        """
        Get a status description of this agent. Provides information about 
        the agent's configuration and decision-making approach.
        
        :returns: String describing the agent's status and configuration
        """
        return (f"{self.name} (Player {self.player_id}): "
                f"Random placement, {self.attack_probability:.0%} attack rate, "
                f"strategic movement to front-lines")


class AgentController:
    """
    Controller class for managing AI agents during gameplay. Integrates 
    agents with the turn management system and coordinates agent decision-
    making with game state updates.
    """
    
    def __init__(self):
        """
        Initialize the agent controller. Sets up agent registry and 
        coordination systems.
        """
        self.agents = {}  # player_id -> agent mapping
    
    def register_agent(self, agent: BaseAgent) -> None:
        """
        Register an AI agent for a specific player. Associates the agent 
        with a player ID for turn management.
        
        :param agent: BaseAgent instance to register for gameplay
        """
        self.agents[agent.player_id] = agent
        print(f"Registered {agent.name} for player {agent.player_id}")
    
    def is_agent_player(self, player_id: int) -> bool:
        """
        Check if a player is controlled by an AI agent. Used to determine 
        if automatic decisions should be made during turns.
        
        :param player_id: ID of the player to check
        :returns: True if player is controlled by an agent, False if human
        """
        return player_id in self.agents
    
    def get_agent(self, player_id: int) -> Optional[BaseAgent]:
        """
        Get the agent controlling a specific player. Returns the registered 
        agent for the given player ID.
        
        :param player_id: ID of the player whose agent to retrieve
        :returns: BaseAgent instance if registered, None otherwise
        """
        return self.agents.get(player_id)
    
    def execute_agent_turn(self, game_state: GameState, turn_manager: TurnManager, 
                          renderer=None) -> bool:
        """
        Execute a complete turn for an AI agent. Handles all phases of the 
        turn (placement, attacking, movement) using agent decision-making.
        
        :param game_state: Current state of the game including all 
                          territories and players
        :param turn_manager: TurnManager instance for coordinating turn 
                            progression and state updates
        :param renderer: Optional renderer for triggering animations
        :returns: True if turn was executed successfully, False if no agent 
                 or turn could not be completed
        """
        current_turn = turn_manager.get_current_turn()
        if not current_turn:
            return False
        
        agent = self.get_agent(current_turn.player_id)
        if not agent:
            return False
        
        print(f"\n=== {agent.name} Turn (Player {agent.player_id}) ===")
        
        # Execute placement phase
        while (current_turn.phase == TurnPhase.PLACEMENT and 
               current_turn.reinforcements_remaining > 0):
            
            territory_id = agent.decide_placement(game_state, current_turn)
            if territory_id is None:
                break
            
            territory = game_state.get_territory(territory_id)
            if (territory and territory.is_owned_by(agent.player_id) and 
                current_turn.can_place_reinforcement(territory_id)):
                
                # Place one army and update territory
                if current_turn.place_reinforcement(territory_id, 1):
                    territory.add_armies(1)
                    print(f"  Placed 1 army on {territory.name} "
                          f"(now {territory.armies} armies)")
        
        # Advance to attacking phase if placement is complete
        if (current_turn.phase == TurnPhase.PLACEMENT and 
            current_turn.reinforcements_remaining == 0):
            current_turn.advance_phase()
            print("  Advanced to attacking phase")
        
        # Execute attacking phase
        attack_count = 0
        max_attacks = 10  # Prevent infinite attack loops
        
        while (current_turn.phase == TurnPhase.ATTACKING and 
               attack_count < max_attacks):
            
            attack_decision = agent.decide_attack(game_state, current_turn)
            if attack_decision is None:
                break
            
            attacker_id, defender_id = attack_decision
            attacker = game_state.get_territory(attacker_id)
            defender = game_state.get_territory(defender_id)
            
            if (attacker and defender and 
                attacker.is_owned_by(agent.player_id) and 
                not defender.is_owned_by(agent.player_id) and 
                attacker.can_attack_from() and defender.can_be_attacked()):
                
                # Start the attack
                if current_turn.start_attack(attacker, defender):
                    print(f"  Attacking {defender.name} from {attacker.name}")
                    
                    # Resolve the attack
                    attack_result = current_turn.resolve_attack()
                    if attack_result:
                        # Update territories based on attack result
                        attacker.armies -= attack_result['attacker_casualties']
                        defender.armies -= attack_result['defender_casualties']
                        
                        print(f"    Attacker casualties: {attack_result['attacker_casualties']}")
                        print(f"    Defender casualties: {attack_result['defender_casualties']}")
                        
                        # Check if territory was conquered
                        if attack_result.get('territory_conquered', False):
                            defender.set_owner(agent.player_id, 
                                             attack_result.get('surviving_attackers', 1))
                            print(f"    Conquered {defender.name}!")
                        
                        attack_count += 1
            else:
                break
        
        # Advance to movement phase
        if current_turn.phase == TurnPhase.ATTACKING:
            current_turn.advance_phase()
            print("  Advanced to movement phase")
        
        # Execute movement phase
        movement_decision = agent.decide_movement(game_state, current_turn)
        if movement_decision is not None:
            source_id, target_id, army_count = movement_decision
            source_territory = game_state.get_territory(source_id)
            target_territory = game_state.get_territory(target_id)
            
            if (source_territory and target_territory and 
                source_territory.is_owned_by(agent.player_id) and 
                target_territory.is_owned_by(agent.player_id) and 
                source_territory.armies > army_count):
                
                # Start the movement
                if current_turn.start_movement(source_territory, target_territory):
                    # Set the army count for movement
                    if current_turn.current_movement:
                        current_turn.current_movement.moving_armies = army_count
                    
                    # Execute the movement
                    movement_result = current_turn.execute_movement()
                    if movement_result:
                        # Update territories based on movement result
                        source_territory.armies -= army_count
                        target_territory.armies += army_count
                        
                        print(f"  Moved {army_count} armies from {source_territory.name} to {target_territory.name}")
                        print(f"    {source_territory.name}: {source_territory.armies + army_count} -> {source_territory.armies} armies")
                        print(f"    {target_territory.name}: {target_territory.armies - army_count} -> {target_territory.armies} armies")
                        
                        # Trigger movement animation if renderer is available
                        if renderer:
                            renderer.start_movement_animation(
                                source_territory_id=source_id,
                                target_territory_id=target_id,
                                duration=1.5
                            )
                else:
                    print(f"  Movement from {source_territory.name} to {target_territory.name} failed - not adjacent or invalid")
        
        # End the turn
        print(f"  {agent.name} turn complete\n")
        return True


# Factory function for creating random agents
def create_random_agents(game_state: GameState, 
                        agent_player_ids: List[int], 
                        attack_probability: float = 0.5) -> AgentController:
    """
    Factory function to create and register random agents for specified 
    players. Creates a configured agent controller with random agents.
    
    :param game_state: GameState containing player information for agent 
                      creation
    :param agent_player_ids: List of player IDs that should be controlled 
                            by random agents
    :param attack_probability: Probability (0.0-1.0) that agents will 
                              attack when opportunities arise
    :returns: AgentController with registered random agents for specified 
             players
    """
    controller = AgentController()
    
    for player_id in agent_player_ids:
        if player_id in game_state.players:
            agent = RandomAgent(player_id, attack_probability)
            controller.register_agent(agent)
            
            # Mark player as non-human in game state
            player = game_state.get_player(player_id)
            if player:
                player.is_human = False
    
    return controller