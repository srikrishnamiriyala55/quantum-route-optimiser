# sessionstate.py
"""Session state initialization for Q-RouteX."""
import streamlit as st
import uuid


def init_session_state():
    """Initialize all session variables if they don't exist."""

    # ── User identity ──────────────────────────────────────────────────────────
    if 'user_agent_id' not in st.session_state:
        st.session_state.user_agent_id = str(uuid.uuid4())

    # ── Solver engine status ───────────────────────────────────────────────────
    if 'solver_status' not in st.session_state:
        st.session_state.solver_status = "Idle"

    # ── Input state ────────────────────────────────────────────────────────────
    if 'stops_data' not in st.session_state:
        st.session_state.stops_data = []

    if 'is_round_trip_active' not in st.session_state:
        st.session_state.is_round_trip_active = False

    # ── Quantum-inspired solver results ───────────────────────────────────────
    if 'optimized_route' not in st.session_state:
        st.session_state.optimized_route = None

    if 'route_metrics' not in st.session_state:
        st.session_state.route_metrics = {}

    if 'optimization_stats' not in st.session_state:
        st.session_state.optimization_stats = None

    if 'quantum_runtime_s' not in st.session_state:
        st.session_state.quantum_runtime_s = None

    # ── Computed metrics (from metrics.py) ────────────────────────────────────
    if 'quantum_metrics' not in st.session_state:
        st.session_state.quantum_metrics = None

    if 'quantum_sla_details' not in st.session_state:
        st.session_state.quantum_sla_details = None

    # ── Classical solver results ───────────────────────────────────────────────
    if 'classical_route' not in st.session_state:
        st.session_state.classical_route = None       # same structure as optimized_route

    if 'classical_metrics' not in st.session_state:
        st.session_state.classical_metrics = None     # output of metrics.calculate_route_metrics

    if 'classical_stats' not in st.session_state:
        st.session_state.classical_stats = None       # runtime, algorithm, energy

    if 'classical_sla_details' not in st.session_state:
        st.session_state.classical_sla_details = None

    # ── Comparison results ────────────────────────────────────────────────────
    if 'comparison_result' not in st.session_state:
        st.session_state.comparison_result = None     # output of comparison.compute_comparison

    if 'optimization_score' not in st.session_state:
        st.session_state.optimization_score = None

    if 'score_breakdown' not in st.session_state:
        st.session_state.score_breakdown = None

    # ── Shared distance/time matrices ─────────────────────────────────────────
    if 'shared_dist_matrix' not in st.session_state:
        st.session_state.shared_dist_matrix = None

    if 'shared_time_matrix' not in st.session_state:
        st.session_state.shared_time_matrix = None

    if 'shared_all_nodes' not in st.session_state:
        st.session_state.shared_all_nodes = None

    # ── Scenario parameters ───────────────────────────────────────────────────
    if 'scenario_params' not in st.session_state:
        st.session_state.scenario_params = {
            "mileage": 12.0,
            "fuel_price": 96.0,
            "emission_factor": 2.68,
            "traffic_multiplier": 1.0,
            "fleet_size": 1,
            "n_iter": 3000,
            "cooling_rate": 0.998,
            "init_temp": 100,
        }

    # ── Run history (in-session only, no persistence) ─────────────────────────
    if 'run_history' not in st.session_state:
        st.session_state.run_history = []

    # ── Optimization timestamp ────────────────────────────────────────────────
    if 'optimization_timestamp' not in st.session_state:
        st.session_state.optimization_timestamp = None

    # ── Navigation ────────────────────────────────────────────────────────────
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "🏠 Dashboard"

    # ── QUBO formulation data ─────────────────────────────────────────────────
    if 'qubo_data' not in st.session_state:
        st.session_state.qubo_data = None
        # Structure: {Q: ndarray, var_map: dict, meta: dict,
        #             sub_nodes: list, sub_dist: ndarray}

    # ── QAOA genuine quantum results ──────────────────────────────────────────
    if 'qaoa_result' not in st.session_state:
        st.session_state.qaoa_result = None
        # Structure: output dict from quantum.qaoa_solver.run_qaoa()

    if 'qaoa_candidates' not in st.session_state:
        st.session_state.qaoa_candidates = []  # List from quantum.decoder.get_all_candidates()

    if 'qaoa_best_candidate' not in st.session_state:
        st.session_state.qaoa_best_candidate = None

    if 'qaoa_telemetry' not in st.session_state:
        st.session_state.qaoa_telemetry = None  # QAOATelemetry dataclass

    if 'sa_telemetry' not in st.session_state:
        st.session_state.sa_telemetry = None    # SATelemetry dataclass

    # ── Exact solver results ──────────────────────────────────────────────────
    if 'exact_result' not in st.session_state:
        st.session_state.exact_result = None
        # Structure: output dict from optimization.exact_solver.brute_force_tsp()

    if 'optimality_gaps' not in st.session_state:
        st.session_state.optimality_gaps = None

    # ── Benchmark lab results ─────────────────────────────────────────────────
    if 'benchmark_results' not in st.session_state:
        st.session_state.benchmark_results = []
        # List of dicts: {n_stops, classical_dist, sa_dist, classical_rt, sa_rt}

    # ── QAOA availability flag ────────────────────────────────────────────────
    if 'qaoa_available' not in st.session_state:
        st.session_state.qaoa_available = None  # None = unchecked, True/False after check
