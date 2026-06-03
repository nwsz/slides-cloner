#!/usr/bin/env python3
"""
Slides Screenshot Tool
------------------------------
Two modes, configured via config.json:

  auto   — You control the slide transitions. The script clicks through for
            you: press right-arrow, screenshot, repeat.

  watch  — You (or someone else) controls the slideshow. The script watches
            the screen with a perceptual hash and fires a screenshot whenever
            it detects a real slide change (ignores cursor flickers / minor
            redraws).

Requirements:
    pip install pyautogui pillow keyboard imagehash

More info: https://github.com/nwsz/slides-cloner/
"""

import hashlib
import json
import os
import threading
import time
from datetime import datetime
from pathlib import Path

import imagehash
import keyboard
import pyautogui
from PIL import Image

# ── Config loading ────────────────────────────────────────────────────────────

CONFIG_PATH = Path(__file__).parent / "config.json"


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"config.json not found at {CONFIG_PATH}\n"
            "Create one next to this script — see the bundled config.json for options."
        )
    with CONFIG_PATH.open() as f:
        return json.load(f)


# ── Stop flag ─────────────────────────────────────────────────────────────────

_stop = threading.Event()


def _listen_for_stop(key: str):
    keyboard.wait(key)
    _stop.set()


# ── Helpers ───────────────────────────────────────────────────────────────────

def countdown(seconds: int):
    print(f"\n  Click into your fullscreen presentation now!\n")
    for i in range(seconds, 0, -1):
        print(f"  Starting in {i}...", end="\r", flush=True)
        time.sleep(1)
    print("  Starting now!          ")


def make_output_dir(base: str, session: str) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder = Path(base) / f"{session}_{timestamp}"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def slide_filename(folder: Path, session: str, index: int, fmt: str) -> Path:
    """e.g.  slides_output/my-talk_20250603_141200/my-talk_001.png"""
    return folder / f"{session}_{index:03d}.{fmt}"


def capture(path: Path) -> tuple[Image.Image, imagehash.ImageHash]:
    """Screenshot → PIL image + perceptual hash."""
    img = pyautogui.screenshot()
    img.save(path)
    phash = imagehash.phash(img)
    return img, phash


def phash_distance(a: imagehash.ImageHash, b: imagehash.ImageHash) -> int:
    """Hamming distance between two perceptual hashes (0 = identical)."""
    return a - b


# ── Mode: auto ────────────────────────────────────────────────────────────────

def run_auto(cfg: dict, output_folder: Path, session: str):
    """
    Drives the slideshow itself. Takes a screenshot, presses right-arrow,
    waits slide_delay, repeat. Stops when two consecutive frames hash the
    same (end of deck) or MAX_SLIDES is reached.
    """
    c          = cfg["auto"]
    delay      = float(c["slide_delay"])
    max_slides = int(c["max_slides"])
    fmt        = cfg["image_format"]

    countdown(int(c["countdown"]))

    slide_num        = 0
    prev_phash       = None
    identical_streak = 0
    MAX_IDENTICAL    = 2  # identical perceptual hashes → end of deck

    try:
        while slide_num < max_slides:
            if _stop.is_set():
                print(f"\n  [{cfg['stop_key'].upper()}] pressed — stopping.")
                break

            slide_num += 1
            path = slide_filename(output_folder, session, slide_num, fmt)
            _, phash = capture(path)
            print(f"  📸  Slide {slide_num:>3}  →  {path.name}")

            if prev_phash is not None and phash_distance(phash, prev_phash) == 0:
                identical_streak += 1
                if identical_streak >= MAX_IDENTICAL:
                    # Delete duplicates captured at the end of the deck
                    for extra in range(slide_num - identical_streak + 1, slide_num + 1):
                        dup = slide_filename(output_folder, session, extra, fmt)
                        if dup.exists():
                            dup.unlink()
                    real = slide_num - identical_streak
                    print(f"\n  End of deck detected after {real} slide(s).")
                    return
            else:
                identical_streak = 0

            prev_phash = phash
            pyautogui.press("right")
            time.sleep(delay)

        else:
            print(f"\n  Hit max_slides ({max_slides}). Raise it in config.json if needed.")

    except KeyboardInterrupt:
        print("\n  Stopped with Ctrl+C.")


# ── Mode: watch ───────────────────────────────────────────────────────────────

def run_watch(cfg: dict, output_folder: Path, session: str):
    """
    Passive mode — polls the screen with a perceptual hash every poll_interval
    seconds. When the hash distance exceeds change_threshold, waits settle_delay
    then fires a screenshot (so we capture the slide after any transition finishes).

    change_threshold  — how different the perceptual hash must be to count as a
                        new slide. 8 is a good default:
                          0–3  : noise / cursor movement
                          4–10 : transition frames / partial redraws  ← threshold here
                          10+  : definite new content
    """
    c          = cfg["watch"]
    poll       = float(c["poll_interval"])
    threshold  = int(c["change_threshold"])
    settle     = float(c["settle_delay"])
    max_slides = int(c["max_slides"])
    fmt        = cfg["image_format"]

    print(f"\n  Watch mode active — monitoring for slide changes.")
    print(f"  Change threshold : {threshold}  |  Poll : {poll}s  |  Settle : {settle}s")
    print(f"  Press [{cfg['stop_key'].upper()}] at any time to stop.\n")

    # Capture the initial slide immediately
    slide_num = 1
    path      = slide_filename(output_folder, session, slide_num, fmt)
    _, prev_phash = capture(path)
    print(f"  📸  Slide {slide_num:>3}  →  {path.name}  (initial)")

    try:
        while slide_num < max_slides:
            if _stop.is_set():
                print(f"\n  [{cfg['stop_key'].upper()}] pressed — stopping.")
                break

            time.sleep(poll)

            # Quick poll: grab screen and compute hash (don't save yet)
            poll_img  = pyautogui.screenshot()
            curr_hash = imagehash.phash(poll_img)
            dist      = phash_distance(curr_hash, prev_phash)

            if dist >= threshold:
                # Wait for the transition to finish before saving
                time.sleep(settle)

                slide_num += 1
                path = slide_filename(output_folder, session, slide_num, fmt)
                _, settled_hash = capture(path)
                print(f"  📸  Slide {slide_num:>3}  →  {path.name}  (Δ={dist})")
                prev_phash = settled_hash

        else:
            print(f"\n Hit max_slides ({max_slides}). Raise it in config.json if needed.")

    except KeyboardInterrupt:
        print("\n  Stopped with Ctrl+C.")


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    cfg     = load_config()
    mode    = cfg.get("mode", "auto").lower()
    session = cfg.get("session_name", "session").strip().replace(" ", "-")
    fmt     = cfg.get("image_format", "png")
    stop    = cfg.get("stop_key", "q")

    if mode not in ("auto", "watch"):
        raise ValueError(f"Unknown mode '{mode}' — set 'mode' to 'auto' or 'watch' in config.json")

    print("=" * 55)
    print("   Google Slides Screenshot Tool")
    print("=" * 55)
    print(f"  Mode          : {mode}")
    print(f"  Session       : {session}")
    print(f"  Output folder : {cfg['output_dir']}/")
    print(f"  Image format  : {fmt}")
    print(f"  Abort key     : [{stop.upper()}]")
    print("=" * 55)

    pyautogui.FAILSAFE = True  # move mouse to top-left corner to emergency-stop

    # Background thread: listen for the stop key at any moment
    t = threading.Thread(target=_listen_for_stop, args=(stop,), daemon=True)
    t.start()

    output_folder = make_output_dir(cfg["output_dir"], session)
    print(f"\n  Saving to: {output_folder.resolve()}")

    if mode == "auto":
        run_auto(cfg, output_folder, session)
    else:
        run_watch(cfg, output_folder, session)

    final = len(list(output_folder.glob(f"*.{fmt}")))
    print(f"\n  Done! {final} slide(s) saved to:\n  {output_folder.resolve()}\n")


if __name__ == "__main__":
    main()
