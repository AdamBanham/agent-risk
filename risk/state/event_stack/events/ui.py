
from ..events import Event
from ...ui import UIAction

class UIActionEvent(Event):
    """
    Event representing a UI action.
    """

    def __init__(self, action: UIAction, parameters: dict):
        super().__init__(
            "UI Action Event :: {}".format(action.name),
            dict(
                action=action,
                parameters=parameters
            )
        )