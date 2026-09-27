"""
algorithm/dijkstra.py

Simple, manual implementation of Dijkstra's Algorithm for FloodSafe.

The graph is built from the "roads" table in the database.
Each road connects two nodes (a location or a shelter).
Each node is identified by a unique string key like "location_1" or "shelter_2".

COST FORMULA
------------
cost of a road = distance_km + flood_penalty

Flood penalty values:
    SAFE    = 0
    LOW     = 2
    MEDIUM  = 5
    HIGH    = 10
    BLOCKED = road is completely removed from the graph (cannot be used)

Dijkstra's algorithm then finds the path with the SMALLEST total cost,
which naturally avoids flooded roads and prefers safer, shorter paths.
"""

import heapq

# Flood risk penalty added to distance for each road status
FLOOD_WEIGHT = {
    "safe": 0,
    "low": 2,
    "medium": 5,
    "high": 10,
}

# Roads with this status are removed completely from the graph
BLOCKED_STATUS = "blocked"


def node_key(node_type, node_id):
    """
    Build a unique string key for a node.
    Example: node_key("location", 1) -> "location_1"
    """
    return f"{node_type}_{node_id}"


def build_graph(roads):
    """
    Build an adjacency list graph from a list of road rows.

    Each road row is expected to be a dict-like object with keys:
        from_type, from_id, to_type, to_id, distance_km, flood_status

    Roads are treated as two-way (undirected).
    Blocked roads are skipped entirely (they are not added to the graph).

    Returns:
        graph: dict where graph[node] = list of (neighbor_node, cost, road_info)
    """
    graph = {}

    for road in roads:
        status = road["flood_status"].lower()

        # Skip blocked roads completely - Dijkstra can never use them
        if status == BLOCKED_STATUS:
            continue

        distance = float(road["distance_km"])
        penalty = FLOOD_WEIGHT.get(status, 0)
        cost = distance + penalty

        a = node_key(road["from_type"], road["from_id"])
        b = node_key(road["to_type"], road["to_id"])

        if a not in graph:
            graph[a] = []
        if b not in graph:
            graph[b] = []

        # Undirected road: add edge in both directions
        graph[a].append((b, cost, road))
        graph[b].append((a, cost, road))

    return graph


def dijkstra(graph, start, destination):
    """
    Run Dijkstra's algorithm on the given graph.

    Args:
        graph: adjacency list built by build_graph()
        start: starting node key, e.g. "location_1"
        destination: destination node key, e.g. "shelter_2"

    Returns:
        A dictionary with:
            "path": list of node keys from start to destination (or None)
            "total_cost": total cost of the path (float, or None)
            "total_distance": total real distance in km (float, or None)
            "edges": list of road rows used along the path
            "found": True/False
    """

    if start not in graph:
        return {
            "found": False,
            "reason": f"Start node '{start}' has no roads connected to it.",
            "path": None,
            "total_cost": None,
            "total_distance": None,
            "edges": [],
        }

    if destination not in graph:
        return {
            "found": False,
            "reason": f"Destination node '{destination}' has no roads connected to it.",
            "path": None,
            "total_cost": None,
            "total_distance": None,
            "edges": [],
        }

    # distances[node] = smallest known cost from start to node
    distances = {node: float("inf") for node in graph}
    distances[start] = 0

    # previous[node] = (previous_node, road_used) for path reconstruction
    previous = {}

    # visited set so we don't process a node twice
    visited = set()

    # Min-heap priority queue: (cost_so_far, node)
    priority_queue = [(0, start)]

    while priority_queue:
        current_cost, current_node = heapq.heappop(priority_queue)

        if current_node in visited:
            continue
        visited.add(current_node)

        # Early exit: destination reached with the smallest possible cost
        if current_node == destination:
            break

        for neighbor, edge_cost, road in graph.get(current_node, []):
            if neighbor in visited:
                continue

            new_cost = current_cost + edge_cost

            if new_cost < distances[neighbor]:
                distances[neighbor] = new_cost
                previous[neighbor] = (current_node, road)
                heapq.heappush(priority_queue, (new_cost, neighbor))

    # If destination was never reached
    if distances.get(destination, float("inf")) == float("inf"):
        return {
            "found": False,
            "reason": "No available route exists (all paths may be blocked).",
            "path": None,
            "total_cost": None,
            "total_distance": None,
            "edges": [],
        }

    # Reconstruct path by walking backwards from destination to start
    path = [destination]
    edges_used = []
    node = destination

    while node != start:
        prev_node, road = previous[node]
        edges_used.append(road)
        path.append(prev_node)
        node = prev_node

    path.reverse()
    edges_used.reverse()

    total_distance = sum(float(r["distance_km"]) for r in edges_used)

    return {
        "found": True,
        "reason": "Route found successfully.",
        "path": path,
        "total_cost": round(distances[destination], 2),
        "total_distance": round(total_distance, 2),
        "edges": edges_used,
    }
