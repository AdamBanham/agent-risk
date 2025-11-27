
def extractStatistics(searcher, action) -> dict:
    """Return simple statistics for ``action`` from ``searcher``."""
    statistics = {}
    statistics["rootNumVisits"] = searcher.root.numVisits
    statistics["rootTotalReward"] = searcher.root.totalReward
    statistics["actionNumVisits"] = searcher.root.children[action].numVisits
    statistics["actionTotalReward"] = searcher.root.children[action].totalReward
    return statistics