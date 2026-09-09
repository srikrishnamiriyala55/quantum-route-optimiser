# quantum/decoder.py
"""
Bitstring → Route Decoder for Q-RouteX
=========================================
Converts QAOA measurement bitstrings back into real-world delivery routes,
validates feasibility, and explains why each candidate is accepted/rejected.

This module implements the critical "quantum result → real route" translation
that demonstrates quantum computation producing a tangible logistics decision.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Any


def decode_bitstring(
    bitstring: str,
    var_map: Dict[Tuple[int, int], int],
    nodes: List[dict],
    dist_matrix: np.ndarray,
) -> Dict:
    """
    Convert a QUBO bitstring into a routing assignment.

    Args:
        bitstring  : Binary string from quantum measurement (MSB first)
        var_map    : Dict mapping (i,j) → qubit index from qubo.py
        nodes      : List of node dicts with 'name', 'coords'
        dist_matrix: Distance matrix in km

    Returns:
        Dict with:
            assignment    : {(i,j): 0|1} edge decisions
            selected_edges: List of (i, j) where x_ij = 1
            route         : Ordered list of node indices
            route_nodes   : Ordered list of node dicts
            is_feasible   : Bool
            feasibility_reason: Human-readable explanation
            total_dist    : Total route distance (km)
            violations    : List of violation descriptions
    """
    n = len(nodes)

    # ── Parse bitstring into edge assignments ─────────────────────────────────
    assignment = {}
    for (i, j), qubit_idx in var_map.items():
        if qubit_idx < len(bitstring):
            assignment[(i, j)] = int(bitstring[qubit_idx])

    selected_edges = [(i, j) for (i, j), val in assignment.items() if val == 1]

    # ── Attempt to reconstruct a Hamiltonian path ─────────────────────────────
    # Build adjacency: successors[i] = list of j where x_ij = 1
    successors = {i: [] for i in range(n)}
    for (i, j) in selected_edges:
        successors[i].append(j)

    # Violations collector
    violations = []

    # ── Feasibility check 1: out-degree = 1 ──────────────────────────────────
    for i in range(n):
        deg = len(successors[i])
        if deg != 1:
            violations.append(
                f"Node {nodes[i]['name'].split(',')[0]}: has {deg} outgoing edges (need exactly 1)"
            )

    # ── Try to trace the route starting from depot (node 0) ──────────────────
    route = [0]
    visited = {0}
    current = 0
    max_steps = n + 1

    for _ in range(max_steps):
        nexts = successors.get(current, [])
        if not nexts:
            break
        next_node = nexts[0]
        if next_node == 0:
            break  # returned to depot
        if next_node in visited:
            violations.append(f"Subtour detected: visited node {next_node} twice")
            break
        route.append(next_node)
        visited.add(next_node)
        current = next_node

    # ── Feasibility check 2: all nodes visited ───────────────────────────────
    unvisited = set(range(n)) - visited
    if unvisited:
        names = [nodes[u]['name'].split(',')[0] for u in unvisited]
        violations.append(f"{len(unvisited)} stop(s) not visited: {', '.join(names[:3])}")

    # ── Calculate total distance ──────────────────────────────────────────────
    total_dist = 0.0
    if len(route) > 1:
        for step in range(len(route) - 1):
            i, j = route[step], route[step + 1]
            if 0 <= i < dist_matrix.shape[0] and 0 <= j < dist_matrix.shape[1]:
                total_dist += dist_matrix[i][j]

    is_feasible = len(violations) == 0
    if is_feasible:
        feasibility_reason = (
            "✅ Feasible: all stops visited, no subtours, "
            f"each node has exactly 1 outgoing edge. Distance: {total_dist:.1f} km"
        )
    else:
        feasibility_reason = "❌ Infeasible: " + "; ".join(violations[:2])

    route_nodes = [nodes[i] for i in route if i < len(nodes)]

    return {
        "assignment": assignment,
        "selected_edges": selected_edges,
        "route": route,
        "route_nodes": route_nodes,
        "is_feasible": is_feasible,
        "feasibility_reason": feasibility_reason,
        "total_dist": round(total_dist, 2),
        "violations": violations,
    }


def get_all_candidates(
    probabilities: Dict[str, float],
    var_map: Dict[Tuple[int, int], int],
    nodes: List[dict],
    dist_matrix: np.ndarray,
    top_n: int = 15,
) -> List[Dict]:
    """
    Process top-N measurement outcomes and return decoded candidates.

    Args:
        probabilities : {bitstring: probability} from QAOA run
        var_map       : Variable mapping from qubo.py
        nodes         : Node list
        dist_matrix   : Distance matrix
        top_n         : Number of top bitstrings to process

    Returns:
        List of candidate dicts, sorted by probability (highest first).
        Each dict has: bitstring, probability, is_feasible, total_dist,
                       route_names, feasibility_reason, violations
    """
    candidates = []
    items = sorted(probabilities.items(), key=lambda x: -x[1])[:top_n]

    for bitstring, prob in items:
        decoded = decode_bitstring(bitstring, var_map, nodes, dist_matrix)
        route_names = [
            nodes[i]['name'].split(',')[0]
            for i in decoded['route']
            if i < len(nodes)
        ]
        candidates.append({
            "bitstring": bitstring,
            "bitstring_short": bitstring[:12] + "…" if len(bitstring) > 12 else bitstring,
            "probability": prob,
            "probability_pct": round(prob * 100, 2),
            "is_feasible": decoded["is_feasible"],
            "total_dist": decoded["total_dist"],
            "route_names": route_names,
            "route_indices": decoded["route"],
            "feasibility_reason": decoded["feasibility_reason"],
            "violations": decoded["violations"],
            "selected_edges": decoded["selected_edges"],
        })

    return candidates


def get_best_feasible(candidates: List[Dict]) -> Optional[Dict]:
    """
    Return the highest-probability feasible candidate.
    Falls back to lowest-distance infeasible if no feasible found.
    """
    feasible = [c for c in candidates if c["is_feasible"]]
    if feasible:
        # Among feasible candidates, pick highest probability
        return max(feasible, key=lambda c: c["probability"])

    # No feasible candidate — return best infeasible (least violated)
    if candidates:
        return min(candidates, key=lambda c: (len(c["violations"]), -c["probability"]))
    return None


def explain_route_selection(
    best_candidate: Dict,
    all_candidates: List[Dict],
    nodes: List[dict],
) -> Dict:
    """
    Generate a human-readable "Why this route?" explanation.

    Returns:
        Dict with explanation text, reasons list, and rejection reasons for others
    """
    if not best_candidate:
        return {
            "summary": "No valid candidates found from QAOA measurement.",
            "reasons_accepted": [],
            "rejection_reasons": [],
        }

    reasons_accepted = []

    if best_candidate["is_feasible"]:
        reasons_accepted.append("✅ Solution is feasible (all constraints satisfied)")
        reasons_accepted.append(f"✅ All {len(nodes)} nodes are visited exactly once")
        reasons_accepted.append("✅ No subtours (valid Hamiltonian path)")
        reasons_accepted.append(
            f"✅ Highest probability among feasible states: "
            f"{best_candidate['probability_pct']:.1f}%"
        )
        reasons_accepted.append(
            f"✅ Route distance: {best_candidate['total_dist']:.1f} km"
        )
    else:
        reasons_accepted.append(
            "⚠️ No fully feasible solution found in QAOA measurement sample"
        )
        reasons_accepted.append(
            "⚠️ Showing best partial solution (fewest violations)"
        )
        reasons_accepted += [f"⚠️ {v}" for v in best_candidate["violations"][:3]]

    # Rejection reasons for top alternatives
    rejection_reasons = []
    other_candidates = [c for c in all_candidates if c["bitstring"] != best_candidate["bitstring"]][:4]
    for c in other_candidates:
        if c["is_feasible"]:
            reason = f"Lower probability ({c['probability_pct']:.1f}% vs {best_candidate['probability_pct']:.1f}%)"
        else:
            v = c["violations"]
            reason = v[0] if v else "Infeasible"
        rejection_reasons.append({
            "bitstring": c["bitstring_short"],
            "probability": c["probability_pct"],
            "reason": reason,
        })

    route_str = " → ".join(best_candidate["route_names"])

    return {
        "summary": (
            f"Selected quantum state **{best_candidate['bitstring_short']}** "
            f"(P = {best_candidate['probability_pct']:.1f}%) → "
            f"Route: {route_str}"
        ),
        "reasons_accepted": reasons_accepted,
        "rejection_reasons": rejection_reasons,
        "route_display": route_str,
    }
