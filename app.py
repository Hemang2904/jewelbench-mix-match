import streamlit as st
import fal_client
import base64
import io
import time
import json
from PIL import Image

st.set_page_config(
    page_title="JewelBench - Mix & Match Designer",
    page_icon="💎",
    layout="wide",
)

st.markdown("""
<style>
    .stApp { background-color: #0E1117; }
    .upload-box {
        border: 2px dashed #4A4A6A;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        background: #1A1A2E;
        margin-bottom: 10px;
    }
    .result-container {
        border: 2px solid #C9A84C;
        border-radius: 12px;
        padding: 10px;
        background: #1A1A2E;
    }
    h1 { color: #C9A84C !important; }
    .stButton > button {
        background: linear-gradient(135deg, #C9A84C, #8B6914);
        color: white;
        border: none;
        padding: 12px 40px;
        font-size: 18px;
        border-radius: 8px;
        width: 100%;
    }
    .spec-label { color: #C9A84C; font-weight: bold; font-size: 14px; }
</style>
""", unsafe_allow_html=True)


def image_to_data_uri(uploaded_file):
    img_bytes = uploaded_file.getvalue()
    b64 = base64.b64encode(img_bytes).decode()
    mime = uploaded_file.type or "image/png"
    return f"data:{mime};base64,{b64}"


def upload_to_fal(uploaded_file):
    img_bytes = uploaded_file.getvalue()
    url = fal_client.upload(img_bytes, content_type=uploaded_file.type or "image/png")
    return url


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
    """Use FLUX Kontext for multi-reference image generation."""
    image_urls = []
    for spec in image_specs:
        if spec["file"]:
            url = upload_to_fal(spec["file"])
            image_urls.append(url)

    if not image_urls:
        st.error("Please upload at least one image.")
        return None

    result = fal_client.subscribe(
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
    return result


def generate_with_omnigen(image_specs, prompt):
    """Use OmniGen for multi-image composition."""
    image_urls = []
    tagged_prompt = prompt
    for i, spec in enumerate(image_specs):
        if spec["file"]:
            url = upload_to_fal(spec["file"])
            image_urls.append(url)
            tagged_prompt = tagged_prompt.replace(
                f"reference image {i+1}", f"<img><|image_{i+1}|></img>"
            )

    input_images = [{"url": url} for url in image_urls]

    result = fal_client.subscribe(
        "fal-ai/omnigen-v1",
        arguments={
            "prompt": tagged_prompt,
            "input_images": input_images,
            "num_images": 1,
            "guidance_scale": 3.0,
            "seed": int(time.time()) % 100000,
        },
    )
    return result


def generate_with_ideogram(image_specs, prompt):
    """Use Ideogram for high-quality remix generation."""
    image_urls = []
    for spec in image_specs:
        if spec["file"]:
            url = upload_to_fal(spec["file"])
            image_urls.append(url)

    if not image_urls:
        st.error("Please upload at least one image.")
        return None

    result = fal_client.subscribe(
        "fal-ai/ideogram/v2/edit",
        arguments={
            "image_url": image_urls[0],
            "prompt": prompt,
            "num_images": 1,
            "magic_prompt_option": "AUTO",
        },
    )
    return result


GENERATORS = {
    "FLUX Kontext Max (Best for single-ref edits)": generate_with_flux_kontext,
    "OmniGen (Best for multi-image composition)": generate_with_omnigen,
    "Ideogram v2 Edit (High quality remix)": generate_with_ideogram,
}


# --- UI ---

st.title("💎 JewelBench — Mix & Match Designer")
st.markdown(
    "Upload multiple jewelry reference images, specify which component to take "
    "from each, and generate a combined render."
)

st.divider()

num_images = st.slider("Number of reference images", min_value=2, max_value=5, value=2)

image_specs = []
cols = st.columns(num_images)

for i in range(num_images):
    with cols[i]:
        st.markdown(f"### Reference {i+1}")
        uploaded = st.file_uploader(
            f"Upload image {i+1}",
            type=["png", "jpg", "jpeg", "webp", "heic"],
            key=f"img_{i}",
        )
        if uploaded:
            st.image(uploaded, use_container_width=True)
        desc = st.text_area(
            f"What to use from this image?",
            placeholder="e.g., 'shank design and band style' or 'head/setting with halo'",
            key=f"desc_{i}",
            height=80,
        )
        image_specs.append({"file": uploaded, "description": desc})

st.divider()
st.markdown("### Additional Specifications")

spec_cols = st.columns(2)
with spec_cols[0]:
    metal = st.selectbox(
        "Metal Type",
        [
            "",
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
        ],
    )
    stones = st.text_area(
        "Stone Details",
        placeholder="e.g., '5.68mm Round center, channel-set side diamonds HI I1'",
        height=80,
    )

with spec_cols[1]:
    dimensions = st.text_area(
        "Dimensions / Measurements",
        placeholder="e.g., '4.5mm shoulder width, 2.2mm depth, 2mm base width'",
        height=80,
    )
    notes = st.text_area(
        "Additional Notes",
        placeholder="e.g., 'Cathedral style setting, milgrain edges'",
        height=80,
    )

additional_specs = {
    "metal": metal,
    "stones": stones,
    "dimensions": dimensions,
    "notes": notes,
}

st.divider()

model_choice = st.selectbox("Select AI Model", list(GENERATORS.keys()))

num_variations = st.slider("Number of variations to generate", 1, 4, 2)

if st.button("🔮 Generate Combined Design", use_container_width=True):
    has_images = any(s["file"] for s in image_specs)
    has_descriptions = any(s["description"] for s in image_specs)

    if not has_images:
        st.error("Please upload at least one reference image.")
    elif not has_descriptions:
        st.error("Please describe what to use from at least one image.")
    else:
        prompt = build_combination_prompt(image_specs, additional_specs)

        with st.expander("Generated Prompt", expanded=False):
            st.code(prompt, language="text")

        generator_fn = GENERATORS[model_choice]
        results = []

        progress = st.progress(0, text="Generating designs...")

        for v in range(num_variations):
            progress.progress(
                (v) / num_variations,
                text=f"Generating variation {v+1}/{num_variations}...",
            )
            try:
                result = generator_fn(image_specs, prompt)
                if result and "images" in result:
                    for img_data in result["images"]:
                        results.append(img_data.get("url"))
                elif result and "image" in result:
                    results.append(result["image"].get("url"))
            except Exception as e:
                st.error(f"Variation {v+1} failed: {str(e)}")

        progress.progress(1.0, text="Done!")

        if results:
            st.markdown("### Generated Designs")
            result_cols = st.columns(min(len(results), 4))
            for idx, url in enumerate(results):
                if url:
                    with result_cols[idx % len(result_cols)]:
                        st.image(url, caption=f"Variation {idx+1}", use_container_width=True)
                        st.markdown(f"[Download]({url})", unsafe_allow_html=True)

            st.session_state["last_results"] = results
            st.session_state["last_prompt"] = prompt

if st.session_state.get("last_results"):
    st.divider()
    st.markdown("### Refine")
    refinement = st.text_input(
        "Describe changes for the next iteration",
        placeholder="e.g., 'Make the prongs thinner, add more milgrain detail'",
    )
    if st.button("🔄 Regenerate with Changes"):
        base_prompt = st.session_state["last_prompt"]
        refined_prompt = f"{base_prompt} Modifications: {refinement}"

        generator_fn = GENERATORS[model_choice]
        with st.spinner("Regenerating..."):
            try:
                result = generator_fn(image_specs, refined_prompt)
                if result and "images" in result:
                    for img_data in result["images"]:
                        st.image(img_data.get("url"), use_container_width=True)
                elif result and "image" in result:
                    st.image(result["image"].get("url"), use_container_width=True)
            except Exception as e:
                st.error(f"Regeneration failed: {str(e)}")
