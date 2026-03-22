"""
grounding.py

ScreenSeekeR-inspired visual grounding system using Groq + Llama 4 Scout vision.
Inspired by: ScreenSpot-Pro / ScreenSeekeR (arxiv.org/pdf/2504.07981)

Core idea: Send a screenshot to a vision LLM and ask it to locate any UI 
element by text description alone. Uses iterative zoom for precision —
first finds the rough area, then zooms in for exact coordinates.
This works on any screen resolution without hardcoded offsets.
"""

import base64
import json
import time
from io import BytesIO

import pyautogui
import requests
from PIL import Image, ImageDraw


def image_to_base64(image: Image.Image) -> str:
    """Convert PIL Image to base64 PNG string."""
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def query_groq_for_element(
    api_key: str,
    image: Image.Image,
    description: str,
    context: str = "",
) -> dict | None:
    """
    Ask Groq Llama 4 Scout to locate a UI element in the given image.
    Returns relative coordinates (0.0-1.0) of the element center.
    """
    w, h = image.size
    b64 = image_to_base64(image)

    prompt = f"""You are a GUI grounding assistant. Your task is to find the exact center of this element: {description}

{("Context: " + context) if context else ""}

Image size: {w}x{h} pixels.

Respond with ONLY valid JSON, no markdown fences, no extra text:
{{
  "found": true or false,
  "x": 0.0 to 1.0,
  "y": 0.0 to 1.0,
  "confidence": "high" or "medium" or "low",
  "reasoning": "brief explanation"
}}

Rules:
- x=0.0 is the LEFT edge, x=1.0 is the RIGHT edge
- y=0.0 is the TOP edge, y=1.0 is the BOTTOM edge  
- Return the EXACT CENTER pixel of the element as a fraction
- Be as precise as possible
- If not found, return found=false"""

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "meta-llama/llama-4-scout-17b-16e-instruct",
        "max_tokens": 300,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{b64}"},
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ],
    }

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30,
        )

        if response.status_code == 429:
            print("  [grounding] Rate limited — waiting 20s...")
            time.sleep(20)
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30,
            )

        response.raise_for_status()
        data = response.json()
        raw = data["choices"][0]["message"]["content"].strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        return json.loads(raw)

    except json.JSONDecodeError as e:
        print(f"  [grounding] JSON parse error: {e}")
        return None
    except Exception as e:
        print(f"  [grounding] API error: {e}")
        return None


def iterative_zoom_grounding(
    api_key: str,
    full_screenshot: Image.Image,
    description: str,
) -> tuple[int, int] | None:
    """
    ScreenSeekeR-style iterative zoom grounding.

    Step 1: Query on full screenshot to get rough location
    Step 2: Crop a tight window around that location  
    Step 3: Re-query on the cropped image for precise center
    Step 4: Map coordinates back to real screen pixels

    This two-pass approach gives accurate coordinates regardless
    of screen resolution or icon position.
    """
    screen_w, screen_h = full_screenshot.size

    # ── Pass 1: rough location on full screenshot ──
    print(f"  [grounding] Pass 1: full screenshot ({screen_w}x{screen_h})")
    result1 = query_groq_for_element(
        api_key,
        full_screenshot,
        description,
        context=f"This is a Windows desktop at {screen_w}x{screen_h}. "
                "Desktop icons are small (32-48px). Find the rough location.",
    )

    if result1 is None or not result1.get("found"):
        print("  [grounding] Not found in pass 1.")
        return None

    rel_x1 = float(result1["x"])
    rel_y1 = float(result1["y"])
    rough_x = int(rel_x1 * screen_w)
    rough_y = int(rel_y1 * screen_h)
    print(f"  [grounding] Pass 1 rough location: ({rough_x}, {rough_y}), confidence={result1.get('confidence')}")

    # ── Pass 2: zoom in for precision ──
    # Crop a 300x300 window centered on the rough location
    crop_size = 300
    left = max(0, rough_x - crop_size // 2)
    top = max(0, rough_y - crop_size // 2)
    right = min(screen_w, left + crop_size)
    bottom = min(screen_h, top + crop_size)

    # Adjust if we hit screen edges
    if right - left < crop_size:
        left = max(0, right - crop_size)
    if bottom - top < crop_size:
        top = max(0, bottom - crop_size)

    cropped = full_screenshot.crop((left, top, right, bottom))
    crop_w = right - left
    crop_h = bottom - top

    print(f"  [grounding] Pass 2: zoomed region ({left},{top}) -> ({right},{bottom})")
    result2 = query_groq_for_element(
        api_key,
        cropped,
        description,
        context=f"This is a zoomed-in portion of a Windows desktop. "
                f"The icon should be near the center of this {crop_w}x{crop_h} image. "
                "Find the EXACT center of the icon.",
    )

    if result2 is None or not result2.get("found"):
        print("  [grounding] Not found in pass 2, using pass 1 result.")
        return (rough_x, rough_y)

    rel_x2 = float(result2["x"])
    rel_y2 = float(result2["y"])

    # Map back to real screen coordinates
    final_x = int(left + rel_x2 * crop_w)
    final_y = int(top + rel_y2 * crop_h)

    print(f"  [grounding] Pass 2 precise location: ({final_x}, {final_y}), confidence={result2.get('confidence')}")
    return (final_x, final_y)


def find_icon_on_desktop(
    api_key: str,
    description: str,
    max_attempts: int = 3,
    retry_delay: float = 3.0,
) -> tuple[int, int] | None:
    """
    Take a fresh screenshot and locate an icon using Groq vision.
    Retries up to max_attempts times with fresh screenshots each time.
    """
    for attempt in range(1, max_attempts + 1):
        print(f"\n[grounding] Attempt {attempt}/{max_attempts}: locating '{description}'")

        screenshot = pyautogui.screenshot()
        screenshot = screenshot.convert("RGB")

        coords = iterative_zoom_grounding(api_key, screenshot, description)

        if coords is not None:
            print(f"[grounding] ✓ Located at {coords}")
            return coords

        if attempt < max_attempts:
            print(f"[grounding] Not found. Retrying in {retry_delay}s...")
            time.sleep(retry_delay)

    print(f"[grounding] ✗ Failed to locate '{description}' after {max_attempts} attempts.")
    return None


def annotate_screenshot(
    screenshot: Image.Image,
    coords: tuple[int, int],
    label: str,
    output_path: str,
) -> None:
    """Save an annotated screenshot highlighting the detected icon location."""
    annotated = screenshot.copy().convert("RGB")
    draw = ImageDraw.Draw(annotated)

    x, y = coords
    radius = 20

    draw.ellipse([(x - radius, y - radius), (x + radius, y + radius)], outline="red", width=3)
    draw.line([(x - radius - 5, y), (x + radius + 5, y)], fill="red", width=2)
    draw.line([(x, y - radius - 5), (x, y + radius + 5)], fill="red", width=2)

    text_x, text_y = x + radius + 5, y - 10
    draw.rectangle([(text_x - 2, text_y - 2), (text_x + len(label) * 7 + 4, text_y + 14)], fill="red")
    draw.text((text_x, text_y), label, fill="white")

    annotated.save(output_path)
    print(f"[grounding] Annotated screenshot saved: {output_path}")
