import streamlit as st
import fal_client
import os
import time
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
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Playfair+Display:wght@400;500;600;700&display=swap');

:root {
    --gold: #C9A84C;
    --gold-light: #E8D48B;
    --gold-dark: #8B6914;
    --bg-primary: #08090D;
    --bg-card: #0F1117;
    --bg-card-hover: #161822;
    --bg-elevated: #1A1C2B;
    --border: rgba(201,168,76,0.15);
    --border-active: rgba(201,168,76,0.5);
    --text-primary: #F0ECE3;
    --text-secondary: #8A8A9A;
    --text-muted: #5A5A6A;
    --accent-blue: #4A6CF7;
    --accent-purple: #7C3AED;
    --glow: 0 0 30px rgba(201,168,76,0.15);
}

.stApp {
    background: var(--bg-primary);
    font-family: 'Inter', sans-serif;
}

/* Hide default streamlit branding */
#MainMenu, footer, header {visibility: hidden;}
.stDeployButton {display: none;}

/* Custom Header */
.jb-header {
    text-align: center;
    padding: 2rem 0 1rem;
    position: relative;
}
.jb-header::after {
    content: '';
    position: absolute;
    bottom: 0;
    left: 50%;
    transform: translateX(-50%);
    width: 120px;
    height: 2px;
    background: linear-gradient(90deg, transparent, var(--gold), transparent);
}
.jb-logo {
    font-family: 'Playfair Display', serif;
    font-size: 2.8rem;
    font-weight: 700;
    background: linear-gradient(135deg, var(--gold-light), var(--gold), var(--gold-dark));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    letter-spacing: 2px;
    margin-bottom: 0.2rem;
}
.jb-tagline {
    font-size: 1rem;
    color: var(--text-secondary);
    font-weight: 300;
    letter-spacing: 4px;
    text-transform: uppercase;
}

/* Step Indicators */
.step-container {
    display: flex;
    justify-content: center;
    gap: 3rem;
    margin: 2rem 0;
    padding: 1.2rem 0;
}
.step-item {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    opacity: 0.4;
    transition: all 0.3s ease;
}
.step-item.active {
    opacity: 1;
}
.step-number {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 600;
    font-size: 0.85rem;
    border: 2px solid var(--text-muted);
    color: var(--text-muted);
    transition: all 0.3s ease;
}
.step-item.active .step-number {
    border-color: var(--gold);
    color: var(--bg-primary);
    background: linear-gradient(135deg, var(--gold-light), var(--gold));
    box-shadow: 0 0 20px rgba(201,168,76,0.3);
}
.step-label {
    font-size: 0.85rem;
    font-weight: 500;
    color: var(--text-muted);
}
.step-item.active .step-label {
    color: var(--text-primary);
}
.step-connector {
    width: 60px;
    height: 2px;
    background: var(--text-muted);
    align-self: center;
    opacity: 0.3;
}

/* Section Titles */
.section-title {
    font-family: 'Playfair Display', serif;
    font-size: 1.5rem;
    color: var(--text-primary);
    margin: 2rem 0 0.5rem;
    font-weight: 500;
}
.section-subtitle {
    font-size: 0.85rem;
    color: var(--text-secondary);
    margin-bottom: 1.5rem;
}

/* Upload Cards */
.upload-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 1.5rem;
    transition: all 0.3s ease;
    position: relative;
    overflow: hidden;
}
.upload-card:hover {
    border-color: var(--border-active);
    background: var(--bg-card-hover);
    box-shadow: var(--glow);
}
.upload-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 3px;
    background: linear-gradient(90deg, var(--gold), var(--accent-purple));
    opacity: 0;
    transition: opacity 0.3s;
}
.upload-card:hover::before {
    opacity: 1;
}
.card-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(201,168,76,0.1);
    border: 1px solid rgba(201,168,76,0.2);
    border-radius: 20px;
    padding: 4px 14px;
    font-size: 0.75rem;
    color: var(--gold);
    font-weight: 600;
    letter-spacing: 1px;
    text-transform: uppercase;
    margin-bottom: 1rem;
}
.card-badge-icon {
    font-size: 0.9rem;
}

/* Spec Cards */
.spec-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
}
.spec-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.2rem;
    transition: all 0.3s ease;
}
.spec-card:hover {
    border-color: var(--border-active);
}
.spec-card-label {
    font-size: 0.7rem;
    color: var(--gold);
    text-transform: uppercase;
    letter-spacing: 2px;
    font-weight: 600;
    margin-bottom: 0.5rem;
}

/* Model Selector */
.model-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1rem 1.2rem;
    cursor: pointer;
    transition: all 0.3s ease;
}
.model-card:hover, .model-card.selected {
    border-color: var(--gold);
    box-shadow: var(--glow);
}
.model-name {
    font-weight: 600;
    color: var(--text-primary);
    font-size: 0.95rem;
}
.model-desc {
    font-size: 0.8rem;
    color: var(--text-secondary);
    margin-top: 2px;
}
.model-tag {
    display: inline-block;
    background: rgba(74,108,247,0.15);
    color: var(--accent-blue);
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 0.7rem;
    font-weight: 600;
    margin-top: 6px;
}

/* Generate Button */
.stButton > button {
    background: linear-gradient(135deg, var(--gold), var(--gold-dark)) !important;
    color: var(--bg-primary) !important;
    border: none !important;
    padding: 0.9rem 2.5rem !important;
    font-size: 1rem !important;
    font-weight: 700 !important;
    border-radius: 12px !important;
    letter-spacing: 1px !important;
    text-transform: uppercase !important;
    transition: all 0.3s ease !important;
    box-shadow: 0 4px 20px rgba(201,168,76,0.3) !important;
}
.stButton > button:hover {
    box-shadow: 0 6px 30px rgba(201,168,76,0.5) !important;
    transform: translateY(-1px);
}
.stButton > button:active {
    transform: translateY(0px);
}

/* Result Gallery */
.result-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 16px;
    overflow: hidden;
    transition: all 0.4s ease;
}
.result-card:hover {
    border-color: var(--gold);
    box-shadow: 0 8px 40px rgba(201,168,76,0.2);
    transform: translateY(-4px);
}
.result-label {
    padding: 0.8rem 1rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-top: 1px solid var(--border);
}
.result-label span {
    font-size: 0.85rem;
    color: var(--text-secondary);
    font-weight: 500;
}

/* Streamlit overrides */
.stTextArea textarea, .stTextInput input {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    color: var(--text-primary) !important;
    font-family: 'Inter', sans-serif !important;
    padding: 0.8rem !important;
    transition: border-color 0.3s !important;
}
.stTextArea textarea:focus, .stTextInput input:focus {
    border-color: var(--gold) !important;
    box-shadow: 0 0 0 1px var(--gold) !important;
}
.stSelectbox > div > div {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
}
div[data-testid="stFileUploader"] {
    background: var(--bg-card);
    border: 2px dashed rgba(201,168,76,0.2);
    border-radius: 12px;
    padding: 0.5rem;
    transition: all 0.3s ease;
}
div[data-testid="stFileUploader"]:hover {
    border-color: rgba(201,168,76,0.5);
    background: var(--bg-card-hover);
}
.stSlider > div > div > div {
    background: var(--gold) !important;
}
.stProgress > div > div > div {
    background: linear-gradient(90deg, var(--gold), var(--accent-purple)) !important;
}
div[data-testid="stExpander"] {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 12px;
}
.stDivider {
    border-color: var(--border) !important;
}

/* Animated gradient border for results */
@keyframes borderGlow {
    0%, 100% { border-color: rgba(201,168,76,0.3); }
    50% { border-color: rgba(201,168,76,0.7); }
}
.generating {
    animation: borderGlow 2s ease-in-out infinite;
}

/* Refinement Section */
.refine-section {
    background: linear-gradient(135deg, rgba(201,168,76,0.05), rgba(124,58,237,0.05));
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 1.5rem;
    margin-top: 1rem;
}

/* Responsive */
@media (max-width: 768px) {
    .jb-logo { font-size: 1.8rem; }
    .step-container { gap: 1rem; flex-wrap: wrap; }
    .spec-grid { grid-template-columns: 1fr; }
}
</style>
""", unsafe_allow_html=True)


# --- HELPER FUNCTIONS ---

def upload_to_fal(uploaded_file):
    img_bytes = uploaded_file.getvalue()
    return fal_client.upload(img_bytes, content_type=uploaded_file.type or "image/png")


def build_combine_prompt(image_specs, additional_specs):
    """Master prompt tuned for fal-ai/bytedance/seedream/v4/edit.

    Seedream v4 responds best to tight imperative prompts with crisp
    per-image extraction lines and short rule blocks. Avoid long meta
    framing — Seedream handles structural fidelity natively when told
    plainly.
    """
    active_specs = [s for s in image_specs if s["file"] and s["description"]]

    ref_lines = []
    component_summary = []
    for i, spec in enumerate(active_specs):
        n = i + 1
        desc = spec["description"].strip().rstrip(".")
        ref_lines.append(
            f"- From Image {n}: take ONLY the {desc}. Reproduce it 1:1 — "
            f"exact metal color (rose-gold stays rose-gold, yellow-gold stays "
            f"yellow-gold, white-gold stays white-gold, platinum stays "
            f"platinum), shape, prongs, stones, surface finish, profile, "
            f"width, taper, and proportions. Ignore everything else in Image {n}."
        )
        component_summary.append(f"the {desc} (from Image {n})")

    refs_block = "\n".join(ref_lines)
    components_text = " + ".join(component_summary)

    component_checklist = "\n".join(
        f"- Is the {spec['description'].strip().rstrip('.')} from Image {i+1} "
        f"visibly present in the output? It MUST be."
        for i, spec in enumerate(active_specs)
    )

    sections = [
        "Combine the reference images into ONE single new piece of jewelry. "
        "This is a precise part-swap — copy each extracted component exactly. "
        "Only the joint where components meet may be invented.",

        f"EXTRACT FROM EACH IMAGE\n{refs_block}",

        "CONSTRUCTION\n"
        f"Assemble: {components_text}. Connect them with a clean, "
        "structurally sound joint. Two-tone (or three-tone) metal is correct "
        "and intended — do not unify, average, or harmonize metal colors "
        "across components. If one component is rose-gold and the other is "
        "white-gold, the output shows rose-gold meeting white-gold at a "
        "crisp boundary. If three different metal colors appear across the "
        "components, all three appear in the output.",

        "ANTI-COPY RULE (CRITICAL)\n"
        "- The output MUST NOT be a copy or near-copy of any single "
        "reference image. It is a NEW piece that visibly fuses parts from "
        "every reference.\n"
        "- The output MUST visibly contain the specified component from "
        "EVERY reference image listed above. Missing any one of them is a "
        "failure.\n"
        "- If your output looks like Image 1 with no Image 2 elements (or "
        "vice versa), discard it and try again — that is the most common "
        "failure mode for this task.\n"
        "- Specifically: a viewer comparing the output side-by-side with "
        "the references must immediately see which part came from which "
        "reference.",

        "SILHOUETTE PRESERVATION (CRITICAL)\n"
        "- Reproduce the exact 2D outline and silhouette of each extracted "
        "component. If the head is shaped like a flower with petals, the "
        "output head is shaped like a flower with petals. If the head is a "
        "6-prong solitaire, the output head is a 6-prong solitaire.\n"
        "- Decorative elements that define the shape — petals, halos, "
        "leaves, scrollwork, filigree, openwork, basket cages — MUST appear "
        "in the output exactly as in the source.\n"
        "- Do NOT simplify an ornate component into a plain one (e.g., "
        "turning a flower halo into a bare 4-prong setting).\n"
        "- Do NOT embellish a plain component into an ornate one.\n"
        "- Color alone is not enough — match the SHAPE.",

        "SURFACE FINISH PRESERVATION\n"
        "- If the source surface is high-polished and smooth, the output "
        "surface is high-polished and smooth.\n"
        "- Do NOT add brushed, hammered, knurled, satin, matte, sandblasted, "
        "wood-grain, or any textured finish that is not in the source.\n"
        "- Do NOT add milgrain edges, engraving lines, or hatching that is "
        "not in the source.",

        "PRESERVATION RULES (STRICT)\n"
        "- Do NOT add stones, diamonds, pavé, channel-set stones, halos, "
        "milgrain, engraving, filigree, or any decoration that is not "
        "visible on that component in its source image.\n"
        "- Do NOT remove stones, prongs, or details that ARE visible in "
        "the source component.\n"
        "- If a component is plain and smooth in the source, keep it plain "
        "and smooth. If it is set with stones, keep exactly those stones in "
        "the same arrangement.\n"
        "- Do NOT change band thickness, shoulder profile, prong count, "
        "prong shape, or stone size.\n"
        "- Do NOT redesign, stylize, or reinterpret — copy.",

        f"VERIFY BEFORE FINALIZING\n{component_checklist}\n"
        f"- Does each extracted component keep its original metal color? It MUST.\n"
        f"- Does each extracted component keep its original SHAPE/silhouette "
        f"(petals, halos, prong count, band profile)? It MUST.\n"
        f"- Are all surfaces in the output finished the same way as their "
        f"source (no added brushed/textured/matte finish)? They MUST be.\n"
        f"- Is the background pure white RGB(255,255,255), not gray? It MUST be.\n"
        f"- Is the output clearly a NEW piece (not a copy of any single reference)? "
        f"It MUST be.",
    ]

    if additional_specs.get("metal"):
        sections.append(
            f"METAL OVERRIDE\nRender the entire piece in {additional_specs['metal']}, "
            "replacing the original metal colors of all references. This "
            "overrides the color preservation rules above."
        )

    if additional_specs.get("stones"):
        sections.append(f"STONES\n{additional_specs['stones']}")

    if additional_specs.get("dimensions"):
        sections.append(f"PROPORTIONS\n{additional_specs['dimensions']}")

    if additional_specs.get("notes"):
        sections.append(f"NOTES\n{additional_specs['notes']}")

    sections.append(
        "OUTPUT\n"
        "One ring on a PURE WHITE seamless background — RGB(255,255,255), "
        "not gray, not cream, not off-white, not tinted — with only a "
        "subtle soft shadow directly under the piece. Professional jewelry "
        "product photography, ultra-sharp macro detail, even studio "
        "lighting, centered three-quarter angle, the piece occupying "
        "roughly 70% of the frame. No hands, no models, no props, no text, "
        "no watermarks, no logos, no collage of references."
    )

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
                    "image_size": "square_hd",
                },
            ),
        },
    ]


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
<div class="section-subtitle">Step 1: References upload directly to fal.ai. Step 2: A Seedream-tuned master prompt is built with strict per-metal-color preservation rules. Step 3: Seedream v4 Edit (ByteDance) renders the combined design natively from both references.</div>
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
        progress = st.progress(0, text="Phase 1/3: Uploading references to fal.ai...")

        # PHASE 1: Upload each reference natively (multi-image models accept a list of URLs)
        active_specs = [s for s in image_specs if s["file"] and s["description"]]
        try:
            image_urls = [upload_to_fal(s["file"]) for s in active_specs]
        except Exception as e:
            st.error(f"Reference upload failed: {e}")
            st.stop()

        # PHASE 2: Build the combination prompt directly from user descriptions
        progress.progress(0.3, text="Phase 2/3: Building combination prompt...")
        combine_prompt = build_combine_prompt(image_specs, additional_specs)

        with st.expander("Generation Prompt", expanded=False):
            st.code(combine_prompt, language="text")

        # PHASE 3: Generate via multi-image edit models
        progress.progress(0.45, text="Phase 3/3: Generating combined designs...")
        strategies = generate_combined_design(image_urls, combine_prompt)
        results = []
        strategy_names = []

        if strategies:
            for si, strategy in enumerate(strategies):
                progress.progress(
                    0.5 + (si + 1) / (len(strategies) * 2),
                    text=f"Phase 3/3: Rendering variation {si+1}/{len(strategies)} ({strategy['name']})...",
                )
                try:
                    result = strategy["fn"]()
                    url = extract_image_url(result)
                    if url:
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
                               style="color:var(--gold);text-decoration:none;font-size:0.8rem;font-weight:600;">
                                Download
                            </a>
                        </div></div>""",
                        unsafe_allow_html=True,
                    )

            st.session_state["last_results"] = results
            st.session_state["last_prompt"] = combine_prompt
            st.session_state["last_image_urls"] = image_urls
        else:
            st.error("No images were generated. Check your FAL_KEY and try again.")


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
                            "image_size": "square_hd",
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
                                f'style="color:var(--gold);font-weight:600;text-decoration:none;">'
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
