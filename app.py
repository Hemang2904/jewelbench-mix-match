import streamlit as st
import fal_client
import base64
import io
import os
import time
import json
from pathlib import Path
from PIL import Image
from dotenv import load_dotenv

load_dotenv()

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


def build_combination_prompt(image_specs, additional_specs):
    parts = []
    for i, spec in enumerate(image_specs):
        if spec["file"] and spec["description"]:
            parts.append(f"From reference image {i+1}: use the {spec['description']}")

    combination = ". ".join(parts)

    prompt = (
        f"Professional jewelry product photograph, studio lighting, white background. "
        f"Create a single cohesive jewelry piece by combining: {combination}. "
    )

    if additional_specs.get("metal"):
        prompt += f"Metal: {additional_specs['metal']}. "
    if additional_specs.get("dimensions"):
        prompt += f"Specifications: {additional_specs['dimensions']}. "
    if additional_specs.get("stones"):
        prompt += f"Stone details: {additional_specs['stones']}. "
    if additional_specs.get("notes"):
        prompt += f"Additional details: {additional_specs['notes']}. "

    prompt += (
        "Photorealistic render, 8K quality, jewelry catalog style, "
        "sharp focus on details, professional product photography."
    )
    return prompt


def generate_with_flux_kontext(image_specs, prompt):
    image_urls = []
    for spec in image_specs:
        if spec["file"]:
            image_urls.append(upload_to_fal(spec["file"]))

    if not image_urls:
        return None

    return fal_client.subscribe(
        "fal-ai/flux-pro/kontext/max",
        arguments={
            "image_url": image_urls[0],
            "prompt": prompt,
            "num_images": 1,
            "guidance_scale": 7.5,
            "output_format": "png",
            "safety_tolerance": 5,
        },
    )


def generate_with_omnigen(image_specs, prompt):
    image_urls = []
    tagged_prompt = prompt
    for i, spec in enumerate(image_specs):
        if spec["file"]:
            url = upload_to_fal(spec["file"])
            image_urls.append(url)
            tagged_prompt = tagged_prompt.replace(
                f"reference image {i+1}", f"<img><|image_{i+1}|></img>"
            )

    return fal_client.subscribe(
        "fal-ai/omnigen-v1",
        arguments={
            "prompt": tagged_prompt,
            "input_images": [{"url": url} for url in image_urls],
            "num_images": 1,
            "guidance_scale": 3.0,
            "seed": int(time.time()) % 100000,
        },
    )


def generate_with_ideogram(image_specs, prompt):
    image_urls = []
    for spec in image_specs:
        if spec["file"]:
            image_urls.append(upload_to_fal(spec["file"]))

    if not image_urls:
        return None

    return fal_client.subscribe(
        "fal-ai/ideogram/v2/edit",
        arguments={
            "image_url": image_urls[0],
            "prompt": prompt,
            "num_images": 1,
            "magic_prompt_option": "AUTO",
        },
    )


GENERATORS = {
    "flux_kontext": {
        "fn": generate_with_flux_kontext,
        "name": "FLUX Kontext Max",
        "desc": "Best for single-reference style transfer & edits",
        "tag": "RECOMMENDED",
    },
    "omnigen": {
        "fn": generate_with_omnigen,
        "name": "OmniGen",
        "desc": "Multi-image composition with tagged references",
        "tag": "MULTI-IMAGE",
    },
    "ideogram": {
        "fn": generate_with_ideogram,
        "name": "Ideogram v2",
        "desc": "High quality remix with magic prompt enhancement",
        "tag": "HD QUALITY",
    },
}


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
            st.image(uploaded, use_container_width=True)

        desc = st.text_area(
            "Component to extract",
            placeholder="e.g., 'shank design' or 'head with halo setting'",
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


# --- MODEL SELECTION ---
st.markdown("""
<div class="section-title">AI Engine</div>
<div class="section-subtitle">Choose the generation model that best fits your use case</div>
""", unsafe_allow_html=True)

model_cols = st.columns(3, gap="medium")
model_keys = list(GENERATORS.keys())

for idx, key in enumerate(model_keys):
    m = GENERATORS[key]
    with model_cols[idx]:
        tag_color = {
            "RECOMMENDED": "rgba(201,168,76,0.15)",
            "MULTI-IMAGE": "rgba(124,58,237,0.15)",
            "HD QUALITY": "rgba(74,108,247,0.15)",
        }.get(m["tag"], "rgba(201,168,76,0.15)")
        tag_text_color = {
            "RECOMMENDED": "var(--gold)",
            "MULTI-IMAGE": "#A78BFA",
            "HD QUALITY": "#818CF8",
        }.get(m["tag"], "var(--gold)")

        st.markdown(f"""
        <div class="model-card">
            <div class="model-name">{m['name']}</div>
            <div class="model-desc">{m['desc']}</div>
            <span style="display:inline-block;background:{tag_color};color:{tag_text_color};
                padding:2px 10px;border-radius:4px;font-size:0.7rem;font-weight:700;margin-top:8px;
                letter-spacing:1px;">
                {m['tag']}
            </span>
        </div>
        """, unsafe_allow_html=True)

model_choice = st.selectbox(
    "Select engine",
    model_keys,
    format_func=lambda k: GENERATORS[k]["name"],
    label_visibility="collapsed",
)

# --- GENERATION CONTROLS ---
st.markdown("<br>", unsafe_allow_html=True)

ctrl_col1, ctrl_col2 = st.columns([1, 1])
with ctrl_col1:
    num_variations = st.slider(
        "Variations",
        min_value=1, max_value=4, value=2,
        help="Number of design variations to generate",
    )

st.markdown("<br>", unsafe_allow_html=True)

generate_clicked = st.button(
    "GENERATE COMBINED DESIGN",
    use_container_width=True,
    type="primary",
)

if generate_clicked:
    has_images = any(s["file"] for s in image_specs)
    has_descriptions = any(s["description"] for s in image_specs)

    if not has_images:
        st.error("Upload at least one reference image to continue.")
    elif not has_descriptions:
        st.warning("Describe what component to use from at least one image.")
    else:
        prompt = build_combination_prompt(image_specs, additional_specs)

        with st.expander("View Generated Prompt", expanded=False):
            st.code(prompt, language="text")

        generator_fn = GENERATORS[model_choice]["fn"]
        results = []

        progress = st.progress(0, text="Initializing AI engine...")
        time.sleep(0.3)

        for v in range(num_variations):
            progress.progress(
                v / num_variations,
                text=f"Rendering variation {v+1} of {num_variations}...",
            )
            try:
                result = generator_fn(image_specs, prompt)
                url = extract_image_url(result)
                if url:
                    results.append(url)
            except Exception as e:
                st.error(f"Variation {v+1} failed: {str(e)}")

        progress.progress(1.0, text="Generation complete")
        time.sleep(0.5)
        progress.empty()

        if results:
            st.markdown("""
            <div class="section-title">Generated Designs</div>
            <div class="section-subtitle">Click to expand, download, or refine any variation</div>
            """, unsafe_allow_html=True)

            result_cols = st.columns(min(len(results), 4), gap="medium")
            for idx, url in enumerate(results):
                with result_cols[idx % len(result_cols)]:
                    st.markdown(
                        '<div class="result-card">',
                        unsafe_allow_html=True,
                    )
                    st.image(url, use_container_width=True)
                    st.markdown(
                        f"""<div class="result-label">
                            <span>Variation {idx+1}</span>
                            <a href="{url}" target="_blank"
                               style="color:var(--gold);text-decoration:none;font-size:0.8rem;font-weight:600;">
                                Download ↗
                            </a>
                        </div></div>""",
                        unsafe_allow_html=True,
                    )

            st.session_state["last_results"] = results
            st.session_state["last_prompt"] = prompt
        else:
            st.error("No images were generated. Please try a different model or prompt.")


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

    if st.button("REGENERATE WITH CHANGES", use_container_width=True):
        if not refinement:
            st.warning("Describe what to change before regenerating.")
        else:
            base_prompt = st.session_state["last_prompt"]
            refined_prompt = f"{base_prompt} Modifications: {refinement}"
            generator_fn = GENERATORS[model_choice]["fn"]

            with st.spinner("Regenerating with modifications..."):
                try:
                    result = generator_fn(image_specs, refined_prompt)
                    url = extract_image_url(result)
                    if url:
                        st.markdown("""
                        <div class="section-title">Refined Design</div>
                        """, unsafe_allow_html=True)
                        col1, col2, col3 = st.columns([1, 2, 1])
                        with col2:
                            st.image(url, use_container_width=True)
                            st.markdown(
                                f'<div style="text-align:center;margin-top:8px;">'
                                f'<a href="{url}" target="_blank" '
                                f'style="color:var(--gold);font-weight:600;text-decoration:none;">'
                                f'Download Full Resolution ↗</a></div>',
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
