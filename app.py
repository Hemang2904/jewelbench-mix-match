import streamlit as st
import fal_client
import os
import time
from prompts import build_combine_prompt
from preprocessing import strip_background_to_white, strip_url_to_white, enrich_description
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
    page_title="JewelBench - Mix & Match Designer",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --- PREMIUM CSS ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Space+Grotesk:wght@400;500;600;700&family=Orbitron:wght@500;600;700&display=swap');

:root {
    --bg-deep: #050B1E;
    --bg-mid: #0B1838;
    --bg-elevated: #142253;
    --glass: rgba(120, 180, 255, 0.06);
    --glass-strong: rgba(120, 180, 255, 0.10);
    --border: rgba(120, 200, 255, 0.18);
    --border-active: rgba(0, 212, 255, 0.55);
    --cyan: #00D4FF;
    --cyan-soft: #6DC5FF;
    --cyan-deep: #0A8FCC;
    --blue: #4A8CFF;
    --blue-deep: #2D5BFF;
    --purple: #6B5DFF;
    --text-primary: #E8F4FF;
    --text-secondary: #93B4D9;
    --text-muted: #5A7BA0;
    --glow-cyan: 0 0 24px rgba(0, 212, 255, 0.35);
    --glow-soft: 0 0 60px rgba(0, 212, 255, 0.10);
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
        radial-gradient(1200px 700px at 15% -10%, rgba(74, 140, 255, 0.25), transparent 60%),
        radial-gradient(900px 600px at 100% 110%, rgba(107, 93, 255, 0.20), transparent 55%),
        radial-gradient(700px 500px at 50% 50%, rgba(0, 212, 255, 0.06), transparent 70%),
        linear-gradient(180deg, #050B1E 0%, #0B1838 60%, #050B1E 100%) !important;
    color: var(--text-primary);
    font-family: 'Inter', sans-serif;
}
.stApp::before {
    content: "";
    position: fixed;
    inset: 0;
    pointer-events: none;
    background-image:
        linear-gradient(rgba(120, 200, 255, 0.05) 1px, transparent 1px),
        linear-gradient(90deg, rgba(120, 200, 255, 0.05) 1px, transparent 1px);
    background-size: 56px 56px;
    mask-image: radial-gradient(ellipse at center, black 40%, transparent 80%);
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
    box-shadow: 0 0 14px rgba(0, 212, 255, 0.6);
}
.jb-logo {
    font-family: 'Orbitron', 'Space Grotesk', sans-serif;
    font-size: 3rem;
    font-weight: 700;
    background: linear-gradient(135deg, #C8EBFF 0%, var(--cyan) 45%, var(--blue) 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    letter-spacing: 6px;
    margin-bottom: 0.3rem;
    animation: logoPulse 4s ease-in-out infinite;
}
@keyframes logoPulse {
    0%, 100% { filter: drop-shadow(0 0 12px rgba(0,212,255,0.35)); }
    50%      { filter: drop-shadow(0 0 24px rgba(0,212,255,0.65)); }
}
.jb-tagline {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.95rem;
    color: var(--cyan-soft);
    font-weight: 400;
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
    border: 1.5px solid rgba(120, 200, 255, 0.25);
    color: var(--text-muted);
    background: rgba(10, 25, 60, 0.5);
    backdrop-filter: blur(8px);
    transition: all 0.4s cubic-bezier(.2,.8,.2,1);
}
.step-item.active .step-number {
    border-color: var(--cyan);
    color: #02101F;
    background: linear-gradient(135deg, var(--cyan-soft), var(--cyan));
    box-shadow: 0 0 24px rgba(0, 212, 255, 0.55), inset 0 0 12px rgba(255,255,255,0.25);
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
    background: linear-gradient(90deg, rgba(120, 200, 255, 0.1), rgba(0, 212, 255, 0.4), rgba(120, 200, 255, 0.1));
    align-self: center;
}

/* Section Titles */
.section-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.55rem;
    margin: 2.2rem 0 0.4rem;
    font-weight: 600;
    letter-spacing: -0.01em;
    background: linear-gradient(120deg, #FFFFFF 0%, var(--cyan-soft) 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.section-subtitle {
    font-size: 0.88rem;
    color: var(--text-secondary);
    margin-bottom: 1.4rem;
    line-height: 1.6;
}

/* Glassmorphic Cards */
.upload-card, .spec-card, .result-card, div[data-testid="stExpander"] {
    background: var(--glass);
    border: 1px solid var(--border);
    border-radius: 18px;
    backdrop-filter: blur(14px);
    -webkit-backdrop-filter: blur(14px);
    transition: all 0.4s cubic-bezier(.2,.8,.2,1);
    position: relative;
    overflow: hidden;
}
.upload-card { padding: 1.4rem; }
.spec-card { padding: 1.2rem; }
.upload-card:hover, .spec-card:hover {
    border-color: var(--border-active);
    background: var(--glass-strong);
    transform: translateY(-2px);
    box-shadow: var(--glow-cyan), 0 12px 40px rgba(0, 30, 80, 0.4);
}
.upload-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, transparent, var(--cyan), var(--blue), transparent);
    opacity: 0;
    transition: opacity 0.4s;
}
.upload-card:hover::before { opacity: 1; }

.card-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: linear-gradient(135deg, rgba(0,212,255,0.10), rgba(74,140,255,0.10));
    border: 1px solid rgba(0, 212, 255, 0.30);
    border-radius: 20px;
    padding: 4px 14px;
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.72rem;
    color: var(--cyan);
    font-weight: 600;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    margin-bottom: 1rem;
    box-shadow: inset 0 0 10px rgba(0, 212, 255, 0.06);
}
.card-badge-icon { font-size: 0.9rem; }

.spec-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
.spec-card-label {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.7rem;
    color: var(--cyan);
    text-transform: uppercase;
    letter-spacing: 2.5px;
    font-weight: 700;
    margin-bottom: 0.6rem;
}

/* Model Cards */
.model-card {
    background: var(--glass);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 1rem 1.2rem;
    cursor: pointer;
    backdrop-filter: blur(10px);
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
    background: rgba(74,140,255,0.15);
    color: var(--blue);
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 0.7rem;
    font-weight: 600;
    margin-top: 6px;
}

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, var(--cyan) 0%, var(--blue) 100%) !important;
    color: #02101F !important;
    border: none !important;
    padding: 0.9rem 2.5rem !important;
    font-family: 'Space Grotesk', sans-serif !important;
    font-size: 0.95rem !important;
    font-weight: 700 !important;
    border-radius: 14px !important;
    letter-spacing: 1.2px !important;
    text-transform: uppercase !important;
    transition: all 0.3s cubic-bezier(.2,.8,.2,1) !important;
    box-shadow: 0 6px 24px rgba(0, 212, 255, 0.30), inset 0 0 16px rgba(255,255,255,0.10) !important;
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
    box-shadow: 0 10px 40px rgba(0, 212, 255, 0.55), inset 0 0 22px rgba(255,255,255,0.15) !important;
}
.stButton > button:hover::after { left: 130%; }
.stButton > button:active { transform: translateY(0); }
button[kind="primary"], button[kind="primaryFormSubmit"] {
    animation: ctaPulse 2.4s ease-in-out infinite;
}
@keyframes ctaPulse {
    0%, 100% { box-shadow: 0 6px 24px rgba(0, 212, 255, 0.30), inset 0 0 16px rgba(255,255,255,0.10); }
    50%      { box-shadow: 0 10px 44px rgba(0, 212, 255, 0.65), inset 0 0 22px rgba(255,255,255,0.20); }
}

/* Result Gallery */
.result-card:hover {
    border-color: var(--cyan);
    box-shadow: 0 12px 48px rgba(0, 212, 255, 0.25), var(--glow-soft);
    transform: translateY(-4px);
}
.result-label {
    padding: 0.85rem 1.1rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-top: 1px solid var(--border);
    background: linear-gradient(180deg, transparent, rgba(0, 30, 80, 0.25));
}
.result-label span {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.85rem;
    color: var(--text-secondary);
    font-weight: 500;
}

/* Streamlit input overrides */
.stTextArea textarea, .stTextInput input {
    background: rgba(10, 25, 60, 0.55) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
    color: var(--text-primary) !important;
    font-family: 'Inter', sans-serif !important;
    padding: 0.85rem !important;
    backdrop-filter: blur(8px);
    transition: all 0.3s cubic-bezier(.2,.8,.2,1) !important;
}
.stTextArea textarea:focus, .stTextInput input:focus {
    border-color: var(--cyan) !important;
    box-shadow: 0 0 0 3px rgba(0, 212, 255, 0.18), 0 0 24px rgba(0, 212, 255, 0.20) !important;
    outline: none !important;
}
.stSelectbox > div > div {
    background: rgba(10, 25, 60, 0.55) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
    color: var(--text-primary) !important;
    backdrop-filter: blur(8px);
}
div[data-testid="stFileUploader"] {
    background: rgba(10, 25, 60, 0.4);
    border: 1.5px dashed rgba(0, 212, 255, 0.30);
    border-radius: 14px;
    padding: 0.6rem;
    backdrop-filter: blur(10px);
    transition: all 0.4s cubic-bezier(.2,.8,.2,1);
}
div[data-testid="stFileUploader"]:hover {
    border-color: var(--cyan);
    background: rgba(0, 212, 255, 0.05);
    box-shadow: var(--glow-cyan);
}
.stSlider > div > div > div { background: var(--cyan) !important; }
.stSlider > div > div > div > div {
    background: linear-gradient(135deg, var(--cyan), var(--blue)) !important;
    box-shadow: 0 0 12px rgba(0, 212, 255, 0.6) !important;
}
.stProgress > div > div > div {
    background: linear-gradient(90deg, var(--cyan), var(--blue), var(--purple)) !important;
    box-shadow: 0 0 12px rgba(0, 212, 255, 0.5);
}
.stDivider { border-color: var(--border) !important; }

/* Animations */
@keyframes borderGlow {
    0%, 100% { border-color: rgba(0, 212, 255, 0.30); box-shadow: 0 0 18px rgba(0,212,255,0.20); }
    50%      { border-color: rgba(0, 212, 255, 0.85); box-shadow: 0 0 36px rgba(0,212,255,0.50); }
}
.generating { animation: borderGlow 2s ease-in-out infinite; }

/* Refinement Section */
.refine-section {
    background:
        linear-gradient(135deg, rgba(0, 212, 255, 0.07), rgba(107, 93, 255, 0.07)),
        var(--glass);
    border: 1px solid var(--border);
    border-radius: 18px;
    padding: 1.6rem;
    margin-top: 1rem;
    backdrop-filter: blur(14px);
    box-shadow: var(--glow-soft);
}

/* Responsive */
@media (max-width: 768px) {
    .jb-logo { font-size: 2rem; letter-spacing: 3px; }
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

    return "\n\n".join(sections)


def generate_combined_design(image_urls, prompt):
    """Run Seedream v4 — the only model that consistently preserves both
    component structure and metal color on jewelry part-swaps."""
    return [
        {
            "name": "Seedream v4 Edit (ByteDance)",
            "fn": lambda: fal_client.subscribe(
                "fal-ai/bytedance/seedream/v4/edit",
                arguments={
                    "image_urls": image_urls,
                    "prompt": prompt,
                    "num_images": 1,
                    "image_size": "auto_2K",
                },
            ),
        },
    ]


VIEW_PROMPTS = {
    "Top View": {
        "model": "fal-ai/bytedance/seedream/v4/edit",
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
        "model": "fal-ai/bytedance/seedream/v4/edit",
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
        "model": "fal-ai/bytedance/seedream/v4/edit",
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
        "model": "fal-ai/bytedance/seedream/v4/edit",
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
        "model": "fal-ai/gemini-25-flash-image/edit",
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


def generate_view(base_url, view_prompt, model="fal-ai/bytedance/seedream/v4/edit"):
    """Re-render a finished design from a different camera angle.

    Always uses the originally generated combined design as the source so
    every view is consistent (no drift from re-using a previous view).
    """
    args = {
        "image_urls": [base_url],
        "prompt": view_prompt,
        "num_images": 1,
    }
    if "seedream" in model:
        args["image_size"] = "auto_2K"
    else:
        args["output_format"] = "png"
    return fal_client.subscribe(model, arguments=args)


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
    <div class="jb-logo">JewelBench</div>
    <div class="jb-tagline">Mix & Match Designer</div>
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
st.markdown("""
<div class="section-title">AI Pipeline</div>
<div class="section-subtitle">Step 1: References upload directly to fal.ai. Step 2: A Seedream-tuned master prompt is built with strict silhouette / finish / symmetry / color preservation rules. Step 3: Seedream v4 Edit (ByteDance) renders the combined design at 2K resolution natively from both references.</div>
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
        progress = st.progress(0, text="Phase 1/4: Cleaning reference backgrounds and uploading to fal.ai...")

        # PHASE 1: Upload + bg-strip each reference natively
        active_specs = [s for s in image_specs if s["file"] and s["description"]]
        try:
            image_urls = [upload_to_fal(s["file"]) for s in active_specs]
        except Exception as e:
            st.error(f"Reference upload failed: {e}")
            st.stop()

        # PHASE 2: Vision-LLM enrichment of terse descriptions
        progress.progress(0.25, text="Phase 2/4: Reading each reference image to enrich your descriptions...")
        enriched_specs = []
        for spec, url in zip(active_specs, image_urls):
            original = spec["description"]
            enriched = enrich_description(url, original)
            enriched_specs.append({"file": spec["file"], "description": enriched, "_original": original})

        # PHASE 3: Build the combination prompt
        progress.progress(0.4, text="Phase 3/4: Building combination prompt...")
        combine_prompt = build_combine_prompt(enriched_specs, additional_specs)

        with st.expander("Enriched Descriptions & Generation Prompt", expanded=False):
            st.markdown("**Vision-enriched descriptions** (used to build the prompt):")
            for i, s in enumerate(enriched_specs):
                st.markdown(f"**Image {i+1}** — original: *“{s['_original']}”*")
                st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;enriched: **{s['description']}**")
            st.markdown("---")
            st.markdown("**Master prompt sent to Seedream:**")
            st.code(combine_prompt, language="text")

        # PHASE 4: Generate via multi-image edit models
        progress.progress(0.55, text="Phase 4/4: Generating combined designs...")
        strategies = generate_combined_design(image_urls, combine_prompt)
        results = []
        strategy_names = []

        if strategies:
            for si, strategy in enumerate(strategies):
                progress.progress(
                    0.55 + (si + 1) / (len(strategies) * 3),
                    text=f"Phase 4/4: Rendering variation {si+1}/{len(strategies)} ({strategy['name']})...",
                )
                try:
                    result = strategy["fn"]()
                    url = extract_image_url(result)
                    if url:
                        # Post-strip the output background so we always end up
                        # on RGB(255,255,255) regardless of Seedream variance.
                        try:
                            url = strip_url_to_white(url)
                        except Exception:
                            pass  # keep original URL if post-strip fails
                        results.append(url)
                        strategy_names.append(strategy["name"])
                except Exception as e:
                    st.warning(f"Strategy '{strategy['name']}' failed: {e}")

        progress.progress(1.0, text="Generation complete")
        time.sleep(0.5)
        progress.empty()

        if results:
            st.markdown("""
            <div class="section-title">Generated Designs</div>
            <div class="section-subtitle">Each variation combines your reference images into a single new piece</div>
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

            st.session_state["last_results"] = results
            st.session_state["last_prompt"] = combine_prompt
            st.session_state["last_image_urls"] = image_urls
            st.session_state["views"] = {}
        else:
            st.error("No images were generated. Check your FAL_KEY and try again.")


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

            image_urls = st.session_state.get("last_image_urls") or [
                upload_to_fal(s["file"]) for s in image_specs if s["file"]
            ]

            with st.spinner("Regenerating with modifications..."):
                try:
                    result = fal_client.subscribe(
                        "fal-ai/bytedance/seedream/v4/edit",
                        arguments={
                            "image_urls": image_urls,
                            "prompt": refined_prompt,
                            "num_images": 1,
                            "image_size": "auto_2K",
                        },
                    )
                    url = extract_image_url(result)
                    if url:
                        st.markdown('<div class="section-title">Refined Design</div>', unsafe_allow_html=True)
                        col1, col2, col3 = st.columns([1, 2, 1])
                        with col2:
                            st.image(url, width="stretch")
                            st.markdown(
                                f'<div style="text-align:center;margin-top:8px;">'
                                f'<a href="{url}" target="_blank" '
                                f'style="color:var(--cyan);font-weight:600;text-decoration:none;">'
                                f'Download Full Resolution</a></div>',
                                unsafe_allow_html=True,
                            )
                except Exception as e:
                    st.error(f"Regeneration failed: {str(e)}")


# --- FOOTER ---
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown("""
<div style="text-align:center;padding:2rem 0;border-top:1px solid rgba(201,168,76,0.1);">
    <span style="color:var(--text-muted);font-size:0.75rem;letter-spacing:2px;">
        POWERED BY JEWELBENCH AI
    </span>
</div>
""", unsafe_allow_html=True)
