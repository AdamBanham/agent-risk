# Agent Risk - Copilot Instructions

## 🤖 New Agent Onboarding
**Before starting any task**, please:

1. **Read these instructions completely** - This document contains essential project-specific architecture, patterns, and constraints
2. **Explore the current codebase** - Check what modules/files already exist vs. what's described here
3. **Update these instructions** - If you discover new patterns, architectural decisions, or find outdated information during your work, please update this file to help future agents
4. **Follow the 4-module architecture** - Ensure your work fits within the `game`, `handler`, `agent`, and `state` module boundaries (note: currently only `game` and `state` are implemented)
5. **Prioritize the formal AI methods** - This is a research project focused on HTN, Behavior Trees, Finite Automata, and Petri nets for agent behaviors (📋 **PLANNED** for future development)

**Key Questions to Ask Yourself:**
- Does my implementation support dynamic board generation with configurable (g, p, s) parameters? ✅ **IMPLEMENTED**
- Am I using the event queue system for all game state changes? (📋 **PLANNED** - not yet implemented)
- Will my code support replay functionality through serializable events? (📋 **PLANNED** - not yet implemented)
- Does my agent implementation follow one of the formal behavior representation methods? (📋 **PLANNED** - not yet implemented)
- Does my implementation work with the keyboard shortcuts for rapid testing? ✅ **IMPLEMENTED**

## Project Overview
A modular event-driven simulation framework inspired by the board game of Risk 
using pygame. This project implements a configurable Risk-like simulation with 
AI agents using formal behavior representation methods (HTN, Behavior Trees, 
Finite Automata, Petri nets). **The board is dynamically generated based on 
simulation parameters, not a fixed 1:1 recreation of the Risk board game.**

## Running the Simulation
The simulation can be started using the `run_game.py` script with configurable parameters:

```bash
python run_game.py [-g REGIONS] [-p PLAYERS] [-s ARMY_SIZE]
```

**Command-line Arguments:**
- `-g, --regions`: Number of territories/regions to generate (default: 15)
- `-p, --players`: Number of players in the simulation (default: 3) 
- `-s, --army-size`: Starting army count **per player** (default: 20) - Each player gets exactly this many armies

**Examples:**
```bash
# Run with default parameters (15 regions, 3 players, 20 armies each)
python run_game.py

# Run a larger simulation (30 regions, 4 players, 15 armies per player = 60 total armies)
python run_game.py -g 30 -p 4 -s 15

# Run a smaller test simulation (8 regions, 2 players, 10 armies per player = 20 total armies)
python run_game.py --regions 8 --players 2 --army-size 10
```

The script includes validation to ensure minimum values (regions ≥ 1, players ≥ 2, army-size ≥ 1).

**Runtime Controls (Keyboard Shortcuts):**
Once the simulation is running, you can use these keyboard shortcuts for real-time testing:

- **Ctrl+R**: Regenerate game state/board with current parameters
- **Ctrl+G**: Increase regions (+1) and regenerate
- **Ctrl+P**: Increase players (+1) and regenerate  
- **Ctrl+S**: Increase starting armies (+1) and regenerate
- **H**: Show help with all available controls
- **I**: Show info for selected territory (click to select)
- **D**: Show debug information
- **ESC**: Quit game

These shortcuts enable rapid iteration and testing of different board configurations without restarting the application.

## Architecture Modules
The project follows a modular architecture with the following structure:

**Current Implementation:**
- **`game`** - Event loop, pygame rendering, and user input handling ✅ **IMPLEMENTED**
- **`state`** - Game state data structures, territory management, and board generation ✅ **IMPLEMENTED**

**Planned Modules:**
- **`handler`** - Event queue management for simulation actions (📋 **PLANNED**)
- **`agent`** - AI agent behaviors using formal methods (📋 **PLANNED**)

**Note for Future Development:** The current implementation uses `state/` for game state management. Future work should implement the `handler/` and `agent/` modules to complete the 4-module architecture. The `state/` module currently handles both world state and board generation functionality.

## Project Structure
**Current Implementation:**
```
risk/
├── game/                    # Pygame event loop and rendering ✅ IMPLEMENTED
│   ├── __init__.py
│   ├── loop.py             # Main game event loop with keyboard shortcuts
│   ├── renderer.py         # Pygame board rendering
│   └── input.py            # User input handling with Ctrl+ shortcuts
├── state/                   # Game state management ✅ IMPLEMENTED
│   ├── __init__.py
│   ├── game_state.py       # Game state representation
│   ├── territory.py        # Territory definitions and management
│   └── board_generator.py  # Dynamic board generation using polygon subdivision
└── tests/                   # Unit and integration tests
    ├── __init__.py
    └── test_board.py
```

**Planned Structure for Future Development:**
```
risk/
├── handler/                 # Event queue system 📋 PLANNED
│   ├── __init__.py
│   ├── queue.py            # Event queue management
│   └── events.py           # Event type definitions
├── agent/                   # AI agent implementations 📋 PLANNED  
│   ├── __init__.py
│   ├── base.py             # Abstract agent interface
│   ├── htn_agent.py        # Hierarchical Task Network agent
│   ├── bt_agent.py         # Behavior Tree agent
│   ├── fa_agent.py         # Finite Automata agent
│   └── pn_agent.py         # Petri Net agent
```

## Game Flow Implementation
Follow the specific game phases as defined:

### Phase Structure
- **`init`** - Setup board with parameters (g=regions, p=players, s=army_size)
- **`game`** - Main event loop containing:
  - **`game turn`** - Cycle through active players
  - **`player turn`** - Individual player actions:
    - `get troops` - Game distributes reinforcement troops
    - `place troops` - Agent decides troop placement
    - `move troops` - Agent attacks/moves to adjacent regions
    - `end turn` - Agent signals turn completion
  - **`game turn cleanup`** - Check win conditions
  - **`game end`** - Victory condition met
- **`score`** - Post-simulation agent performance evaluation

## Development Patterns

### Event System Design (📋 **PLANNED**)
- Use event queue in `handler` module for all game actions
- Events should be serializable for replay functionality
- Implement clear event types for each game action (place_troop, attack, etc.)

Example event structure:
```python
@dataclass
class PlaceTroopEvent:
    player_id: int
    territory_id: int
    troop_count: int
    timestamp: float

@dataclass  
class AttackEvent:
    attacker_id: int
    from_territory: int
    to_territory: int
    attacking_armies: int
    dice_results: List[int]
```

### Agent Formal Methods (📋 **PLANNED**)
Implement agents using academic formalisms from "Action, Planning, and Learning":
- **HTN (Hierarchical Task Networks)** - Decompose high-level strategies into 
primitive actions
- **Behavior Trees** - Reactive decision-making with clear success/failure states  
- **Finite Automata** - State-based decision making for different game phases
- **Petri Nets** - Concurrent action modeling and resource management

Example agent interface:
```python
class BaseAgent(ABC):
    @abstractmethod
    def place_reinforcements(self, game_state: GameState, available_troops: int) -> List[PlacementAction]:
        pass
    
    @abstractmethod
    def choose_attacks(self, game_state: GameState) -> List[AttackAction]:
        pass
    
    @abstractmethod
    def end_turn_movements(self, game_state: GameState) -> List[MovementAction]:
        pass
```

### Pygame Integration (✅ **IMPLEMENTED**)
- Use pygame for board visualization and user interaction
- Separate rendering logic from game state logic
- Support both human player input and agent visualization

Example pygame structure:
```python
class GameRenderer:
    def draw_board(self, game_state: GameState) -> None:
        # Render territories based on current board configuration
        # Highlight available moves/attacks for current board layout
        # Show current player turn
        
    def handle_click(self, pos: Tuple[int, int]) -> Optional[Territory]:
        # Convert screen coordinates to territory selection
```

### World State Management (✅ **IMPLEMENTED**)
- Maintain complete game state for replay capability
- Generate board layout dynamically based on simulation parameters (g=regions, 
p=players, s=army_size)
- Handle adjacency relationships for generated territories
- Track armies, territory ownership, and game state across different board configurations

## Board Generation and Game Rules Implementation
Key mechanics for the configurable simulation:

### Dynamic Board Setup
- Generate `g` territories based on simulation parameters
- Create adjacency graph for territory connections
- Distribute `p` players across the generated board
- Assign starting army size `s` **per player** (each player gets exactly `s` armies)
- Optional: Generate continent groupings for bonus calculations

**Current Board Generation Implementation:**
The current system uses **polygon subdivision** for dynamic board generation:
1. **Initial Continent**: Creates a large jagged polygon covering ~75% of the screen
2. **Recursive Subdivision**: Uses random walk division lines to split polygons
3. **Shared Boundaries**: Ensures territories share exact boundary segments for proper adjacency
4. **Area Preservation**: Tracks and minimizes area loss during subdivision process
5. **Adjacency Calculation**: Automatically determines which territories border each other
6. **Territory Assignment**: Randomly distributes territories among players with initial armies

**⚠️ Important Army Distribution Rule:**
The `s` parameter represents armies **per player**, not total armies to share. Each player receives exactly `s` armies distributed across their territories. For example, with parameters `(g=10, p=3, s=15)`, each of the 3 players gets exactly 15 armies, for a total of 45 armies on the board.

The board generator is robust and handles edge cases like very small polygons without crashing.

### Core Game Mechanics
- **Reinforcements**: Configurable reinforcement rules based on territories 
controlled
- **Attacking**: Dice-based combat between adjacent territories
- **Movement**: Movement between connected owned territories
- **Victory**: Game ends when one player controls all territories on the 
generated board

## Key Dependencies to Consider
- `pygame` for graphics and user interface (required)
- `dataclasses` for event/state definitions
- `enum` for game constants (territories, continents, phases)
- `typing` for comprehensive type hints
- `unittest` for testing framework

## Testing Strategy
- Unit tests for game rules and mechanics
- Integration tests for full game simulations
- Property-based testing for game invariants
- Agent vs agent testing for strategy validation

## Common Patterns
- Use type hints extensively for agent interfaces and game state
- Implement `__repr__` methods for debugging game states
- Create factory methods for complex game setup scenarios
- Use context managers for simulation lifecycle management

Example patterns:
```python
# Factory method for game setup
def create_game(g: int, p: int, s: int) -> GameState:
    return GameState.from_parameters(regions=g, players=p, army_size=s)

# Context manager for simulations  
with GameSimulation(agents=[agent1, agent2], regions=20, army_size=10) as sim:
    result = sim.run_complete_game()
```

## Testing and Development
When testing new features:
- Use `python run_game.py -g 5 -p 2 -s 5` for quick testing with minimal setup (2 players, 5 armies each = 10 total)
- Use `python run_game.py -g 20 -p 4 -s 30` for comprehensive behavior testing (4 players, 30 armies each = 120 total)
- Default parameters (`python run_game.py`) provide balanced simulation for development (3 players, 20 armies each = 60 total)

**Runtime Testing with Keyboard Shortcuts:**
For rapid iteration and testing of different board configurations:
- Use `python run_game.py -g 3 -p 2 -s 3` for minimal startup time
- Use **Ctrl+G** repeatedly to test different region counts incrementally
- Use **Ctrl+P** to add more players and see how territory distribution changes
- Use **Ctrl+S** to increase armies and see how initial placement affects gameplay
- Use **Ctrl+R** to regenerate the same configuration with different random layouts
- All changes trigger immediate board regeneration for visual feedback

## Performance Considerations
- Cache territory adjacency calculations
- Use efficient data structures for large-scale tournaments
- Consider async patterns for parallel agent decision-making
- Profile bottlenecks in simulation loops