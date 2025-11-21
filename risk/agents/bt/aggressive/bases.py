from py_trees.composites import Sequence
from py_trees.decorators import Retry

from risk.utils.map import Graph
from risk.utils.logging import debug

from ..bases import (
    Selector,
    ExecuteIf,
    Checker,
    Compute,
    PutInto,
    GetBestFrom,
)


class ComputePotential(Compute):
    """
    Computes the attack potential for the selected territory.
    """

    def __init__(self, state_name: str, map: Graph):
        super().__init__(state_name, "potential")
        self.map = map

    def compute(self, state) -> float:
        node = self.map.get_node(state.front)
        armies = node.value

        total = 0.0
        for neighbor in self.map.get_adjacent_nodes(node.id):
            if neighbor.owner != state.player:
                total += armies / neighbor.value

        debug(f"Computed attack potential for {node.id}: {total}")
        return total


class FindBestPotential(GetBestFrom):
    """
    Finds the territory with the best attack potential from the frontlines.
    """

    def __init__(self, state_name: str, collection_name: str, put_name: str):
        super().__init__(state_name, collection_name, put_name)

    def best(self, collection):
        items = collection.items()
        best = max(items, key=lambda x: x[1])
        debug(f"Best territory by attack potential: {best}")
        return best[0]


class BuildAndFindBestPotential(Sequence):
    """
    Builds placements and finds the best potential placements.
    """

    def __init__(self, state_name: str, put_name: str, map: Graph):
        super().__init__("Build and Find Best Potential", False)
        self.state_name = state_name

        self.add_children(
            [
                ExecuteIf(
                    "Fronts Depleted",
                    [
                        Checker(
                            self.state_name,
                            "frontlines",
                            lambda s: len(s) == 0,
                        ),
                    ],
                    Retry(
                        "Finding Frontline",
                        Sequence(
                            "Process Frontline",
                            False,
                            [
                                Selector(
                                    self.state_name,
                                    "frontlines",
                                    "front",
                                    with_replacement=False,
                                ),
                                ComputePotential(self.state_name, map),
                                PutInto(
                                    self.state_name,
                                    "potential",
                                    "attack_potential",
                                    "front",
                                ),
                                Checker(
                                    self.state_name,
                                    "frontlines",
                                    lambda s: len(s) == 0,
                                ),
                            ],
                        ),
                        -1,
                    ),
                ),
                FindBestPotential(
                    self.state_name,
                    "attack_potential",
                    put_name,
                ),
            ]
        )
