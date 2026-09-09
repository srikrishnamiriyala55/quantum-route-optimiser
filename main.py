# main.py
"""
Q-RouteX — Quantum-Enhanced Intelligent Route Optimization
=============================================================
Main entry point. Orchestrates:
  1. UI setup (page config, CSS, session state, sidebar)
  2. Optimization trigger:
     a. Classical baseline (Nearest Neighbor + 2-opt)
     b. Quantum-Inspired SA (Simulated Annealing — classical CPU, quantum-inspired)
     c. QUBO formulation from actual problem data
     d. Real QAOA (Qiskit Aer simulator — only for small instances)
     e. Exact solver (brute-force, only for ≤8 stops)
  3. Comparison (honest: no metric swapping)
  4. Page routing to the correct frontend renderer

SCIENTIFIC INTEGRITY NOTE:
  - Classical (NN + 2-opt) and Quantum-Inspired (SA) results are shown AS-IS.
  - There is NO artificial swapping to make quantum "win".
  - QAOA results come from real Qiskit circuit simulation.
  - Quantum-Inspired ≠ Quantum. Correctly labeled throughout.
"""

import time
import datetime
import streamlit as st

import config
import sessionstate
import api
import frontend

from app import build_matrices, solve_hybrid_quantum
from classical_solver import solve_classical_hybrid
from metrics import calculate_route_metrics, calculate_sla_details, calculate_optimization_score
from comparison import compute_comparison
from logic import optimize_route_algo   # kept for backward compatibility

# ──────────────────────────────────────────────────────────────────────────────
# 1. Page Setup
# ──────────────────────────────────────────────────────────────────────────────

st.set_page_config(**config.PAGE_CONFIG)
config.load_css()
sessionstate.init_session_state()

# ──────────────────────────────────────────────────────────────────────────────
# 2. Sidebar (returns all inputs)
# ──────────────────────────────────────────────────────────────────────────────

(
    page,
    start_loc,
    is_round_trip,
    mileage,
    fuel_price,
    emission_factor,
    traffic_multiplier,
    fleet_size,
    q_params,
    go_btn,
) = frontend.render_sidebar()

# ──────────────────────────────────────────────────────────────────────────────
# 3. Optimization Trigger
# ──────────────────────────────────────────────────────────────────────────────

if go_btn:
    # ── Input validation ──────────────────────────────────────────────────────
    errors = []
    if not start_loc:
        errors.append("Please select a **Start Location** in the sidebar.")
    if not st.session_state.stops_data:
        errors.append("Please add **at least one stop** in the sidebar.")
    if fleet_size < 1 or fleet_size > 10:
        errors.append("Fleet size must be between 1 and 10.")

    if errors:
        for e in errors:
            st.error(f"⚠️ {e}")
        st.session_state.solver_status = "Failed"
    else:
        with st.status("🚀 Launching Q-RouteX Optimization Engine...", expanded=True) as status:
            try:
                stops = st.session_state.stops_data
                all_nodes = [start_loc] + stops

                # ── Step 1: Build shared distance/time matrices ───────────────
                st.write("🔧 Building distance & time matrices (OSRM / geodesic)...")
                dist_matrix, time_matrix = build_matrices(all_nodes)
                st.session_state.shared_dist_matrix = dist_matrix
                st.session_state.shared_time_matrix = time_matrix
                st.session_state.shared_all_nodes = all_nodes

                # ── Step 2: Classical Baseline ────────────────────────────────
                st.write("📐 Running classical baseline (Greedy Nearest Neighbor dispatch)...")
                t_classical_start = time.perf_counter()
                classical_routes, classical_stats = solve_classical_hybrid(
                    start_loc, stops, n_vehicles=fleet_size, dist_matrix=dist_matrix, time_matrix=time_matrix
                )
                classical_runtime = round(time.perf_counter() - t_classical_start, 3)
                classical_stats["runtime_s"] = classical_runtime

                # Apply round-trip to classical
                if is_round_trip or fleet_size > 1:
                    for i in range(len(classical_routes)):
                        classical_routes[i].append(classical_routes[i][0])

                # Build classical route geometry for map
                c_all_markers, c_all_coords, c_all_routes_geo = [], [], []
                for v_idx, route_nodes in enumerate(classical_routes):
                    coords_seq = [n['coords'] for n in route_nodes]
                    path_geo, _, _ = api.get_road_path(coords_seq)
                    c_all_routes_geo.append(path_geo if path_geo else coords_seq)
                    for s_idx, node in enumerate(route_nodes):
                        c_all_markers.append({
                            "coords": node['coords'],
                            "name": node['name'],
                            "vehicle_id": v_idx,
                            "stop_idx": s_idx,
                            "is_last": s_idx == len(route_nodes) - 1,
                            "window": node.get('window'),
                        })
                        c_all_coords.append(node['coords'])

                st.session_state.classical_route = {
                    "markers": c_all_markers,
                    "coords": c_all_coords,
                    "routes_geo": c_all_routes_geo,
                    "routes_nodes": classical_routes,
                }
                st.session_state.classical_stats = classical_stats

                # Classical metrics
                classical_metrics = calculate_route_metrics(
                    classical_routes, dist_matrix, time_matrix, all_nodes,
                    mileage, fuel_price, emission_factor, traffic_multiplier
                )
                st.session_state.classical_metrics = classical_metrics

                # Classical SLA details (first vehicle route for display)
                if classical_routes:
                    st.session_state.classical_sla_details = calculate_sla_details(
                        classical_routes[0], dist_matrix, time_matrix, all_nodes, traffic_multiplier
                    )

                # ── Step 3: Quantum-Inspired Optimizer (SA) ───────────────────
                st.write("⚛️ Running quantum-inspired simulated annealing...")
                t_quantum_start = time.perf_counter()
                quantum_routes_raw, q_stats = solve_hybrid_quantum(
                    start_loc, stops, n_vehicles=fleet_size, q_params=q_params,
                    dist_matrix=dist_matrix, time_matrix=time_matrix
                )
                quantum_runtime = round(time.perf_counter() - t_quantum_start, 3)

                # Apply round-trip to quantum
                st.session_state.is_round_trip_active = is_round_trip
                if is_round_trip or fleet_size > 1:
                    for i in range(len(quantum_routes_raw)):
                        quantum_routes_raw[i].append(quantum_routes_raw[i][0])

                # Build quantum route geometry for map
                q_all_markers, q_all_coords, q_all_routes_geo = [], [], []
                q_vehicle_metrics_basic = []
                for v_idx, route_nodes in enumerate(quantum_routes_raw):
                    coords_seq = [n['coords'] for n in route_nodes]
                    path_geo, km, mins = api.get_road_path(coords_seq)
                    q_all_routes_geo.append(path_geo if path_geo else coords_seq)
                    q_vehicle_metrics_basic.append({"id": v_idx + 1, "dist": km, "time": mins})
                    for s_idx, node in enumerate(route_nodes):
                        q_all_markers.append({
                            "coords": node['coords'],
                            "name": node['name'],
                            "vehicle_id": v_idx,
                            "stop_idx": s_idx,
                            "is_last": s_idx == len(route_nodes) - 1,
                            "window": node.get('window'),
                        })
                        q_all_coords.append(node['coords'])

                # Backwards-compatible session keys
                st.session_state.optimized_route = {
                    "markers": q_all_markers,
                    "coords": q_all_coords,
                    "routes_geo": q_all_routes_geo,
                    "routes_nodes": quantum_routes_raw,
                }
                st.session_state.optimization_stats = q_stats
                st.session_state.quantum_runtime_s = quantum_runtime

                # Build rich SA telemetry
                try:
                    from quantum.telemetry import build_sa_telemetry
                    st.session_state.sa_telemetry = build_sa_telemetry(q_stats, quantum_runtime)
                except Exception:
                    pass

                # Quantum metrics
                quantum_metrics = calculate_route_metrics(
                    quantum_routes_raw, dist_matrix, time_matrix, all_nodes,
                    mileage, fuel_price, emission_factor, traffic_multiplier
                )
                st.session_state.quantum_metrics = quantum_metrics

                # Backwards-compatible route_metrics
                st.session_state.route_metrics = {
                    "dist": quantum_metrics["dist_km"],
                    "time": quantum_metrics["time_min"],
                    "fuel": quantum_metrics["fuel_l"],
                    "cost": quantum_metrics["cost_inr"],
                    "vehicles": q_vehicle_metrics_basic,
                }

                # Quantum SLA details
                if quantum_routes_raw:
                    st.session_state.quantum_sla_details = calculate_sla_details(
                        quantum_routes_raw[0], dist_matrix, time_matrix, all_nodes, traffic_multiplier
                    )

                # ── Step 4: QUBO Formulation (from actual problem data) ────────
                st.write("⧛ Formulating QUBO from routing problem...")
                try:
                    from quantum.qubo import get_qubo_subproblem
                    Q, var_map, qubo_meta, sub_nodes, sub_dist = get_qubo_subproblem(
                        all_nodes, dist_matrix, max_qubits=16
                    )
                    st.session_state.qubo_data = {
                        "Q": Q,
                        "var_map": var_map,
                        "meta": qubo_meta,
                        "sub_nodes": sub_nodes,
                        "sub_dist": sub_dist,
                    }
                except Exception as qe:
                    st.write(f"  ⚠️ QUBO formulation skipped: {qe}")
                    st.session_state.qubo_data = None

                # ── Step 5: Exact Solver (small instances only) ───────────────
                st.write("🔢 Checking exact solver eligibility...")
                try:
                    from optimization.exact_solver import (
                        brute_force_tsp, compute_optimality_gaps, should_run_exact
                    )
                    n_stops = len(stops)
                    run_exact, exact_reason = should_run_exact(n_stops)
                    if run_exact:
                        st.write(f"  ✅ Exact solver running ({exact_reason})...")
                        exact_result = brute_force_tsp(all_nodes, dist_matrix)
                        st.session_state.exact_result = exact_result

                        gaps = compute_optimality_gaps(
                            exact_result["optimal_dist"],
                            classical_metrics["dist_km"],
                            quantum_metrics["dist_km"],
                        )
                        st.session_state.optimality_gaps = gaps
                    else:
                        st.write(f"  ⏭️ Exact solver skipped: {exact_reason}")
                        st.session_state.exact_result = {
                            "optimal_dist": 0.0,
                            "is_feasible": False,
                            "note": exact_reason,
                        }
                        st.session_state.optimality_gaps = None
                except Exception as ee:
                    st.write(f"  ⚠️ Exact solver error: {ee}")
                    st.session_state.exact_result = None
                    st.session_state.optimality_gaps = None

                # ── Step 6: QAOA (genuine quantum, small instances) ───────────
                qubo_data = st.session_state.qubo_data
                if qubo_data and qubo_data["meta"]["n_variables"] <= 16:
                    st.write(
                        f"⚛️ Running QAOA on {qubo_data['meta']['subproblem_size']}-node "
                        f"sub-instance ({qubo_data['meta']['n_variables']} qubits)..."
                    )
                    try:
                        from quantum.qaoa_solver import run_qaoa, get_qaoa_availability, QISKIT_AVAILABLE
                        from quantum.decoder import get_all_candidates, get_best_feasible, explain_route_selection
                        from quantum.telemetry import build_qaoa_telemetry

                        qaoa_avail, qaoa_msg = get_qaoa_availability()
                        st.session_state.qaoa_available = qaoa_avail

                        if qaoa_avail:
                            qaoa_result = run_qaoa(
                                qubo_data["Q"],
                                p=q_params.get("qaoa_p", 1),
                                n_shots=q_params.get("qaoa_shots", 512),
                                max_iter_opt=q_params.get("qaoa_iter", 50),
                            )
                            # Exclude qc_object from session state (not serializable)
                            qaoa_serializable = {
                                k: v for k, v in qaoa_result.items() if k != "qc_object"
                            }
                            st.session_state.qaoa_result = qaoa_serializable

                            # Decode candidates
                            candidates = get_all_candidates(
                                qaoa_result.get("probabilities", {}),
                                qubo_data["var_map"],
                                qubo_data["sub_nodes"],
                                qubo_data["sub_dist"],
                            )
                            st.session_state.qaoa_candidates = candidates
                            best_cand = get_best_feasible(candidates)
                            st.session_state.qaoa_best_candidate = best_cand

                            # Build telemetry
                            tel = build_qaoa_telemetry(qaoa_result, candidates, qubo_data["meta"])
                            st.session_state.qaoa_telemetry = tel.to_dict()
                        else:
                            st.write(f"  ⚠️ QAOA unavailable: {qaoa_msg}")
                            st.session_state.qaoa_available = False
                    except Exception as qe:
                        st.write(f"  ⚠️ QAOA execution error: {qe}")
                        import traceback
                        print(f"[QAOA ERROR] {traceback.format_exc()}")
                        st.session_state.qaoa_available = False
                else:
                    if qubo_data:
                        n_vars = qubo_data["meta"]["n_variables"]
                        st.write(
                            f"  ⏭️ QAOA skipped: problem has {n_vars} variables "
                            f"(> 16 qubit limit). SA handles full optimization."
                        )
                    st.session_state.qaoa_available = False

                # ── Step 7: Comparison (HONEST — no metric swapping) ──────────
                st.write("📊 Computing classical vs quantum comparison...")
                comparison = compute_comparison(classical_metrics, quantum_metrics)
                st.session_state.comparison_result = comparison

                # Optimization Score
                score, score_breakdown = calculate_optimization_score(quantum_metrics, classical_metrics)
                st.session_state.optimization_score = score
                st.session_state.score_breakdown = score_breakdown

                # ── Step 8: Save to run history ───────────────────────────────
                ts = datetime.datetime.now().strftime("%H:%M:%S")
                history_entry = {
                    "timestamp": ts,
                    "stops": len(stops),
                    "vehicles": fleet_size,
                    "classical_dist": classical_metrics["dist_km"],
                    "quantum_dist": quantum_metrics["dist_km"],
                    "classical_cost": classical_metrics["cost_inr"],
                    "quantum_cost": quantum_metrics["cost_inr"],
                    "classical_co2": classical_metrics["co2_kg"],
                    "quantum_co2": quantum_metrics["co2_kg"],
                    "sla_violations_classical": classical_metrics["sla_violations"],
                    "sla_violations_quantum": quantum_metrics["sla_violations"],
                    "score": score,
                    "q_runtime_s": quantum_runtime,
                    "c_runtime_s": classical_runtime,
                }
                if len(st.session_state.run_history) >= 20:
                    st.session_state.run_history.pop(0)
                st.session_state.run_history.append(history_entry)

                # ── Finalize ──────────────────────────────────────────────────
                st.session_state.solver_status = "Completed"
                st.session_state.optimization_timestamp = ts
                st.session_state.scenario_params = {
                    "mileage": mileage,
                    "fuel_price": fuel_price,
                    "emission_factor": emission_factor,
                    "traffic_multiplier": traffic_multiplier,
                    "fleet_size": fleet_size,
                    "n_iter": q_params.get("iter", 3000),
                    "cooling_rate": q_params.get("cool", 0.998),
                    "init_temp": q_params.get("temp", 100),
                }

                status.update(label="✅ Optimization Complete!", state="complete", expanded=False)
                time.sleep(0.5)
                st.rerun()

            except Exception as exc:
                st.session_state.solver_status = "Failed"
                st.error(f"❌ Optimization failed: {exc}")
                import traceback
                print(f"[Q-RouteX ERROR] {traceback.format_exc()}")
                status.update(label="❌ Optimization Failed", state="error", expanded=True)

# ──────────────────────────────────────────────────────────────────────────────
# 4. Page Routing
# ──────────────────────────────────────────────────────────────────────────────

frontend.render_header()

has_results = bool(st.session_state.get("optimized_route"))

if page == "🏠 Dashboard":
    frontend.render_dashboard()
elif page == "🗺️ Route Optimizer":
    frontend.render_optimizer_view()
elif page == "⚖️ Classical vs Quantum":
    frontend.render_comparison_view()
elif page == "⚛️ Quantum Analytics":
    frontend.render_analytics_view()
elif page == "⧛️ QUBO Explorer":
    frontend.render_qubo_explorer()
elif page == "🧬 QAOA Visualization":
    frontend.render_qaoa_visualization()
elif page == "🚛 Fleet Intelligence":
    frontend.render_fleet_view()
elif page == "🌱 Sustainability":
    frontend.render_sustainability_view()
elif page == "🔬 Scenario Simulator":
    frontend.render_scenario_simulator()
elif page == "📊 Benchmark Lab":
    frontend.render_benchmark_lab()
elif page == "📋 Results History":
    frontend.render_history_view()
elif page == "📤 Export & Reports":
    frontend.render_export_view()
elif page == "📖 Methodology":
    frontend.render_methodology_view()
else:
    st.info("Select a page from the sidebar.")
