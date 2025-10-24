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

class SystemInterruptEvent(Event):
    """
    An event that indicates processing should be interrupted.
    """

    def __init__(self):
        super().__init__(
            "SYSTEM: Interrupted Processing of Event Stack"
        )

class SystemResumeEvent(Event):
    """
    An event that indicates processing should be resumed.
    """

    def __init__(self):
        super().__init__(
            "SYSTEM: Resumed Processing of Event Stack"
        )

class SystemStepEvent(Event):
    """
    An event that indicates a single step in processing should be forced.
    """

    def __init__(self):
        super().__init__(
            "SYSTEM: Forced Step in Processing of Event Stack"
        )