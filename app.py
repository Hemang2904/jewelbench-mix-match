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

VALIDATION_THRESHOLD = int(os.environ.get("VALIDATION_THRESHOLD", "80"))
MAX_VALIDATION_TRIES = int(os.environ.get("MAX_VALIDATION_TRIES", "3"))
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Load FAL_KEY from all possible sources
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
    initial_sidebar_state="collapsed",
)

# --- PREMIUM CSS ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Space+Grotesk:wght@400;500;600;700&family=Orbitron:wght@500;600;700&display=swap');

:root {
    /* Light theme — white canvas with sky-blue accents */
    --bg-deep: #FFFFFF;
    --bg-mid: #F8FAFC;
    --bg-elevated: #FFFFFF;
    --glass: rgba(255, 255, 255, 0.85);
    --glass-strong: rgba(255, 255, 255, 0.96);
    --border: rgba(56, 189, 248, 0.20);
    --border-active: rgba(2, 132, 199, 0.55);
    --cyan: #0EA5E9;        /* sky-500  primary accent */
    --cyan-soft: #7DD3FC;   /* sky-300  hover wash      */
    --cyan-deep: #0369A1;   /* sky-700  hover/text      */
    --blue: #38BDF8;        /* sky-400                  */
    --blue-deep: #0284C7;   /* sky-600                  */
    --purple: #6366F1;      /* indigo-500 secondary     */
    --text-primary: #0F172A;   /* slate-900 */
    --text-secondary: #475569; /* slate-600 */
    --text-muted: #94A3B8;     /* slate-400 */
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

/* Hide default streamlit branding */
#MainMenu, footer, header {visibility: hidden;}
.stDeployButton {display: none;}

/* Header */
.jb-header { text-align: center; padding: 2.4rem 0 1rem; position: relative; }
.jb-header::after {
    content: '';
    position: absolute;
    bottom: 0;
    left: 50%;
    transform: translateX(-50%);
    width: 180px;
    height: 2px;
    background: linear-gradient(90deg, transparent, var(--cyan), transparent);
    box-shadow: 0 0 14px rgba(56, 189, 248, 0.45);
}
.jb-logo-img {
    max-height: 64px;
    width: auto;
    margin-bottom: 0.5rem;
    filter: drop-shadow(0 2px 10px rgba(56, 189, 248, 0.18));
    animation: logoPulse 4s ease-in-out infinite;
}
@keyframes logoPulse {
    0%, 100% { filter: drop-shadow(0 2px 10px rgba(56, 189, 248, 0.18)); }
    50%      { filter: drop-shadow(0 4px 18px rgba(56, 189, 248, 0.35)); }
}
.jb-tagline {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.95rem;
    color: var(--cyan-deep);
    font-weight: 500;
    letter-spacing: 5px;
    text-transform: uppercase;
}

/* Step Indicators */
.step-container { display: flex; justify-content: center; gap: 2.5rem; margin: 2rem 0; padding: 1.2rem 0; }
.step-item { display: flex; align-items: center; gap: 0.75rem; opacity: 0.45; transition: all 0.4s cubic-bezier(.2,.8,.2,1); }
.step-item.active { opacity: 1; }
.step-number {
    width: 38px; height: 38px;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-weight: 700;
    font-family: 'Orbitron', sans-serif;
    font-size: 0.85rem;
    border: 1.5px solid rgba(56, 189, 248, 0.30);
    color: var(--text-muted);
    background: #FFFFFF;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
    transition: all 0.4s cubic-bezier(.2,.8,.2,1);
}
.step-item.active .step-number {
    border-color: var(--cyan);
    color: #FFFFFF;
    background: linear-gradient(135deg, var(--blue) 0%, var(--blue-deep) 100%);
    box-shadow: 0 4px 14px rgba(56, 189, 248, 0.45);
    transform: scale(1.05);
}
.step-label {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.85rem; font-weight: 500;
    color: var(--text-muted);
    letter-spacing: 0.5px;
}
.step-item.active .step-label { color: var(--text-primary); }
.step-connector {
    width: 70px; height: 1.5px;
    background: linear-gradient(90deg, rgba(56, 189, 248, 0.12), rgba(56, 189, 248, 0.50), rgba(56, 189, 248, 0.12));
    align-self: center;
}

/* Section Titles */
.section-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.55rem;
    margin: 2.2rem 0 0.4rem;
    font-weight: 600;
    letter-spacing: -0.01em;
    color: var(--text-primary);
}
.section-subtitle {
    font-size: 0.88rem;
    color: var(--text-secondary);
    margin-bottom: 1.4rem;
    line-height: 1.6;
}

/* Cards */
.upload-card, .spec-card, .result-card, div[data-testid="stExpander"] {
    background: #FFFFFF;
    border: 1px solid var(--border);
    border-radius: 18px;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04), 0 4px 20px rgba(56, 189, 248, 0.06);
    transition: all 0.4s cubic-bezier(.2,.8,.2,1);
    position: relative;
    overflow: hidden;
}
.upload-card { padding: 1.4rem; }
.spec-card { padding: 1.2rem; }
.upload-card:hover, .spec-card:hover {
    border-color: var(--border-active);
    transform: translateY(-2px);
    box-shadow: 0 8px 32px rgba(56, 189, 248, 0.18);
}
.upload-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, transparent, var(--cyan), var(--blue-deep), transparent);
    opacity: 0;
    transition: opacity 0.4s;
}
.upload-card:hover::before { opacity: 1; }

.card-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: linear-gradient(135deg, rgba(56, 189, 248, 0.10), rgba(99, 102, 241, 0.08));
    border: 1px solid rgba(56, 189, 248, 0.30);
    border-radius: 20px;
    padding: 4px 14px;
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.72rem;
    color: var(--cyan-deep);
    font-weight: 600;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    margin-bottom: 1rem;
}
.card-badge-icon { font-size: 0.9rem; }

.spec-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
.spec-card-label {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.7rem;
    color: var(--cyan-deep);
    text-transform: uppercase;
    letter-spacing: 2.5px;
    font-weight: 700;
    margin-bottom: 0.6rem;
}

/* Model Cards */
.model-card {
    background: #FFFFFF;
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 1rem 1.2rem;
    cursor: pointer;
    transition: all 0.4s cubic-bezier(.2,.8,.2,1);
}
.model-card:hover, .model-card.selected {
    border-color: var(--cyan);
    box-shadow: var(--glow-cyan);
    transform: translateY(-1px);
}
.model-name { font-weight: 600; color: var(--text-primary); font-size: 0.95rem; }
.model-desc { font-size: 0.8rem; color: var(--text-secondary); margin-top: 2px; }
.model-tag {
    display: inline-block;
    background: rgba(56, 189, 248, 0.14);
    color: var(--blue-deep);
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 0.7rem;
    font-weight: 600;
    margin-top: 6px;
}

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, var(--blue) 0%, var(--blue-deep) 100%) !important;
    color: #FFFFFF !important;
    border: none !important;
    padding: 0.9rem 2.5rem !important;
    font-family: 'Space Grotesk', sans-serif !important;
    font-size: 0.95rem !important;
    font-weight: 700 !important;
    border-radius: 14px !important;
    letter-spacing: 1.2px !important;
    text-transform: uppercase !important;
    transition: all 0.3s cubic-bezier(.2,.8,.2,1) !important;
    box-shadow: 0 6px 18px rgba(56, 189, 248, 0.32), inset 0 0 16px rgba(255,255,255,0.18) !important;
    position: relative;
    overflow: hidden;
}
.stButton > button::after {
    content: '';
    position: absolute;
    top: 0; left: -75%;
    width: 50%; height: 100%;
    background: linear-gradient(120deg, transparent, rgba(255,255,255,0.3), transparent);
    transform: skewX(-20deg);
    transition: left 0.6s ease;
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
    50%      { box-shadow: 0 10px 32px rgba(56, 189, 248, 0.55), inset 0 0 22px rgba(255,255,255,0.25); }
}

/* Result Gallery */
.result-card:hover {
    border-color: var(--cyan);
    box-shadow: 0 12px 40px rgba(56, 189, 248, 0.20);
    transform: translateY(-4px);
}
.result-label {
    padding: 0.85rem 1.1rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-top: 1px solid var(--border);
    background: rgba(240, 249, 255, 0.6);
}
.result-label span {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.85rem;
    color: var(--text-secondary);
    font-weight: 500;
}

/* Streamlit input overrides */
.stTextArea textarea, .stTextInput input {
    background: #FFFFFF !important;
    border: 1px solid rgba(148, 163, 184, 0.30) !important;
    border-radius: 12px !important;
    color: var(--text-primary) !important;
    font-family: 'Inter', sans-serif !important;
    padding: 0.85rem !important;
    transition: all 0.3s cubic-bezier(.2,.8,.2,1) !important;
}
.stTextArea textarea:focus, .stTextInput input:focus {
    border-color: var(--cyan) !important;
    box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.16), 0 0 18px rgba(56, 189, 248, 0.12) !important;
    outline: none !important;
}
.stSelectbox > div > div {
    background: #FFFFFF !important;
    border: 1px solid rgba(148, 163, 184, 0.30) !important;
    border-radius: 12px !important;
    color: var(--text-primary) !important;
}
div[data-testid="stFileUploader"] {
    background: rgba(240, 249, 255, 0.55);
    border: 1.5px dashed rgba(56, 189, 248, 0.40);
    border-radius: 14px;
    padding: 0.6rem;
    transition: all 0.4s cubic-bezier(.2,.8,.2,1);
}
div[data-testid="stFileUploader"]:hover {
    border-color: var(--cyan);
    background: rgba(186, 230, 253, 0.20);
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

/* Markdown + expander text on light bg */
.stMarkdown p, .stMarkdown li, .stMarkdown { color: var(--text-primary); }
div[data-testid="stExpander"] summary,
div[data-testid="stExpander"] summary p { color: var(--text-primary) !important; }
div[data-testid="stExpander"] code, .stCode, pre {
    background: rgba(240, 249, 255, 0.7) !important;
    color: var(--text-primary) !important;
    border: 1px solid var(--border);
}

/* Animations */
@keyframes borderGlow {
    0%, 100% { border-color: rgba(56, 189, 248, 0.30); box-shadow: 0 0 18px rgba(56, 189, 248, 0.18); }
    50%      { border-color: rgba(56, 189, 248, 0.85); box-shadow: 0 0 30px rgba(56, 189, 248, 0.40); }
}
.generating { animation: borderGlow 2s ease-in-out infinite; }

/* Refinement Section */
.refine-section {
    background:
        linear-gradient(135deg, rgba(56, 189, 248, 0.06), rgba(99, 102, 241, 0.04)),
        #FFFFFF;
    border: 1px solid var(--border);
    border-radius: 18px;
    padding: 1.6rem;
    margin-top: 1rem;
    box-shadow: var(--glow-soft);
}

/* Responsive */
@media (max-width: 768px) {
    .jb-logo-img { max-height: 48px; }
    .step-container { gap: 1rem; flex-wrap: wrap; }
    .step-connector { width: 32px; }
    .spec-grid { grid-template-columns: 1fr; }
}
</style>
""", unsafe_allow_html=True)


# --- HELPER FUNCTIONS ---

def upload_to_fal(uploaded_file):
    """Upload a reference image. Strips the background and composites onto pure
    white before returning the URL — Seedream then has a clean source and
    won't average a tinted backdrop into the final output.
    """
    img_bytes = uploaded_file.getvalue()
    content_type = uploaded_file.type or "image/png"
    return strip_background_to_white(img_bytes, content_type=content_type)


VIEW_PROMPTS = {
    "Top View": {
        "model": "fal-ai/nano-banana-pro/edit",
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
    """Re-render a finished design from a different camera angle.

    Always uses the originally generated combined design as the source so
    every view is consistent (no drift from re-using a previous view).
    """
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


# --- KEY CHECK ---
if not os.environ.get("FAL_KEY"):
    st.error(
        "**FAL_KEY not found.** Add it in Streamlit Cloud: "
        "Manage app > Settings > Secrets > add `FAL_KEY = \"your-key\"`"
    )

# --- HEADER ---
st.markdown("""
<div class="jb-header">
    <img class="jb-logo-img"
         src="https://jewelbench.ai/wp-content/uploads/2025/05/jewelbench_logo.svg"
         alt="JewelBench" />
    <div class="jb-tagline">Component Composer</div>
</div>
""", unsafe_allow_html=True)

# --- STEP INDICATORS ---
current_step = 1
if any(st.session_state.get(f"img_{i}") for i in range(5)):
    current_step = 2
if st.session_state.get("last_results"):
    current_step = 3

steps_html = f"""
<div class="step-container">
    <div class="step-item {'active' if current_step >= 1 else ''}">
        <div class="step-number">1</div>
        <div class="step-label">Upload References</div>
    </div>
    <div class="step-connector"></div>
    <div class="step-item {'active' if current_step >= 2 else ''}">
        <div class="step-number">2</div>
        <div class="step-label">Specify & Configure</div>
    </div>
    <div class="step-connector"></div>
    <div class="step-item {'active' if current_step >= 3 else ''}">
        <div class="step-number">3</div>
        <div class="step-label">Generate & Refine</div>
    </div>
</div>
"""
st.markdown(steps_html, unsafe_allow_html=True)


# --- STEP 1: UPLOAD REFERENCES ---
st.markdown("""
<div class="section-title">Reference Images</div>
<div class="section-subtitle">Upload jewelry images and describe which component to extract from each</div>
""", unsafe_allow_html=True)

num_images = st.slider(
    "Number of references",
    min_value=2, max_value=5, value=2,
    label_visibility="collapsed",
    help="How many reference images to combine",
)

# Invisible label for the slider
left_pad, slider_area, right_pad = st.columns([1, 3, 1])
with slider_area:
    st.markdown(
        f"<div style='text-align:center;color:var(--text-secondary);font-size:0.8rem;margin-top:-10px;'>"
        f"{num_images} reference images selected</div>",
        unsafe_allow_html=True,
    )

image_specs = []
cols = st.columns(num_images, gap="medium")

for i in range(num_images):
    with cols[i]:
        badge_icons = ["◆", "◇", "○", "□", "△"]
        st.markdown(
            f"""<div class="upload-card">
                <div class="card-badge">
                    <span class="card-badge-icon">{badge_icons[i]}</span>
                    Reference {i+1}
                </div>
            </div>""",
            unsafe_allow_html=True,
        )

        uploaded = st.file_uploader(
            f"ref_{i+1}",
            type=["png", "jpg", "jpeg", "webp", "heic"],
            key=f"img_{i}",
            label_visibility="collapsed",
        )

        if uploaded:
            st.image(uploaded, width="stretch")

        desc = st.text_area(
            "Component to extract",
            placeholder=(
                "Be specific — include color, finish, and detail.\n"
                "e.g., 'pavé white-gold shank with rose-gold accents' "
                "or 'yellow-gold 6-prong solitaire head'"
            ),
            key=f"desc_{i}",
            height=80,
            label_visibility="collapsed",
        )

        image_specs.append({"file": uploaded, "description": desc})


# --- STEP 2: SPECIFICATIONS ---
st.markdown("""
<div class="section-title">Design Specifications</div>
<div class="section-subtitle">Define metal, stones, dimensions, and special requirements</div>
""", unsafe_allow_html=True)

spec_col1, spec_col2 = st.columns(2, gap="medium")

with spec_col1:
    st.markdown(
        '<div class="spec-card-label">METAL TYPE</div>',
        unsafe_allow_html=True,
    )
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

    st.markdown(
        '<div class="spec-card-label">STONE DETAILS</div>',
        unsafe_allow_html=True,
    )
    stones = st.text_area(
        "Stones",
        placeholder="5.68mm Round center stone\nChannel-set side diamonds\nNatural HI I1",
        height=100,
        label_visibility="collapsed",
    )

with spec_col2:
    st.markdown(
        '<div class="spec-card-label">DIMENSIONS</div>',
        unsafe_allow_html=True,
    )
    dimensions = st.text_area(
        "Dimensions",
        placeholder="4.5mm shoulder width\n2.2mm shoulder depth\n2mm shank base width",
        height=100,
        label_visibility="collapsed",
    )

    st.markdown(
        '<div class="spec-card-label">ADDITIONAL NOTES</div>',
        unsafe_allow_html=True,
    )
    notes = st.text_area(
        "Notes",
        placeholder="Cathedral setting, milgrain edges, pave bridge...",
        height=100,
        label_visibility="collapsed",
    )

additional_specs = {
    "metal": metal,
    "stones": stones,
    "dimensions": dimensions,
    "notes": notes,
}


# --- HOW IT WORKS ---
st.markdown(f"""
<div class="section-title">AI Pipeline</div>
<div class="section-subtitle">Step 1: References upload to fal.ai with backgrounds stripped to white via BiRefNet v2. Step 2: Gemini 2.5 Pro enriches your terse component descriptions. Step 3: A master prompt is built with strict silhouette / finish / symmetry / color rules. Step 4: Nano Banana Pro Edit (Gemini 3 Pro Image — multi-reference compositional reasoning) renders at 2K. Step 5: Claude Sonnet 4.5 scores the output against the target description on a calibrated rubric (80% = production-ready) — if below threshold, the validator's per-component diagnosis is fed back as a surgical correction (preserving what was already correct) and Nano Banana Pro re-renders, up to {MAX_VALIDATION_TRIES} attempts. Early-stops if a retry makes things worse.</div>
""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

generate_clicked = st.button(
    "GENERATE COMBINED DESIGN",
    width="stretch",
    type="primary",
)

if generate_clicked:
    has_images = sum(1 for s in image_specs if s["file"]) >= 2
    has_descriptions = sum(1 for s in image_specs if s["description"]) >= 2

    if not has_images:
        st.error("Upload at least 2 reference images to combine.")
    elif not has_descriptions:
        st.warning("Describe what component to use from each image.")
    else:
        progress = st.progress(0, text="Phase 1/5: Cleaning reference backgrounds and uploading to fal.ai...")

        # PHASE 1: Upload + bg-strip each reference natively
        active_specs = [s for s in image_specs if s["file"] and s["description"]]
        try:
            image_urls = [upload_to_fal(s["file"]) for s in active_specs]
        except Exception as e:
            st.error(f"Reference upload failed: {e}")
            st.stop()

        # PHASE 2: Vision-LLM enrichment of terse descriptions
        progress.progress(0.20, text="Phase 2/5: Reading each reference image to enrich your descriptions...")
        enriched_specs = []
        for spec, url in zip(active_specs, image_urls):
            original = spec["description"]
            enriched = enrich_description(url, original)
            enriched_specs.append({"file": spec["file"], "description": enriched, "_original": original})

        # PHASE 3: Build the combination prompt + the validator's target summary
        progress.progress(0.35, text="Phase 3/5: Building combination prompt...")
        combine_prompt = build_combine_prompt(enriched_specs, additional_specs)
        target_summary = build_target_summary(enriched_specs, additional_specs)

        with st.expander("Enriched Descriptions & Generation Prompt", expanded=False):
            st.markdown("**Vision-enriched descriptions** (used to build the prompt):")
            for i, s in enumerate(enriched_specs):
                st.markdown(f"**Image {i+1}** — original: *“{s['_original']}”*")
                st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;enriched: **{s['description']}**")
            st.markdown("---")
            st.markdown("**Validator target description:**")
            st.code(target_summary, language="text")
            st.markdown("**Master prompt sent to Nano Banana Pro:**")
            st.code(combine_prompt, language="text")

        # PHASE 4 + 5: Generate, then self-validate with retry up to MAX_VALIDATION_TRIES.
        # On each attempt below the 85 threshold we feed the validator's diagnosis
        # back into the prompt as a correction directive. We always keep the
        # best-scoring attempt so the user never sees nothing.
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
            phase_base = 0.45 + (attempt - 1) * (0.5 / MAX_VALIDATION_TRIES)
            progress.progress(
                phase_base,
                text=f"Phase 4/5: Rendering attempt {attempt}/{MAX_VALIDATION_TRIES} with Nano Banana Pro...",
            )
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
                st.warning(f"Attempt {attempt} failed: {e}")
                attempts_log.append({"attempt": attempt, "error": str(e)})
                continue

            url = extract_image_url(result)
            if not url:
                attempts_log.append({"attempt": attempt, "error": "no image returned"})
                continue

            try:
                url = strip_url_to_white(url)
            except Exception:
                pass  # keep original URL if post-strip fails

            progress.progress(
                phase_base + (0.5 / MAX_VALIDATION_TRIES) * 0.6,
                text=f"Phase 5/5: AI validating attempt {attempt} against target description...",
            )
            diagnosis = validate_design(url, target_summary)
            score = diagnosis.get("score", 0)
            attempts_log.append({"attempt": attempt, "score": score, "url": url})

            if score > best_score:
                best_url = url
                best_score = score
                best_diagnosis = diagnosis

            if score >= VALIDATION_THRESHOLD:
                break

            # Early-stop: if a retry made things worse (score dropped),
            # the corrective directive isn't helping. Stop here and use
            # the best result so far rather than spending more API calls.
            if attempt > 1 and score < prev_score:
                attempts_log[-1]["regressed"] = True
                break
            prev_score = score

            # Below threshold and we still have retries: append the corrective
            # directive to the prompt and try again.
            if attempt < MAX_VALIDATION_TRIES:
                current_prompt = (
                    combine_prompt
                    + "\n\n"
                    + build_correction_addendum(diagnosis, attempt + 1)
                )

        if best_url:
            results.append(best_url)
            strategy_names.append("Nano Banana Pro Edit (Gemini 3 Pro Image)")
            diagnoses.append(best_diagnosis or {})

        progress.progress(1.0, text="Generation complete")
        time.sleep(0.5)
        progress.empty()

        if results:
            tries_used = len(attempts_log)
            passed = best_score >= VALIDATION_THRESHOLD
            badge_color = "#22D67A" if passed else "#FFB547"
            status_text = (
                f"Passed self-validation in {tries_used} "
                f"{'try' if tries_used == 1 else 'tries'}"
                if passed
                else f"Best of {tries_used} {'try' if tries_used == 1 else 'tries'} "
                     f"(below {VALIDATION_THRESHOLD}% threshold)"
            )

            st.markdown(f"""
            <div class="section-title">Generated Design</div>
            <div class="section-subtitle">
                <span style="display:inline-block;padding:3px 10px;border-radius:10px;
                             background:rgba(34,214,122,0.10);border:1px solid {badge_color};
                             color:{badge_color};font-weight:700;font-size:0.78rem;
                             letter-spacing:1px;text-transform:uppercase;">
                    Match: {best_score}%
                </span>
                &nbsp;&nbsp;{status_text}
            </div>
            """, unsafe_allow_html=True)

            result_cols = st.columns(min(len(results), 4), gap="medium")
            for idx, url in enumerate(results):
                label = strategy_names[idx] if idx < len(strategy_names) else f"Var {idx+1}"

                with result_cols[idx % len(result_cols)]:
                    st.markdown('<div class="result-card">', unsafe_allow_html=True)
                    st.image(url, width="stretch")
                    st.markdown(
                        f"""<div class="result-label">
                            <span>{label}</span>
                            <a href="{url}" target="_blank"
                               style="color:var(--cyan);text-decoration:none;font-size:0.8rem;font-weight:600;">
                                Download
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
                        st.markdown(
                            f"**Attempt {entry['attempt']}** — score "
                            f"**{entry.get('score', 0)}/100**{regressed}"
                        )
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
                        st.markdown("**Rendered incorrectly in final output:**")
                        for w in best_diagnosis["wrong"]:
                            st.markdown(f"- ⚠ {w}")
                    if best_diagnosis.get("suggestion"):
                        st.markdown(f"**Validator's suggestion:** {best_diagnosis['suggestion']}")
                    if best_diagnosis.get("_model"):
                        st.caption(f"Reviewed by {best_diagnosis['_model']}")
                    if best_diagnosis.get("_error"):
                        st.caption(f"Validator note: {best_diagnosis['_error']}")

            st.session_state["last_results"] = results
            st.session_state["last_prompt"] = combine_prompt
            st.session_state["last_target_summary"] = target_summary
            st.session_state["last_image_urls"] = image_urls
            st.session_state["views"] = {}

            with st.spinner("Sonnet computing Bill of Materials..."):
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
        else:
            st.error("No images were generated. Check your FAL_KEY and try again.")


# --- BILL OF MATERIALS SECTION ---
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
        f"USD/INR {_gold['usd_inr']:,.2f} · "
        f"fetched {_ts_str} · source: {_gold['source']}"
    )

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        f"""
    <div class="section-title">Bill of Materials</div>
    <div class="section-subtitle">{_rate_line}</div>
    """,
        unsafe_allow_html=True,
    )

    _metal = _costs["metal"]
    _alloy_pretty = _metal["alloy"].replace("_", " ").title()
    st.markdown(f"**Metal — {_alloy_pretty}**")
    st.markdown(
        f"""
| Alloy | Weight | Rate USD/g | Rate INR/g | Subtotal USD | Subtotal INR |
|---|---|---|---|---|---|
| {_alloy_pretty} | {_metal['weight_g']:.2f} g | ${_metal['rate_usd_per_g']:,.2f} | ₹{_metal['rate_inr_per_g']:,.2f} | ${_metal['total_usd']:,.2f} | ₹{_metal['total_inr']:,.2f} |
"""
    )

    _dia = _costs["diamonds"]
    if _dia["groups"]:
        st.markdown(
            f"**Diamonds — {_dia['total_count']} stones · "
            f"{_dia['total_carat']:.3f} ct total** _(reference wholesale "
            f"rates — edit `diamond_rates.json` to match your supplier)_"
        )
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

    _mf = _costs["manufacturing"]
    st.markdown("**Manufacturing**")
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

    _gt = _costs["grand_total"]
    st.markdown(
        f"""
<div style="padding:18px 22px;border-radius:14px;
            background:linear-gradient(135deg, rgba(14,165,233,0.12), rgba(99,102,241,0.06));
            border:1px solid var(--border);margin-top:14px;">
  <div style="font-size:0.82rem;color:var(--text-secondary);
              text-transform:uppercase;letter-spacing:1.4px;font-weight:600;">
    Total Input Cost
  </div>
  <div style="display:flex;gap:36px;margin-top:6px;align-items:baseline;flex-wrap:wrap;">
    <div>
      <span style="font-family:'Space Grotesk',sans-serif;font-size:2rem;
                   font-weight:700;color:var(--cyan-deep);">${_gt['usd']:,.2f}</span>
      <span style="color:var(--text-secondary);font-size:0.85rem;">&nbsp;USD</span>
    </div>
    <div>
      <span style="font-family:'Space Grotesk',sans-serif;font-size:2rem;
                   font-weight:700;color:var(--cyan-deep);">₹{_gt['inr']:,.2f}</span>
      <span style="color:var(--text-secondary);font-size:0.85rem;">&nbsp;INR</span>
    </div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    _dim = _bom.get("dimensions_mm") or {}
    _rs = _bom.get("ring_size") or {}
    _sr = _bom.get("size_range") or {}
    _tol = _bom.get("weight_tolerance_pct")
    _cn = _bom.get("construction_notes") or ""

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
            f"- BoM by: _{_bom.get('_model', 'sonnet')}_"
        )
        if _cn:
            st.markdown(f"_{_cn}_")

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
        (
            f"- Weight: **{_metal['weight_g']:.2f} g** (tolerance ±{_tol}%)"
            if _tol
            else f"- Weight: **{_metal['weight_g']:.2f} g**"
        ),
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
            "Download BoM (JSON)",
            data=_bom_json,
            file_name=f"{_sku}_bom.json",
            mime="application/json",
            use_container_width=True,
        )
    with _dl_cols[1]:
        st.download_button(
            "Download BoM (Markdown)",
            data=_bom_md,
            file_name=f"{_sku}_bom.md",
            mime="text/markdown",
            use_container_width=True,
        )

elif st.session_state.get("last_bom_error"):
    st.markdown("<br>", unsafe_allow_html=True)
    st.warning(
        f"Bill of Materials unavailable: {st.session_state['last_bom_error']}"
    )


# --- ADDITIONAL VIEWS SECTION ---
if st.session_state.get("last_results"):
    base_design_url = st.session_state["last_results"][0]

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("""
    <div class="section-title">Additional Views</div>
    <div class="section-subtitle">Re-render the generated design from different camera angles, plus a Technical Drawing with mm dimensions and a 10mm scale bar. Every view uses the original generated design as the source. Use ⚡ Generate All to fan out all 5 views in parallel (~60s, ~$0.30 total).</div>
    """, unsafe_allow_html=True)

    view_names = list(VIEW_PROMPTS.keys())

    # Batch button: render every view in parallel.
    if st.button("⚡ Generate All Views (parallel)", key="view_btn_all", width="stretch", type="primary"):
        from concurrent.futures import ThreadPoolExecutor, as_completed
        with st.spinner(f"Rendering {len(view_names)} views in parallel (~60s)..."):
            results = {}
            errors = {}
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
                            results[name] = url
                        else:
                            errors[name] = "no image returned"
                    except Exception as e:
                        errors[name] = str(e)
            if results:
                st.session_state.setdefault("views", {}).update(results)
            for n, msg in errors.items():
                st.warning(f"{n} failed: {msg}")

    # Individual buttons for one-off retries.
    btn_cols = st.columns(len(view_names), gap="small")
    for idx, view_name in enumerate(view_names):
        with btn_cols[idx]:
            if st.button(view_name, key=f"view_btn_{view_name}", width="stretch"):
                with st.spinner(f"Rendering {view_name}..."):
                    try:
                        cfg = VIEW_PROMPTS[view_name]
                        result = generate_view(base_design_url, cfg["prompt"], cfg["model"])
                        url = extract_image_url(result)
                        if url:
                            st.session_state.setdefault("views", {})[view_name] = url
                        else:
                            st.warning(f"{view_name} produced no image.")
                    except Exception as e:
                        st.error(f"{view_name} failed: {e}")

    if st.session_state.get("views"):
        st.markdown("<br>", unsafe_allow_html=True)
        view_items = list(st.session_state["views"].items())
        view_result_cols = st.columns(min(len(view_items), 4), gap="medium")
        for idx, (vname, vurl) in enumerate(view_items):
            with view_result_cols[idx % len(view_result_cols)]:
                st.markdown('<div class="result-card">', unsafe_allow_html=True)
                st.image(vurl, width="stretch")
                st.markdown(
                    f"""<div class="result-label">
                        <span>{vname}</span>
                        <a href="{vurl}" target="_blank"
                           style="color:var(--cyan);text-decoration:none;font-size:0.8rem;font-weight:600;">
                            Download
                        </a>
                    </div></div>""",
                    unsafe_allow_html=True,
                )


# --- REFINEMENT SECTION ---
if st.session_state.get("last_results"):
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("""
    <div class="refine-section">
        <div class="section-title" style="margin-top:0;">Refine Your Design</div>
        <div class="section-subtitle">Describe modifications and regenerate with adjustments</div>
    </div>
    """, unsafe_allow_html=True)

    refinement = st.text_input(
        "Modifications",
        placeholder="e.g., 'Thinner prongs, add milgrain detail, make the halo more pronounced'",
        label_visibility="collapsed",
    )

    if st.button("REGENERATE WITH CHANGES", width="stretch"):
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

            # Update the validator's target with the refinement so the score
            # reflects what the user actually asked for, not the original spec.
            base_target = st.session_state.get("last_target_summary", "")
            refinement_target = (
                f"{base_target}\n\nADDITIONAL REFINEMENT REQUESTED: "
                f"{refinement.strip()}"
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

            with st.spinner(f"Regenerating + validating (up to {MAX_VALIDATION_TRIES} tries)..."):
                for attempt in range(1, MAX_VALIDATION_TRIES + 1):
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

                    diagnosis = validate_design(url, refinement_target)
                    score = diagnosis.get("score", 0)
                    r_attempts_log.append({"attempt": attempt, "score": score, "url": url})

                    if score > r_best_score:
                        r_best_url = url
                        r_best_score = score
                        r_best_diagnosis = diagnosis

                    if score >= VALIDATION_THRESHOLD:
                        break
                    if attempt > 1 and score < r_prev_score:
                        r_attempts_log[-1]["regressed"] = True
                        break
                    r_prev_score = score

                    if attempt < MAX_VALIDATION_TRIES:
                        r_current_prompt = (
                            refined_prompt
                            + "\n\n"
                            + build_correction_addendum(diagnosis, attempt + 1)
                        )

            if r_best_url:
                r_passed = r_best_score >= VALIDATION_THRESHOLD
                r_badge_color = "#22D67A" if r_passed else "#FFB547"
                r_tries_used = len(r_attempts_log)
                r_status_text = (
                    f"Passed in {r_tries_used} {'try' if r_tries_used == 1 else 'tries'}"
                    if r_passed
                    else f"Best of {r_tries_used} {'try' if r_tries_used == 1 else 'tries'} "
                         f"(below {VALIDATION_THRESHOLD}% threshold)"
                )

                st.markdown(f"""
                <div class="section-title">Refined Design</div>
                <div class="section-subtitle">
                    <span style="display:inline-block;padding:3px 10px;border-radius:10px;
                                 background:rgba(34,214,122,0.10);border:1px solid {r_badge_color};
                                 color:{r_badge_color};font-weight:700;font-size:0.78rem;
                                 letter-spacing:1px;text-transform:uppercase;">
                        Match: {r_best_score}%
                    </span>
                    &nbsp;&nbsp;{r_status_text}
                </div>
                """, unsafe_allow_html=True)

                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    st.image(r_best_url, width="stretch")
                    st.markdown(
                        f'<div style="text-align:center;margin-top:8px;">'
                        f'<a href="{r_best_url}" target="_blank" '
                        f'style="color:var(--cyan-deep);font-weight:600;text-decoration:none;">'
                        f'Download Full Resolution</a></div>',
                        unsafe_allow_html=True,
                    )

                with st.expander("Refinement Self-Validation Report", expanded=not r_passed):
                    for entry in r_attempts_log:
                        if "error" in entry:
                            st.markdown(f"**Attempt {entry['attempt']}** — failed: {entry['error']}")
                        else:
                            regressed = " — *stopped (score regressed)*" if entry.get("regressed") else ""
                            st.markdown(
                                f"**Attempt {entry['attempt']}** — score "
                                f"**{entry.get('score', 0)}/100**{regressed}"
                            )
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
            else:
                st.error("Refinement failed — no image was generated. Check your FAL_KEY and try again.")


# --- FOOTER ---
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown("""
<div style="text-align:center;padding:2rem 0;border-top:1px solid var(--border);">
    <span style="color:var(--text-muted);font-size:0.75rem;letter-spacing:2px;">
        POWERED BY JEWELBENCH AI
    </span>
</div>
""", unsafe_allow_html=True)
