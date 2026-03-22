# TJM Labs — Vision-Based Desktop Automation

A Python automation tool that uses **Groq Llama 4 Scout vision** to dynamically locate desktop icons and automate Notepad — no hardcoded positions, no template images.

---

## How It Works

### The Core Problem
Most desktop automation uses fixed coordinates or template image matching. Both break when icons move. This project solves that with **visual grounding**: describe what you want in plain English, and a vision LLM finds it.

### Grounding Approach (ScreenSeekeR-inspired)
Based on [ScreenSpot-Pro (arxiv.org/pdf/2504.07981)](https://arxiv.org/pdf/2504.07981):

1. **Take a screenshot** of the full desktop
2. **Send to Groq Llama 4 Scout** with the prompt: *"Locate the Notepad desktop icon"*
3. The model returns **relative coordinates** (0.0–1.0) of the rough location
4. **Zoom in** — crop a 300x300 window around that spot and re-query for the exact center
5. Convert relative coords to **absolute screen pixels** → click

This works for **any icon or button** — just change the description string in `main.py`.

### Why This Over Alternatives?

| Approach | Flexibility | Robustness |
|---|---|---|
| Hardcoded coords | ✗ Breaks if icon moves | ✗ |
| Template matching (OpenCV) | Requires reference image | Fails on theme/size changes |
| **Groq visual grounding** ✓ | Any icon by description | Handles themes, sizes, clutter |

---

## Setup

### 1. Install `uv`
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```
Restart your terminal after installing.

### 2. Get a Free Groq API Key
1. Go to [console.groq.com](https://console.groq.com) and sign up (free, no credit card needed)
2. Click **API Keys** on the left
3. Click **Create API Key** and copy it

### 3. Set Your API Key
```powershell
# PowerShell
$env:GROQ_API_KEY="your-key-here"
```

### 4. Create a Notepad shortcut on your Desktop
- Right-click on empty desktop space
- Click **New → Shortcut**
- Enter: `C:\Windows\System32\notepad.exe`
- Name it **Notepad** and click Finish

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
├── grounding.py     # Visual grounding system (ScreenSeekeR two-pass approach)
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
- Use a specialized GUI grounding model (OSAtlas, SeeClick) for lower cost and faster inference
- Cache the last known position and search that region first

**Performance**
- Each grounding call takes ~1–2 seconds (one Groq API call)
- Two-pass zoom adds ~1s for the second query
- Total per post: ~4–5 seconds for grounding + automation

**Scaling to other icons**
- Change `ICON_DESCRIPTION` in `main.py` to target any icon
- Works on different resolutions — coordinates are always relative (0.0–1.0)
- No reference images needed — pure text description drives the search
