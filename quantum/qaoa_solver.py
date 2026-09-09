# quantum/qaoa_solver.py
"""
Genuine QAOA Solver for Q-RouteX
==================================
Implements a real Quantum Approximate Optimization Algorithm (QAOA) pipeline
using Qiskit and the Qiskit Aer local simulator.

Pipeline:
    QUBO matrix
        ↓
    Ising Hamiltonian (h, J, offset)
        ↓
    QAOA Circuit (p layers of H_cost + H_mixer)
        ↓
    Parameter optimization (COBYLA)
        ↓
    Shot-based measurement
        ↓
    Probability distribution over bitstrings
        ↓
    Decoded candidate solutions

Scientific Notes:
    - "Quantum" here means a simulated quantum circuit on a classical computer
      (Qiskit AerSimulator). This is NOT a real quantum processor.
    - QAOA is limited to small instances due to simulator complexity.
    - For larger problems, the full SA solver handles optimization; QAOA
      demonstrates the quantum approach on a reduced sub-instance.
    - No quantum speedup is claimed. Results are compared honestly.
"""

import time
import numpy as np
from typing import Dict, List, Tuple, Optional

# ── Qiskit imports (all wrapped for graceful degradation) ────────────────────
QISKIT_AVAILABLE = False
try:
    from qiskit import QuantumCircuit, transpile
    from qiskit.circuit import ParameterVector
    from qiskit_aer import AerSimulator
    from qiskit_aer.primitives import Sampler as AerSampler
    from scipy.optimize import minimize as scipy_minimize
    QISKIT_AVAILABLE = True
except ImportError:
    pass

from quantum.qubo import qubo_to_ising, energy_from_bitstring


# ── Constants ─────────────────────────────────────────────────────────────────
MAX_QUBITS_QAOA = 16   # hard cap — prevents simulator from hanging
MAX_NODES_QAOA  = 4    # n² ≤ 16 qubits → max 4 nodes (depot + 3 stops)


def _build_qaoa_circuit(
    h: np.ndarray,
    J: np.ndarray,
    p: int,
) -> "QuantumCircuit":
    """
    Build a p-layer QAOA circuit for the given Ising model.

    Circuit structure (per layer):
        Cost unitary:  Σ_{i<j} exp(-i·γ·J_ij·Z_i·Z_j) + Σ_i exp(-i·γ·h_i·Z_i)
        Mixer unitary: Σ_i exp(-i·β·X_i)

    Args:
        h  : Linear Ising terms (n,)
        J  : Quadratic Ising couplings (n, n)
        p  : Number of QAOA layers

    Returns:
        qc : QuantumCircuit with 2p free parameters (gamma[0..p-1], beta[0..p-1])
    """
    n = len(h)
    gamma = ParameterVector("γ", p)
    beta  = ParameterVector("β", p)

    qc = QuantumCircuit(n)

    # Initial state: uniform superposition |+⟩^n
    qc.h(range(n))

    for layer in range(p):
        # ── Cost unitary exp(-i·γ·H_C) ────────────────────────────────────
        # Two-qubit ZZ terms: RZZ(2γJ_ij)
        for i in range(n):
            for j in range(i + 1, n):
                if abs(J[i, j]) > 1e-10:
                    qc.rzz(2 * gamma[layer] * J[i, j], i, j)

        # Single-qubit Z terms: RZ(-2γh_i)
        for i in range(n):
            if abs(h[i]) > 1e-10:
                qc.rz(-2 * gamma[layer] * h[i], i)

        # ── Mixer unitary exp(-i·β·H_B) ───────────────────────────────────
        # Standard transverse-field mixer: RX(2β) on each qubit
        for i in range(n):
            qc.rx(2 * beta[layer], i)

    qc.measure_all()
    return qc


def run_qaoa(
    Q: np.ndarray,
    p: int = 1,
    n_shots: int = 1024,
    max_iter_opt: int = 100,
    backend_name: str = "aer_simulator",
    seed: int = 42,
) -> Dict:
    """
    Run a full QAOA pipeline on the given QUBO matrix.

    Args:
        Q            : QUBO matrix (n_vars × n_vars)
        p            : Number of QAOA layers (circuit depth)
        n_shots      : Number of measurement shots
        max_iter_opt : Maximum iterations for classical parameter optimizer
        backend_name : Qiskit backend name
        seed         : RNG seed for reproducibility

    Returns:
        result dict with keys:
            counts           : Raw measurement counts {bitstring: count}
            probabilities    : Normalized {bitstring: probability}
            best_bitstring   : Highest-probability bitstring
            best_energy      : QUBO energy of best bitstring
            gamma_opt        : Optimized gamma parameters
            beta_opt         : Optimized beta parameters
            energy_landscape : List of (iteration, energy) during optimization
            circuit_info     : Dict with circuit statistics
            runtime_s        : Wall-clock time in seconds
            backend          : Backend used
            n_qubits         : Number of qubits
            n_shots          : Number of shots
            p_layers         : QAOA layers
            feasibility_note : Human-readable note about this run
    """
    if not QISKIT_AVAILABLE:
        return _qaoa_unavailable_result()

    t_start = time.perf_counter()
    n = Q.shape[0]

    if n > MAX_QUBITS_QAOA:
        return {
            "error": f"QUBO has {n} variables ({n} qubits). Max supported: {MAX_QUBITS_QAOA}.",
            "counts": {},
            "probabilities": {},
            "best_bitstring": "0" * n,
            "best_energy": 0.0,
            "gamma_opt": [],
            "beta_opt": [],
            "energy_landscape": [],
            "circuit_info": {},
            "runtime_s": 0.0,
            "backend": backend_name,
            "n_qubits": n,
            "n_shots": n_shots,
            "p_layers": p,
            "feasibility_note": f"Problem too large for QAOA ({n} qubits > {MAX_QUBITS_QAOA} max).",
        }

    # ── Convert QUBO → Ising ─────────────────────────────────────────────────
    h, J, offset = qubo_to_ising(Q)

    # ── Build QAOA circuit ───────────────────────────────────────────────────
    qc = _build_qaoa_circuit(h, J, p)

    # ── Set up Aer backend ───────────────────────────────────────────────────
    try:
        backend = AerSimulator(method="statevector", seed_simulator=seed)
    except Exception:
        try:
            backend = AerSimulator(seed_simulator=seed)
        except Exception as e:
            return _qaoa_unavailable_result(str(e))

    # ── Classical optimizer for QAOA parameters ──────────────────────────────
    rng = np.random.default_rng(seed)
    # Initial guess: small random values
    x0 = rng.uniform(0, np.pi, 2 * p)
    energy_landscape = []
    best_params = x0.copy()
    best_cost = np.inf

    def _objective(params):
        nonlocal best_params, best_cost
        gamma_vals = params[:p]
        beta_vals  = params[p:]

        # Bind parameters and run circuit
        param_dict = {}
        gamma_syms = qc.parameters[:p]  # ParameterVector γ
        beta_syms  = qc.parameters[p:]  # ParameterVector β

        bound_qc = qc.assign_parameters(
            dict(zip(list(qc.parameters), params))
        )

        try:
            transpiled = transpile(bound_qc, backend=backend, optimization_level=1)
            job = backend.run(transpiled, shots=n_shots, seed_simulator=seed)
            result = job.result()
            counts = result.get_counts()
        except Exception:
            return 1e9

        # Compute expected energy over measurement outcomes
        total = sum(counts.values())
        exp_energy = 0.0
        for bits, cnt in counts.items():
            # Qiskit returns bits in little-endian order → reverse for our convention
            bits_rev = bits[::-1].replace(" ", "")
            e = energy_from_bitstring(bits_rev, Q)
            exp_energy += (cnt / total) * e

        exp_energy += offset
        energy_landscape.append(float(exp_energy))

        if exp_energy < best_cost:
            best_cost = exp_energy
            best_params = params.copy()

        return exp_energy

    # Run optimizer
    try:
        opt_result = scipy_minimize(
            _objective,
            x0,
            method="COBYLA",
            options={"maxiter": max_iter_opt, "rhobeg": 0.5},
        )
        gamma_opt = best_params[:p].tolist()
        beta_opt  = best_params[p:].tolist()
    except Exception as e:
        gamma_opt = x0[:p].tolist()
        beta_opt  = x0[p:].tolist()

    # ── Final measurement with optimized parameters ───────────────────────────
    bound_final = qc.assign_parameters(
        dict(zip(list(qc.parameters), np.concatenate([gamma_opt, beta_opt])))
    )
    try:
        transpiled_final = transpile(bound_final, backend=backend, optimization_level=1)
        job_final = backend.run(transpiled_final, shots=n_shots, seed_simulator=seed)
        final_result = job_final.result()
        raw_counts = final_result.get_counts()
    except Exception as e:
        return _qaoa_unavailable_result(f"Final measurement failed: {e}")

    # ── Process results ───────────────────────────────────────────────────────
    total_shots = sum(raw_counts.values())
    # Normalize bitstrings (remove spaces, reverse for MSB convention)
    counts = {}
    for bits, cnt in raw_counts.items():
        bits_clean = bits.replace(" ", "")[::-1]  # little-endian → MSB first
        counts[bits_clean] = counts.get(bits_clean, 0) + cnt

    probabilities = {b: c / total_shots for b, c in sorted(counts.items(), key=lambda x: -x[1])}

    best_bitstring = max(counts, key=counts.get)
    best_energy = energy_from_bitstring(best_bitstring, Q)

    # Circuit statistics
    try:
        circuit_info = {
            "n_qubits": qc.num_qubits,
            "depth_before_transpile": qc.depth(),
            "n_parameters": len(qc.parameters),
            "p_layers": p,
            "gate_counts": dict(qc.count_ops()),
        }
    except Exception:
        circuit_info = {"n_qubits": n, "p_layers": p}

    runtime_s = round(time.perf_counter() - t_start, 3)

    return {
        "counts": counts,
        "probabilities": probabilities,
        "best_bitstring": best_bitstring,
        "best_energy": float(best_energy),
        "gamma_opt": gamma_opt,
        "beta_opt": beta_opt,
        "energy_landscape": energy_landscape,
        "circuit_info": circuit_info,
        "runtime_s": runtime_s,
        "backend": "Qiskit Aer (AerSimulator)",
        "n_qubits": n,
        "n_shots": n_shots,
        "p_layers": p,
        "feasibility_note": (
            f"QAOA run on {n}-qubit local simulator. "
            f"Results represent actual quantum circuit measurement probabilities."
        ),
        "qc_object": qc,  # Circuit object for visualization
    }


def _qaoa_unavailable_result(msg: str = "") -> Dict:
    """Return a structured 'unavailable' result when Qiskit is not installed."""
    return {
        "error": f"Qiskit not available. {msg}".strip(),
        "counts": {},
        "probabilities": {},
        "best_bitstring": "",
        "best_energy": 0.0,
        "gamma_opt": [],
        "beta_opt": [],
        "energy_landscape": [],
        "circuit_info": {},
        "runtime_s": 0.0,
        "backend": "Unavailable",
        "n_qubits": 0,
        "n_shots": 0,
        "p_layers": 0,
        "feasibility_note": "Qiskit / Qiskit-Aer is not installed in this environment.",
    }


def get_qaoa_availability() -> Tuple[bool, str]:
    """Check if QAOA is available and return status message."""
    if not QISKIT_AVAILABLE:
        return False, "Qiskit not installed. Run: pip install qiskit qiskit-aer"
    try:
        sim = AerSimulator()
        return True, f"Qiskit Aer available — backend: {sim.name}"
    except Exception as e:
        return False, f"Qiskit Aer initialization failed: {e}"
