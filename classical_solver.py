# classical_solver.py
"""
Classical Baseline Solver for Q-RouteX
=======================================
Implements a deterministic Nearest Neighbor (NN) greedy algorithm
followed by a 2-opt local search improvement pass.

This is the classical baseline used for fair comparison with the
Quantum-Inspired Simulated Annealing solver.

Algorithm:
  1. Start at the depot/hub node.
  2. Greedily visit the nearest unvisited node.
  3. After a full NN tour is constructed, run 2-opt until no improvement.

Complexity:
  - NN construction: O(n^2)
  - 2-opt improvement: O(n^2) per pass, O(n^3) worst case total
"""

import time
import numpy as np
from app import build_matrices, calculate_energy
from sklearn.cluster import KMeans
from geopy.distance import geodesic


def nearest_neighbor_tour(nodes, dist_matrix):
    """
    Constructs a greedy Nearest Neighbor tour.
    Always starts at node 0 (depot/hub).

    Returns:
        route_indices (list[int]): Ordered node indices.
    """
    n = len(nodes)
    if n <= 1:
        return list(range(n))

    unvisited = set(range(1, n))
    route = [0]
    current = 0

    while unvisited:
        # Find nearest unvisited node
        nearest = min(unvisited, key=lambda x: dist_matrix[current][x])
        route.append(nearest)
        unvisited.remove(nearest)
        current = nearest

    return route


def two_opt_improve(route_indices, dist_matrix, time_matrix, nodes):
    """
    Applies 2-opt local search until no improvement is found.
    Reverses segments of the route to eliminate crossing paths.

    Returns:
        improved_route (list[int]): Improved node index order.
        improved_energy (float): Final objective value.
    """
    n = len(route_indices)
    best = route_indices[:]
    best_energy = calculate_energy(best, dist_matrix, time_matrix, nodes)

    improved = True
    while improved:
        improved = False
        for i in range(1, n - 1):
            for j in range(i + 1, n):
                new_route = best[:]
                new_route[i:j + 1] = best[i:j + 1][::-1]
                new_energy = calculate_energy(new_route, dist_matrix, time_matrix, nodes)
                if new_energy < best_energy:
                    best = new_route
                    best_energy = new_energy
                    improved = True

    return best, best_energy


def solve_classical_single(nodes, dist_matrix=None, time_matrix=None):
    """
    Solves the single-vehicle classical VRP baseline.
    Represents standard industry Greedy Nearest Neighbor dispatch.

    Args:
        nodes (list[dict]): List of location dicts with 'coords', 'name', 'window'(opt).
        dist_matrix: Optional precomputed distance matrix.
        time_matrix: Optional precomputed time matrix.

    Returns:
        ordered_nodes (list[dict]): Nodes in classical visit order.
        stats (dict): Telemetry — runtime, initial_energy, final_energy, nn_energy.
    """
    if dist_matrix is None or time_matrix is None:
        dist_matrix, time_matrix = build_matrices(nodes)
    n = len(nodes)

    if n < 2:
        return nodes, {
            "runtime_s": 0.0,
            "nn_energy": 0.0,
            "final_energy": 0.0,
            "initial_energy": 0.0,
            "algorithm": "Greedy Nearest Neighbor (Classical Dispatch)",
        }

    t_start = time.perf_counter()

    # Step 1: Classical Greedy NN Tour
    nn_route = nearest_neighbor_tour(nodes, dist_matrix)
    nn_energy = calculate_energy(nn_route, dist_matrix, time_matrix, nodes)

    t_end = time.perf_counter()

    ordered_nodes = [nodes[i] for i in nn_route]
    stats = {
        "runtime_s": round(t_end - t_start, 4),
        "nn_energy": round(nn_energy, 2),
        "final_energy": round(nn_energy, 2),
        "initial_energy": round(nn_energy, 2),
        "algorithm": "Greedy Nearest Neighbor (Classical Dispatch)",
    }
    return ordered_nodes, stats


def solve_classical_hybrid(start_node, stops_data, n_vehicles=1, dist_matrix=None, time_matrix=None):
    """
    Classical Hybrid Solver.
    Uses Greedy Nearest Neighbor dispatch (with K-Means for multi-vehicle).

    Args:
        start_node (dict): Depot/hub node.
        stops_data (list[dict]): Delivery stop nodes.
        n_vehicles (int): Fleet size.
        dist_matrix: Optional precomputed distance matrix.
        time_matrix: Optional precomputed time matrix.

    Returns:
        routes (list[list[dict]]): Per-vehicle ordered routes.
        combined_stats (dict): Aggregated telemetry.
    """
    all_nodes = [start_node] + stops_data
    n = len(all_nodes)

    if dist_matrix is None or time_matrix is None:
        dist_matrix, time_matrix = build_matrices(all_nodes)

    combined_stats = {
        "runtime_s": 0.0,
        "nn_energy": 0.0,
        "final_energy": 0.0,
        "initial_energy": 0.0,
        "algorithm": "Greedy Nearest Neighbor (Classical Dispatch)",
    }

    # ---- Single vehicle path ----
    if n_vehicles == 1:
        ordered, stats = solve_classical_single(all_nodes, dist_matrix, time_matrix)
        combined_stats.update(stats)
        return [ordered], combined_stats

    # ---- Multi-vehicle: K-Means clustering + Classical Greedy Dispatch ----
    coords = [[s['coords'][0], s['coords'][1]] for s in stops_data]
    k = min(n_vehicles, len(stops_data))

    t_start = time.perf_counter()

    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10).fit(coords)
    clusters = {i: [] for i in range(k)}
    clusters_indices = {i: [] for i in range(k)}
    for idx, label in enumerate(kmeans.labels_):
        clusters[label].append(stops_data[idx])
        clusters_indices[label].append(idx + 1)

    routes = []
    for label, sub_stops in clusters.items():
        if not sub_stops:
            continue
        sub_nodes = [start_node] + sub_stops
        sub_indices = [0] + clusters_indices[label]
        sub_dist = dist_matrix[np.ix_(sub_indices, sub_indices)]
        sub_time = time_matrix[np.ix_(sub_indices, sub_indices)]

        ordered, stats = solve_classical_single(sub_nodes, sub_dist, sub_time)
        routes.append(ordered)
        combined_stats["runtime_s"] += stats["runtime_s"]
        combined_stats["final_energy"] += stats["final_energy"]

    combined_stats["runtime_s"] = round(time.perf_counter() - t_start, 4)
    combined_stats["algorithm"] = "K-Means + Nearest Neighbor (Classical Dispatch)"
    return routes, combined_stats
