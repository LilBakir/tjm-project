"""
main.py

Entry point for the TJM Labs take-home project.
"""

import os
import sys
import time

import pyautogui

from automation import (
    close_notepad,
    fetch_posts,
    focus_notepad,
    format_post_content,
    get_save_directory,
    minimize_all_windows,
    save_file_as,
    type_post_in_notepad,
    wait_for_notepad,
)
from grounding import annotate_screenshot, find_icon_on_desktop

ICON_DESCRIPTION = "Notepad desktop shortcut icon (small icon with a notepad and pencil)"

pyautogui.PAUSE = 0.3
pyautogui.FAILSAFE = True

SCREENSHOTS_DIR = "screenshots"

# Offset to nudge click onto the icon center (adjust if still off)
CLICK_OFFSET_X = 0
CLICK_OFFSET_Y = 0


def get_groq_api_key() -> str:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print(
            "\n[ERROR] GROQ_API_KEY environment variable not set.\n"
            "Please set it in PowerShell first:\n"
            '  $env:GROQ_API_KEY="your-key-here"\n'
        )
        sys.exit(1)
    return api_key


def launch_notepad_via_grounding(api_key: str, post_index: int) -> bool:
    print(f"\n{'─' * 60}")
    print(f"[main] Launching Notepad for post {post_index + 1}/10")
    print(f"{'─' * 60}")

    minimize_all_windows()

    coords = find_icon_on_desktop(api_key, ICON_DESCRIPTION)

    if coords is None:
        print("[main] ✗ Could not locate Notepad icon. Skipping this post.")
        return False

    # Apply offset to land on icon center
    click_x = coords[0] + CLICK_OFFSET_X
    click_y = coords[1] + CLICK_OFFSET_Y

    # Save annotated screenshot for deliverable (posts 1, 5, 10)
    if post_index in (0, 4, 9):
        os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
        screenshot = pyautogui.screenshot()
        label = f"Notepad detected ({coords[0]}, {coords[1]})"
        output_path = os.path.join(SCREENSHOTS_DIR, f"detection_post_{post_index + 1}.png")
        annotate_screenshot(screenshot, coords, label, output_path)

    print(f"[main] Moving to ({click_x}, {click_y}) and double-clicking...")
    pyautogui.moveTo(click_x, click_y, duration=0.5)
    time.sleep(0.4)
    pyautogui.doubleClick(click_x, click_y)

    if not wait_for_notepad():
        print("[main] ✗ Notepad did not open. Trying one more double-click...")
        time.sleep(1.5)
        pyautogui.moveTo(click_x, click_y, duration=0.5)
        time.sleep(0.4)
        pyautogui.doubleClick(click_x, click_y)
        if not wait_for_notepad():
            return False

    focus_notepad()
    return True


def main() -> None:
    print("=" * 60)
    print("  TJM Labs — Vision-Based Desktop Automation")
    print("=" * 60)
    print("\nTip: Move mouse to the TOP-LEFT corner at any time to abort.\n")

    api_key = get_groq_api_key()
    save_dir = get_save_directory()
    print(f"[main] Files will be saved to: {save_dir}")

    posts = fetch_posts()
    if not posts:
        print("\n[main] ✗ No posts fetched. Cannot continue.")
        sys.exit(1)

    success_count = 0

    for i, post in enumerate(posts):
        post_id = post["id"]
        filename = f"post_{post_id}.txt"
        content = format_post_content(post)

        print(f"\n[main] ── Post {i + 1}/10 (id={post_id}) ──")

        launched = launch_notepad_via_grounding(api_key, i)
        if not launched:
            print(f"[main] Skipping post {post_id} due to launch failure.")
            continue

        print(f"[main] Typing content for post {post_id}...")
        type_post_in_notepad(content)

        print(f"[main] Saving as {filename}...")
        save_file_as(filename, save_dir)

        close_notepad()

        success_count += 1
        print(f"[main] ✓ Post {post_id} complete.")

        time.sleep(0.5)

    print("\n" + "=" * 60)
    print(f"  Done! {success_count}/10 posts saved to Desktop\\tjm-project\\")
    print(f"  Annotated screenshots saved to .\\{SCREENSHOTS_DIR}\\")
    print("=" * 60)


if __name__ == "__main__":
    main()
