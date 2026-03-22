"""
automation.py

Handles all Notepad automation: launching, typing, saving, and closing.
Separated from grounding so each concern is clearly isolated.
"""

import os
import time

import pyautogui
import pygetwindow as gw
import requests

# How long to wait for Notepad to fully open before typing
NOTEPAD_LAUNCH_TIMEOUT = 5.0
# How long to wait between keystrokes (reduces errors on slower machines)
TYPING_INTERVAL = 0.01
# Base directory for saving files — Desktop\tjm-project
SAVE_DIR_NAME = "tjm-project"


def get_desktop_path() -> str:
    """Return the path to the current user's Desktop."""
    return os.path.join(os.path.expanduser("~"), "Desktop")


def get_save_directory() -> str:
    """Return the full path to Desktop\\tjm-project, creating it if needed."""
    save_dir = os.path.join(get_desktop_path(), SAVE_DIR_NAME)
    os.makedirs(save_dir, exist_ok=True)
    return save_dir


def fetch_posts(api_url: str = "https://jsonplaceholder.typicode.com/posts") -> list[dict]:
    """
    Fetch blog posts from JSONPlaceholder API.
    Returns the first 10 posts, or an empty list on failure.
    """
    try:
        print(f"[automation] Fetching posts from {api_url} ...")
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()
        posts = response.json()[:10]
        print(f"[automation] ✓ Fetched {len(posts)} posts.")
        return posts
    except requests.exceptions.ConnectionError:
        print("[automation] ✗ No internet connection. Cannot fetch posts.")
        return []
    except requests.exceptions.Timeout:
        print("[automation] ✗ API request timed out.")
        return []
    except Exception as e:
        print(f"[automation] ✗ Failed to fetch posts: {e}")
        return []


def format_post_content(post: dict) -> str:
    """Format a post dict into the required text format."""
    return f"Title: {post['title']}\n\n{post['body']}"


def wait_for_notepad(timeout: float = NOTEPAD_LAUNCH_TIMEOUT) -> bool:
    """
    Wait until a Notepad window appears in the taskbar.
    Returns True if found within timeout, False otherwise.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        windows = gw.getWindowsWithTitle("Notepad")
        if windows:
            print("[automation] ✓ Notepad window detected.")
            return True
        time.sleep(0.3)
    print("[automation] ✗ Notepad did not open within timeout.")
    return False


def focus_notepad() -> bool:
    """
    Bring the Notepad window to the foreground.
    Returns True on success.
    """
    windows = gw.getWindowsWithTitle("Notepad")
    if not windows:
        return False
    try:
        win = windows[0]
        win.restore()
        win.activate()
        time.sleep(0.3)
        return True
    except Exception as e:
        print(f"[automation] Warning: could not focus Notepad: {e}")
        # Fall back to Alt+Tab if activate fails
        pyautogui.hotkey("alt", "tab")
        time.sleep(0.3)
        return True


def type_post_in_notepad(content: str) -> None:
    """
    Type post content into the active Notepad window.
    Uses pyautogui.write for ASCII and typewrite for safety;
    falls back to clipboard paste for special characters.
    """
    # Click the text area to make sure it has focus
    pyautogui.click()
    time.sleep(0.2)

    # Use clipboard paste for reliability with special characters
    import subprocess
    # Set clipboard via PowerShell (works on all Windows versions)
    escaped = content.replace('"', '`"')
    try:
        subprocess.run(
            ["powershell", "-command", f'Set-Clipboard -Value "{escaped}"'],
            check=True,
            capture_output=True,
        )
        pyautogui.hotkey("ctrl", "v")
    except Exception:
        # Fallback: type character by character
        pyautogui.write(content, interval=TYPING_INTERVAL)

    time.sleep(0.3)


def save_file_as(filename: str, directory: str) -> bool:
    """
    Save the current Notepad document using File > Save As.
    Types the full path to ensure it lands in the right directory.
    Returns True on success.
    """
    full_path = os.path.join(directory, filename)

    # Open Save As dialog
    pyautogui.hotkey("ctrl", "shift", "s")
    time.sleep(1.0)

    # If Ctrl+Shift+S doesn't work (older Notepad), use Ctrl+S on a new file
    # Check if a Save As dialog appeared
    save_dialogs = gw.getWindowsWithTitle("Save As")
    if not save_dialogs:
        # Try the menu approach
        pyautogui.hotkey("alt", "f")
        time.sleep(0.4)
        pyautogui.press("a")
        time.sleep(1.0)

    # Type the full file path into the filename box
    # First clear whatever is there, then type our path
    pyautogui.hotkey("ctrl", "a")
    time.sleep(0.2)
    pyautogui.typewrite(full_path, interval=0.03)
    time.sleep(0.3)
    pyautogui.press("enter")
    time.sleep(0.5)

    # Handle "file already exists" confirmation dialog if it appears
    confirm_dialogs = gw.getWindowsWithTitle("Confirm Save As")
    if confirm_dialogs:
        pyautogui.press("enter")  # Press Yes/OK
        time.sleep(0.3)

    print(f"[automation] ✓ Saved: {full_path}")
    return True


def close_notepad() -> None:
    """Close the active Notepad window."""
    pyautogui.hotkey("alt", "f4")
    time.sleep(0.5)

    # If an "unsaved changes" dialog appears, don't save (we already saved)
    unsaved_dialogs = (
        gw.getWindowsWithTitle("Notepad")
        + gw.getWindowsWithTitle("Save")
    )
    for dlg in unsaved_dialogs:
        if "Notepad" not in dlg.title or dlg.title == "Notepad":
            continue
        # Click "Don't Save" / "No"
        pyautogui.press("tab")
        time.sleep(0.1)
        pyautogui.press("enter")
        break

    time.sleep(0.3)
    print("[automation] ✓ Notepad closed.")


def minimize_all_windows() -> None:
    """Show the desktop (Win+D) so icons are visible for grounding."""
    pyautogui.hotkey("win", "d")
    time.sleep(0.8)
