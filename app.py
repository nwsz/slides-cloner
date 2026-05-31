"""
Google Slides Screenshot Tool
------------------------------
Put your presentation into fullscreen mode first (press F5 in Google Slides),
then run this script. It will:
  1. Count down so you can click into the presentation window
  2. Screenshot each slide
  3. Press the right arrow key to advance
  4. Repeat until it detects the end or hits the slide limit

Requirements:
    pip install pyautogui pillow keyboard
"""

import os
import threading
import time
import hashlib
import pyautogui
import keyboard
from PIL import Image
from datetime import datetime

# ── Configuration ────────────────────────────────────────────────────────────

OUTPUT_DIR   = "slides_output"  # folder where screenshots are saved
SLIDE_DELAY  = 0.3              # seconds to wait after advancing — lower = faster
                                # increase if slides have transitions/animations

COUNTDOWN    = 5                # seconds before capture starts
MAX_SLIDES   = 40              # safety cap
IMAGE_FORMAT = "png"            # "png" or "jpg"
STOP_KEY     = "q"              # press this anytime to abort immediately

# ── Stop flag (set by background listener) ───────────────────────────────────

_stop = threading.Event()

def _listen_for_stop():
    keyboard.wait(STOP_KEY)
    _stop.set()

# ── Helpers ───────────────────────────────────────────────────────────────────

def countdown(seconds: int):
    print(f"\n  Click into your fullscreen presentation now!\n")
    for i in range(seconds, 0, -1):
        print(f"  Starting in {i}...", end="\r", flush=True)
        time.sleep(1)
    print("  Starting now!          ")


def make_output_dir(base: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder = os.path.join(base, f"session_{timestamp}")
    os.makedirs(folder, exist_ok=True)
    return folder


def take_screenshot(folder: str, slide_num: int) -> tuple[str, str]:
    """Take a screenshot, save it, and return (filepath, md5_hash)."""
    filename = os.path.join(folder, f"slide_{slide_num:03d}.{IMAGE_FORMAT}")
    screenshot = pyautogui.screenshot()
    screenshot.save(filename)
    raw = screenshot.tobytes()
    img_hash = hashlib.md5(raw).hexdigest()
    return filename, img_hash


def advance_slide():
    pyautogui.press("right")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("=" * 55)
    print("   Google Slides Screenshot Tool")
    print("=" * 55)
    print(f"  Output folder : {OUTPUT_DIR}/")
    print(f"  Delay/slide   : {SLIDE_DELAY}s")
    print(f"  Max slides    : {MAX_SLIDES}")
    print(f"  Abort key     : [{STOP_KEY}]  (works instantly)")
    print("=" * 55)

    pyautogui.FAILSAFE = True  # move mouse to top-left corner to emergency-stop

    # Start background thread that listens for Q at any moment
    t = threading.Thread(target=_listen_for_stop, daemon=True)
    t.start()

    output_folder = make_output_dir(OUTPUT_DIR)
    print(f"\n  Saving to: {output_folder}")

    countdown(COUNTDOWN)

    slide_count      = 0
    prev_hash        = None
    identical_streak = 0
    MAX_IDENTICAL    = 2  # 2 identical frames in a row = end of deck

    try:
        while slide_count < MAX_SLIDES:

            if _stop.is_set():
                print(f"\n  [{STOP_KEY.upper()}] pressed — stopping.")
                break

            slide_count += 1
            path, img_hash = take_screenshot(output_folder, slide_count)
            print(f"  📸  Slide {slide_count:>3}  →  {os.path.basename(path)}")

            # End-of-deck detection via hash comparison (much faster than pixel diff)
            if img_hash == prev_hash:
                identical_streak += 1
                if identical_streak >= MAX_IDENTICAL:
                    # Remove the duplicate(s)
                    for extra in range(slide_count - identical_streak + 1, slide_count + 1):
                        dup = os.path.join(output_folder, f"slide_{extra:03d}.{IMAGE_FORMAT}")
                        if os.path.exists(dup):
                            os.remove(dup)
                    real_count = slide_count - identical_streak
                    print(f"\n End of deck detected after {real_count} slide(s).")
                    break
            else:
                identical_streak = 0

            prev_hash = img_hash

            advance_slide()
            time.sleep(SLIDE_DELAY)

        else:
            print(f"\n Hit MAX_SLIDES ({MAX_SLIDES}). Raise it in the config if needed.")

    except KeyboardInterrupt:
        print("\n  Stopped with Ctrl+C.")

    final_count = len([f for f in os.listdir(output_folder) if f.endswith(f".{IMAGE_FORMAT}")])
    print(f"\n  Done! {final_count} slide(s) saved to:\n  {os.path.abspath(output_folder)}\n")


if __name__ == "__main__":
    main()
