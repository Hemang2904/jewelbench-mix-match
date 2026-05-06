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

    result = fal_client.subscribe(
        "fal-ai/birefnet/v2",
        arguments={"image_url": raw_url},
    )
    transparent_url = (
        result.get("image", {}).get("url")
        or (result.get("images") or [{}])[0].get("url")
    )
    if not transparent_url:
        return raw_url

    transparent_bytes = _download(transparent_url)
    fg = Image.open(io.BytesIO(transparent_bytes)).convert("RGBA")
    white_bg = Image.new("RGBA", fg.size, (255, 255, 255, 255))
    composite = Image.alpha_composite(white_bg, fg).convert("RGB")

    buf = io.BytesIO()
    composite.save(buf, format="PNG", optimize=True)
    return fal_client.upload(buf.getvalue(), content_type="image/png")
