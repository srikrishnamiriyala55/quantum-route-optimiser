# quantum/qubo.py
"""
QUBO Formulation for Vehicle Routing Problems
==============================================
Converts a real routing problem (node list + distance matrix) into a
Quadratic Unconstrained Binary Optimization (QUBO) formulation suitable
for quantum optimization (QAOA).

Mathematical Formulation
-------------------------
Decision variables:
    x_ij ∈ {0,1}  = 1 if vehicle travels directly from node i to node j

Objective (minimize total distance):
    cost = Σ_{i≠j} d_ij * x_ij

Constraints (encoded as quadratic penalty terms):
    C1 (out-degree = 1):  Σ_j x_ij = 1  for all i   (every node has exactly one successor)
    C2 (in-degree = 1):   Σ_i x_ij = 1  for all j   (every node has exactly one predecessor)
    C3 (subtour elim):    u_i - u_j + n*x_ij ≤ n-1  (MTZ lifted; approximated here)

Full QUBO energy:
    E(x) = cost + λ1 * Σ_i (Σ_j x_ij - 1)² + λ2 * Σ_j (Σ_i x_ij - 1)²

The diagonal of the QUBO matrix encodes linear terms; off-diagonal encodes quadratic interactions.

NOTE: For k nodes (including depot), this produces k² binary variables.
QAOA is demonstrated on small sub-instances (≤6 stops) due to simulator complexity.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional


def build_qubo_matrix(
    nodes: List[dict],
    dist_matrix: np.ndarray,
    lambda1: float = 8.0,
    lambda2: float = 8.0,
    normalize_distances: bool = True,
) -> Tuple[np.ndarray, Dict, Dict]:
    """
    Build the QUBO matrix for a TSP/VRP routing instance.

    Args:
        nodes        : List of node dicts with 'name', 'coords'
        dist_matrix  : N×N distance matrix in km (real road or geodesic)
        lambda1      : Penalty coefficient for out-degree constraint
        lambda2      : Penalty coefficient for in-degree constraint
        normalize_distances: If True, scale distances to [0,1] for better conditioning

    Returns:
        Q            : QUBO matrix as np.ndarray, shape (n², n²)
        var_map      : Dict mapping (i,j) → qubit index
        metadata     : Dict with problem stats and formula string
    """
    n = len(nodes)
    n_vars = n * n  # one binary var x_ij per ordered pair

    # ── Variable mapping ──────────────────────────────────────────────────────
    # x_ij maps to qubit index: i * n + j
    # We exclude self-loops (i == j) but keep them in matrix as 0
    var_map = {}
    idx = 0
    for i in range(n):
        for j in range(n):
            if i != j:
                var_map[(i, j)] = i * n + j

    # ── Initialize QUBO matrix ────────────────────────────────────────────────
    Q = np.zeros((n_vars, n_vars))

    # ── Normalize distance matrix ─────────────────────────────────────────────
    d = dist_matrix.copy()
    np.fill_diagonal(d, 0.0)
    d_max = d.max()
    d_range = d_max if d_max > 0 else 1.0

    if normalize_distances:
        d_norm = d / d_range
    else:
        d_norm = d

    # ── Term 1: Distance cost (linear diagonal terms) ─────────────────────────
    # E_dist = Σ_{i≠j} d_ij * x_ij
    # Linear term → diagonal Q[k,k] where k = var_map[(i,j)]
    for i in range(n):
        for j in range(n):
            if i != j:
                k = var_map[(i, j)]
                Q[k, k] += d_norm[i, j]

    # ── Term 2: Out-degree constraint: Σ_j x_ij = 1 ──────────────────────────
    # Penalty: λ1 * (Σ_j x_ij - 1)² = λ1 * (Σ_j x_ij)² - 2λ1 * Σ_j x_ij + λ1
    # Expanding (Σ_j x_ij)²: Σ_j x_ij² + 2 Σ_{j<k} x_ij * x_ik
    # Since x_ij ∈ {0,1}: x_ij² = x_ij → linear terms only from diagonal
    for i in range(n):
        successors = [j for j in range(n) if j != i]
        # Diagonal: x_ij² - 2*x_ij → -λ1 per variable
        for j in successors:
            k = var_map[(i, j)]
            Q[k, k] += lambda1 * (1 - 2)  # x_ij² - 2*x_ij = -x_ij
        # Off-diagonal: 2 * λ1 per pair x_ij * x_ik (j ≠ k)
        for idx_a, j in enumerate(successors):
            for k_n in successors[idx_a + 1:]:
                a = var_map[(i, j)]
                b = var_map[(i, k_n)]
                Q[a, b] += 2 * lambda1
                Q[b, a] += 2 * lambda1  # symmetric

    # ── Term 3: In-degree constraint: Σ_i x_ij = 1 ───────────────────────────
    for j in range(n):
        predecessors = [i for i in range(n) if i != j]
        for i in predecessors:
            k = var_map[(i, j)]
            Q[k, k] += lambda2 * (1 - 2)
        for idx_a, i in enumerate(predecessors):
            for i2 in predecessors[idx_a + 1:]:
                a = var_map[(i, j)]
                b = var_map[(i2, j)]
                Q[a, b] += 2 * lambda2
                Q[b, a] += 2 * lambda2

    # ── Metadata ──────────────────────────────────────────────────────────────
    metadata = {
        "n_nodes": n,
        "n_variables": n_vars,
        "n_active_variables": n_vars - n,  # excluding self-loops
        "lambda1": lambda1,
        "lambda2": lambda2,
        "d_max_km": float(d_max),
        "normalized": normalize_distances,
        "formula": (
            "E(x) = Σ_{i≠j} d_ij·x_ij  "
            "+ λ₁·Σᵢ(Σⱼ xᵢⱼ − 1)²  "
            "+ λ₂·Σⱼ(Σᵢ xᵢⱼ − 1)²"
        ),
        "variable_description": "x_ij = 1 if vehicle travels directly from node i to node j",
        "node_names": [n_["name"].split(",")[0] for n_ in nodes],
        "qubo_min": float(Q.min()),
        "qubo_max": float(Q.max()),
        "n_nonzero": int(np.count_nonzero(Q)),
    }

    return Q, var_map, metadata


def qubo_to_ising(Q: np.ndarray) -> Tuple[np.ndarray, np.ndarray, float]:
    """
    Convert QUBO matrix to Ising model: H = Σ h_i σ_i^z + Σ J_ij σ_i^z σ_j^z + offset

    QUBO → Ising substitution: x_i = (1 - σ_i^z) / 2, so σ_i^z = 1 - 2*x_i

    Returns:
        h      : Linear (longitudinal field) terms, shape (n,)
        J      : Quadratic (coupling) terms, shape (n, n)
        offset : Constant energy offset
    """
    n = Q.shape[0]
    h = np.zeros(n)
    J = np.zeros((n, n))
    offset = 0.0

    # Diagonal Q_ii terms → h_i = -Q_ii/2, offset += Q_ii/4
    for i in range(n):
        h[i] += -Q[i, i] / 2
        offset += Q[i, i] / 4

    # Off-diagonal Q_ij terms → J_ij = Q_ij/4, h_i += -Q_ij/4, h_j += -Q_ij/4, offset += Q_ij/4
    for i in range(n):
        for j in range(i + 1, n):
            val = Q[i, j] + Q[j, i]  # symmetric
            J[i, j] += val / 4
            J[j, i] += val / 4
            h[i] += -val / 4
            h[j] += -val / 4
            offset += val / 4

    return h, J, offset


def get_qubo_subproblem(
    nodes: List[dict],
    dist_matrix: np.ndarray,
    max_qubits: int = 16,
    lambda1: float = 8.0,
    lambda2: float = 8.0,
) -> Tuple[np.ndarray, Dict, Dict, List[dict], np.ndarray]:
    """
    Returns a QUBO for a sub-problem of at most sqrt(max_qubits) nodes.
    Used to keep QAOA feasible on the local simulator.

    Returns: Q, var_map, metadata, sub_nodes, sub_dist_matrix
    """
    n = len(nodes)
    # Maximum nodes such that n² ≤ max_qubits
    max_nodes = int(max_qubits ** 0.5)
    max_nodes = max(3, max_nodes)  # at least 3 nodes (depot + 2 stops)

    if n > max_nodes:
        # Take depot (index 0) + first (max_nodes - 1) stops
        sub_idx = list(range(min(max_nodes, n)))
        sub_nodes = [nodes[i] for i in sub_idx]
        sub_dist = dist_matrix[np.ix_(sub_idx, sub_idx)]
    else:
        sub_nodes = nodes
        sub_dist = dist_matrix

    Q, var_map, meta = build_qubo_matrix(sub_nodes, sub_dist, lambda1, lambda2)
    meta["is_subproblem"] = len(sub_nodes) < n
    meta["full_problem_size"] = n
    meta["subproblem_size"] = len(sub_nodes)

    return Q, var_map, meta, sub_nodes, sub_dist


def energy_from_bitstring(bitstring: str, Q: np.ndarray) -> float:
    """
    Compute the QUBO energy E = x^T Q x for a given binary string.
    """
    x = np.array([int(b) for b in bitstring], dtype=float)
    return float(x @ Q @ x)


def bitstring_to_assignment(bitstring: str, var_map: Dict, n: int) -> Dict:
    """
    Convert a bitstring to a dict of (i,j) → 0/1 assignments.
    """
    assignment = {}
    for (i, j), qubit_idx in var_map.items():
        if qubit_idx < len(bitstring):
            assignment[(i, j)] = int(bitstring[qubit_idx])
    return assignment
