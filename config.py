# config.py
"""
Configuration for Q-RouteX
============================
Branding, page settings, light theme CSS, and application constants.
"""
import streamlit as st

# ──────────────────────────────────────────────────────────────────────────────
# Application Constants
# ──────────────────────────────────────────────────────────────────────────────

APP_NAME = "Q-RouteX"
APP_SUBTITLE = "Quantum-Enhanced Intelligent Route Optimization for Sustainable Logistics"

CO2_EMISSION_FACTOR_DEFAULT = 2.68   # kg CO2 per litre diesel (IPCC / CPCB ref.)
DEFAULT_MILEAGE_KM_L = 12.0
DEFAULT_FUEL_PRICE_INR = 96.0
DEFAULT_AVG_SPEED_KMH = 50.0

# Navigation pages (only pages that are actually implemented)
NAV_PAGES = [
    "🏠 Dashboard",
    "🗺️ Route Optimizer",
    "⚖️ Classical vs Quantum",
    "⚛️ Quantum Analytics",
    "⧛️ QUBO Explorer",
    "🧬 QAOA Visualization",
    "🚛 Fleet Intelligence",
    "🌱 Sustainability",
    "🔬 Scenario Simulator",
    "📊 Benchmark Lab",
    "📋 Results History",
    "📤 Export & Reports",
    "📖 Methodology",
]

PAGE_CONFIG = {
    "page_title": "Q-RouteX — Quantum Logistics",
    "page_icon": "⚛️",
    "layout": "wide",
    "initial_sidebar_state": "expanded",
}

# ──────────────────────────────────────────────────────────────────────────────
# CSS Theme — Professional Light / Quantum Logistics
# ──────────────────────────────────────────────────────────────────────────────

CUSTOM_CSS = """
<style>
/* ─── Google Fonts ───────────────────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;600;700;900&family=Inter:wght@300;400;500;600;700&display=swap');

/* ─── Root Variables ─────────────────────────────────────────────────────── */
:root {
    --primary:      #0f4c8a;
    --primary-lt:   #1a6bbf;
    --accent:       #0ea5e9;
    --accent2:      #6d28d9;
    --success:      #059669;
    --warning:      #d97706;
    --danger:       #dc2626;
    --quantum:      #7c3aed;
    --bg-main:      #eef3fb;
    --bg-card:      #ffffff;
    --text-main:    #0f172a;
    --text-sub:     #475569;
    --text-muted:   #94a3b8;
    --border:       #e2e8f0;
    --border-acc:   rgba(14,165,233,0.3);
    --shadow-sm:    0 1px 6px rgba(15,76,138,0.08);
    --shadow-md:    0 4px 20px rgba(15,76,138,0.12);
    --shadow-lg:    0 8px 40px rgba(15,76,138,0.18);
}

/* ─── Global App ─────────────────────────────────────────────────────────── */
/*   Light pearl-blue background with a subtle dot-grid network pattern
     (simulates a logistics route map / quantum node network).
     Soft radial colour bursts add depth without being distracting. */
.stApp {
    background-color: #eef3fb;
    background-image:
        radial-gradient(ellipse at 15% 15%, rgba(14,165,233,0.10) 0%, transparent 55%),
        radial-gradient(ellipse at 85% 80%, rgba(109,40,217,0.08) 0%, transparent 55%),
        radial-gradient(ellipse at 55%  5%, rgba(15,76,138,0.07) 0%, transparent 45%),
        radial-gradient(circle, rgba(14,165,233,0.20) 1.2px, transparent 1.2px),
        radial-gradient(circle, rgba(109,40,217,0.11) 1px,   transparent 1px);
    background-size:
        100% 100%, 100% 100%, 100% 100%,
        30px 30px,
        60px 60px;
    background-position:
        0 0, 0 0, 0 0,
        0 0,
        15px 15px;
    color: var(--text-main);
    font-family: 'Inter', sans-serif;
}

/* ─── Main Content Area — extra top breathing room ───────────────────────── */
.block-container {
    padding-top: 2rem !important;
}

/* ─── Sidebar ────────────────────────────────────────────────────────────── */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #ffffff 0%, #f4f8ff 100%) !important;
    border-right: 1px solid var(--border);
    box-shadow: 2px 0 16px rgba(15,76,138,0.06);
}
section[data-testid="stSidebar"] > div {
    background: transparent !important;
}

/* ─── Headings ───────────────────────────────────────────────────────────── */
h1 {
    font-family: 'Orbitron', sans-serif !important;
    background: linear-gradient(135deg, #0f4c8a 0%, #0ea5e9 50%, #6d28d9 100%);
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;               /* gradient-text trick — keeps emoji colours intact */
    font-weight: 900 !important;
    letter-spacing: 1.5px !important;
    line-height: 1.3 !important;
}
h2 {
    font-family: 'Orbitron', sans-serif !important;
    background: linear-gradient(135deg, #0f4c8a 0%, #1a6bbf 100%);
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;               /* gradient-text trick — keeps emoji colours intact */
    font-weight: 700 !important;
    letter-spacing: 1px !important;
    line-height: 1.4 !important;
}
h3 {
    font-family: 'Inter', sans-serif !important;
    color: #0f172a !important;
    font-weight: 700 !important;
    /* No -webkit-text-fill-color override — lets emoji render in natural colour */
    line-height: 1.4 !important;
}
h4, h5, h6 {
    font-family: 'Inter', sans-serif !important;
    color: var(--text-sub) !important;
    font-weight: 600 !important;
    /* No -webkit-text-fill-color override — lets emoji render in natural colour */
}

/* ─── KPI / Metric Cards ─────────────────────────────────────────────────── */
div[data-testid="stMetric"] {
    background: linear-gradient(135deg, #ffffff 0%, #f5f9ff 100%);
    border-radius: 16px;
    border: 1px solid var(--border);
    border-top: 3px solid var(--accent);
    padding: 18px !important;
    box-shadow: var(--shadow-md);
    transition: all 0.3s ease;
}
div[data-testid="stMetric"]:hover {
    transform: translateY(-3px);
    box-shadow: var(--shadow-lg);
    border-top-color: var(--accent2);
}
div[data-testid="stMetricValue"] {
    color: var(--primary) !important;
    font-family: 'Orbitron', sans-serif !important;
    font-size: 22px !important;
    font-weight: 700 !important;
    -webkit-text-fill-color: var(--primary) !important;
}
div[data-testid="stMetricLabel"] {
    color: var(--text-sub) !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 11px !important;
    font-weight: 600 !important;
    text-transform: uppercase;
    letter-spacing: 1.2px;
    -webkit-text-fill-color: var(--text-sub) !important;
}
div[data-testid="stMetricDelta"] > div {
    font-family: 'Inter', sans-serif !important;
    font-size: 12px !important;
    font-weight: 600 !important;
}

/* ─── Expanders ──────────────────────────────────────────────────────────── */
div[data-testid="stExpander"] {
    background: #ffffff;
    border-radius: 12px;
    border: 1px solid var(--border);
    box-shadow: var(--shadow-sm);
    margin-bottom: 8px;
}

/* ─── Primary Button (RUN) ───────────────────────────────────────────────── */
div.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #0f4c8a 0%, #1565c0 50%, #0ea5e9 100%) !important;
    border: none !important;
    color: #ffffff !important;
    font-family: 'Orbitron', sans-serif !important;
    font-weight: 700 !important;
    font-size: 13px !important;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    border-radius: 12px !important;
    box-shadow: 0 4px 20px rgba(14,165,233,0.35) !important;
    transition: all 0.3s ease !important;
    position: relative;
    overflow: hidden;
}
div.stButton > button[kind="primary"]:hover {
    background: linear-gradient(135deg, #6d28d9 0%, #0f4c8a 100%) !important;
    box-shadow: 0 6px 28px rgba(109,40,217,0.40) !important;
    transform: translateY(-2px);
    color: #ffffff !important;
}
div.stButton > button[kind="primary"]::after {
    content: '';
    position: absolute;
    top: 0; left: -100%;
    width: 100%; height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.25), transparent);
    animation: shimmer-btn 3s infinite;
}
@keyframes shimmer-btn { 0%{left:-100%} 30%{left:100%} 100%{left:100%} }

/* ─── Secondary Buttons ──────────────────────────────────────────────────── */
div.stButton > button {
    background: #ffffff !important;
    border: 1.5px solid rgba(14,165,233,0.35) !important;
    color: var(--primary) !important;
    border-radius: 10px !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 500 !important;
    box-shadow: var(--shadow-sm) !important;
    transition: all 0.25s ease !important;
}
div.stButton > button:hover {
    background: #eff6ff !important;
    border-color: var(--accent) !important;
    color: var(--accent) !important;
    box-shadow: 0 4px 14px rgba(14,165,233,0.20) !important;
    transform: translateY(-1px);
}

/* ─── Download Buttons ───────────────────────────────────────────────────── */
div[data-testid="stDownloadButton"] > button {
    background: linear-gradient(135deg, #f3f0ff, #ede9ff) !important;
    border: 1.5px solid rgba(109,40,217,0.30) !important;
    color: var(--quantum) !important;
    font-family: 'Inter', sans-serif !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    box-shadow: 0 2px 8px rgba(109,40,217,0.10) !important;
    transition: all 0.25s ease !important;
}
div[data-testid="stDownloadButton"] > button:hover {
    background: linear-gradient(135deg, #ede9ff, #ddd6fe) !important;
    box-shadow: 0 4px 16px rgba(109,40,217,0.22) !important;
    transform: translateY(-1px);
}

/* ─── Tables ─────────────────────────────────────────────────────────────── */
div[data-testid="stDataFrame"] {
    background: #ffffff;
    border: 1px solid var(--border);
    border-radius: 12px;
    box-shadow: var(--shadow-sm);
}

/* ─── Alerts ─────────────────────────────────────────────────────────────── */
div[data-testid="stAlert"] {
    border-radius: 12px;
    font-family: 'Inter', sans-serif;
}

/* ─── Radio (Navigation) ─────────────────────────────────────────────────── */
div[data-testid="stRadio"] label {
    font-family: 'Inter', sans-serif !important;
    font-size: 13px !important;
    color: var(--text-sub) !important;
    padding: 5px 0 !important;
}
div[data-testid="stRadio"] label:hover {
    color: var(--primary) !important;
}

/* ─── Inputs ─────────────────────────────────────────────────────────────── */
div[data-testid="stTextInput"] > div > div > input,
div[data-testid="stNumberInput"] > div > div > input {
    background: #ffffff !important;
    border: 1.5px solid var(--border) !important;
    border-radius: 8px !important;
    color: var(--text-main) !important;
    font-family: 'Inter', sans-serif !important;
}
div[data-testid="stTextInput"] > div > div > input:focus,
div[data-testid="stNumberInput"] > div > div > input:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px rgba(14,165,233,0.15) !important;
}

/* ─── Selectbox ──────────────────────────────────────────────────────────── */
div[data-testid="stSelectbox"] > div > div {
    background: #ffffff !important;
    border: 1.5px solid var(--border) !important;
    border-radius: 8px !important;
    color: var(--text-main) !important;
}

/* ─── Tabs ───────────────────────────────────────────────────────────────── */
div[data-testid="stTabs"] button[data-baseweb="tab"] {
    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important;
    color: var(--text-sub) !important;
}
div[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"] {
    color: var(--primary) !important;
    border-bottom-color: var(--accent) !important;
}

/* ─── Scrollbar ──────────────────────────────────────────────────────────── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #f1f5f9; border-radius: 4px; }
::-webkit-scrollbar-thumb { background: rgba(14,165,233,0.35); border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: rgba(15,76,138,0.5); }

/* ─── Dividers ───────────────────────────────────────────────────────────── */
hr { border: none; border-top: 1px solid var(--border); margin: 16px 0; }

/* ─── Page content ───────────────────────────────────────────────────────── */
.block-container {
    background: transparent !important;
    padding-top: 1.5rem !important;
}

/* ─── General text ───────────────────────────────────────────────────────── */
.stMarkdown p, .stMarkdown li {
    color: var(--text-main) !important;
    font-family: 'Inter', sans-serif !important;
}
em { color: var(--text-sub) !important; }
div[data-testid="stCaptionContainer"] p { color: var(--text-muted) !important; }

/* ─── Code blocks ────────────────────────────────────────────────────────── */
code {
    background: #f1f5f9 !important;
    color: #0f4c8a !important;
    border: 1px solid var(--border) !important;
    border-radius: 6px !important;
    font-size: 13px !important;
}
pre { background: #f8faff !important; border: 1px solid var(--border) !important; border-radius: 10px !important; }
pre code { background: transparent !important; border: none !important; color: #0f172a !important; }

/* ─── Status containers ──────────────────────────────────────────────────── */
div[data-testid="stStatusContainer"] {
    background: #ffffff !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
}

/* ─── Toggles ────────────────────────────────────────────────────────────── */
div[data-testid="stToggle"] label span {
    color: var(--text-main) !important;
    font-family: 'Inter', sans-serif !important;
}

/* ─── Status Pills ───────────────────────────────────────────────────────── */
.pill-success { background:#d1fae5; border:1.5px solid #059669; color:#065f46; padding:5px 14px; border-radius:20px; font-size:12px; font-family:'Inter',sans-serif; font-weight:600; display:inline-block; }
.pill-warn    { background:#fef3c7; border:1.5px solid #d97706; color:#92400e; padding:5px 14px; border-radius:20px; font-size:12px; font-family:'Inter',sans-serif; font-weight:600; display:inline-block; }
.pill-error   { background:#fee2e2; border:1.5px solid #dc2626; color:#991b1b; padding:5px 14px; border-radius:20px; font-size:12px; font-family:'Inter',sans-serif; font-weight:600; display:inline-block; }
.pill-idle    { background:#f1f5f9; border:1.5px solid #94a3b8; color:#475569; padding:5px 14px; border-radius:20px; font-size:12px; font-family:'Inter',sans-serif; font-weight:600; display:inline-block; }
.pill-quantum { background:#ede9fe; border:1.5px solid #6d28d9; color:#4c1d95; padding:5px 14px; border-radius:20px; font-size:12px; font-family:'Inter',sans-serif; font-weight:600; display:inline-block; }

/* ─── Comparison badges ──────────────────────────────────────────────────── */
.badge-win  { background:#d1fae5; color:#065f46; border:1.5px solid #059669; padding:2px 10px; border-radius:8px; font-size:11px; font-weight:700; display:inline-block; }
.badge-lose { background:#fee2e2; color:#991b1b; border:1.5px solid #dc2626; padding:2px 10px; border-radius:8px; font-size:11px; font-weight:700; display:inline-block; }
.badge-tie  { background:#f1f5f9; color:#475569; border:1.5px solid #94a3b8; padding:2px 10px; border-radius:8px; font-size:11px; font-weight:700; display:inline-block; }

/* ─── Savings / impact cards ─────────────────────────────────────────────── */
.savings-card {
    background: linear-gradient(135deg, #f0fdf4, #dcfce7);
    border: 1.5px solid rgba(5,150,105,0.25);
    border-radius: 16px;
    padding: 20px;
    text-align: center;
    transition: all 0.3s ease;
    box-shadow: var(--shadow-sm);
}
.savings-card:hover { transform: translateY(-3px); box-shadow: var(--shadow-md); }
.savings-value { font-family: 'Orbitron', sans-serif; font-size: 22px; font-weight: 700; color: #065f46; }
.savings-label { font-family: 'Inter', sans-serif; font-size: 10px; color: var(--text-sub); text-transform: uppercase; letter-spacing: 1.5px; margin-top: 4px; }

/* ─── Info / metric rows ─────────────────────────────────────────────────── */
.metric-row {
    display: flex;
    align-items: center;
    padding: 10px 16px;
    border-radius: 10px;
    margin: 4px 0;
    font-family: 'Inter', sans-serif;
    background: #ffffff;
    border: 1px solid var(--border);
    box-shadow: var(--shadow-sm);
    gap: 12px;
}
.metric-row:hover { background: #eff6ff; border-color: var(--border-acc); }
</style>
"""


def load_css():
    """Inject custom CSS into the Streamlit app."""
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
