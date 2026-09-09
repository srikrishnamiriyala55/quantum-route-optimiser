# quantum/circuit.py
"""
QAOA Circuit Visualization Helpers
=====================================
Provides circuit statistics and Plotly-based circuit diagrams.
Works with or without Qiskit being available.
"""

import numpy as np
from typing import Dict, List, Optional, Any
import plotly.graph_objects as go


QISKIT_AVAILABLE = False
try:
    from qiskit import QuantumCircuit
    from qiskit import transpile
    from qiskit_aer import AerSimulator
    QISKIT_AVAILABLE = True
except ImportError:
    pass


def get_circuit_stats(circuit_info: Dict, p: int = 1, n_qubits: int = 0) -> Dict:
    """
    Extract key statistics from a QAOA circuit info dict.

    Args:
        circuit_info : Dict from qaoa_solver.run_qaoa() circuit_info key
        p            : QAOA layers (p)
        n_qubits     : Number of qubits

    Returns:
        stats dict with human-readable metrics
    """
    if not circuit_info:
        return {
            "n_qubits": n_qubits,
            "p_layers": p,
            "circuit_depth": "N/A",
            "n_parameters": 2 * p,
            "gate_counts": {},
            "rzz_gates": 0,
            "rx_gates": 0,
            "h_gates": 0,
        }

    gate_counts = circuit_info.get("gate_counts", {})
    return {
        "n_qubits": circuit_info.get("n_qubits", n_qubits),
        "p_layers": circuit_info.get("p_layers", p),
        "circuit_depth": circuit_info.get("depth_before_transpile", "N/A"),
        "n_parameters": circuit_info.get("n_parameters", 2 * p),
        "gate_counts": gate_counts,
        "rzz_gates": gate_counts.get("rzz", 0),
        "rx_gates": gate_counts.get("rx", 0),
        "h_gates": gate_counts.get("h", 0),
        "rz_gates": gate_counts.get("rz", 0),
        "measure_gates": gate_counts.get("measure", 0),
    }


def build_circuit_diagram_plotly(
    n_qubits: int,
    p_layers: int,
    h: Optional[np.ndarray] = None,
    J: Optional[np.ndarray] = None,
    gamma_opt: Optional[List[float]] = None,
    beta_opt: Optional[List[float]] = None,
) -> go.Figure:
    """
    Build a Plotly-based visual representation of the QAOA circuit.
    This creates a schematic diagram showing the gate structure,
    NOT a 1:1 wire diagram (which would be too complex for large circuits).

    Args:
        n_qubits  : Number of qubits
        p_layers  : QAOA repetition count
        h         : Ising linear terms (to show active qubits)
        J         : Ising coupling matrix (to show connections)
        gamma_opt : Optimized gamma values
        beta_opt  : Optimized beta values

    Returns:
        Plotly Figure with circuit schematic
    """
    fig = go.Figure()

    # ── Layout parameters ─────────────────────────────────────────────────────
    qubit_y = list(range(n_qubits))
    max_qubits_shown = min(n_qubits, 12)  # cap for readability
    shown_qubits = list(range(max_qubits_shown))

    # Column positions: |+⟩ init | p layers of (H_C + H_B) | Measure
    col_init    = 0.5
    col_measure = 0.5 + 1 + p_layers * 2 + 0.5

    circuit_width  = col_measure + 0.5
    circuit_height = max_qubits_shown

    # ── Wire lines ────────────────────────────────────────────────────────────
    for q in shown_qubits:
        fig.add_shape(
            type="line",
            x0=0, x1=circuit_width, y0=q, y1=q,
            line=dict(color="#334155", width=1.5),
        )

    # ── Qubit labels ──────────────────────────────────────────────────────────
    for q in shown_qubits:
        fig.add_annotation(
            x=-0.3, y=q,
            text=f"q[{q}]",
            showarrow=False,
            font=dict(family="monospace", size=10, color="#64748b"),
            xanchor="right",
        )

    # ── Initial H gate (|+⟩ superposition) ───────────────────────────────────
    for q in shown_qubits:
        _add_gate_box(fig, col_init, q, "H", "#0ea5e9")

    # ── QAOA layers ───────────────────────────────────────────────────────────
    for layer in range(p_layers):
        col_cost  = col_init + 1 + layer * 2
        col_mixer = col_cost + 1

        g_val = f"γ{layer}" if not gamma_opt else f"γ={gamma_opt[layer]:.2f}"
        b_val = f"β{layer}" if not beta_opt  else f"β={beta_opt[layer]:.2f}"

        # Cost Hamiltonian block
        for q in shown_qubits:
            _add_gate_box(fig, col_cost, q, f"RZ\n{g_val}", "#7c3aed", width=0.55)

        # ZZ coupling lines (show first few to avoid clutter)
        n_couplings_shown = 0
        if J is not None:
            for i in range(min(max_qubits_shown, J.shape[0])):
                for j in range(i + 1, min(max_qubits_shown, J.shape[1])):
                    if abs(J[i, j]) > 1e-10 and n_couplings_shown < 6:
                        fig.add_shape(
                            type="line",
                            x0=col_cost, x1=col_cost, y0=i, y1=j,
                            line=dict(color="#7c3aed", width=2, dash="dot"),
                        )
                        n_couplings_shown += 1

        # Mixer Hamiltonian block
        for q in shown_qubits:
            _add_gate_box(fig, col_mixer, q, f"RX\n{b_val}", "#0ea5e9", width=0.55)

        # Layer label
        fig.add_annotation(
            x=(col_cost + col_mixer) / 2,
            y=max_qubits_shown + 0.3,
            text=f"Layer {layer + 1}",
            showarrow=False,
            font=dict(family="Inter", size=10, color="#475569"),
        )

    # ── Measurement boxes ─────────────────────────────────────────────────────
    for q in shown_qubits:
        _add_gate_box(fig, col_measure, q, "M", "#059669")

    if max_qubits_shown < n_qubits:
        fig.add_annotation(
            x=col_measure, y=-0.8,
            text=f"(+{n_qubits - max_qubits_shown} more qubits)",
            showarrow=False,
            font=dict(family="Inter", size=9, color="#94a3b8"),
        )

    # ── Layer separator lines ─────────────────────────────────────────────────
    for layer in range(p_layers):
        x_sep = col_init + 0.5 + layer * 2
        fig.add_shape(
            type="line",
            x0=x_sep, x1=x_sep,
            y0=-0.5, y1=max_qubits_shown - 0.5,
            line=dict(color="#e2e8f0", width=1, dash="dash"),
        )

    # ── Labels ────────────────────────────────────────────────────────────────
    for label_x, label_text, label_color in [
        (col_init,    "|+⟩ Init", "#0ea5e9"),
        (col_measure, "Measure",  "#059669"),
    ]:
        fig.add_annotation(
            x=label_x, y=max_qubits_shown + 0.3,
            text=label_text, showarrow=False,
            font=dict(family="Inter", size=10, color=label_color),
        )

    # ── Figure layout ─────────────────────────────────────────────────────────
    height = max(250, max_qubits_shown * 45 + 80)
    fig.update_layout(
        paper_bgcolor="rgba(255,255,255,0)",
        plot_bgcolor="#f8faff",
        xaxis=dict(
            showgrid=False, showticklabels=False, zeroline=False,
            range=[-0.8, circuit_width + 0.3],
        ),
        yaxis=dict(
            showgrid=False, showticklabels=False, zeroline=False,
            range=[-1, max_qubits_shown + 0.8],
            autorange="reversed",
        ),
        height=height,
        margin=dict(l=60, r=20, t=30, b=20),
        showlegend=False,
    )

    return fig


def _add_gate_box(fig: go.Figure, x: float, y: float, label: str,
                  color: str = "#0ea5e9", width: float = 0.4) -> None:
    """Add a rectangular gate box to a Plotly figure."""
    hw = width / 2
    hh = 0.32

    # Box
    fig.add_shape(
        type="rect",
        x0=x - hw, x1=x + hw, y0=y - hh, y1=y + hh,
        fillcolor=color,
        line=dict(color=color, width=1.5),
        opacity=0.85,
    )
    # Label (may include newline for params)
    display_label = label.split("\n")[0]  # first line only for compact display
    fig.add_annotation(
        x=x, y=y,
        text=display_label,
        showarrow=False,
        font=dict(family="monospace", size=9, color="white"),
    )


def build_probability_histogram(
    probabilities: Dict[str, float],
    top_n: int = 20,
    highlight_bitstring: Optional[str] = None,
) -> go.Figure:
    """
    Build a Plotly bar chart of QAOA measurement probabilities.

    Args:
        probabilities     : {bitstring: probability} sorted by probability
        top_n             : Number of top bitstrings to show
        highlight_bitstring: Bitstring to highlight as "best"

    Returns:
        Plotly Figure
    """
    items = sorted(probabilities.items(), key=lambda x: -x[1])[:top_n]
    if not items:
        fig = go.Figure()
        fig.add_annotation(text="No measurement data", x=0.5, y=0.5, showarrow=False)
        return fig

    labels = [b[:8] + "…" if len(b) > 8 else b for b, _ in items]
    probs  = [p * 100 for _, p in items]
    colors = []
    for b, _ in items:
        if highlight_bitstring and b == highlight_bitstring:
            colors.append("#059669")  # green for best
        else:
            colors.append("#6d28d9")  # purple for others

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=labels,
        y=probs,
        marker_color=colors,
        marker_line=dict(color="rgba(255,255,255,0.3)", width=0.5),
        text=[f"{p:.1f}%" for p in probs],
        textposition="outside",
        textfont=dict(size=9, color="#1e293b"),
    ))

    if highlight_bitstring:
        best_short = highlight_bitstring[:8] + "…" if len(highlight_bitstring) > 8 else highlight_bitstring
        if best_short in labels:
            fig.add_annotation(
                x=best_short, y=max(probs) * 1.15,
                text="⭐ Best",
                showarrow=False,
                font=dict(color="#059669", size=11, family="Inter"),
            )

    fig.update_layout(
        paper_bgcolor="rgba(255,255,255,0)",
        plot_bgcolor="#f8faff",
        xaxis=dict(
            title="Quantum State (bitstring)",
            tickfont=dict(family="monospace", size=9, color="#475569"),
            gridcolor="rgba(15,76,138,0.06)",
            title_font=dict(color="#1e293b"),
        ),
        yaxis=dict(
            title="Measurement Probability (%)",
            gridcolor="rgba(15,76,138,0.08)",
            tickfont=dict(color="#475569"),
            title_font=dict(color="#1e293b"),
        ),
        font=dict(family="Inter", color="#1e293b"),
        margin=dict(l=0, r=0, t=30, b=0),
        height=340,
    )
    return fig


def build_energy_convergence_plotly(energy_landscape: List[float]) -> go.Figure:
    """
    Build a Plotly chart of QAOA parameter optimization convergence.
    Shows expected energy vs optimizer iteration.
    """
    if not energy_landscape:
        fig = go.Figure()
        fig.add_annotation(text="No convergence data", x=0.5, y=0.5, showarrow=False)
        return fig

    iters = list(range(len(energy_landscape)))
    best_so_far = []
    current_best = energy_landscape[0]
    for e in energy_landscape:
        if e < current_best:
            current_best = e
        best_so_far.append(current_best)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=iters, y=energy_landscape,
        mode="lines",
        name="QAOA Cost (per iteration)",
        line=dict(color="rgba(109,40,217,0.4)", width=1.5),
    ))
    fig.add_trace(go.Scatter(
        x=iters, y=best_so_far,
        mode="lines",
        name="Best-so-far",
        line=dict(color="#6d28d9", width=2.5),
    ))
    fig.add_annotation(
        x=iters[-1], y=best_so_far[-1],
        text=f"Final: {best_so_far[-1]:.3f}",
        showarrow=True, arrowhead=2,
        font=dict(color="#059669", size=11),
        arrowcolor="#059669",
    )

    fig.update_layout(
        paper_bgcolor="rgba(255,255,255,0)",
        plot_bgcolor="#f8faff",
        xaxis=dict(
            title="Optimizer Iteration",
            gridcolor="rgba(15,76,138,0.06)",
            tickfont=dict(color="#475569"),
            title_font=dict(color="#1e293b"),
        ),
        yaxis=dict(
            title="Expected QAOA Energy",
            gridcolor="rgba(15,76,138,0.08)",
            tickfont=dict(color="#475569"),
            title_font=dict(color="#1e293b"),
        ),
        legend=dict(bgcolor="rgba(255,255,255,0.9)", font=dict(color="#1e293b")),
        font=dict(family="Inter", color="#1e293b"),
        margin=dict(l=0, r=0, t=10, b=0),
        height=300,
    )
    return fig
