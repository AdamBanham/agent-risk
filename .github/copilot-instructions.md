# Agent Risk - Copilot Instructions

## 🤖 New Agent Onboarding
**Before starting any task**, please:

1. **Read these instructions completely** - This document contains essential project-specific architecture, patterns, and constraints
2. **Explore the current codebase** - Check what modules/files already exist vs. what's described here
3. **Update these instructions** - If you discover new patterns, architectural decisions, or find outdated information during your work, please update this file to help future agents
4. **Follow the separation of concerns** - Ensure your code follows the established architectural patterns and module boundaries described below
5. **Prioritize the formal AI methods** - This is a research project focused on HTN, Behavior Trees, Finite Automata, and Petri nets for agent behaviors (📋 **PLANNED** for future development)

**Key Questions to Ask Yourself:**
- Does my implementation support dynamic board generation with configurable (g, p, s) parameters? ✅ **IMPLEMENTED**
- Am I following the established separation of concerns (state management, rendering, input handling, etc.)? ✅ **CRITICAL**
- Does my code preserve the modular architecture with proper imports and dependencies? ✅ **CRITICAL**
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
The project follows a **modular architecture with clear separation of concerns**. Each module has distinct responsibilities and should maintain clean boundaries:

**Current Implementation (✅ IMPLEMENTED):**
- **`risk.game`** - Event loop, pygame rendering, and user input handling
  - `loop.py` - Main game event loop with keyboard shortcuts and parameter management
  - `renderer.py` - Pygame board rendering and visualization
  - `input.py` - User input handling with Ctrl+ shortcuts and event processing
- **`risk.state`** - Game state data structures, territory management, and board generation
  - `game_state.py` - Core GameState, Player classes, and game phase management
  - `territory.py` - Territory definitions, ownership states, and adjacency management
  - `board_generator.py` - Dynamic board generation using polygon subdivision algorithms
- **`risk.utils`** - Shared utility functions and helper classes
  - `distance.py` - Point geometry, distance calculations, polygon operations, and random walk algorithms

**Planned Modules (📋 PLANNED):**
- **`risk.handler`** - Event queue management for simulation actions
- **`risk.agent`** - AI agent behaviors using formal methods

## Critical Architectural Patterns

### ✅ **SEPARATION OF CONCERNS - STRICTLY ENFORCE**
The codebase follows clear module boundaries that **MUST** be preserved:

**1. Geometric/Mathematical Operations → `risk.utils.distance`**
```python
# ✅ CORRECT: Put pure math functions here
def euclidean_distance(point1: Point, point2: Point) -> float
def random_walk(start: Point, end: Point, ...) -> List[Point]
def clean_sequence(vertices: List[Point]) -> List[Point]

# ❌ WRONG: Don't put these in board_generator.py or other modules
```

**2. Game State & Board Logic → `risk.state.*`**
```python
# ✅ CORRECT: Game entities and board generation
class GameState, Player, Territory  # in game_state.py
class PolygonTerritory, BoardGenerator  # in board_generator.py

# ❌ WRONG: Don't put pygame rendering code here
# ❌ WRONG: Don't put input handling here
```

**3. Rendering & Visualization → `risk.game.renderer`**
```python
# ✅ CORRECT: Pure rendering - reads state, never modifies it
def draw_board(self) -> None:
def get_territory_at_position(self, pos) -> Optional[Territory]:

# ❌ WRONG: Don't modify game state in renderer
# ❌ WRONG: Don't put game logic here
```

**4. Input & Events → `risk.game.input`**
```python
# ✅ CORRECT: Event processing with callbacks
def handle_event(self, event: pygame.event.Event) -> None:
def register_callback(self, event_type: str, callback: Callable) -> None:

# ❌ WRONG: Don't put rendering code here
# ❌ WRONG: Don't put game logic here
```

**5. Coordination & Lifecycle → `risk.game.loop`**
```python
# ✅ CORRECT: Orchestrates all components
def __init__(self, ...): # dependency injection
def run(self) -> None:   # main game loop

# ❌ WRONG: Don't put specific rendering/input logic here
```

**Critical Import Patterns:**
```python
# ✅ GOOD: utils ← state ← game (dependency flow)
from ..utils.distance import Point, random_walk  # state uses utils
from ..state import GameState, Territory         # game uses state

# ❌ BAD: No circular dependencies
# Don't import game modules in state modules
# Don't import state modules in utils modules
```

## Current Separation of Concerns

### ✅ **State Management** (`risk.state`)
- **Purpose**: Pure data structures and game state logic
- **Responsibilities**: 
  - Game state representation (`GameState`, `Player`, `Territory`)
  - Territory ownership and army management
  - Board generation and territory adjacency calculation
  - Game phase tracking and turn management
- **Dependencies**: Only depends on `risk.utils` for geometric calculations
- **Key Pattern**: Immutable-focused design with clear state transitions

### ✅ **Rendering** (`risk.game.renderer`)
- **Purpose**: Pygame-based visualization of game state
- **Responsibilities**:
  - Drawing territories, armies, and player information
  - Color management and visual styling
  - Territory selection and hit testing
  - UI legends and game information display
- **Dependencies**: Depends on `risk.state` for game data, pygame for graphics
- **Key Pattern**: Renderer operates on read-only game state, no state mutations

### ✅ **Input Handling** (`risk.game.input`)
- **Purpose**: Event processing and user interaction
- **Responsibilities**:
  - Pygame event processing and keyboard shortcuts
  - Mouse click handling and territory selection
  - Command pattern for input events
  - Help and debug information display
- **Dependencies**: pygame for events, minimal coupling to other modules
- **Key Pattern**: Callback-based event system with clean abstractions

### ✅ **Game Loop** (`risk.game.loop`)
- **Purpose**: Main coordination and application lifecycle
- **Responsibilities**:
  - Pygame initialization and window management
  - Main event loop and frame rate control
  - Parameter management and board regeneration
  - Coordination between renderer, input handler, and game state
- **Dependencies**: Orchestrates all other modules
- **Key Pattern**: Central coordinator with dependency injection

### ✅ **Utilities** (`risk.utils`)
- **Purpose**: Shared geometric and mathematical operations
- **Responsibilities**:
  - Point geometry and distance calculations
  - Random walk generation for polygon subdivision
  - Polygon validation and cleanup operations
  - Generic algorithms used across modules
- **Dependencies**: No internal dependencies, only standard library
- **Key Pattern**: Pure functions with clear mathematical abstractions

## Project Structure
**Current Implementation (✅ IMPLEMENTED):**
```
risk/
├── __init__.py                 # Package version info
├── game/                       # Pygame event loop and rendering
│   ├── __init__.py            # Module exports (GameLoop, GameRenderer, etc.)
│   ├── loop.py                # Main game event loop with keyboard shortcuts
│   ├── renderer.py            # Pygame board rendering and visualization
│   └── input.py               # User input handling with Ctrl+ shortcuts
├── state/                      # Game state management
│   ├── __init__.py            # Module exports (GameState, Territory, etc.)
│   ├── game_state.py          # GameState, Player classes, and game phases
│   ├── territory.py           # Territory definitions and ownership management
│   └── board_generator.py     # Dynamic board generation using polygon subdivision
├── utils/                      # Shared utility functions
│   └── distance.py            # Point geometry, distance calculations, random walks
└── tests/                      # Unit and integration tests
    ├── __init__.py
    └── state/
        ├── __init__.py
        └── test_board.py       # Board generation tests
```

**Planned Structure for Future Development (📋 PLANNED):**
```
risk/
├── handler/                    # Event queue system
│   ├── __init__.py
│   ├── queue.py               # Event queue management
│   └── events.py              # Event type definitions
├── agent/                      # AI agent implementations  
│   ├── __init__.py
│   ├── base.py                # Abstract agent interface
│   ├── htn_agent.py           # Hierarchical Task Network agent
│   ├── bt_agent.py            # Behavior Tree agent
│   ├── fa_agent.py            # Finite Automata agent
│   └── pn_agent.py            # Petri Net agent
```

**Entry Point:**
- `run_game.py` - Command-line script with argument parsing for (g, p, s) parameters

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

### Architectural Principles (✅ **CRITICAL PATTERNS**)
The codebase follows these essential architectural patterns:

**Separation of Concerns:**
- **Geometric calculations** (Point class, distance functions, random walks) → `risk.utils.distance`
- **Polygon operations** (subdivision, validation, area calculations) → `risk.state.board_generator` 
- **Game state management** (GameState, Player, Territory classes) → `risk.state`
- **Rendering logic** (pygame drawing, colors, visualization) → `risk.game.renderer`
- **Input handling** (events, callbacks, keyboard shortcuts) → `risk.game.input`
- **Application lifecycle** (initialization, main loop, coordination) → `risk.game.loop`

**Dependency Flow:**
```
risk.game.loop (coordinator)
├── risk.game.renderer (depends on state)
├── risk.game.input (minimal dependencies)
└── risk.state (depends on utils)
    └── risk.utils (no internal dependencies)
```

**Key Design Patterns:**
- **Event-Driven Architecture**: Input handlers use callbacks for loose coupling
- **Dependency Injection**: GameLoop coordinates components through constructor injection
- **Immutable State Focus**: GameState designed for clear state transitions
- **Factory Methods**: `GameState.create_new_game()` for consistent initialization
- **Pure Functions**: Utility functions in `risk.utils` have no side effects

### Current Board Generation Implementation (✅ **IMPLEMENTED**)
The board generation uses **polygon subdivision** with these key components:

**In `risk.state.board_generator` (State Management):**
- `PolygonTerritory` class: Manages polygon data during subdivision process
- `BoardGenerator` class: Orchestrates board creation and territory assignment
- `create_polygon_to_fill_space()`: Creates initial continent using random walks
- Adjacency calculation: Determines territory borders through shared edges
- Territory distribution: Assigns territories and armies to players
- Continent assignment: Geographic grouping of territories

**In `risk.utils.distance` (Pure Utilities):**
- `Point` dataclass: Represents geometric coordinates
- `random_walk()`: Generates jagged lines for polygon subdivision
- `clean_sequence()`: Removes duplicate/close vertices for polygon cleanup
- Distance functions: Euclidean and Manhattan distance calculations
- Pure mathematical functions with no side effects

**Critical Separation Patterns:**
```python
# ✅ GOOD: BoardGenerator uses utilities for geometry
from ..utils.distance import Point, random_walk, clean_sequence

# ✅ GOOD: GameLoop coordinates state generation
from ..state.board_generator import generate_sample_board

# ❌ AVOID: Don't put geometric algorithms in board_generator
# ❌ AVOID: Don't put state management in distance utilities
```

**Key Implementation Details:**
- **Polygon Subdivision**: Recursively divides large continent into territories
- **Random Walk Boundaries**: Creates natural, irregular territory borders
- **Shared Edge Detection**: Ensures territories properly connect via shared boundaries
- **Army Distribution**: Each player gets exactly `s` armies distributed among their territories
- **Validation**: Comprehensive polygon validation with error reporting

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
The pygame integration follows a clean separation between rendering and game logic:

**Current Architecture:**
```python
# ✅ GOOD: Clear separation of concerns
class GameRenderer:
    def __init__(self, screen: pygame.Surface, game_state: GameState):
        # Renderer depends on GameState (read-only)
        
    def draw_board(self) -> None:
        # Pure rendering - no state mutations
        self._draw_territories()
        self._draw_continent_labels() 
        self._draw_player_summaries()
        self._draw_legend()
        
    def get_territory_at_position(self, pos: Tuple[int, int]) -> Optional[Territory]:
        # Hit testing for user interaction

class GameInputHandler:
    def __init__(self, renderer: GameRenderer):
        # Input handler coordinates with renderer for hit testing
        
    def handle_event(self, event: pygame.event.Event) -> None:
        # Event processing with callback pattern
        
class GameLoop:
    def __init__(self, ...):
        # Central coordinator - dependency injection pattern
        self.renderer = GameRenderer(self.screen, self.game_state)
        self.input_handler = GameInputHandler(self.renderer)
```

**Key Patterns:**
- **Read-Only Rendering**: Renderer never modifies game state
- **Callback Architecture**: Input handler uses callbacks for loose coupling
- **Dependency Injection**: GameLoop provides dependencies to components
- **Hit Testing**: Clean separation between coordinate math and game logic

### World State Management (✅ **IMPLEMENTED**)
The current implementation features robust state management with clear patterns:

**Game State Architecture:**
```python
# ✅ GOOD: Immutable-focused design
@dataclass
class GameState:
    # Configuration (immutable after creation)
    regions: int
    num_players: int  
    starting_armies: int
    
    # Mutable game state
    phase: GamePhase = GamePhase.INIT
    current_turn: int = 0
    current_player_id: Optional[int] = None
    
    # Entity collections
    territories: Dict[int, Territory] = field(default_factory=dict)
    players: Dict[int, Player] = field(default_factory=dict)
    
    @classmethod
    def create_new_game(cls, regions: int, num_players: int, starting_armies: int) -> 'GameState':
        # Factory method for consistent initialization
```

**Key Features:**
- **Dynamic Board Generation**: Based on (g, p, s) simulation parameters  
- **Adjacency Management**: Automatically calculated during board generation
- **Army Tracking**: Precise distribution ensuring each player gets exactly `s` armies
- **State Validation**: Comprehensive checks for polygon validity and game consistency
- **Phase Management**: Clear game phases from INIT through SCORE
- **Player Statistics**: Real-time updates of territory counts and army totals

**Army Distribution Rule:**
Each player receives exactly `starting_armies` (s parameter) distributed across their territories. The system validates this constraint and reports any discrepancies during initialization.

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
- Use type hints extensively for all interfaces and function signatures
- Implement `__repr__` methods for debugging all data classes
- Use dataclasses with clear field types and default factories
- Create factory methods for complex object initialization
- Follow consistent import patterns and module boundaries

Current import patterns:
```python
# Within risk.state modules
from .territory import Territory, TerritoryState
from .game_state import GameState, Player, GamePhase

# Cross-module dependencies (state → utils)
from ..utils.distance import Point, random_walk, clean_sequence

# Game modules depending on state
from ..state import GameState, Territory
from ..state.board_generator import generate_sample_board

# Entry point imports
from risk.game import main
```

Example patterns currently used:
```python
# Factory method for game setup (✅ IMPLEMENTED)
@classmethod
def create_new_game(cls, regions: int, players: int, army_size: int) -> GameState:
    return GameState(regions=regions, num_players=players, starting_armies=army_size)

# Dataclass with proper defaults (✅ IMPLEMENTED)
@dataclass
class Player:
    id: int
    name: str
    color: Tuple[int, int, int]
    territories_controlled: Set[int] = field(default_factory=set)
    
# Callback registration for loose coupling (✅ IMPLEMENTED)
def register_callback(self, event_type: str, callback: Callable) -> None:
    self.callbacks[event_type] = callback
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

**Testing Separation of Concerns:**
When adding new functionality, verify the architectural boundaries:
```python
# ✅ Test that utilities work independently
from risk.utils.distance import Point, random_walk
points = random_walk(Point(0, 0), Point(100, 100))

# ✅ Test that state management is pure
from risk.state import GameState
game = GameState.create_new_game(5, 2, 10)

# ✅ Test that rendering doesn't modify state
from risk.game import GameRenderer
renderer = GameRenderer(screen, game_state)
original_state = copy.deepcopy(game_state)
renderer.draw_board()
assert game_state == original_state  # State unchanged
```

## Performance Considerations
- Cache territory adjacency calculations
- Use efficient data structures for large-scale tournaments
- Consider async patterns for parallel agent decision-making
- Profile bottlenecks in simulation loops

**Current Implementation Notes:**
- Board generation is optimized for reasonable region counts (up to ~50 territories)
- Polygon subdivision algorithm has O(n²) adjacency calculation complexity
- Pygame rendering at 60 FPS works well for typical board sizes
- Memory usage scales linearly with number of territories and game history