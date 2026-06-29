import json
import os
from typing import Optional
from urllib.parse import urlparse

import aiohttp

from .QwenGenerateRequest import (
    ImageResult,
    QwenImageRequest,
    QwenImageResponse,
    parse_response,
)

# ---------------------------------------------------------------------------
# Bailian Qwen-Image multimodal generation endpoint
# ---------------------------------------------------------------------------


class QwenImageError(Exception):
    """Raised when the Qwen-Image API returns an error."""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


async def multimodal_generation(
    request: QwenImageRequest,
    baseurl: str,
    api_key: str,
    *,
    timeout: float = 120.0,
) -> QwenImageResponse:
    """Call the Bailian Qwen-Image multimodal generation API.

    Args:
        request: A fully-built ``QwenImageRequest``.
        api_key: DashScope / Bailian API key (Bearer token).
        timeout: Request timeout in seconds (generation can be slow).

    Returns:
        A parsed ``QwenImageResponse`` with typed access to images,
        usage info, and the raw response dict.

    Raises:
        QwenImageError: When the API returns a non-2xx status or an error
            code in the response body.
        aiohttp.ClientError: On network / connection failures.
    """
    payload = request.to_dict()
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
        async with session.post(baseurl, headers=headers, json=payload) as resp:
            body = await resp.json()

    # Bailian returns HTTP 200 even for some logical errors — check body
    if resp.status != 200:
        raise QwenImageError(
            code=body.get("code", str(resp.status)),
            message=body.get("message", f"HTTP {resp.status}"),
        )

    if "code" in body and body.get("code") != "":
        raise QwenImageError(
            code=body["code"],
            message=body.get("message", "Unknown error"),
        )

    return parse_response(body)


def extract_image_urls(response: dict | QwenImageResponse) -> list[str]:
    """Extract generated image URLs from an API response.

    Accepts either a raw dict or a parsed ``QwenImageResponse``.

    The Bailian multimodal API returns images in
    ``output.choices[].message.content[]`` where each content block with
    an ``image`` key holds a generated image URL.
    """
    if isinstance(response, QwenImageResponse):
        return [img.url for img in response.images]
    urls: list[str] = []
    for choice in response.get("output", {}).get("choices", []):
        for block in choice.get("message", {}).get("content", []):
            if "image" in block:
                urls.append(block["image"])
    return urls


async def save_images(
    response: dict | QwenImageResponse,
    output_dir: str = "./test/images",
    *,
    timeout: float = 120.0,
) -> list[str]:
    """Download generated images from an API response to a local directory.

    Each image is saved using the last path segment of its URL as the
    filename (e.g. ``https://example.com/path/to/img_abc.png`` becomes
    ``img_abc.png``).  If the URL has no filename, falls back to
    ``image.png``.

    Args:
        response: API response from ``multimodal_generation``
            (dict or ``QwenImageResponse``).
        output_dir: Directory to save images into (created if it doesn't exist).
        timeout: Per-image download timeout in seconds.

    Returns:
        List of saved file paths.
    """
    urls = extract_image_urls(response)
    if not urls:
        return []

    os.makedirs(output_dir, exist_ok=True)
    saved: list[str] = []

    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
        for url in urls:
            # Use the last path segment of the URL as the filename
            filename = os.path.basename(urlparse(url).path) or "image.png"
            filepath = os.path.join(output_dir, filename)
            async with session.get(url) as resp:
                resp.raise_for_status()
                with open(filepath, "wb") as f:
                    f.write(await resp.read())
            saved.append(filepath)

    return saved
