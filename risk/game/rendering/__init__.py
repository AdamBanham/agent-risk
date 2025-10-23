
from abc import abstractmethod
from pygame.surface import Surface

from ...state import GameState


class Renderer():
    """
    A template for all renderers in the game loop.
    """

    @abstractmethod
    def render(self, game_state: GameState, surface: Surface) -> None:
        """
        Render the newest state of the renderer responsibility.
        """
        pass