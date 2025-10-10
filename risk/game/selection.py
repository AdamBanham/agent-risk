"""
Territory selection handler for the Risk simulation.
Manages territory selection state and responds to selection events.
"""

from typing import Optional, Set
from ..state import GameState, Territory


class TerritorySelectionHandler:
    """Handles territory selection logic and state management."""
    
    def __init__(self, game_state: GameState):
        """Initialize the selection handler. Sets up selection state tracking for the given game state.
        
        :param game_state: GameState to manage selections for
        """
        self.game_state = game_state
        self.selected_territories: Set[int] = set()  # Territory IDs
        self.primary_selection: Optional[int] = None  # Primary selected territory ID
        self.multi_select_enabled = False  # Allow multiple selections
    
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
        
        # Handle multi-select vs single-select behavior
        if self.multi_select_enabled:
            self._handle_multi_select(territory_id, territory)
        else:
            self._handle_single_select(territory_id, territory)
        
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