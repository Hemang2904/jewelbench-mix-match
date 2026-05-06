"""Reference image preprocessing.

Removes the background of every reference image and composites the
foreground onto a pure-white backdrop before sending it to Seedream.
This is the single biggest lever for getting clean RGB(255,255,255)
backgrounds in the final output — without it, Seedream averages with
whatever background the input had.
"""

import io
import urllib.request

import fal_client
from PIL import Image


def _download(url: str) -> bytes:
    with urllib.request.urlopen(url) as r:
        return r.read()


def strip_background_to_white(file_bytes: bytes, content_type: str = "image/png") -> str:
    """Upload original, run birefnet, composite on white, re-upload. Returns final URL.

    Two API calls + one local composite. Adds ~2-4s and ~$0.005 per image.
    """
    raw_url = fal_client.upload(file_bytes, content_type=content_type)
    return strip_url_to_white(raw_url)


def strip_url_to_white(image_url: str) -> str:
    """Run birefnet on a URL and re-upload the white-composited result. Returns new URL."""
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
    fg = Image.open(io.BytesIO(transparent_bytes)).convert("RGBA")
    white_bg = Image.new("RGBA", fg.size, (255, 255, 255, 255))
    composite = Image.alpha_composite(white_bg, fg).convert("RGB")

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
        f"specific component from the ring shown in this image: \"{user_desc}\". "
        "Write ONE detailed sentence (max 35 words) precisely describing "
        "this component AS IT ACTUALLY APPEARS in this image. Include all "
        "of these where applicable: exact silhouette/shape (e.g. 'flower "
        "halo with rose petals', 'six-prong solitaire', 'three-stone with "
        "round side accents', 'wide lattice openwork band'), metal color "
        "(rose-gold / yellow-gold / white-gold / platinum / two-tone X+Y), "
        "prong count, decoration (scrollwork, undergallery, milgrain, "
        "halo, openwork), and stones (pavé full-length / shoulder-only / "
        "no stones / center stone shape). Output ONLY the description "
        "sentence — no preamble, no quotes, no 'The component is...'."
    )

    try:
        result = fal_client.subscribe(
            "fal-ai/any-llm/vision",
            arguments={
                "model": "google/gemini-flash-1.5",
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
