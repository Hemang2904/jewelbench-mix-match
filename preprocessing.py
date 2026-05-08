"""Reference image preprocessing.

Removes the background of every reference image and composites the
foreground onto a pure-white backdrop before sending it to Seedream.
This is the single biggest lever for getting clean RGB(255,255,255)
backgrounds in the final output — without it, Seedream averages with
whatever background the input had.
"""

import io
import json
import os
import re
import urllib.request

import fal_client
from PIL import Image


ENRICHMENT_MODEL = os.environ.get("ENRICHMENT_MODEL", "google/gemini-2.5-pro")
VALIDATOR_MODEL = os.environ.get("VALIDATOR_MODEL", "anthropic/claude-sonnet-4.5")
VALIDATOR_FALLBACK_MODEL = os.environ.get(
    "VALIDATOR_FALLBACK_MODEL", "openai/gpt-5-chat"
)


def _download(url: str) -> bytes:
    with urllib.request.urlopen(url) as r:
        return r.read()


def strip_background_to_white(file_bytes: bytes, content_type: str = "image/png") -> str:
    """Upload original, run birefnet, composite on white, re-upload. Returns final URL.

    Two API calls + one local composite. Adds ~2-4s and ~$0.005 per image.
    """
    raw_url = fal_client.upload(file_bytes, content_type=content_type)
    return strip_url_to_white(raw_url)


def _has_dark_corners(rgb_img: "Image.Image", threshold: int = 60) -> bool:
    """Return True if all four corner regions of an RGB image are dark.

    Used to detect Seedream outputs that came back with a black/navy bg so
    we can force a fresh white composite even if birefnet's alpha channel
    was already removed somewhere in the pipeline.
    """
    w, h = rgb_img.size
    sample = 8
    corners = [
        rgb_img.crop((0, 0, sample, sample)),
        rgb_img.crop((w - sample, 0, w, sample)),
        rgb_img.crop((0, h - sample, sample, h)),
        rgb_img.crop((w - sample, h - sample, w, h)),
    ]
    for c in corners:
        pixels = list(c.getdata())
        avg = sum(sum(p[:3]) for p in pixels) / (len(pixels) * 3)
        if avg > threshold:
            return False
    return True


def strip_url_to_white(image_url: str) -> str:
    """Run birefnet on a URL and re-upload the white-composited result. Returns new URL.

    If birefnet gives us a proper RGBA mask we use that. If it doesn't (or
    if the result still looks dark in its corners), we re-strip the
    original image once more and force the dark bg to white via a luminance
    threshold so we always end up on RGB(255,255,255).
    """
    result = fal_client.subscribe(
        "fal-ai/birefnet/v2",
        arguments={"image_url": image_url},
    )
    transparent_url = (
        result.get("image", {}).get("url")
        or (result.get("images") or [{}])[0].get("url")
    )
    if not transparent_url:
        return image_url

    transparent_bytes = _download(transparent_url)
    fg_raw = Image.open(io.BytesIO(transparent_bytes))

    if fg_raw.mode != "RGBA":
        # Some birefnet variants paint bg as black rather than transparent.
        # Build an alpha mask from luminance: dark pixels become transparent.
        rgb = fg_raw.convert("RGB")
        gray = rgb.convert("L")
        alpha = gray.point(lambda v: 255 if v > 30 else 0)
        fg = Image.merge("RGBA", (*rgb.split(), alpha))
    else:
        fg = fg_raw

    white_bg = Image.new("RGBA", fg.size, (255, 255, 255, 255))
    composite = Image.alpha_composite(white_bg, fg).convert("RGB")

    # Belt-and-braces: if corners are still dark, the alpha mask missed; do a
    # final luminance-keying pass against the composite itself.
    if _has_dark_corners(composite):
        rgb = composite
        gray = rgb.convert("L")
        alpha = gray.point(lambda v: 255 if v > 30 else 0)
        masked = Image.merge("RGBA", (*rgb.split(), alpha))
        composite = Image.alpha_composite(white_bg, masked).convert("RGB")

    buf = io.BytesIO()
    composite.save(buf, format="PNG", optimize=True)
    return fal_client.upload(buf.getvalue(), content_type="image/png")


def enrich_description(image_url: str, user_desc: str) -> str:
    """Use a vision LLM to expand a terse description into a rich one that
    captures shape, decoration, metal color, prong count, and stones.

    Falls back to user_desc if the LLM call fails or returns nothing useful.
    The user can still pre-empt enrichment by writing a long description
    (>= 60 chars).
    """
    if len(user_desc.strip()) >= 60:
        return user_desc

    prompt = (
        "You are a jewelry CAD expert. The user wants to extract this "
        f"specific component from the jewelry piece in this image: \"{user_desc}\". "
        "Write ONE detailed phrase (max 30 words) precisely describing "
        "ONLY the component itself, NOT the whole piece. Include where "
        "applicable: exact silhouette/shape (e.g. 'flower halo with rose "
        "petals', '6-prong solitaire head', '3-stone head with round "
        "accents', 'wide lattice openwork shank'), metal color (rose-gold "
        "/ yellow-gold / white-gold / platinum / two-tone), prong count, "
        "decoration (scrollwork, undergallery, milgrain, halo, openwork), "
        "and stones (pavé full-length / shoulder-only / no stones / "
        "center stone shape).\n\n"
        "STRICT RULES:\n"
        "- Do NOT use the words 'ring', 'piece', 'the piece', or 'this "
        "ring'. Describe ONLY the component (head / shank / halo / etc.).\n"
        "- Do NOT describe other parts of the jewelry that are not the "
        "requested component.\n"
        "- Do NOT add any preamble, no quotes, no 'The component is…', "
        "no 'This is a…'. Start directly with the component description.\n"
        "- Output a single noun phrase, e.g. 'rose-gold flower-halo head "
        "with five rose-petal cup around a 4-prong round-diamond center'."
    )

    try:
        result = fal_client.subscribe(
            "fal-ai/any-llm/vision",
            arguments={
                "model": ENRICHMENT_MODEL,
                "prompt": prompt,
                "image_url": image_url,
            },
        )
    except Exception:
        return user_desc

    enriched = (result.get("output") or "").strip().strip('"').strip("'")
    if enriched and len(enriched) > len(user_desc) + 10:
        return enriched
    return user_desc


_JSON_BLOCK = re.compile(r"\{.*\}", re.DOTALL)


def _extract_json(text: str) -> dict | None:
    """Pull the first JSON object out of a VLM response.

    VLMs sometimes wrap JSON in ```json fences or add a sentence before/after,
    so we tolerate both. Returns None if nothing parseable is found.
    """
    if not text:
        return None
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except Exception:
        pass
    match = _JSON_BLOCK.search(text)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except Exception:
        return None


def validate_design(
    image_url: str,
    target_description: str,
    model: str | None = None,
) -> dict:
    """Score how faithfully the generated jewelry image matches the target description.

    Returns {score: int 0-100, missing: list[str], wrong: list[str], suggestion: str}.
    On any LLM/parse failure returns score=0 with a non-fatal note so the caller
    can still surface the result and decide whether to retry.
    """
    chosen = model or VALIDATOR_MODEL

    prompt = (
        "You are a senior jewelry-design QA reviewer. Compare the attached "
        "rendered ring image against the TARGET DESCRIPTION below and decide "
        "how faithfully the render reproduces it.\n\n"
        f"TARGET DESCRIPTION:\n{target_description}\n\n"
        "Score on a 0-100 scale where 100 = every named component is "
        "present with correct shape, metal color, prong/stone count, "
        "decoration extent, and surface finish; 85+ = minor cosmetic drift "
        "only; <85 = at least one component is missing, swapped, "
        "miscolored, simplified, or embellished beyond the description.\n\n"
        "Treat these as hard failures (force score < 85): wrong metal "
        "color on any component, missing component from any reference, "
        "shank pavé/stones added or removed vs. description, halo or "
        "prong count changed, two rings instead of one, colored gem "
        "rendered where the description says white diamond, or a tinted/"
        "non-white background.\n\n"
        "Return ONLY a single JSON object — no prose, no code fences — "
        "with this exact shape:\n"
        "{\n"
        '  "score": <integer 0-100>,\n'
        '  "missing": [<short strings naming components from the target '
        "that are absent or barely visible>],\n"
        '  "wrong":   [<short strings naming components that are present '
        "but rendered incorrectly, with what is wrong>],\n"
        '  "suggestion": "<one imperative sentence telling the image '
        "model exactly what to fix on the next attempt — name the "
        "component, the current defect, and the correct target state>\"\n"
        "}"
    )

    def _call(model_id: str) -> dict | None:
        try:
            result = fal_client.subscribe(
                "fal-ai/any-llm/vision",
                arguments={
                    "model": model_id,
                    "prompt": prompt,
                    "image_url": image_url,
                },
            )
        except Exception as e:
            return {"_error": f"{model_id}: {e}"}
        return {"_raw": (result.get("output") or "").strip(), "_model": model_id}

    raw = _call(chosen)
    if raw and raw.get("_error") and VALIDATOR_FALLBACK_MODEL and VALIDATOR_FALLBACK_MODEL != chosen:
        raw = _call(VALIDATOR_FALLBACK_MODEL)

    if not raw or "_raw" not in raw:
        return {
            "score": 0,
            "missing": [],
            "wrong": [],
            "suggestion": "",
            "_error": (raw or {}).get("_error", "validator unavailable"),
            "_model": chosen,
        }

    parsed = _extract_json(raw["_raw"])
    if not parsed:
        return {
            "score": 0,
            "missing": [],
            "wrong": [],
            "suggestion": "",
            "_error": "validator returned non-JSON",
            "_raw": raw["_raw"][:400],
            "_model": raw["_model"],
        }

    try:
        score = int(parsed.get("score", 0))
    except (TypeError, ValueError):
        score = 0
    score = max(0, min(100, score))

    return {
        "score": score,
        "missing": list(parsed.get("missing") or []),
        "wrong": list(parsed.get("wrong") or []),
        "suggestion": (parsed.get("suggestion") or "").strip(),
        "_model": raw["_model"],
    }
