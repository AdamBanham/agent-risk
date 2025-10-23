
from risk.engine import Engine

from risk.state.event_stack.events.sideffects import (
    TransferArmies,
    AdjustArmies,
    CaptureTerritory,
    CasualitiesOnTerritory,
    ClearTerritory
)
from risk.state.event_stack import ResolveFightEvent, Event
from risk.state import GameState
from risk.state.fight import FightResult
from ..animation import AnimationManager

colors = {
    'player_colors': [
                (200, 50, 50),   # Red
                (50, 200, 50),   # Green
                (50, 50, 200),   # Blue
                (200, 200, 50),  # Yellow
                (200, 50, 200),  # Magenta
                (50, 200, 200),  # Cyan
                (150, 75, 0),    # Brown
                (255, 165, 0),   # Orange
            ],
    'fight_fail': (220, 20, 60),  # Crimson
    'fight_success': (34, 139, 34),  # ForestGreen
    'loss_troops': (128, 0, 0),  # Maroon
    'gain_troops': (0, 100, 0),  # DarkGreen
    'flash': (255, 255, 255),  # White
}

class AnimationEngine(Engine):
    """
    Taps into the event stack to process side effects into
    animations.
    """

    def __init__(self, animation_manager: AnimationManager):
        super().__init__("animation-hookin-engine")
        self.manager = animation_manager

    allowed_elements = [
        TransferArmies,
        AdjustArmies,
        CaptureTerritory,
        CasualitiesOnTerritory,
        ClearTerritory,
        ResolveFightEvent
    ]

    def process(self, game_state: GameState, element: Event):       
        if isinstance(element, TransferArmies):
            src = game_state.get_territory(element.context.from_territory_id).center
            dst = game_state.get_territory(element.context.to_territory_id).center

            self.manager.add_random_walk_animation(
                src, dst, 1.2
            )
        elif isinstance(element, AdjustArmies):
            territory = game_state.get_territory(element.context.territory_id)
            center = territory.center
            amount = element.context.num_armies

            if amount < 0:
                self.manager.add_cross_animation(
                    center,
                    0.1,
                    1.2,
                    colors.get('loss_troops')
                )
            elif amount > 0:
                self.manager.add_tick_animation(
                    center,
                    0.1,
                    1.2,
                    colors.get('gain_troops')
                )
        elif isinstance(element, (CaptureTerritory, ClearTerritory)):
            
            territory = game_state.get_territory(element.context.territory_id)
            center = territory.center

            self.manager.add_flash_animation(
                center,
                1,
                colors.get('flash')
            )

        elif isinstance(element, CasualitiesOnTerritory):
            territory = game_state.get_territory(element.context.territory_id)
            center = territory.center

            self.manager.add_cross_animation(
                center,
                0.1,
                1.2,
                colors.get('loss_troops')
            )
        elif isinstance(element, ResolveFightEvent):
            attacker = game_state.get_territory(
                element.context.attacking_territory_id
                )
            defender = game_state.get_territory(
                element.context.defending_territory_id
            )
            color = colors.get('player_colors')[
                attacker.owner % len(colors['player_colors'])
            ]

            self.manager.add_arrow_animation(
                attacker.center,
                defender.center,
                1.2,
                color
            )
            
            result:FightResult = element.context.fight_result

            if result.attacker_won():
                self.manager.add_tick_animation(
                    defender.center,
                    1.0,
                    1.2,
                    colors.get('fight_success')
                )
            elif result.defender_won():
                self.manager.add_cross_animation(
                    defender.center,
                    1.0,
                    1.2,
                    colors.get('fight_fail')
                )


        return super().process(game_state, element)
