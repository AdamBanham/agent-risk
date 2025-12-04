"""
This module contains utility functions for understanding
the current state of the map in the simulation.
"""

from dataclasses import dataclass
from typing import Collection, TYPE_CHECKING
from copy import deepcopy

if TYPE_CHECKING:
    from risk.state import GameState


@dataclass
class Node:
    id: int
    owner: int
    value: object

    def __str__(self):
        return "[{},{},{}]".format(self.id, self.owner, self.value)

    def __hash__(self):
        return hash((self.id))

    def __eq__(self, other):
        if not isinstance(other, Node):
            return False
        return self.id == other.id


@dataclass
class SafeNode(Node):
    value: bool

    def __str__(self):
        return "[{}:{}]".format(self.id, self.value)

    def __hash__(self):
        return hash((self.id))

    def __eq__(self, other):
        if not isinstance(other, Node):
            return False
        return self.id == other.id


@dataclass
class NetworkNode(Node):
    value: int
    safe: bool = False

    def __str__(self):
        return "[{}#{}]:{}".format(self.id, self.value, self.safe)

    def __hash__(self):
        return hash((self.id))

    def __eq__(self, other):
        if not isinstance(other, Node):
            return False
        return self.id == other.id


@dataclass
class Edge:
    src: int
    dest: int
    value: object

    def __str__(self):
        return "({} -> {}):{}".format(self.src, self.dest, self.value)


@dataclass
class Graph[N, E]:
    nodes: Collection[N]
    edges: Collection[E]

    def get_node(self, node: int) -> N | None:
        """
        Attempts to find and return the node with the given ID.

        :param node: ID of the node to find
        :return: The node if found, else None
        """
        for n in self.nodes:
            if n.id == node:
                return n
        return None

    def nodes_for_player(self, player_id: int) -> Collection[N]:
        """
        Returns all nodes owned by the given player.

        :param player_id: ID of the player
        :return: Collection of nodes owned by the player
        """
        return [n for n in self.nodes if n.owner == player_id]

    def get_adjacent_nodes(self, node: int) -> Collection[N]:
        """
        Returns all nodes adjacent to the given node.

        :param node: ID of the source node
        :return: Collection of adjacent nodes
        """
        adjacent_nodes = []
        for e in self.get_edges_from(node):
            dest_node = self.get_node(e.dest)
            if dest_node:
                adjacent_nodes.append(dest_node)
        return adjacent_nodes

    def get_edges_from(self, node: int) -> Collection[E]:
        """
        Returns all edges originating from the given node.

        :param node: ID of the source node
        :return: Collection of edges from the node
        """
        return [e for e in self.edges if e.src == node]

    def get_edges_to(self, node: int) -> Collection[E]:
        """
        Returns all edges leading to the given node.

        :param node: ID of the destination node
        :return: Collection of edges to the node
        """
        return [e for e in self.edges if e.dest == node]

    def get_edge(self, src: int, dest: int) -> E | None:
        """
        Attempts to find and return the edge between the given source.

        :param src: ID of the source node
        :param dest: ID of the destination node
        :return: The edge if found, else None
        """
        for e in self.edges:
            if e.src == src and e.dest == dest:
                return e
        return None

    @property
    def size(self) -> int:
        """
        Returns the number of nodes in the graph.
        """
        return len(self.nodes)

    def clone(self) -> "Graph[N, E]":
        """
        Creates a deep copy of the graph.
        """
        return Graph(nodes=deepcopy(self.nodes), edges=deepcopy(self.edges))

    def __str__(self):
        ret = "MapView:\n  Nodes:\n"
        for n in self.nodes:
            ret += " " * 4 + "{}\n".format(n)
        ret += "  Edges:\n"
        for e in self.edges:
            ret += " " * 4 + "{}\n".format(e)
        return ret


def construct_graph(game_state: "GameState") -> Graph[Node, Edge]:
    """
    Constructs a graph representation of the game state.
    """
    nodes = []
    edges = []

    for terr in game_state.territories.values():
        node = Node(id=terr.id, owner=terr.owner, value=terr.armies)
        nodes.append(node)

    for terr in game_state.territories.values():
        for adj in terr.adjacent_territories:
            edge = Edge(src=terr.id, dest=adj.id, value=None)
            edges.append(edge)

    return Graph(nodes=nodes, edges=edges)


class SafeGraph(Graph[SafeNode, Edge]):
    """
    A graph that represents safe territories and their connections
    for a given player in the Risk simulation.
    """

    @property
    def safe_nodes(self) -> Collection[SafeNode]:
        """
        Returns all safe nodes in the graph.
        """
        return [n for n in self.nodes if n.value]

    @property
    def frontline_nodes(self) -> Collection[SafeNode]:
        """
        Returns all frontline nodes in the graph.
        """
        return [n for n in self.nodes if not n.value]

    def is_safe(self, territory_id: int) -> bool:
        """
        Checks if the given territory is safe.

        :param territory_id: ID of the territory to check
        :returns: True if the territory is safe, else False
        """
        node = self.get_node(territory_id)
        if node:
            return node.value
        return False

    def clone(self):
        return SafeGraph(nodes=deepcopy(self.nodes), edges=deepcopy(self.edges))


def construct_safe_view(map: Graph[Node, Edge], player: int) -> SafeGraph:
    """
    Constructs a SafeGraph representing safe territories for the given player.
    """
    player_nodes = map.nodes_for_player(player)
    safes = dict()
    safe_nodes = []
    edges = []
    if player_nodes:
        for n in player_nodes:
            is_safe = True
            for adj in map.get_adjacent_nodes(n.id):
                if adj.owner != player:
                    is_safe = False
                    break
            safe_node = SafeNode(id=n.id, owner=n.owner, value=is_safe)
            safes[n.id] = safe_node
            safe_nodes.append(safe_node)

        for e in map.edges:
            src_node = safes.get(e.src, None)
            dest_node = safes.get(e.dest, None)
            if src_node and dest_node:
                edges.append(
                    Edge(
                        src=e.src, dest=e.dest, value=src_node.value and dest_node.value
                    )
                )

    return SafeGraph(nodes=safe_nodes, edges=edges)


class NetworkGraph(Graph[NetworkNode, Edge]):
    """
    A graph that represents networks of connected territories owned by a player
    in the Risk simulation.
    """

    @property
    def networks(self) -> Collection[int]:
        """
        Returns all unique network IDs in the graph.
        """
        return set(n.value for n in self.nodes)

    def nodes_in_network(self, network: int) -> Collection[NetworkNode]:
        """
        Returns all nodes belonging to the given network.

        :param network_id: ID of the network
        :return: Collection of nodes in the network
        """
        return [n for n in self.nodes if n.value == network]

    def safes_in_network(self, network: int) -> Collection[NetworkNode]:
        """
        Returns all safe nodes belonging to the given network.

        :param network_id: ID of the network
        :return: Collection of safe nodes in the network
        """
        return [n for n in self.nodes if n.value == network and n.safe]

    def frontlines_in_network(self, network: int) -> Collection[NetworkNode]:
        """
        Returns all frontline nodes belonging to the given network.

        :param network_id: ID of the network
        :return: Collection of frontline nodes in the network
        """
        return [n for n in self.nodes if n.value == network and not n.safe]

    def view(self, network: int) -> "NetworkGraph":
        """
        Returns a subgraph view of the given network.

        :param network: ID of the network
        :return: A NetworkGraph representing the subgraph of the network
        """
        nodes = self.nodes_in_network(network)
        edges = []
        for edge in self.edges:
            src_in_network = any(n.id == edge.src for n in nodes)
            dest_in_network = any(n.id == edge.dest for n in nodes)
            if src_in_network and dest_in_network:
                edges.append(edge)
        return NetworkGraph(nodes=nodes, edges=edges)


def construct_network_view(map: Graph[Node, Edge], player: int) -> NetworkGraph:
    """
    Constructs a map of the simulation from the perspective of the given player,
    where each node's value showns the network of nodes that it belongs to. A
    network is a group of connected territories owned by the player. Nodes in a
    network can either be safe (not adjacent to enemy territories) or frontline
    (adjacent to enemy territories).

    :param game_state: The current state of the game
    :param player: The ID of the player for whom to construct the view
    :return: A Graph representing the player's view of the map via networks
    """
    network_nodes = []
    network_edges = []
    safe_map = construct_safe_view(map, player)
    player_nodes = map.nodes_for_player(player)
    seen_ids = set()
    network = 0

    for n in player_nodes:
        if n.id in seen_ids:
            continue
        # Start a new network
        network += 1
        network_node = NetworkNode(
            id=n.id, owner=n.owner, value=network, safe=safe_map.is_safe(n.id)
        )
        network_nodes.append(network_node)
        seen_ids.add(n.id)

        # explore and expand the network
        adjacent_ids = map.get_adjacent_nodes(n.id)
        while len(adjacent_ids) > 0:
            adj = adjacent_ids.pop()

            # check if already seen or not owned by player
            if adj.id in seen_ids:
                continue
            if adj.owner != player:
                continue

            # add to network
            seen_ids.add(adj.id)
            network_node = NetworkNode(
                id=adj.id, owner=adj.owner, value=network, safe=safe_map.is_safe(adj.id)
            )
            network_nodes.append(network_node)

            # add its adjacents to explore
            for next_adj in map.get_adjacent_nodes(adj.id):
                if next_adj.id in seen_ids:
                    continue
                if next_adj.owner != player:
                    continue
                adjacent_ids.append(next_adj)

    # add in network edges
    for edge in map.edges:
        src_in_network = any(n.id == edge.src for n in network_nodes)
        dest_in_network = any(n.id == edge.dest for n in network_nodes)
        if src_in_network and dest_in_network:
            networks = set(
                n.value for n in network_nodes if n.id == edge.src or n.id == edge.dest
            )
            network_edges.append(Edge(src=edge.src, dest=edge.dest, value=networks))

    return NetworkGraph(nodes=network_nodes, edges=network_edges)


def get_value(map: Graph, terr: int):
    """
    A shortcut to getting the value of a given territory.

    :param map: the map to check against
    :param terr: the territory to check for
    :returns: the value of te node or None
    """
    node = map.get_node(terr)
    if node:
        return node.value
    return None 


if __name__ == "__main__":
    from risk.utils.replay import simulate_turns
    from risk.state import GamePhase
    from risk.utils.logging import setLevel
    from logging import INFO

    setLevel(INFO)

    state = GameState.create_new_game(10, 2, 50)
    state.initialise()

    map = construct_graph(state)
    print(map)

    while state.phase != GamePhase.GAME_END:
        state, _ = simulate_turns(state, 5)
        map = construct_graph(state)

        input("show player 0 safe view?")
        safe_graph = construct_safe_view(map, 0)
        print(safe_graph)

        input("show player 0 network view?")
        network_map = construct_network_view(map, 0)
        print(network_map)

        input("show player 1 safe view?")
        safe_graph = construct_safe_view(map, 1)
        print(safe_graph)

        input("show player 1 network view?")
        network_map = construct_network_view(map, 1)
        print(network_map)

        input("continue?")
