"""
Territory selection handler for the Risk simulation.
Manages territory selection state and responds to selection events.
"""

from typing import Optional, Set, Callable
from ..state import GameState, Territory
from ..state.turn_manager import TurnManager, TurnPhase


class TerritorySelectionHandler:
    """Handles territory selection logic and state management."""
    
    def __init__(self, game_state: GameState, turn_manager: Optional[TurnManager] = None):
        """Initialize the selection handler. Sets up selection state tracking for the given game state.
        
        :param game_state: GameState to manage selections for
        :param turn_manager: Optional TurnManager for turn-based selection handling
        """
        self.game_state = game_state
        self.turn_manager = turn_manager
        self.selected_territories: Set[int] = set()  # Territory IDs
        self.primary_selection: Optional[int] = None  # Primary selected territory ID
        self.multi_select_enabled = False  # Allow multiple selections
        
        # Turn-based action callbacks
        self.placement_callback: Optional[Callable] = None
        self.attack_callback: Optional[Callable] = None
        self.movement_callback: Optional[Callable] = None
    
    def handle_territory_selected(self, input_event) -> None:
        """Handle territory selection events. Processes territory selection and updates selection state.
        
        :param input_event: Input event containing territory selection data with territory_id and territory
        """
        if not input_event.data or 'territory_id' not in input_event.data:
            return
        
        territory_id = input_event.data['territory_id']
        territory = input_event.data.get('territory')
        
        if not territory:
            territory = self.game_state.territories.get(territory_id)
        
        if not territory:
            print(f"Warning: Territory with ID {territory_id} not found")
            return
        
        # Handle turn-based actions BEFORE changing selection
        self._handle_turn_based_action_before_selection(territory)
        
        # Handle multi-select vs single-select behavior
        if self.multi_select_enabled:
            self._handle_multi_select(territory_id, territory)
        else:
            self._handle_single_select(territory_id, territory)
        
        # Handle turn-based actions AFTER changing selection (for placement mainly)
        self._handle_turn_based_action(territory)
        
        print(f"Territory selection handler: Selected {territory.name} (ID: {territory_id})")
        print(f"  Total selected territories: {len(self.selected_territories)}")
    
    def handle_territory_deselected(self, input_event) -> None:
        """Handle territory deselection events (clicking on empty space). Clears selections when clicking empty areas.
        
        :param input_event: Input event containing deselection data
        """
        if not self.multi_select_enabled:
            # Clear all selections when clicking empty space in single-select mode
            self.clear_all_selections()
            print("Territory selection handler: Cleared all selections")
    
    def _handle_single_select(self, territory_id: int, territory: Territory) -> None:
        """Handle single territory selection (clear others, select this one). Implements single-selection behavior.
        
        :param territory_id: ID of territory to select
        :param territory: Territory object to select
        """
        # Clear previous selections
        self.clear_all_selections()
        
        # Select the new territory
        self.selected_territories.add(territory_id)
        self.primary_selection = territory_id
        territory.set_selected(True)
    
    def _handle_multi_select(self, territory_id: int, territory: Territory) -> None:
        """Handle multi-territory selection (toggle selection). Implements multi-selection behavior with toggling.
        
        :param territory_id: ID of territory to toggle selection for
        :param territory: Territory object to toggle selection for
        """
        if territory_id in self.selected_territories:
            # Deselect if already selected
            self.selected_territories.remove(territory_id)
            territory.set_selected(False)
            
            # Update primary selection if this was the primary
            if self.primary_selection == territory_id:
                self.primary_selection = next(iter(self.selected_territories), None)
        else:
            # Select if not already selected
            self.selected_territories.add(territory_id)
            territory.set_selected(True)
            
            # Set as primary if no primary exists
            if self.primary_selection is None:
                self.primary_selection = territory_id
    
    def clear_all_selections(self) -> None:
        """
        Clear all territory selections.
        """
        for territory_id in self.selected_territories:
            territory = self.game_state.territories.get(territory_id)
            if territory:
                territory.set_selected(False)
        
        self.selected_territories.clear()
        self.primary_selection = None
    
    def set_multi_select_enabled(self, enabled: bool) -> None:
        """
        Enable or disable multi-select mode.
        
        :param enabled: True to enable multi-select, False for single-select
        """
        # If disabling multi-select while multiple territories are selected,
        # keep only the primary selection
        if not enabled and len(self.selected_territories) > 1:
            primary_id = self.primary_selection
            self.clear_all_selections()
            
            if (primary_id and 
                primary_id in self.game_state.territories):
                self.selected_territories.add(primary_id)
                self.primary_selection = primary_id
                self.game_state.territories[primary_id].set_selected(True)
        
        self.multi_select_enabled = enabled
    
    def get_selected_territories(self) -> Set[int]:
        """Get IDs of all selected territories.
        
        Returns:
            Set of territory IDs
        """
        return self.selected_territories.copy()
    
    def get_primary_selected_territory(self) -> Optional[Territory]:
        """Get the primary selected territory.
        
        Returns:
            Primary selected Territory object, or None if no selection
        """
        if self.primary_selection is None:
            return None
        return self.game_state.territories.get(self.primary_selection)
    
    def is_territory_selected(self, territory_id: int) -> bool:
        """Check if a territory is currently selected.
        
        Args:
            territory_id: ID of territory to check
            
        Returns:
            True if territory is selected
        """
        return territory_id in self.selected_territories
    
    def select_territory_by_id(self, territory_id: int) -> bool:
        """Programmatically select a territory by ID.
        
        Args:
            territory_id: ID of territory to select
            
        Returns:
            True if selection successful, False if territory not found
        """
        territory = self.game_state.territories.get(territory_id)
        if not territory:
            return False
        
        if self.multi_select_enabled:
            self._handle_multi_select(territory_id, territory)
        else:
            self._handle_single_select(territory_id, territory)
        
        return True
    
    def deselect_territory_by_id(self, territory_id: int) -> bool:
        """Programmatically deselect a territory by ID.
        
        Args:
            territory_id: ID of territory to deselect
            
        Returns:
            True if deselection successful, False if territory not found/selected
        """
        if territory_id not in self.selected_territories:
            return False
        
        territory = self.game_state.territories.get(territory_id)
        if not territory:
            return False
        
        self.selected_territories.remove(territory_id)
        territory.set_selected(False)
        
        # Update primary selection if this was the primary
        if self.primary_selection == territory_id:
            self.primary_selection = next(iter(self.selected_territories), None)
        
        return True
    
    def get_selection_info(self) -> dict:
        """Get detailed information about current selections.
        
        Returns:
            Dictionary with selection information
        """
        selected_territories = []
        for territory_id in self.selected_territories:
            territory = self.game_state.territories.get(territory_id)
            if territory:
                selected_territories.append({
                    'id': territory.id,
                    'name': territory.name,
                    'owner': territory.owner,
                    'armies': territory.armies,
                    'continent': territory.continent,
                    'is_primary': territory_id == self.primary_selection
                })
        
        return {
            'count': len(self.selected_territories),
            'multi_select_enabled': self.multi_select_enabled,
            'primary_selection_id': self.primary_selection,
            'territories': selected_territories
        }
    
    def set_turn_manager(self, turn_manager: TurnManager) -> None:
        """
        Set the turn manager for turn-based selection handling.
        
        :param turn_manager: TurnManager instance to use for turn-based actions
        """
        self.turn_manager = turn_manager
    
    def set_action_callbacks(self, placement_callback: Optional[Callable] = None,
                           attack_callback: Optional[Callable] = None, 
                           movement_callback: Optional[Callable] = None) -> None:
        """
        Set callbacks for turn-based actions.
        
        :param placement_callback: Function to call for reinforcement placement
        :param attack_callback: Function to call for starting attacks
        :param movement_callback: Function to call for starting movements
        """
        self.placement_callback = placement_callback
        self.attack_callback = attack_callback
        self.movement_callback = movement_callback
    
    def _handle_turn_based_action(self, territory: Territory) -> None:
        """
        Handle turn-based actions when a territory is selected (for placement).
        
        :param territory: Territory that was selected
        """
        if not self.turn_manager:
            return
        
        current_turn = self.turn_manager.get_current_turn()
        if not current_turn:
            return
        
        # Only handle placement here - other phases are handled before selection
        if current_turn.phase == TurnPhase.PLACEMENT:
            self._handle_placement_click(territory, current_turn)
    
    def _handle_turn_based_action_before_selection(self, territory: Territory) -> None:
        """
        Handle turn-based actions when a territory is selected (before changing selection).
        
        :param territory: Territory that was selected
        """
        if not self.turn_manager:
            print("DEBUG: No turn manager available")
            return
        
        current_turn = self.turn_manager.get_current_turn()
        if not current_turn:
            print("DEBUG: No current turn available")
            return
        
        print(f"DEBUG: Current turn phase: {current_turn.phase.value}, player: {current_turn.player_id}")
        print(f"DEBUG: Reinforcements remaining: {current_turn.reinforcements_remaining}")
        
        # Handle phases that need to know previous selection
        if current_turn.phase == TurnPhase.ATTACKING:
            self._handle_attack_click(territory, current_turn)
        elif current_turn.phase == TurnPhase.MOVING:
            self._handle_movement_click(territory, current_turn)
    
    def _handle_placement_click(self, territory: Territory, current_turn) -> None:
        """
        Handle territory click during placement phase.
        
        :param territory: Territory that was clicked
        :param current_turn: Current turn state
        """
        # Can only place on owned territories
        if territory.owner != current_turn.player_id:
            print("Cannot place reinforcements on territory you don't own")
            return
        
        # Trigger placement if callback is set
        if self.placement_callback:
            self.placement_callback()
    
    def _handle_attack_click(self, territory: Territory, current_turn) -> None:
        """
        Handle territory click during attacking phase.
        
        :param territory: Territory that was clicked  
        :param current_turn: Current turn state
        """
        print(f"DEBUG: Attack click on {territory.name}, current phase: {current_turn.phase.value}")
        print(f"DEBUG: Current selection state - primary: {self.primary_selection}, selected: {self.selected_territories}")
        
        if current_turn.current_attack:
            # Already in an attack - ignore additional clicks
            print("DEBUG: Already in an attack, ignoring click")
            return
        
        # Get previously selected territory as potential attacker
        primary_territory = self.get_primary_selected_territory()
        print(f"DEBUG: Primary territory: {primary_territory.name if primary_territory else 'None'}")
        
        if not primary_territory or primary_territory.id == territory.id:
            # No previous selection or clicking same territory - check if this can be an attacker
            if (territory.owner == current_turn.player_id and 
                territory.armies > 1):
                print(f"Selected {territory.name} as attacker. Now click on adjacent enemy territory.")
                # print(f"DEBUG: Adjacent territories: {territory.adjacent_territories}")
                # Don't change selection here - let the normal selection logic handle it
            else:
                print("Selected territory cannot attack (need >1 army and ownership)")
                print(f"DEBUG: Territory owner: {territory.owner}, player: {current_turn.player_id}, armies: {territory.armies}")
            return
        
        print(f"DEBUG: Attempting attack from {primary_territory.name} (owner: {primary_territory.owner}) to {territory.name} (owner: {territory.owner})")
        print(f"DEBUG: Primary territory adjacent: {[ t.name for t in primary_territory.adjacent_territories]}")
        print(f"DEBUG: Target territory ID: {territory.id}")
        
        # Check if this is a valid attack target
        if (territory.owner != current_turn.player_id and  # Enemy territory
            territory in primary_territory.adjacent_territories):  # Adjacent
            
            # Start attack
            if current_turn.start_attack(primary_territory, territory):
                print(f"Starting attack from {primary_territory.name} to {territory.name}")
                if self.attack_callback:
                    self.attack_callback()
            else:
                print("Cannot start attack - invalid conditions")
        else:
            if territory.owner == current_turn.player_id:
                print("Invalid attack target - cannot attack own territory")
            elif territory.id not in primary_territory.adjacent_territories:
                print("Invalid attack target - territories are not adjacent")
                print(f"DEBUG: Available adjacent targets: {[self.game_state.territories[tid].name for tid in primary_territory.adjacent_territories if tid in self.game_state.territories]}")
            else:
                print("Invalid attack target - must be adjacent enemy territory")
    
    def _handle_movement_click(self, territory: Territory, current_turn) -> None:
        """
        Handle territory click during movement phase.
        
        :param territory: Territory that was clicked
        :param current_turn: Current turn state  
        """
        if current_turn.current_movement:
            # Already in a movement - ignore additional clicks
            return
        
        # Get previously selected territory as potential source
        primary_territory = self.get_primary_selected_territory()
        
        if not primary_territory:
            # No previous selection - check if this can be a source
            if (territory.owner == current_turn.player_id and 
                territory.armies > 1):
                print(f"Selected {territory.name} as movement source. Now click on adjacent owned territory.")
            else:
                print("Selected territory cannot move armies (need >1 army and ownership)")
            return
        
        # Check if this is a valid movement target
        if (territory.owner == current_turn.player_id and  # Owned territory
            territory.id in primary_territory.adjacent_territories):  # Adjacent
            
            # Start movement
            if current_turn.start_movement(primary_territory, territory):
                print(f"Starting movement from {primary_territory.name} to {territory.name}")
                if self.movement_callback:
                    self.movement_callback()
            else:
                print("Cannot start movement - invalid conditions")
        else:
            print("Invalid movement target - must be adjacent owned territory")