from ..events import Event 

class PauseProcessingEvent(Event):
    """
    An event that indicates processing should be paused.
    
    .. attributes::
        - context.delay: 
            The duration of the pause in seconds.
    """

    def __init__(self, delay: float):
        super().__init__(
            f"SYSTEM: Paused Processing of Event Stack for {delay}",
            dict(
                delay=delay
            )
        )

