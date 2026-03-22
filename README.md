# TJM Labs — Vision-Based Desktop Automation

A Python automation tool that uses **GPT-4o vision** to dynamically locate desktop icons and automate Notepad — no hardcoded positions, no template images.

---

## How It Works

### The Core Problem
Most desktop automation uses fixed coordinates or template image matching. Both break when icons move. This project solves that with **visual grounding**: describe what you want in plain English, and a vision LLM finds it.

### Grounding Approach (ScreenSeekeR-inspired)
Based on [ScreenSpot-Pro (arxiv.org/pdf/2504.07981)](https://arxiv.org/pdf/2504.07981):

1. **Take a screenshot** of the full desktop
2. **Send to GPT-4o** with the prompt: *"Locate the Notepad desktop icon"*
3. GPT-4o returns **relative coordinates** (0.0–1.0) of the icon center
4. If confidence is low → **zoom in** on that region and re-query (iterative zoom)
5. Convert relative coords to **absolute screen pixels** → click

This works for **any icon or button** — just change the description string in `main.py`.

### Why This Over Alternatives?
| Approach | Flexibility | Robustness |
|---|---|---|
| Hardcoded coords | ✗ Breaks if icon moves | ✗ |
| Template matching (OpenCV) | Requires reference image | Fails on theme/size changes |
| **GPT-4o visual grounding** ✓ | Any icon by description | Handles themes, sizes, clutter |

---

## Setup

### 1. Install `uv`
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```
Restart your terminal after installing.

### 2. Get an OpenAI API Key
1. Go to [platform.openai.com](https://platform.openai.com)
2. Sign up → API Keys → Create new key
3. Add ~$5 credit (one full run costs ~$0.10)

### 3. Set Your API Key
```powershell
# PowerShell
$env:OPENAI_API_KEY="sk-your-key-here"
```

### 4. Create a Notepad shortcut on your Desktop
- Press `Win`, search "Notepad"
- Right-click → Send to → Desktop (create shortcut)

### 5. Install dependencies & run
```powershell
# From the project folder:
uv sync
uv run main.py
```

---

## Project Structure

```
tjm-project/
├── main.py          # Entry point — orchestrates the full workflow
├── grounding.py     # Visual grounding system (ScreenSeekeR approach)
├── automation.py    # Notepad automation (launch, type, save, close)
├── pyproject.toml   # uv / dependency configuration
├── screenshots/     # Auto-generated annotated detection screenshots
└── README.md
```

---

## Output

- **10 files** saved to `Desktop\tjm-project\`: `post_1.txt` through `post_10.txt`
- **3 annotated screenshots** in `screenshots/` showing icon detection at posts 1, 5, and 10

Each text file follows the format:
```
Title: {post title}

{post body}
```

---

## Abort Anytime
Move your mouse to the **top-left corner** of the screen to immediately stop execution (pyautogui failsafe).

---

## Discussion Notes (for the interview)

**When would detection fail?**
- Icon hidden behind a fullscreen window (mitigated by Win+D)
- Extremely cluttered desktop with many similar icons
- Very dark/busy wallpaper that blends with the icon

**How would you improve it?**
- Add OCR fallback: read icon labels as text to confirm identity
- Use a specialized GUI grounding model (OSAtlas, SeeClick) instead of GPT-4o for lower cost and faster inference
- Cache the last known position and search that region first

**Performance**
- Each grounding call takes ~1–2 seconds (one GPT-4o API call)
- Zoom iteration adds ~1s per level
- Total per post: ~4–5 seconds for grounding + automation
