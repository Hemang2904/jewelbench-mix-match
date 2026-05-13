import streamlit as st
import fal_client
import os
import time
from prompts import (
    build_combine_prompt,
    build_target_summary,
    build_correction_addendum,
)
from preprocessing import (
    strip_background_to_white,
    strip_url_to_white,
    enrich_description,
    validate_design,
    extract_bom,
)
from pricing import (
    get_gold_rates,
    load_diamond_rates,
    compute_costs,
)
import hashlib
import datetime
import json as _json

_ENV_VALIDATION_THRESHOLD = int(os.environ.get("VALIDATION_THRESHOLD", "80"))
_ENV_MAX_VALIDATION_TRIES = int(os.environ.get("MAX_VALIDATION_TRIES", "3"))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    if hasattr(st, "secrets") and "FAL_KEY" in st.secrets:
        os.environ["FAL_KEY"] = st.secrets["FAL_KEY"]
except Exception:
    pass

if not os.environ.get("FAL_KEY"):
    try:
        fal_key = st.secrets.get("FAL_KEY", "")
        if fal_key:
            os.environ["FAL_KEY"] = fal_key
    except Exception:
        pass

st.set_page_config(
    page_title="JewelBench — Component Composer",
    page_icon="https://jewelbench.ai/wp-content/uploads/2025/05/jewelbench_logo.svg",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Space+Grotesk:wght@400;500;600;700&family=Orbitron:wght@500;600;700&display=swap');

:root {
    --bg-deep: #FFFFFF;
    --bg-mid: #F8FAFC;
    --bg-elevated: #FFFFFF;
    --glass: rgba(255, 255, 255, 0.85);
    --glass-strong: rgba(255, 255, 255, 0.96);
    --border: rgba(56, 189, 248, 0.20);
    --border-active: rgba(2, 132, 199, 0.55);
    --cyan: #0EA5E9;
    --cyan-soft: #7DD3FC;
    --cyan-deep: #0369A1;
    --blue: #38BDF8;
    --blue-deep: #0284C7;
    --purple: #6366F1;
    --green: #22D67A;
    --amber: #FFB547;
    --text-primary: #0F172A;
    --text-secondary: #475569;
    --text-muted: #94A3B8;
    --glow-cyan: 0 4px 20px rgba(56, 189, 248, 0.20);
    --glow-soft: 0 12px 40px rgba(56, 189, 248, 0.10);
    --gold: var(--cyan);
    --gold-light: var(--cyan-soft);
    --gold-dark: var(--cyan-deep);
    --bg-primary: var(--bg-deep);
    --bg-card: var(--glass);
    --bg-card-hover: var(--glass-strong);
    --accent-blue: var(--blue);
    --accent-purple: var(--purple);
    --glow: var(--glow-cyan);
}

html, body, .stApp {
    background:
        radial-gradient(1200px 700px at 15% -10%, rgba(186, 230, 253, 0.55), transparent 60%),
        radial-gradient(900px 600px at 100% 110%, rgba(199, 210, 254, 0.40), transparent 55%),
        radial-gradient(700px 500px at 50% 50%, rgba(56, 189, 248, 0.06), transparent 70%),
        linear-gradient(180deg, #FFFFFF 0%, #F0F9FF 60%, #FFFFFF 100%) !important;
    color: var(--text-primary);
    font-family: 'Inter', sans-serif;
}
.stApp::before {
    content: "";
    position: fixed;
    inset: 0;
    pointer-events: none;
    background-image:
        linear-gradient(rgba(56, 189, 248, 0.06) 1px, transparent 1px),
        linear-gradient(90deg, rgba(56, 189, 248, 0.06) 1px, transparent 1px);
    background-size: 56px 56px;
    mask-image: radial-gradient(ellipse at center, black 30%, transparent 75%);
    animation: gridDrift 40s linear infinite;
    z-index: 0;
}
@keyframes gridDrift {
    0% { background-position: 0 0, 0 0; }
    100% { background-position: 56px 56px, 56px 56px; }
}
.stApp > div { position: relative; z-index: 1; }

#MainMenu, footer, header {visibility: hidden;}
.stDeployButton {display: none;}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #F0F9FF 0%, #FFFFFF 100%) !important;
    border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] .stMarkdown h3 {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 2.5px;
    text-transform: uppercase;
    color: var(--cyan-deep);
    margin-top: 1.4rem;
    margin-bottom: 0.6rem;
}
.sidebar-key-ok {
    display: flex; align-items: center; gap: 8px;
    padding: 8px 12px; border-radius: 10px;
    background: rgba(34, 214, 122, 0.10);
    border: 1px solid rgba(34, 214, 122, 0.35);
    font-size: 0.82rem; font-weight: 600; color: #15803d;
    margin-bottom: 0.8rem;
}
.sidebar-key-err {
    display: flex; align-items: center; gap: 8px;
    padding: 8px 12px; border-radius: 10px;
    background: rgba(239, 68, 68, 0.08);
    border: 1px solid rgba(239, 68, 68, 0.30);
    font-size: 0.82rem; font-weight: 600; color: #b91c1c;
    margin-bottom: 0.8rem;
}
.sidebar-stat {
    display: flex; justify-content: space-between; align-items: center;
    padding: 5px 0;
    border-bottom: 1px solid rgba(56, 189, 248, 0.12);
    font-size: 0.82rem; color: var(--text-secondary);
}
.sidebar-stat-val {
    font-weight: 600; color: var(--text-primary);
    font-family: 'Space Grotesk', sans-serif;
}

/* ── Header ── */
.jb-header { text-align: center; padding: 2.4rem 0 1rem; position: relative; }
.jb-header::after {
    content: '';
    position: absolute; bottom: 0; left: 50%; transform: translateX(-50%);
    width: 180px; height: 2px;
    background: linear-gradient(90deg, transparent, var(--cyan), transparent);
    box-shadow: 0 0 14px rgba(56, 189, 248, 0.45);
}
.jb-logo-img {
    max-height: 64px; width: auto; margin-bottom: 0.5rem;
    filter: drop-shadow(0 2px 10px rgba(56, 189, 248, 0.18));
    animation: logoPulse 4s ease-in-out infinite;
}
@keyframes logoPulse {
    0%, 100% { filter: drop-shadow(0 2px 10px rgba(56, 189, 248, 0.18)); }
    50%       { filter: drop-shadow(0 4px 18px rgba(56, 189, 248, 0.35)); }
}
.jb-tagline {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.95rem; color: var(--cyan-deep);
    font-weight: 500; letter-spacing: 5px; text-transform: uppercase;
}

/* ── Step Indicators ── */
.step-container { display: flex; justify-content: center; gap: 2.5rem; margin: 2rem 0; padding: 1.2rem 0; }
.step-item { display: flex; align-items: center; gap: 0.75rem; opacity: 0.45; transition: all 0.4s cubic-bezier(.2,.8,.2,1); }
.step-item.active { opacity: 1; }
.step-number {
    width: 38px; height: 38px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-weight: 700; font-family: 'Orbitron', sans-serif; font-size: 0.85rem;
    border: 1.5px solid rgba(56, 189, 248, 0.30); color: var(--text-muted);
    background: #FFFFFF;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
    transition: all 0.4s cubic-bezier(.2,.8,.2,1);
}
.step-item.active .step-number {
    border-color: var(--cyan); color: #FFFFFF;
    background: linear-gradient(135deg, var(--blue) 0%, var(--blue-deep) 100%);
    box-shadow: 0 4px 14px rgba(56, 189, 248, 0.45);
    transform: scale(1.05);
}
.step-item.done .step-number {
    border-color: var(--green); color: #FFFFFF;
    background: linear-gradient(135deg, #22D67A 0%, #16a34a 100%);
    box-shadow: 0 4px 14px rgba(34, 214, 122, 0.35);
}
.step-label { font-family: 'Space Grotesk', sans-serif; font-size: 0.85rem; font-weight: 500; color: var(--text-muted); letter-spacing: 0.5px; }
.step-item.active .step-label, .step-item.done .step-label { color: var(--text-primary); }
.step-connector {
    width: 70px; height: 1.5px;
    background: linear-gradient(90deg, rgba(56, 189, 248, 0.12), rgba(56, 189, 248, 0.50), rgba(56, 189, 248, 0.12));
    align-self: center;
}

/* ── Section Titles ── */
.section-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.55rem; margin: 2.2rem 0 0.4rem;
    font-weight: 600; letter-spacing: -0.01em; color: var(--text-primary);
}
.section-subtitle { font-size: 0.88rem; color: var(--text-secondary); margin-bottom: 1.4rem; line-height: 1.6; }

/* ── Reference cards via native container border ── */
div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlockBorderWrapper"] {
    border-color: var(--border) !important;
    border-radius: 16px !important;
    background: #FFFFFF !important;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04), 0 4px 20px rgba(56, 189, 248, 0.06) !important;
    transition: all 0.35s cubic-bezier(.2,.8,.2,1) !important;
}
div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlockBorderWrapper"]:hover {
    border-color: var(--border-active) !important;
    box-shadow: 0 8px 32px rgba(56, 189, 248, 0.18) !important;
    transform: translateY(-1px);
}

/* ── Card Badge ── */
.card-badge {
    display: inline-flex; align-items: center; gap: 6px;
    background: linear-gradient(135deg, rgba(56, 189, 248, 0.10), rgba(99, 102, 241, 0.08));
    border: 1px solid rgba(56, 189, 248, 0.30); border-radius: 20px;
    padding: 4px 14px;
    font-family: 'Space Grotesk', sans-serif; font-size: 0.72rem;
    color: var(--cyan-deep); font-weight: 600; letter-spacing: 1.5px; text-transform: uppercase;
    margin-bottom: 0.5rem;
}

/* ── Spec grid ── */
.spec-card-label {
    font-family: 'Space Grotesk', sans-serif; font-size: 0.7rem;
    color: var(--cyan-deep); text-transform: uppercase;
    letter-spacing: 2.5px; font-weight: 700; margin-bottom: 0.6rem;
}

/* ── Pipeline Steps ── */
.pipeline-wrap {
    display: flex; gap: 0; margin: 1rem 0 1.6rem;
    border-radius: 16px; overflow: hidden;
    border: 1px solid var(--border);
    box-shadow: var(--glow-soft);
}
.pipeline-step {
    flex: 1; padding: 1rem 1.1rem; background: #FFFFFF;
    border-right: 1px solid var(--border);
    position: relative; text-align: center;
}
.pipeline-step:last-child { border-right: none; }
.pipeline-step:hover { background: rgba(240, 249, 255, 0.85); }
.pipeline-num {
    width: 28px; height: 28px; border-radius: 50%;
    background: linear-gradient(135deg, var(--blue), var(--blue-deep));
    color: #fff; display: inline-flex; align-items: center; justify-content: center;
    font-family: 'Orbitron', sans-serif; font-size: 0.72rem; font-weight: 700;
    margin-bottom: 0.5rem; box-shadow: 0 2px 10px rgba(56, 189, 248, 0.35);
}
.pipeline-icon { font-size: 1.4rem; display: block; margin-bottom: 0.25rem; }
.pipeline-label {
    font-family: 'Space Grotesk', sans-serif; font-size: 0.75rem;
    font-weight: 600; color: var(--text-primary); display: block;
    margin-bottom: 0.25rem;
}
.pipeline-model {
    font-size: 0.65rem; color: var(--text-muted);
    font-family: 'Inter', sans-serif;
}

/* ── Pre-flight ── */
.preflight-wrap {
    background: rgba(240, 249, 255, 0.6);
    border: 1px solid var(--border); border-radius: 14px;
    padding: 1rem 1.4rem; margin-bottom: 1.2rem;
}
.preflight-title {
    font-family: 'Space Grotesk', sans-serif; font-size: 0.72rem;
    font-weight: 700; letter-spacing: 2px; text-transform: uppercase;
    color: var(--cyan-deep); margin-bottom: 0.6rem;
}
.preflight-row {
    display: flex; align-items: center; gap: 8px;
    font-size: 0.83rem; color: var(--text-secondary);
    padding: 3px 0;
}
.preflight-ok { color: #16a34a; font-weight: 700; }
.preflight-no { color: #94a3b8; }

/* ── Score Metric ── */
.score-block {
    padding: 1.4rem 2rem; border-radius: 20px;
    background: linear-gradient(135deg, rgba(56, 189, 248, 0.06), rgba(99, 102, 241, 0.04));
    border: 1px solid var(--border);
    display: flex; align-items: center; gap: 2.2rem; flex-wrap: wrap;
    margin-bottom: 1.2rem;
    box-shadow: var(--glow-soft);
}
.score-ring-wrap { position: relative; width: 100px; height: 100px; flex-shrink: 0; }
.score-ring-wrap svg { transform: rotate(-90deg); }
.score-ring-center {
    position: absolute; inset: 0;
    display: flex; flex-direction: column; align-items: center; justify-content: center;
}
.score-ring-num {
    font-family: 'Orbitron', sans-serif; font-size: 1.6rem; font-weight: 700; line-height: 1;
}
.score-ring-num.pass { color: var(--green); }
.score-ring-num.warn { color: var(--amber); }
.score-ring-pct { font-size: 0.65rem; color: var(--text-muted); letter-spacing: 1px; }
.score-label { font-size: 0.72rem; color: var(--text-muted); letter-spacing: 2px; text-transform: uppercase; font-family: 'Space Grotesk', sans-serif; margin-bottom: 4px; }
.score-status-title { font-family: 'Space Grotesk', sans-serif; font-size: 1.05rem; font-weight: 600; color: var(--text-primary); }
.score-status-sub { font-size: 0.83rem; color: var(--text-secondary); margin-top: 4px; }
.score-badge {
    display: inline-block; padding: 4px 14px; border-radius: 20px;
    font-size: 0.72rem; font-weight: 700; letter-spacing: 1.5px; text-transform: uppercase;
    font-family: 'Space Grotesk', sans-serif; margin-top: 10px;
}
.score-badge.pass { background: rgba(34,214,122,0.12); border: 1px solid rgba(34,214,122,0.40); color: #15803d; }
.score-badge.warn { background: rgba(255,181,71,0.12); border: 1px solid rgba(255,181,71,0.40); color: #92400e; }

/* ── Result Gallery ── */
.result-card {
    background: #FFFFFF; border: 1px solid var(--border); border-radius: 18px;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04), 0 4px 20px rgba(56, 189, 248, 0.06);
    transition: all 0.4s cubic-bezier(.2,.8,.2,1); overflow: hidden;
    position: relative;
}
.result-card:hover {
    border-color: var(--cyan); box-shadow: 0 12px 40px rgba(56, 189, 248, 0.20);
    transform: translateY(-4px);
}
.result-card::after {
    content: ''; position: absolute; top: 0; left: -100%;
    width: 60%; height: 100%;
    background: linear-gradient(120deg, transparent, rgba(255,255,255,0.22), transparent);
    transform: skewX(-20deg);
    transition: left 0.6s ease;
    pointer-events: none;
}
.result-card:hover::after { left: 140%; }
.result-label {
    padding: 0.85rem 1.1rem; display: flex; justify-content: space-between; align-items: center;
    border-top: 1px solid var(--border); background: rgba(240, 249, 255, 0.6);
}
.result-label span { font-family: 'Space Grotesk', sans-serif; font-size: 0.85rem; color: var(--text-secondary); font-weight: 500; }

/* ── View Placeholder ── */
.view-placeholder {
    aspect-ratio: 1; min-height: 160px;
    background: linear-gradient(135deg, rgba(240, 249, 255, 0.8), rgba(224, 242, 254, 0.5));
    border: 1.5px dashed rgba(56, 189, 248, 0.35); border-radius: 14px;
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    gap: 8px; color: var(--text-muted); font-size: 0.8rem;
    font-family: 'Space Grotesk', sans-serif;
    transition: all 0.3s;
}
.view-placeholder:hover {
    border-color: var(--cyan); background: rgba(186, 230, 253, 0.20);
    color: var(--cyan-deep);
}
.view-placeholder-icon { font-size: 1.8rem; opacity: 0.5; }

/* ── Buttons ── */
.stButton > button {
    background: linear-gradient(135deg, var(--blue) 0%, var(--blue-deep) 100%) !important;
    color: #FFFFFF !important; border: none !important;
    padding: 0.9rem 2.5rem !important;
    font-family: 'Space Grotesk', sans-serif !important; font-size: 0.95rem !important;
    font-weight: 700 !important; border-radius: 14px !important;
    letter-spacing: 1.2px !important; text-transform: uppercase !important;
    transition: all 0.3s cubic-bezier(.2,.8,.2,1) !important;
    box-shadow: 0 6px 18px rgba(56, 189, 248, 0.32), inset 0 0 16px rgba(255,255,255,0.18) !important;
    position: relative; overflow: hidden;
}
.stButton > button::after {
    content: ''; position: absolute; top: 0; left: -75%;
    width: 50%; height: 100%;
    background: linear-gradient(120deg, transparent, rgba(255,255,255,0.3), transparent);
    transform: skewX(-20deg); transition: left 0.6s ease;
}
.stButton > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 10px 28px rgba(56, 189, 248, 0.50), inset 0 0 22px rgba(255,255,255,0.25) !important;
}
.stButton > button:hover::after { left: 130%; }
.stButton > button:active { transform: translateY(0); }
button[kind="primary"], button[kind="primaryFormSubmit"] {
    animation: ctaPulse 2.4s ease-in-out infinite;
}
@keyframes ctaPulse {
    0%, 100% { box-shadow: 0 6px 18px rgba(56, 189, 248, 0.32), inset 0 0 16px rgba(255,255,255,0.18); }
    50%       { box-shadow: 0 10px 32px rgba(56, 189, 248, 0.55), inset 0 0 22px rgba(255,255,255,0.25); }
}

/* ── Inputs ── */
.stTextArea textarea, .stTextInput input {
    background: #FFFFFF !important; border: 1px solid rgba(148, 163, 184, 0.30) !important;
    border-radius: 12px !important; color: var(--text-primary) !important;
    font-family: 'Inter', sans-serif !important; padding: 0.85rem !important;
    transition: all 0.3s cubic-bezier(.2,.8,.2,1) !important;
}
.stTextArea textarea:focus, .stTextInput input:focus {
    border-color: var(--cyan) !important;
    box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.16), 0 0 18px rgba(56, 189, 248, 0.12) !important;
    outline: none !important;
}
.stSelectbox > div > div {
    background: #FFFFFF !important; border: 1px solid rgba(148, 163, 184, 0.30) !important;
    border-radius: 12px !important; color: var(--text-primary) !important;
}
div[data-testid="stFileUploader"] {
    background: rgba(240, 249, 255, 0.55);
    border: 1.5px dashed rgba(56, 189, 248, 0.40); border-radius: 14px;
    padding: 0.6rem; transition: all 0.4s cubic-bezier(.2,.8,.2,1);
}
div[data-testid="stFileUploader"]:hover {
    border-color: var(--cyan); background: rgba(186, 230, 253, 0.20);
    box-shadow: var(--glow-cyan);
}
div[data-testid="stFileUploader"] * { color: var(--text-secondary) !important; }
.stSlider > div > div > div { background: rgba(56, 189, 248, 0.22) !important; }
.stSlider > div > div > div > div {
    background: linear-gradient(135deg, var(--cyan), var(--blue-deep)) !important;
    box-shadow: 0 0 12px rgba(56, 189, 248, 0.45) !important;
}
.stProgress > div > div > div {
    background: linear-gradient(90deg, var(--cyan), var(--blue-deep), var(--purple)) !important;
    box-shadow: 0 0 10px rgba(56, 189, 248, 0.40);
}
.stDivider { border-color: var(--border) !important; }

/* ── st.status container ── */
div[data-testid="stStatusContainer"] {
    border-color: var(--border) !important; border-radius: 14px !important;
    background: rgba(240, 249, 255, 0.5) !important;
}

/* ── st.metric ── */
[data-testid="stMetric"] {
    background: #FFFFFF; border: 1px solid var(--border);
    border-radius: 14px; padding: 1rem 1.2rem !important;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
}
[data-testid="stMetricLabel"] { font-family: 'Space Grotesk', sans-serif !important; font-size: 0.72rem !important; font-weight: 700 !important; letter-spacing: 1.5px !important; text-transform: uppercase !important; color: var(--cyan-deep) !important; }
[data-testid="stMetricValue"] { font-family: 'Space Grotesk', sans-serif !important; font-size: 1.6rem !important; font-weight: 700 !important; color: var(--text-primary) !important; }

/* ── BOM ── */
.bom-grand-total {
    padding: 18px 22px; border-radius: 14px;
    background: linear-gradient(135deg, rgba(14,165,233,0.12), rgba(99,102,241,0.06));
    border: 1px solid var(--border); margin-top: 14px;
}

/* ── Refinement ── */
.refine-header {
    font-family: 'Space Grotesk', sans-serif; font-size: 1.3rem; font-weight: 600;
    color: var(--text-primary); margin-bottom: 0.3rem;
}
.refine-sub { font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 1rem; }

/* ── Markdown + expander ── */
.stMarkdown p, .stMarkdown li, .stMarkdown { color: var(--text-primary); }
div[data-testid="stExpander"] summary,
div[data-testid="stExpander"] summary p { color: var(--text-primary) !important; }
div[data-testid="stExpander"] code, .stCode, pre {
    background: rgba(240, 249, 255, 0.7) !important; color: var(--text-primary) !important;
    border: 1px solid var(--border);
}

@keyframes borderGlow {
    0%, 100% { border-color: rgba(56, 189, 248, 0.30); box-shadow: 0 0 18px rgba(56, 189, 248, 0.18); }
    50%       { border-color: rgba(56, 189, 248, 0.85); box-shadow: 0 0 30px rgba(56, 189, 248, 0.40); }
}
.generating { animation: borderGlow 2s ease-in-out infinite; }

@media (max-width: 768px) {
    .jb-logo-img { max-height: 48px; }
    .step-container { gap: 1rem; flex-wrap: wrap; }
    .step-connector { width: 32px; }
    .pipeline-wrap { flex-direction: column; }
}
</style>
""", unsafe_allow_html=True)


# ── HELPERS ──────────────────────────────────────────────────────────────────

def upload_to_fal(uploaded_file):
    img_bytes = uploaded_file.getvalue()
    content_type = uploaded_file.type or "image/png"
    return strip_background_to_white(img_bytes, content_type=content_type)


VIEW_PROMPTS = {
    "Top View": {
        "model": "fal-ai/nano-banana-pro/edit",
        "icon": "⬆️",
        "prompt": (
            "Re-render this EXACT same ring design from a directly overhead "
            "top-down camera angle, looking straight down at the head and "
            "crown with the band visible curving around below. Preserve "
            "every single detail — same head shape, shank profile, metal "
            "colors (rose-gold stays rose-gold, white-gold stays white-gold), "
            "stones, proportions, surface finish, prong count. ONLY the "
            "camera angle changes. Pure white seamless background "
            "RGB(255,255,255), subtle soft shadow, professional jewelry "
            "product photography, ultra-sharp macro detail."
        ),
    },
    "Side Profile": {
        "model": "fal-ai/nano-banana-pro/edit",
        "icon": "↔️",
        "prompt": (
            "Re-render this EXACT same ring design from a pure side profile "
            "view (90-degree side view), showing the full thickness of the "
            "band and the silhouette of the head from the side. Preserve "
            "every single detail. ONLY the camera angle changes. Pure white "
            "seamless background RGB(255,255,255), subtle soft shadow, "
            "professional jewelry product photography, ultra-sharp macro detail."
        ),
    },
    "Front View": {
        "model": "fal-ai/nano-banana-pro/edit",
        "icon": "🔭",
        "prompt": (
            "Re-render this EXACT same ring design from a head-on front "
            "camera angle, looking directly at the face of the center stone "
            "with the band curving away symmetrically on both sides. "
            "Preserve every single detail. ONLY the camera angle changes. "
            "Pure white seamless background RGB(255,255,255), subtle soft "
            "shadow, professional jewelry product photography, ultra-sharp "
            "macro detail."
        ),
    },
    "Macro Detail": {
        "model": "fal-ai/nano-banana-pro/edit",
        "icon": "🔬",
        "prompt": (
            "Re-render this EXACT same ring design as an extreme macro "
            "close-up of the head and setting, filling the frame with the "
            "crown, prongs, center stone facets, and immediate shoulder "
            "area. Preserve every detail. ONLY the camera distance and "
            "focal length change. Pure white seamless background, subtle "
            "soft shadow, professional jewelry product photography, "
            "ultra-sharp macro."
        ),
    },
    "Technical Drawing": {
        "model": "fal-ai/nano-banana-pro/edit",
        "icon": "📐",
        "prompt": (
            "Re-render this EXACT ring design as a professional jewelry "
            "technical specification drawing in pure side profile view. "
            "Add a clean dimensional callout system: thin dark grey arrow "
            "lines pointing to the band width, the head/setting height, "
            "the center stone diameter, and the total ring height, each "
            "labeled in millimeters using standard 1.0-carat round-brilliant "
            "engagement-ring proportions (band ≈ 2.0 mm, head ≈ 7.0 mm "
            "diameter, center stone ≈ 6.5 mm, total height ≈ 10.0 mm). "
            "Add a small 10 mm scale bar in the bottom-right corner for "
            "reference. The ring itself is rendered photorealistically in "
            "its actual metal colors and stones — preserve every design "
            "detail (head shape, prong count, shank profile, decoration). "
            "Pure white seamless background RGB(255,255,255). The dimension "
            "lines, arrows, mm labels, and scale bar are crisp dark-grey "
            "vector overlays drawn ON TOP of the photorealistic ring."
        ),
    },
}


def generate_view(base_url, view_prompt, model="fal-ai/nano-banana-pro/edit"):
    return fal_client.subscribe(
        model,
        arguments={
            "image_urls": [base_url],
            "prompt": view_prompt,
            "num_images": 1,
            "resolution": "2K",
            "aspect_ratio": "auto",
            "output_format": "png",
        },
    )


def extract_image_url(result):
    if not result:
        return None
    if "images" in result:
        for img in result["images"]:
            url = img.get("url")
            if url:
                return url
    if "image" in result:
        return result["image"].get("url")
    return None


# ── SIDEBAR ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(
        '<img src="https://jewelbench.ai/wp-content/uploads/2025/05/jewelbench_logo.svg" '
        'style="width:100%;max-width:160px;display:block;margin:0 auto 1rem;" />',
        unsafe_allow_html=True,
    )

    fal_ok = bool(os.environ.get("FAL_KEY"))
    if fal_ok:
        st.markdown(
            '<div class="sidebar-key-ok">✓ &nbsp;FAL_KEY connected</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="sidebar-key-err">✗ &nbsp;FAL_KEY missing</div>',
            unsafe_allow_html=True,
        )

    st.markdown("### Settings")
    VALIDATION_THRESHOLD = st.slider(
        "Validation threshold (%)",
        min_value=60, max_value=95, value=_ENV_VALIDATION_THRESHOLD, step=5,
        help="Score required for a render to pass without retrying",
    )
    MAX_VALIDATION_TRIES = st.slider(
        "Max retry attempts",
        min_value=1, max_value=5, value=_ENV_MAX_VALIDATION_TRIES,
        help="How many times to retry a render that scores below the threshold",
    )

    st.markdown("### Session")
    _imgs_loaded = sum(
        1 for i in range(5)
        if st.session_state.get(f"img_{i}") is not None
    )
    _has_results = bool(st.session_state.get("last_results"))
    _views_done = len(st.session_state.get("views", {}))

    st.markdown(
        f'<div class="sidebar-stat"><span>References uploaded</span>'
        f'<span class="sidebar-stat-val">{_imgs_loaded}</span></div>'
        f'<div class="sidebar-stat"><span>Design generated</span>'
        f'<span class="sidebar-stat-val">{"Yes" if _has_results else "No"}</span></div>'
        f'<div class="sidebar-stat"><span>Views rendered</span>'
        f'<span class="sidebar-stat-val">{_views_done} / 5</span></div>',
        unsafe_allow_html=True,
    )

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🗑️ Clear Session", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

    st.markdown("### Pipeline")
    st.caption(
        "Background strip → Vision enrichment → Prompt build → "
        "Background strip → Vision enrichment → Prompt build → AI render → Validation"
    )


# ── KEY CHECK ──────────────────────────────────────────────────────────────

if not fal_ok:
    st.error(
        "**FAL_KEY not found.** Add it in Streamlit Cloud: "
        "Manage app → Settings → Secrets → `FAL_KEY = \"your-key\"`"
    )


# ── HEADER ─────────────────────────────────────────────────────────────────

st.markdown("""
<div class="jb-header">
    <img class="jb-logo-img"
         src="https://jewelbench.ai/wp-content/uploads/2025/05/jewelbench_logo.svg"
         alt="JewelBench" />
    <div class="jb-tagline">Component Composer</div>
</div>
""", unsafe_allow_html=True)


# ── STEP INDICATORS ─────────────────────────────────────────────────────────

current_step = 1
if any(st.session_state.get(f"img_{i}") for i in range(5)):
    current_step = 2
if st.session_state.get("last_results"):
    current_step = 3

def _step_cls(n):
    if n < current_step:
        return "done"
    if n == current_step:
        return "active"
    return ""

def _step_num(n):
    if n < current_step:
        return "✓"
    return str(n)

steps_html = f"""
<div class="step-container">
    <div class="step-item {_step_cls(1)}">
        <div class="step-number">{_step_num(1)}</div>
        <div class="step-label">Upload References</div>
    </div>
    <div class="step-connector"></div>
    <div class="step-item {_step_cls(2)}">
        <div class="step-number">{_step_num(2)}</div>
        <div class="step-label">Specify & Configure</div>
    </div>
    <div class="step-connector"></div>
    <div class="step-item {_step_cls(3)}">
        <div class="step-number">{_step_num(3)}</div>
        <div class="step-label">Generate & Refine</div>
    </div>
</div>
"""
st.markdown(steps_html, unsafe_allow_html=True)


# ── STEP 1: UPLOAD REFERENCES ────────────────────────────────────────────────

st.markdown("""
<div class="section-title">Reference Images</div>
<div class="section-subtitle">Upload jewelry images and describe which component to extract from each</div>
""", unsafe_allow_html=True)

_ref_count_col, _ref_hint_col = st.columns([2, 3])
with _ref_count_col:
    num_images = st.slider(
        "References",
        min_value=2, max_value=5, value=2,
        help="How many reference images to combine",
    )
with _ref_hint_col:
    st.markdown(
        f"<div style='padding-top:2rem;color:var(--text-muted);font-size:0.82rem;'>"
        f"Combining <strong style='color:var(--cyan-deep)'>{num_images}</strong> "
        f"reference images &nbsp;·&nbsp; drag the slider to add more</div>",
        unsafe_allow_html=True,
    )

badge_icons = ["◆", "◇", "○", "□", "△"]
image_specs = []
cols = st.columns(num_images, gap="medium")

for i in range(num_images):
    with cols[i]:
        with st.container(border=True):
            st.markdown(
                f'<div class="card-badge"><span>{badge_icons[i]}</span> Reference {i+1}</div>',
                unsafe_allow_html=True,
            )
            uploaded = st.file_uploader(
                f"ref_{i+1}",
                type=["png", "jpg", "jpeg", "webp", "heic"],
                key=f"img_{i}",
                label_visibility="collapsed",
            )
            if uploaded:
                st.image(uploaded, use_container_width=True)

            desc = st.text_area(
                "Component to extract",
                placeholder=(
                    "Be specific — include color, finish, detail.\n"
                    "e.g. 'pavé white-gold shank with rose-gold accents' "
                    "or '6-prong solitaire head, yellow gold'"
                ),
                key=f"desc_{i}",
                height=90,
                label_visibility="collapsed",
            )
        image_specs.append({"file": uploaded, "description": desc})


# ── STEP 2: SPECIFICATIONS ───────────────────────────────────────────────────

st.markdown("""
<div class="section-title">Design Specifications</div>
<div class="section-subtitle">Define metal, stones, dimensions, and special requirements</div>
""", unsafe_allow_html=True)

spec_col1, spec_col2 = st.columns(2, gap="medium")

with spec_col1:
    with st.container(border=True):
        st.markdown('<div class="spec-card-label">METAL TYPE</div>', unsafe_allow_html=True)
        metal = st.selectbox(
            "Metal",
            [
                "— Select —",
                "14K White Gold",
                "14K Yellow Gold",
                "14K Rose Gold",
                "18K White Gold",
                "18K Yellow Gold",
                "18K Rose Gold",
                "Platinum",
                "Two-Tone (White + Rose)",
                "Two-Tone (White + Yellow)",
                "Three-Tone",
                "Sterling Silver",
            ],
            label_visibility="collapsed",
        )
        if metal == "— Select —":
            metal = ""

        st.markdown('<div class="spec-card-label" style="margin-top:1rem;">STONE DETAILS</div>', unsafe_allow_html=True)
        stones = st.text_area(
            "Stones",
            placeholder="5.68mm Round center stone\nChannel-set side diamonds\nNatural HI I1",
            height=100,
            label_visibility="collapsed",
        )

with spec_col2:
    with st.container(border=True):
        st.markdown('<div class="spec-card-label">DIMENSIONS</div>', unsafe_allow_html=True)
        dimensions = st.text_area(
            "Dimensions",
            placeholder="4.5mm shoulder width\n2.2mm shoulder depth\n2mm shank base width",
            height=100,
            label_visibility="collapsed",
        )
        st.markdown('<div class="spec-card-label" style="margin-top:1rem;">ADDITIONAL NOTES</div>', unsafe_allow_html=True)
        notes = st.text_area(
            "Notes",
            placeholder="Cathedral setting, milgrain edges, pave bridge...",
            height=100,
            label_visibility="collapsed",
        )

additional_specs = {"metal": metal, "stones": stones, "dimensions": dimensions, "notes": notes}


# ── AI PIPELINE VISUALIZATION ────────────────────────────────────────────────

st.markdown("""
<div class="section-title">AI Pipeline</div>
<div class="section-subtitle">Five-stage process — from raw uploads to a validated, production-ready design</div>
""", unsafe_allow_html=True)

st.markdown(f"""
<div class="pipeline-wrap">
  <div class="pipeline-step">
    <div class="pipeline-num">1</div>
    <span class="pipeline-icon">🧹</span>
    <span class="pipeline-label">Background Strip</span>
    <span class="pipeline-model">Precision background removal</span>
  </div>
  <div class="pipeline-step">
    <div class="pipeline-num">2</div>
    <span class="pipeline-icon">🔍</span>
    <span class="pipeline-label">Vision Enrich</span>
    <span class="pipeline-model">Reads each reference deeply</span>
  </div>
  <div class="pipeline-step">
    <div class="pipeline-num">3</div>
    <span class="pipeline-icon">📝</span>
    <span class="pipeline-label">Prompt Build</span>
    <span class="pipeline-model">Silhouette · finish · color rules</span>
  </div>
  <div class="pipeline-step">
    <div class="pipeline-num">4</div>
    <span class="pipeline-icon">✨</span>
    <span class="pipeline-label">Render @ 2K</span>
    <span class="pipeline-model">JewelBench multi-reference engine</span>
  </div>
  <div class="pipeline-step">
    <div class="pipeline-num">5</div>
    <span class="pipeline-icon">🎯</span>
    <span class="pipeline-label">Validate &amp; Retry</span>
    <span class="pipeline-model">JewelBench AI · threshold {VALIDATION_THRESHOLD}% · up to {MAX_VALIDATION_TRIES} tries</span>
  </div>
</div>
""", unsafe_allow_html=True)


# ── PRE-FLIGHT CHECKLIST ─────────────────────────────────────────────────────

_n_images = sum(1 for s in image_specs if s["file"])
_n_descs = sum(1 for s in image_specs if s["description"].strip())
_check_images = _n_images >= 2
_check_descs = _n_descs >= 2
_check_key = fal_ok
_ready = _check_images and _check_descs and _check_key

def _chk(ok, label):
    icon = '<span class="preflight-ok">✓</span>' if ok else '<span class="preflight-no">○</span>'
    style = "color:var(--text-primary)" if ok else "color:var(--text-muted)"
    return f'<div class="preflight-row">{icon}<span style="{style}">{label}</span></div>'

st.markdown(f"""
<div class="preflight-wrap">
  <div class="preflight-title">Ready to generate?</div>
  {_chk(_check_key, "FAL_KEY connected")}
  {_chk(_check_images, f"At least 2 reference images ({_n_images} uploaded)")}
  {_chk(_check_descs, f"At least 2 component descriptions ({_n_descs} filled)")}
</div>
""", unsafe_allow_html=True)

_gen_cols = st.columns([1, 4, 1])
with _gen_cols[1]:
    generate_clicked = st.button(
        "✨ GENERATE COMBINED DESIGN",
        use_container_width=True,
        type="primary",
        disabled=not _ready,
    )


# ── GENERATION ───────────────────────────────────────────────────────────────

if generate_clicked and _ready:
    active_specs = [s for s in image_specs if s["file"] and s["description"]]

    with st.status("Running AI pipeline...", expanded=True) as gen_status:

        # Phase 1
        st.write("🧹 Phase 1/5 — Cleaning reference backgrounds...")
        try:
            image_urls = [upload_to_fal(s["file"]) for s in active_specs]
        except Exception as e:
            gen_status.update(label="Upload failed", state="error")
            st.error(f"Reference upload failed: {e}")
            st.stop()
        st.write(f"✓ {len(image_urls)} image(s) cleaned and uploaded")

        # Phase 2
        st.write("🔍 Phase 2/5 — Reading reference images to enrich descriptions...")
        enriched_specs = []
        for spec, url in zip(active_specs, image_urls):
            enriched = enrich_description(url, spec["description"])
            enriched_specs.append({"file": spec["file"], "description": enriched, "_original": spec["description"]})
        st.write(f"✓ Descriptions enriched for {len(enriched_specs)} reference(s)")

        # Phase 3
        st.write("📝 Phase 3/5 — Building master combination prompt...")
        combine_prompt = build_combine_prompt(enriched_specs, additional_specs)
        target_summary = build_target_summary(enriched_specs, additional_specs)
        st.write("✓ Prompt built")

        with st.expander("View enriched descriptions & prompt", expanded=False):
            st.markdown("**Vision-enriched descriptions:**")
            for i, s in enumerate(enriched_specs):
                st.markdown(f"**Image {i+1}** — original: *\"{s['_original']}\"*")
                st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;enriched: **{s['description']}**")
            st.markdown("---")
            st.markdown("**Validator target description:**")
            st.code(target_summary, language="text")
            st.markdown("**Master prompt sent to render engine:**")
            st.code(combine_prompt, language="text")

        # Phase 4+5
        results = []
        strategy_names = []
        diagnoses = []
        attempts_log = []
        best_url = None
        best_score = -1
        best_diagnosis = None
        current_prompt = combine_prompt
        prev_score = -1

        for attempt in range(1, MAX_VALIDATION_TRIES + 1):
            st.write(f"✨ Phase 4/5 — Rendering attempt {attempt}/{MAX_VALIDATION_TRIES} at 2K...")
            try:
                result = fal_client.subscribe(
                    "fal-ai/nano-banana-pro/edit",
                    arguments={
                        "image_urls": image_urls,
                        "prompt": current_prompt,
                        "num_images": 1,
                        "resolution": "2K",
                        "aspect_ratio": "auto",
                        "output_format": "png",
                    },
                )
            except Exception as e:
                st.warning(f"Attempt {attempt} render failed: {e}")
                attempts_log.append({"attempt": attempt, "error": str(e)})
                continue

            url = extract_image_url(result)
            if not url:
                attempts_log.append({"attempt": attempt, "error": "no image returned"})
                continue

            try:
                url = strip_url_to_white(url)
            except Exception:
                pass

            st.write(f"🎯 Phase 5/5 — Validating attempt {attempt} against target spec...")
            diagnosis = validate_design(url, target_summary)
            score = diagnosis.get("score", 0)
            attempts_log.append({"attempt": attempt, "score": score, "url": url})

            if score > best_score:
                best_url = url
                best_score = score
                best_diagnosis = diagnosis

            if score >= VALIDATION_THRESHOLD:
                st.write(f"✓ Passed validation — score {score}/100")
                break

            if attempt > 1 and score < prev_score:
                attempts_log[-1]["regressed"] = True
                st.write(f"⚠ Score regressed ({score} < {prev_score}), stopping early")
                break

            prev_score = score

            if attempt < MAX_VALIDATION_TRIES:
                st.write(f"↻ Score {score}% — below threshold {VALIDATION_THRESHOLD}%, refining prompt...")
                current_prompt = (
                    combine_prompt + "\n\n" + build_correction_addendum(diagnosis, attempt + 1)
                )

        if best_url:
            results.append(best_url)
            strategy_names.append("JewelBench AI Render")
            diagnoses.append(best_diagnosis or {})
            passed = best_score >= VALIDATION_THRESHOLD
            gen_status.update(
                label=f"✓ Generation complete — score {best_score}/100" + (" (passed)" if passed else " (best attempt)"),
                state="complete",
            )
        else:
            gen_status.update(label="Generation failed", state="error")

    if results:
        tries_used = len(attempts_log)
        passed = best_score >= VALIDATION_THRESHOLD
        badge_color = "#22D67A" if passed else "#FFB547"
        status_text = (
            f"Passed self-validation in {tries_used} {'try' if tries_used == 1 else 'tries'}"
            if passed
            else f"Best of {tries_used} {'try' if tries_used == 1 else 'tries'} (below {VALIDATION_THRESHOLD}% threshold)"
        )

        st.markdown("""
        <div class="section-title">Generated Design</div>
        """, unsafe_allow_html=True)

        _score_class = "pass" if passed else "warn"
        _ring_color = "#22D67A" if passed else "#FFB547"
        _circumference = 2 * 3.14159 * 40
        _dash = (_circumference * best_score) / 100
        _gap = _circumference - _dash
        st.markdown(f"""
        <div class="score-block">
          <div class="score-ring-wrap">
            <svg width="100" height="100" viewBox="0 0 100 100">
              <circle cx="50" cy="50" r="40" fill="none" stroke="rgba(56,189,248,0.12)" stroke-width="8"/>
              <circle cx="50" cy="50" r="40" fill="none" stroke="{_ring_color}"
                stroke-width="8" stroke-linecap="round"
                stroke-dasharray="{_dash:.1f} {_gap:.1f}"
                style="filter:drop-shadow(0 0 6px {_ring_color}88);transition:stroke-dasharray 1s ease;"/>
            </svg>
            <div class="score-ring-center">
              <span class="score-ring-num {_score_class}">{best_score}</span>
              <span class="score-ring-pct">/ 100</span>
            </div>
          </div>
          <div>
            <div class="score-label">Design Match</div>
            <div class="score-status-title">{'Passed Validation' if passed else 'Best Attempt'}</div>
            <div class="score-status-sub">{status_text}</div>
            <div class="score-badge {_score_class}">{'✓ Production Ready' if passed else '⚠ Below Threshold'}</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        result_cols = st.columns(min(len(results), 4), gap="medium")
        for idx, url in enumerate(results):
            label = strategy_names[idx] if idx < len(strategy_names) else f"Var {idx+1}"
            with result_cols[idx % len(result_cols)]:
                st.markdown('<div class="result-card">', unsafe_allow_html=True)
                st.image(url, use_container_width=True)
                st.markdown(
                    f"""<div class="result-label">
                        <span>{label}</span>
                        <a href="{url}" target="_blank"
                           style="color:var(--cyan);text-decoration:none;font-size:0.8rem;font-weight:600;">
                            ↓ Download
                        </a>
                    </div></div>""",
                    unsafe_allow_html=True,
                )

        with st.expander("AI Self-Validation Report", expanded=not passed):
            for entry in attempts_log:
                if "error" in entry:
                    st.markdown(f"**Attempt {entry['attempt']}** — failed: {entry['error']}")
                else:
                    regressed = " — *stopped (score regressed)*" if entry.get("regressed") else ""
                    st.markdown(f"**Attempt {entry['attempt']}** — score **{entry.get('score', 0)}/100**{regressed}")
            if best_diagnosis:
                if best_diagnosis.get("per_component"):
                    st.markdown("**Per-component scores (final output):**")
                    for component, comp_score in best_diagnosis["per_component"].items():
                        bar = "█" * (comp_score // 10) + "░" * (10 - comp_score // 10)
                        st.markdown(f"- `{bar}` **{comp_score}/100** — {component}")
                if best_diagnosis.get("correct"):
                    st.markdown("**Rendered correctly:**")
                    for c in best_diagnosis["correct"]:
                        st.markdown(f"- ✓ {c}")
                if best_diagnosis.get("missing"):
                    st.markdown("**Missing from final output:**")
                    for m in best_diagnosis["missing"]:
                        st.markdown(f"- ✗ {m}")
                if best_diagnosis.get("wrong"):
                    st.markdown("**Rendered incorrectly:**")
                    for w in best_diagnosis["wrong"]:
                        st.markdown(f"- ⚠ {w}")
                if best_diagnosis.get("suggestion"):
                    st.markdown(f"**Validator's suggestion:** {best_diagnosis['suggestion']}")
                pass
                if best_diagnosis.get("_error"):
                    st.caption(f"Validator note: {best_diagnosis['_error']}")

        st.session_state["last_results"] = results
        st.session_state["last_prompt"] = combine_prompt
        st.session_state["last_target_summary"] = target_summary
        st.session_state["last_image_urls"] = image_urls
        st.session_state.setdefault("views", {})

        with st.spinner("Computing Bill of Materials..."):
            try:
                bom_raw = extract_bom(results[0], target_summary)
                if bom_raw and not bom_raw.get("_error"):
                    gold = get_gold_rates()
                    diamond_rates = load_diamond_rates()
                    costed = compute_costs(bom_raw, gold, diamond_rates)
                    st.session_state["last_bom"] = bom_raw
                    st.session_state["last_bom_costs"] = costed
                    st.session_state["last_bom_gold"] = gold
                    st.session_state["last_bom_url"] = results[0]
                    st.session_state.pop("last_bom_error", None)
                else:
                    st.session_state["last_bom_error"] = (
                        (bom_raw or {}).get("_error", "BoM extractor returned nothing")
                    )
                    st.session_state.pop("last_bom", None)
                    st.session_state.pop("last_bom_costs", None)
            except Exception as bom_exc:
                st.session_state["last_bom_error"] = f"BoM exception: {bom_exc}"
                st.session_state.pop("last_bom", None)
                st.session_state.pop("last_bom_costs", None)

        st.toast("Design generated successfully!", icon="✨")
    else:
        st.error("No images were generated. Check your FAL_KEY and try again.")


# ── BILL OF MATERIALS ─────────────────────────────────────────────────────────

if st.session_state.get("last_bom") and st.session_state.get("last_bom_costs"):
    _bom = st.session_state["last_bom"]
    _costs = st.session_state["last_bom_costs"]
    _gold = st.session_state.get("last_bom_gold") or get_gold_rates()
    _fx = _gold["usd_inr"]

    _sku_seed = (
        (st.session_state.get("last_prompt") or "")
        + (st.session_state.get("last_bom_url") or "")
    )
    _sku = "JBR-" + hashlib.sha1(_sku_seed.encode()).hexdigest()[:8].upper()
    _ts_str = datetime.datetime.fromtimestamp(_gold["ts"]).strftime("%H:%M")
    _live_tag = "LIVE" if _gold.get("live_gold") and _gold.get("live_fx") else "FALLBACK"
    _rate_line = (
        f"{_live_tag} · Gold ${_gold['usd_per_oz_xau']:,.2f}/oz · "
        f"₹{_gold['per_g'].get('18k_inr', 0):,.0f}/g 18k · "
        f"USD/INR {_gold['usd_inr']:,.2f} · fetched {_ts_str} · source: {_gold['source']}"
    )

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        f'<div class="section-title">Bill of Materials</div>'
        f'<div class="section-subtitle">{_rate_line}</div>',
        unsafe_allow_html=True,
    )

    _metal = _costs["metal"]
    _dia = _costs["diamonds"]
    _mf = _costs["manufacturing"]
    _gt = _costs["grand_total"]
    _alloy_pretty = _metal["alloy"].replace("_", " ").title()

    # Metric summary row
    _mc1, _mc2, _mc3, _mc4 = st.columns(4, gap="medium")
    _mc1.metric("Metal", f"${_metal['total_usd']:,.2f}", f"₹{_metal['total_inr']:,.0f}")
    _mc2.metric("Diamonds", f"${_dia['total_usd']:,.2f}", f"₹{_dia['total_inr']:,.0f}")
    _mc3.metric("Manufacturing", f"${_mf['total_usd']:,.2f}", f"₹{_mf['total_inr']:,.0f}")
    _mc4.metric("Grand Total", f"${_gt['usd']:,.2f}", f"₹{_gt['inr']:,.0f}")

    st.markdown("<br>", unsafe_allow_html=True)

    with st.expander(f"Metal — {_alloy_pretty}", expanded=True):
        st.markdown(
            f"""
| Alloy | Weight | Rate USD/g | Rate INR/g | Subtotal USD | Subtotal INR |
|---|---|---|---|---|---|
| {_alloy_pretty} | {_metal['weight_g']:.2f} g | ${_metal['rate_usd_per_g']:,.2f} | ₹{_metal['rate_inr_per_g']:,.2f} | ${_metal['total_usd']:,.2f} | ₹{_metal['total_inr']:,.2f} |
"""
        )

    if _dia["groups"]:
        with st.expander(
            f"Diamonds — {_dia['total_count']} stones · {_dia['total_carat']:.3f} ct total",
            expanded=True,
        ):
            st.caption("Reference wholesale rates — edit `diamond_rates.json` to match your supplier")
            _dia_rows = "\n".join(
                f"| {g['location'].replace('_', ' ')} | {g['shape']} | "
                f"{g['count']} | {g['carat_each']:.3f} | "
                f"{(g.get('mm_each') if g.get('mm_each') is not None else '—')} | "
                f"{g['clarity']} | {g['setting']} | "
                f"${g['unit_usd']:,.2f} | ${g['line_total_usd']:,.2f} | "
                f"₹{g['line_total_usd'] * _fx:,.2f} |"
                for g in _dia["groups"]
            )
            st.markdown(
                f"""
| Location | Shape | Count | ct each | mm | Clarity | Setting | $/stone | Subtotal USD | Subtotal INR |
|---|---|---|---|---|---|---|---|---|---|
{_dia_rows}
| **TOTAL** | | **{_dia['total_count']}** | | | | | | **${_dia['total_usd']:,.2f}** | **₹{_dia['total_inr']:,.2f}** |
"""
            )

    with st.expander("Manufacturing", expanded=False):
        st.markdown(
            f"""
| Line | USD | INR |
|---|---|---|
| CAD | ${_mf['cad_usd']:.2f} | ₹{_mf['cad_usd'] * _fx:,.2f} |
| Wax printing | ${_mf['wax_usd']:.2f} | ₹{_mf['wax_usd'] * _fx:,.2f} |
| Casting | ${_mf['casting_usd']:.2f} | ₹{_mf['casting_usd'] * _fx:,.2f} |
| Polishing | ${_mf['polishing_usd']:.2f} | ₹{_mf['polishing_usd'] * _fx:,.2f} |
| Stone setting | ${_mf['stone_setting_usd']:.2f} | ₹{_mf['stone_setting_usd'] * _fx:,.2f} |
| Labour | ${_mf['labour_usd']:.2f} | ₹{_mf['labour_usd'] * _fx:,.2f} |
| **TOTAL** | **${_mf['total_usd']:,.2f}** | **₹{_mf['total_inr']:,.2f}** |
"""
        )

    # Dimensions + ring size
    _dim = _bom.get("dimensions_mm") or {}
    _rs = _bom.get("ring_size") or {}
    _sr = _bom.get("size_range") or {}
    _tol = _bom.get("weight_tolerance_pct")
    _cn = _bom.get("construction_notes") or ""

    with st.expander("Dimensions, Size & Production", expanded=False):
        _spec_cols = st.columns(3, gap="medium")
        with _spec_cols[0]:
            st.markdown("**Dimensions (mm)**")
            st.markdown(
                f"- Inner diameter: **{_dim.get('inner_diameter', '—')}**\n"
                f"- Band width (bottom): **{_dim.get('band_width_at_bottom', '—')}**\n"
                f"- Band width (shoulder): **{_dim.get('band_width_at_shoulder', '—')}**\n"
                f"- Band thickness: **{_dim.get('band_thickness', '—')}**\n"
                f"- Head height: **{_dim.get('head_height_above_finger', '—')}**\n"
                f"- Head diameter: **{_dim.get('head_diameter', '—')}**"
            )
        with _spec_cols[1]:
            st.markdown("**Ring Size**")
            _sr_min = _sr.get("us_min", "—")
            _sr_max = _sr.get("us_max", "—")
            st.markdown(
                f"- US: **{_rs.get('us', '—')}**\n"
                f"- UK: **{_rs.get('uk', '—')}**\n"
                f"- Inner circumference: **{_rs.get('inner_circumference_mm', '—')} mm**\n"
                f"- Producible range: **US {_sr_min} – US {_sr_max}**"
            )
        with _spec_cols[2]:
            st.markdown("**Production**")
            _tol_line = f"- Weight tolerance: **±{_tol}%**\n" if _tol else ""
            st.markdown(
                f"- SKU: **{_sku}**\n"
                f"{_tol_line}"
                f"- Analyzed by: _JewelBench AI_"
            )
            if _cn:
                st.markdown(f"_{_cn}_")

    # Downloads
    _full_bom = {
        "sku": _sku,
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "source_image": st.session_state.get("last_bom_url"),
        "design_summary": st.session_state.get("last_target_summary"),
        "bom": _bom,
        "costs": _costs,
        "gold_rates": _gold,
    }
    _bom_json = _json.dumps(_full_bom, indent=2, default=str)
    _md_lines = [
        f"# Bill of Materials — {_sku}",
        f"_Generated {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}_",
        f"_Rates: {_rate_line}_",
        "",
        "## Metal",
        f"- Alloy: **{_alloy_pretty}**",
        (f"- Weight: **{_metal['weight_g']:.2f} g** (tolerance ±{_tol}%)" if _tol else f"- Weight: **{_metal['weight_g']:.2f} g**"),
        f"- Cost: **${_metal['total_usd']:,.2f}** / **₹{_metal['total_inr']:,.2f}**",
        "",
        f"## Diamonds — {_dia['total_count']} stones, {_dia['total_carat']:.3f} ct total",
    ]
    for g in _dia["groups"]:
        _md_lines.append(
            f"- {g['location'].replace('_', ' ')}: {g['count']} × "
            f"{g['shape']} {g['carat_each']:.3f} ct ({g['clarity']}, "
            f"{g['setting']}) — ${g['line_total_usd']:,.2f} / "
            f"₹{g['line_total_usd'] * _fx:,.2f}"
        )
    _md_lines += [
        f"- **Diamond subtotal: ${_dia['total_usd']:,.2f} / ₹{_dia['total_inr']:,.2f}**",
        "",
        "## Manufacturing",
        f"- CAD: ${_mf['cad_usd']:.2f}",
        f"- Wax: ${_mf['wax_usd']:.2f}",
        f"- Casting: ${_mf['casting_usd']:.2f}",
        f"- Polishing: ${_mf['polishing_usd']:.2f}",
        f"- Stone setting: ${_mf['stone_setting_usd']:.2f}",
        f"- Labour: ${_mf['labour_usd']:.2f}",
        f"- **Manufacturing subtotal: ${_mf['total_usd']:.2f} / ₹{_mf['total_inr']:,.2f}**",
        "",
        "## Total Input Cost",
        f"**${_gt['usd']:,.2f} USD / ₹{_gt['inr']:,.2f} INR**",
        "",
        "## Dimensions (mm)",
        f"- Inner diameter: {_dim.get('inner_diameter', '—')}",
        f"- Band width (bottom): {_dim.get('band_width_at_bottom', '—')}",
        f"- Band width (shoulder): {_dim.get('band_width_at_shoulder', '—')}",
        f"- Band thickness: {_dim.get('band_thickness', '—')}",
        f"- Head height: {_dim.get('head_height_above_finger', '—')}",
        f"- Head diameter: {_dim.get('head_diameter', '—')}",
        "",
        "## Ring Size",
        f"- US: {_rs.get('us', '—')}",
        f"- UK: {_rs.get('uk', '—')}",
        f"- Inner circumference: {_rs.get('inner_circumference_mm', '—')} mm",
        f"- Producible range: US {_sr_min} – US {_sr_max}",
        "",
        "## Construction notes",
        _cn or "_(none provided)_",
    ]
    _bom_md = "\n".join(_md_lines)

    _dl_cols = st.columns(2, gap="small")
    with _dl_cols[0]:
        st.download_button(
            "↓ Download BoM (JSON)",
            data=_bom_json,
            file_name=f"{_sku}_bom.json",
            mime="application/json",
            use_container_width=True,
        )
    with _dl_cols[1]:
        st.download_button(
            "↓ Download BoM (Markdown)",
            data=_bom_md,
            file_name=f"{_sku}_bom.md",
            mime="text/markdown",
            use_container_width=True,
        )

elif st.session_state.get("last_bom_error"):
    st.markdown("<br>", unsafe_allow_html=True)
    st.warning(f"Bill of Materials unavailable: {st.session_state['last_bom_error']}")


# ── ADDITIONAL VIEWS ──────────────────────────────────────────────────────────

if st.session_state.get("last_results"):
    base_design_url = st.session_state["last_results"][0]

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("""
    <div class="section-title">Additional Views</div>
    <div class="section-subtitle">Re-render the generated design from different camera angles. Generate all 5 in parallel (~60 s, ~$0.30) or pick individual views to retry.</div>
    """, unsafe_allow_html=True)

    view_names = list(VIEW_PROMPTS.keys())

    # Batch button
    _vbatch_col = st.columns([1, 3, 1])[1]
    with _vbatch_col:
        if st.button("⚡ Generate All Views (parallel)", key="view_btn_all", use_container_width=True, type="primary"):
            from concurrent.futures import ThreadPoolExecutor, as_completed
            with st.status(f"Rendering {len(view_names)} views in parallel...", expanded=True) as _vs:
                _vresults = {}
                _verrors = {}
                with ThreadPoolExecutor(max_workers=len(view_names)) as executor:
                    futures = {
                        executor.submit(
                            generate_view,
                            base_design_url,
                            VIEW_PROMPTS[name]["prompt"],
                            VIEW_PROMPTS[name]["model"],
                        ): name
                        for name in view_names
                    }
                    for future in as_completed(futures):
                        name = futures[future]
                        try:
                            result = future.result()
                            url = extract_image_url(result)
                            if url:
                                _vresults[name] = url
                                st.write(f"✓ {name}")
                            else:
                                _verrors[name] = "no image returned"
                        except Exception as e:
                            _verrors[name] = str(e)
                if _vresults:
                    st.session_state.setdefault("views", {}).update(_vresults)
                for n, msg in _verrors.items():
                    st.warning(f"{n} failed: {msg}")
                _vs.update(
                    label=f"Done — {len(_vresults)}/{len(view_names)} views rendered",
                    state="complete" if not _verrors else "error",
                )
            if _vresults:
                st.toast(f"{len(_vresults)} view(s) rendered!", icon="✨")

    st.markdown("<br>", unsafe_allow_html=True)

    # Always-visible 5-slot grid
    existing_views = st.session_state.get("views", {})
    view_grid_cols = st.columns(5, gap="small")
    for idx, view_name in enumerate(view_names):
        cfg = VIEW_PROMPTS[view_name]
        with view_grid_cols[idx]:
            vurl = existing_views.get(view_name)
            if vurl:
                st.markdown('<div class="result-card">', unsafe_allow_html=True)
                st.image(vurl, use_container_width=True)
                st.markdown(
                    f"""<div class="result-label">
                        <span style="font-size:0.78rem">{view_name}</span>
                        <a href="{vurl}" target="_blank"
                           style="color:var(--cyan);text-decoration:none;font-size:0.75rem;font-weight:600;">
                            ↓
                        </a>
                    </div></div>""",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<div class="view-placeholder">'
                    f'<span class="view-placeholder-icon">{cfg["icon"]}</span>'
                    f'<span>{view_name}</span>'
                    f'<span style="font-size:0.7rem;opacity:0.6;">not rendered</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            # Individual generate button below each slot
            if st.button(
                "Generate" if not vurl else "Re-render",
                key=f"view_btn_{view_name}",
                use_container_width=True,
            ):
                with st.spinner(f"Rendering {view_name}..."):
                    try:
                        result = generate_view(base_design_url, cfg["prompt"], cfg["model"])
                        url = extract_image_url(result)
                        if url:
                            st.session_state.setdefault("views", {})[view_name] = url
                            st.toast(f"{view_name} ready!", icon=cfg["icon"])
                            st.rerun()
                        else:
                            st.warning(f"{view_name} produced no image.")
                    except Exception as e:
                        st.error(f"{view_name} failed: {e}")


# ── REFINEMENT ────────────────────────────────────────────────────────────────

if st.session_state.get("last_results"):
    st.markdown("<br>", unsafe_allow_html=True)

    with st.container(border=True):
        st.markdown(
            '<div class="refine-header">Refine Your Design</div>'
            '<div class="refine-sub">Describe modifications — the original references and specs are preserved unless you override them</div>',
            unsafe_allow_html=True,
        )

        refinement = st.text_input(
            "Modifications",
            placeholder="e.g. 'Thinner prongs, add milgrain detail, make the halo more pronounced'",
            label_visibility="collapsed",
        )

        _ref_btn_cols = st.columns([1, 3, 1])
        with _ref_btn_cols[1]:
            _regen = st.button("↺ REGENERATE WITH CHANGES", use_container_width=True)

    if _regen:
        if not refinement:
            st.warning("Describe what to change before regenerating.")
        else:
            base_prompt = st.session_state["last_prompt"]
            refined_prompt = (
                f"{base_prompt}\n\n"
                f"REFINEMENT (apply on top of the above)\n{refinement.strip()}\n"
                f"Keep the previously specified components, metals, and stones unchanged "
                f"except where the refinement explicitly overrides them."
            )
            base_target = st.session_state.get("last_target_summary", "")
            refinement_target = (
                f"{base_target}\n\nADDITIONAL REFINEMENT REQUESTED: {refinement.strip()}"
            )
            image_urls = st.session_state.get("last_image_urls") or [
                upload_to_fal(s["file"]) for s in image_specs if s["file"]
            ]

            r_best_url = None
            r_best_score = -1
            r_best_diagnosis = None
            r_attempts_log = []
            r_current_prompt = refined_prompt
            r_prev_score = -1

            with st.status("Regenerating with refinements...", expanded=True) as r_status:
                for attempt in range(1, MAX_VALIDATION_TRIES + 1):
                    st.write(f"✨ Rendering attempt {attempt}/{MAX_VALIDATION_TRIES}...")
                    try:
                        result = fal_client.subscribe(
                            "fal-ai/nano-banana-pro/edit",
                            arguments={
                                "image_urls": image_urls,
                                "prompt": r_current_prompt,
                                "num_images": 1,
                                "resolution": "2K",
                                "aspect_ratio": "auto",
                                "output_format": "png",
                            },
                        )
                    except Exception as e:
                        r_attempts_log.append({"attempt": attempt, "error": str(e)})
                        continue

                    url = extract_image_url(result)
                    if not url:
                        r_attempts_log.append({"attempt": attempt, "error": "no image returned"})
                        continue

                    try:
                        url = strip_url_to_white(url)
                    except Exception:
                        pass

                    st.write(f"🎯 Validating attempt {attempt}...")
                    diagnosis = validate_design(url, refinement_target)
                    score = diagnosis.get("score", 0)
                    r_attempts_log.append({"attempt": attempt, "score": score, "url": url})

                    if score > r_best_score:
                        r_best_url = url
                        r_best_score = score
                        r_best_diagnosis = diagnosis

                    if score >= VALIDATION_THRESHOLD:
                        st.write(f"✓ Passed — score {score}/100")
                        break
                    if attempt > 1 and score < r_prev_score:
                        r_attempts_log[-1]["regressed"] = True
                        st.write(f"⚠ Score regressed, stopping early")
                        break
                    r_prev_score = score

                    if attempt < MAX_VALIDATION_TRIES:
                        st.write(f"↻ Score {score}% — refining prompt for next attempt...")
                        r_current_prompt = (
                            refined_prompt + "\n\n" + build_correction_addendum(diagnosis, attempt + 1)
                        )

                r_passed = r_best_score >= VALIDATION_THRESHOLD
                r_status.update(
                    label=f"✓ Refinement complete — score {r_best_score}/100",
                    state="complete" if r_best_url else "error",
                )

            if r_best_url:
                r_tries_used = len(r_attempts_log)
                r_status_text = (
                    f"Passed in {r_tries_used} {'try' if r_tries_used == 1 else 'tries'}"
                    if r_passed
                    else f"Best of {r_tries_used} {'try' if r_tries_used == 1 else 'tries'} (below {VALIDATION_THRESHOLD}%)"
                )

                st.markdown('<div class="section-title">Refined Design</div>', unsafe_allow_html=True)
                _rscore_class = "pass" if r_passed else "warn"
                _rring_color = "#22D67A" if r_passed else "#FFB547"
                _rcirc = 2 * 3.14159 * 40
                _rdash = (_rcirc * r_best_score) / 100
                _rgap = _rcirc - _rdash
                st.markdown(f"""
                <div class="score-block">
                  <div class="score-ring-wrap">
                    <svg width="100" height="100" viewBox="0 0 100 100">
                      <circle cx="50" cy="50" r="40" fill="none" stroke="rgba(56,189,248,0.12)" stroke-width="8"/>
                      <circle cx="50" cy="50" r="40" fill="none" stroke="{_rring_color}"
                        stroke-width="8" stroke-linecap="round"
                        stroke-dasharray="{_rdash:.1f} {_rgap:.1f}"
                        style="filter:drop-shadow(0 0 6px {_rring_color}88);"/>
                    </svg>
                    <div class="score-ring-center">
                      <span class="score-ring-num {_rscore_class}">{r_best_score}</span>
                      <span class="score-ring-pct">/ 100</span>
                    </div>
                  </div>
                  <div>
                    <div class="score-label">Design Match</div>
                    <div class="score-status-title">{'Passed Validation' if r_passed else 'Best Attempt'}</div>
                    <div class="score-status-sub">{r_status_text}</div>
                    <div class="score-badge {_rscore_class}">{'✓ Production Ready' if r_passed else '⚠ Below Threshold'}</div>
                  </div>
                </div>
                """, unsafe_allow_html=True)

                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    st.image(r_best_url, use_container_width=True)
                    st.markdown(
                        f'<div style="text-align:center;margin-top:8px;">'
                        f'<a href="{r_best_url}" target="_blank" '
                        f'style="color:var(--cyan-deep);font-weight:600;text-decoration:none;">'
                        f'↓ Download Full Resolution</a></div>',
                        unsafe_allow_html=True,
                    )

                with st.expander("Refinement Validation Report", expanded=not r_passed):
                    for entry in r_attempts_log:
                        if "error" in entry:
                            st.markdown(f"**Attempt {entry['attempt']}** — failed: {entry['error']}")
                        else:
                            regressed = " — *stopped (score regressed)*" if entry.get("regressed") else ""
                            st.markdown(f"**Attempt {entry['attempt']}** — score **{entry.get('score', 0)}/100**{regressed}")
                    if r_best_diagnosis:
                        if r_best_diagnosis.get("per_component"):
                            st.markdown("**Per-component scores:**")
                            for component, comp_score in r_best_diagnosis["per_component"].items():
                                bar = "█" * (comp_score // 10) + "░" * (10 - comp_score // 10)
                                st.markdown(f"- `{bar}` **{comp_score}/100** — {component}")
                        if r_best_diagnosis.get("correct"):
                            st.markdown("**Rendered correctly:**")
                            for c in r_best_diagnosis["correct"]:
                                st.markdown(f"- ✓ {c}")
                        if r_best_diagnosis.get("missing"):
                            st.markdown("**Missing:**")
                            for m in r_best_diagnosis["missing"]:
                                st.markdown(f"- ✗ {m}")
                        if r_best_diagnosis.get("wrong"):
                            st.markdown("**Rendered incorrectly:**")
                            for w in r_best_diagnosis["wrong"]:
                                st.markdown(f"- ⚠ {w}")
                        if r_best_diagnosis.get("suggestion"):
                            st.markdown(f"**Validator's suggestion:** {r_best_diagnosis['suggestion']}")
                st.toast("Refined design ready!", icon="✨")
            else:
                st.error("Refinement failed — no image was generated. Check your FAL_KEY and try again.")


# ── FOOTER ────────────────────────────────────────────────────────────────────

st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown("""
<div style="text-align:center;padding:2rem 0;border-top:1px solid var(--border);">
    <span style="color:var(--text-muted);font-size:0.75rem;letter-spacing:2px;">
        POWERED BY JEWELBENCH AI
    </span>
</div>
""", unsafe_allow_html=True)
