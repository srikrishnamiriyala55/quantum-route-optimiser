# quantum/telemetry.py
"""
Structured Telemetry for Q-RouteX
====================================
Telemetry data structures for both quantum and quantum-inspired solvers.
Clearly separates classical SA metrics from genuine QAOA metrics.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any


@dataclass
class SATelemetry:
    """
    Telemetry for Quantum-Inspired Simulated Annealing.
    Correctly labeled as 'quantum-inspired' — NOT quantum hardware.
    """
    algorithm: str = "Quantum-Inspired Simulated Annealing"
    iterations: int = 0
    initial_temperature: float = 0.0
    final_temperature: float = 0.0
    cooling_rate: float = 0.0
    tunneling_events: int = 0       # times a worse state was accepted
    accepted_moves: int = 0         # total moves accepted (improve + tunnel)
    rejected_moves: int = 0         # total moves rejected
    initial_energy: float = 0.0
    best_energy: float = 0.0
    final_energy: float = 0.0
    best_iter: int = 0
    runtime_s: float = 0.0
    energy_history: List[float] = field(default_factory=list)
    best_history: List[float] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return asdict(self)

    @property
    def acceptance_rate_pct(self) -> float:
        total = self.accepted_moves + self.rejected_moves
        return round(self.accepted_moves / total * 100, 1) if total > 0 else 0.0

    @property
    def tunneling_rate_pct(self) -> float:
        total = self.accepted_moves + self.rejected_moves
        return round(self.tunneling_events / total * 100, 2) if total > 0 else 0.0

    @property
    def improvement_pct(self) -> float:
        if self.initial_energy > 0:
            return round((self.initial_energy - self.best_energy) / self.initial_energy * 100, 2)
        return 0.0


@dataclass
class QAOATelemetry:
    """
    Telemetry for genuine QAOA (Qiskit Aer quantum circuit simulation).
    """
    algorithm: str = "QAOA (Quantum Approximate Optimization Algorithm)"
    backend: str = "Qiskit Aer AerSimulator"
    n_qubits: int = 0
    p_layers: int = 0
    n_shots: int = 0
    gamma_opt: List[float] = field(default_factory=list)
    beta_opt: List[float] = field(default_factory=list)
    best_bitstring: str = ""
    best_energy: float = 0.0
    best_probability_pct: float = 0.0
    n_feasible_candidates: int = 0
    n_total_candidates: int = 0
    optimizer: str = "COBYLA"
    optimizer_iterations: int = 0
    runtime_s: float = 0.0
    circuit_depth: Any = "N/A"
    n_parameters: int = 0
    gate_counts: Dict = field(default_factory=dict)
    is_subproblem: bool = False
    subproblem_size: int = 0
    full_problem_size: int = 0
    energy_landscape: List[float] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return asdict(self)

    @property
    def feasibility_rate_pct(self) -> float:
        if self.n_total_candidates > 0:
            return round(self.n_feasible_candidates / self.n_total_candidates * 100, 1)
        return 0.0


def build_sa_telemetry(stats: Dict, runtime_s: float = 0.0) -> SATelemetry:
    """
    Build SATelemetry from the dict returned by app.simulated_quantum_annealing().
    """
    history = stats.get("history", [])
    best_energy = min(history) if history else 0.0
    best_iter   = history.index(best_energy) if history else 0
    tunnels     = stats.get("tunnels", 0)
    final_t     = stats.get("final_temp", 0.0)

    # Rich telemetry if available (from enhanced app.py)
    return SATelemetry(
        iterations=len(history),
        initial_temperature=stats.get("initial_temp", 0.0),
        final_temperature=final_t,
        cooling_rate=stats.get("cooling_rate", 0.0),
        tunneling_events=tunnels,
        accepted_moves=stats.get("accepted_moves", tunnels),
        rejected_moves=stats.get("rejected_moves", max(0, len(history) - tunnels)),
        initial_energy=history[0] if history else 0.0,
        best_energy=best_energy,
        final_energy=history[-1] if history else 0.0,
        best_iter=best_iter,
        runtime_s=runtime_s,
        energy_history=history,
        best_history=stats.get("best_history", []),
    )


def build_qaoa_telemetry(
    qaoa_result: Dict,
    candidates: List[Dict],
    qubo_meta: Dict,
) -> QAOATelemetry:
    """Build QAOATelemetry from QAOA run result dict."""
    circuit_info = qaoa_result.get("circuit_info", {})
    feasible_count = sum(1 for c in candidates if c.get("is_feasible", False))
    best_prob = max((c["probability_pct"] for c in candidates if c.get("is_feasible")), default=0.0)

    return QAOATelemetry(
        backend=qaoa_result.get("backend", "Qiskit Aer"),
        n_qubits=qaoa_result.get("n_qubits", 0),
        p_layers=qaoa_result.get("p_layers", 1),
        n_shots=qaoa_result.get("n_shots", 0),
        gamma_opt=qaoa_result.get("gamma_opt", []),
        beta_opt=qaoa_result.get("beta_opt", []),
        best_bitstring=qaoa_result.get("best_bitstring", ""),
        best_energy=qaoa_result.get("best_energy", 0.0),
        best_probability_pct=best_prob,
        n_feasible_candidates=feasible_count,
        n_total_candidates=len(candidates),
        optimizer_iterations=len(qaoa_result.get("energy_landscape", [])),
        runtime_s=qaoa_result.get("runtime_s", 0.0),
        circuit_depth=circuit_info.get("depth_before_transpile", "N/A"),
        n_parameters=circuit_info.get("n_parameters", 0),
        gate_counts=circuit_info.get("gate_counts", {}),
        is_subproblem=qubo_meta.get("is_subproblem", False),
        subproblem_size=qubo_meta.get("subproblem_size", qubo_meta.get("n_nodes", 0)),
        full_problem_size=qubo_meta.get("full_problem_size", qubo_meta.get("n_nodes", 0)),
        energy_landscape=qaoa_result.get("energy_landscape", []),
    )
