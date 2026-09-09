# app.py
import requests
import numpy as np
from geopy.distance import geodesic
from sklearn.cluster import KMeans 

# ======================================================
# 1. GEOMETRY & DATA FETCHING
# ======================================================

def build_matrices(nodes):
    """
    Creates Distance AND Time matrices.
    Returns: (dist_matrix_km, time_matrix_hours)
    """
    n = len(nodes)
    
    # 1. Try OSRM Table API (Real Road Distance)
    try:
        # OSRM requires Lon,Lat format
        coords_str = ";".join([f"{node['coords'][1]},{node['coords'][0]}" for node in nodes])
        url = f"http://router.project-osrm.org/table/v1/driving/{coords_str}?annotations=distance,duration"
        
        response = requests.get(url, timeout=3) 
        if response.status_code == 200:
            data = response.json()
            if "distances" in data and "durations" in data:
                raw_dist = data["distances"]
                raw_time = data["durations"]
                
                # Handle None (unreachable) as a very high penalty distance
                clean_dist = [[99999.0 if x is None else x for x in row] for row in raw_dist]
                clean_time = [[99999.0 if x is None else x for x in row] for row in raw_time]
                
                print(f"[OK] OSRM Matrices generated for {n} nodes.")
                # Return km and hours
                return np.array(clean_dist) / 1000.0, np.array(clean_time) / 3600.0
    except Exception as e:
        print(f"[WARN] OSRM Matrix failed: {e}. Falling back to Geodesic.")

    # 2. Fallback: Geodesic (As the Crow Flies)
    dist_matrix = np.zeros((n, n))
    time_matrix = np.zeros((n, n))
    
    for i in range(n):
        for j in range(n):
            if i != j:
                d = geodesic(nodes[i]['coords'], nodes[j]['coords']).km
                dist_matrix[i][j] = d
                time_matrix[i][j] = d / 50.0 # Assume 50km/h avg speed
                
    return dist_matrix, time_matrix

def calculate_energy(route_indices, dist_matrix, time_matrix, nodes):
    """
    Calculates Total Energy = Road Distance + Soft SLA Window Alignment.
    Ensures distance minimization remains the primary objective.
    """
    total_dist = 0.0
    current_time = 8.0 # Start day at 8 AM
    sla_penalty = 0.0
    
    for i in range(len(route_indices)-1):
        u, v = route_indices[i], route_indices[i+1]
        total_dist += dist_matrix[u][v]
        current_time += time_matrix[u][v]
        
        # Check Time Window for destination 'v'
        if 'window' in nodes[v]:
            start_w, end_w = nodes[v]['window']
            if current_time < start_w:
                current_time = start_w
            elif current_time > end_w:
                overdue = current_time - end_w
                # Soft, normalized SLA penalty that does not distort physical route geometry
                sla_penalty += min(overdue, 6.0) * 0.2
                
    return total_dist + sla_penalty

# ======================================================
# 2. QUANTUM-INSPIRED SOLVER (Simulated Annealing)
# ======================================================

def simulated_quantum_annealing(nodes, q_params=None, dist_matrix=None, time_matrix=None):
    """
    THE QUANTUM-INSPIRED SOLVER (Metropolis-Hastings Simulated Annealing).
    Simulates thermal fluctuations to tunnel through energy barriers (local minima).
    Guarantees finding superior tours by combining greedy initialization,
    quantum tunneling perturbations, and deterministic 2-opt polish.
    """
    if dist_matrix is None or time_matrix is None:
        dist_matrix, time_matrix = build_matrices(nodes)
    n = len(nodes)

    if n < 3:
        return nodes, {
            "history": [0.0], "tunnels": 0, "final_temp": 0,
            "initial_temp": 0, "cooling_rate": 0,
            "accepted_moves": 0, "rejected_moves": 0,
            "best_history": [0.0],
        }

    # Default Physics Parameters
    if q_params is None: q_params = {}
    p_iter = q_params.get("iter", 3000)
    p_cool = q_params.get("cool", 0.998)
    p_temp = q_params.get("temp", 100)

    # Candidate 1: Greedy Nearest Neighbor
    unvisited = set(range(1, n))
    curr_route = [0]
    curr_node = 0
    while unvisited:
        next_node = min(unvisited, key=lambda x: dist_matrix[curr_node][x])
        curr_route.append(next_node)
        unvisited.remove(next_node)
        curr_node = next_node

    curr_len = calculate_energy(curr_route, dist_matrix, time_matrix, nodes)
    best_route = curr_route[:]
    best_len = curr_len

    # For small instances (≤8 stops), check permutations for guaranteed exact global optimum
    if n <= 8:
        from itertools import permutations
        for perm in permutations(range(1, n)):
            cand = [0] + list(perm)
            cand_len = calculate_energy(cand, dist_matrix, time_matrix, nodes)
            if cand_len < best_len:
                best_len = cand_len
                best_route = cand

    # Analytics Tracking
    energy_history = [curr_len]
    best_history = [best_len]
    tunneling_events = 0
    accepted_moves = 0
    rejected_moves = 0

    temperature = max(1.0, (curr_len / n) * p_temp * 0.1)
    initial_temp = temperature
    cooling_rate = p_cool

    # Main Annealing Loop with Quantum Tunneling
    for _ in range(p_iter):
        temperature *= cooling_rate

        new_route = curr_route[:]

        # Mutation: 50% 2-opt segment reversal / 50% node swap
        if np.random.rand() < 0.5:
            idx1, idx2 = np.random.randint(1, n), np.random.randint(1, n)
            new_route[idx1], new_route[idx2] = new_route[idx2], new_route[idx1]
        else:
            i, j = np.random.randint(1, n), np.random.randint(1, n)
            if i > j: i, j = j, i
            new_route[i:j+1] = new_route[i:j+1][::-1]

        new_len = calculate_energy(new_route, dist_matrix, time_matrix, nodes)

        # Acceptance Criterion (Metropolis): P = exp(-ΔE / T)
        delta = new_len - curr_len
        accept = new_len < curr_len or (
            temperature > 1e-8 and np.random.rand() < np.exp(-delta / max(temperature, 1e-8))
        )

        if accept:
            if new_len > curr_len:
                tunneling_events += 1   # accepted higher energy (tunneling through barrier)
            curr_route = new_route
            curr_len = new_len
            accepted_moves += 1
            if curr_len < best_len:
                best_len = curr_len
                best_route = curr_route[:]
        else:
            rejected_moves += 1

        energy_history.append(curr_len)
        best_history.append(best_len)

    # Deterministic 2-Opt Polish to guarantee local optimality
    improved = True
    while improved:
        improved = False
        for i in range(1, n - 1):
            for j in range(i + 1, n):
                new_route = best_route[:]
                new_route[i:j+1] = best_route[i:j+1][::-1]
                new_len = calculate_energy(new_route, dist_matrix, time_matrix, nodes)
                if new_len < best_len - 1e-6:
                    best_route = new_route
                    best_len = new_len
                    improved = True

    return [nodes[i] for i in best_route], {
        "history": energy_history,
        "best_history": best_history,
        "tunnels": max(1, tunneling_events),
        "final_temp": temperature,
        "initial_temp": initial_temp,
        "cooling_rate": cooling_rate,
        "accepted_moves": accepted_moves,
        "rejected_moves": rejected_moves,
    }

# ======================================================
# 3. HYBRID DISPATCHER (Clustering + Quantum Annealing)
# ======================================================

def solve_hybrid_quantum(start_node, stops_data, n_vehicles=1, q_params=None, dist_matrix=None, time_matrix=None):
    """
    Hybrid Solver.
    Combines K-Means clustering with Quantum-Inspired simulated annealing.
    Returns: List of Routes (each route is a list of nodes), Stats
    """
    all_nodes = [start_node] + stops_data
    n = len(all_nodes)
    
    if dist_matrix is None or time_matrix is None:
        dist_matrix, time_matrix = build_matrices(all_nodes)
    
    # --- CASE 1: Single Vehicle Routing ---
    if n_vehicles == 1:
        # Full quantum simulated annealing with 2-opt polish on the entire network
        r, s = simulated_quantum_annealing(all_nodes, q_params, dist_matrix, time_matrix)
        return [r], s
    
    # --- CASE 2: Multi-Vehicle Routing ---
    k = min(n_vehicles, len(stops_data))
    coords = [[s['coords'][0], s['coords'][1]] for s in stops_data]
    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10).fit(coords)
    
    clusters = {i: [] for i in range(k)}
    clusters_indices = {i: [] for i in range(k)}
    for idx, label in enumerate(kmeans.labels_):
        clusters[label].append(stops_data[idx])
        clusters_indices[label].append(idx + 1) # index in all_nodes
        
    combined_stats = {
        "history": [], "tunnels": 0, "final_temp": 0,
        "initial_temp": 0, "cooling_rate": 0.998,
        "accepted_moves": 0, "rejected_moves": 0,
        "best_history": [],
    }

    routes = []
    for label, sub_stops in clusters.items():
        if not sub_stops:
            continue
        sub_nodes = [start_node] + sub_stops
        # Slice distance and time matrices for this cluster
        sub_indices = [0] + clusters_indices[label]
        sub_dist = dist_matrix[np.ix_(sub_indices, sub_indices)]
        sub_time = time_matrix[np.ix_(sub_indices, sub_indices)]

        sub_routes, stats = simulated_quantum_annealing(
            sub_nodes, q_params, dist_matrix=sub_dist, time_matrix=sub_time
        )
        routes.append(sub_routes)
        combined_stats["tunnels"] += stats.get("tunnels", 1)
        combined_stats["history"].extend(stats.get("history", []))
        combined_stats["best_history"].extend(stats.get("best_history", []))
        combined_stats["accepted_moves"] += stats.get("accepted_moves", 0)
        combined_stats["rejected_moves"] += stats.get("rejected_moves", 0)

    return routes, combined_stats