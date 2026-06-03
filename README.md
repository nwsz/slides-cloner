# 📸 slides-capture

A no-API, no-browser-extension Python tool for capturing every slide in a presentation as a clean, numbered screenshot. Works in two modes — drive the deck yourself, or just watch passively while someone else presents.

---

## Supports

<p align="left">
  <img src="assets/slides.png" alt="Google Slides" height="48" title="Google Slides" />
  &nbsp;&nbsp;
  <img src="assets/powerpoint.png" alt="Microsoft PowerPoint" height="48" title="Microsoft PowerPoint" />
</p>

Anything you can fullscreen on your monitor — Google Slides, PowerPoint, Keynote, LibreOffice Impress, PDF decks.

---

## Built with Python

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat&logo=python&logoColor=white)
![pyautogui](https://img.shields.io/badge/pyautogui-screenshot%20%26%20keys-grey?style=flat)
![Pillow](https://img.shields.io/badge/Pillow-image%20IO-grey?style=flat)
![imagehash](https://img.shields.io/badge/imagehash-perceptual%20diff-grey?style=flat)
![keyboard](https://img.shields.io/badge/keyboard-hotkey%20listener-grey?style=flat)

No Selenium. No browser extensions. No API keys. Just Python talking directly to your screen and keyboard.

---

## Modes

### `auto` — You're in control
Put the presentation into fullscreen, run the script, and it drives itself. It takes a screenshot, presses `→`, waits, repeats — and stops automatically when it detects the end of the deck via perceptual hashing.

Best for: exporting your own deck when you have full keyboard control.

### `watch` — Someone else is presenting
The script polls the screen every N milliseconds with a perceptual hash. The moment it detects a real slide change (ignoring cursor movement and transition noise), it waits for the transition to settle, then fires a screenshot.

Best for: recording a live presentation, screenshare, or video where you can't click through yourself.

---

## Installation

**1. Clone the repo**
```bash
git clone https://github.com/your-username/slides-capture.git
cd slides-capture
```

**2. Install dependencies**
```bash
pip install pyautogui pillow keyboard imagehash
```

> **Linux users:** `keyboard` requires root or a `uinput` group membership to listen for global keypresses. Run with `sudo python slides_capture.py` or [add yourself to the uinput group](https://github.com/boppreh/keyboard#linux).

> **macOS users:** You'll need to grant Terminal (or your IDE) **Accessibility** and **Screen Recording** permissions under *System Settings → Privacy & Security*.

**3. Copy `config.json` next to the script** (it's already there if you cloned the repo) and edit it for your session — see [Configuration](#configuration) below.

---

## Setup & Usage

### Auto mode (you control the slides)

1. Open your presentation and switch to **fullscreen** (`F5` in Google Slides / PowerPoint, `⌘⇧F` in Keynote).
2. Edit `config.json`: set `"mode": "auto"` and give your session a name.
3. Run the script:
   ```bash
   python slides_capture.py
   ```
4. A countdown starts — click into the presentation window before it hits zero.
5. The script takes over: screenshot → advance → repeat until the end of the deck is detected.

### Watch mode (someone else is presenting)

1. Get the presentation visible and fullscreen on your screen.
2. Edit `config.json`: set `"mode": "watch"`.
3. Run the script:
   ```bash
   python slides_capture.py
   ```
4. The script immediately captures the first slide, then silently watches. Every time a new slide appears, it captures it.
5. Press your `stop_key` (default `Q`) at any time to stop.

### Emergency stops
- Press the configured `stop_key` (default `Q`) anywhere, any time — it's a background thread listener.
- Move your mouse to the **top-left corner** of the screen — `pyautogui`'s built-in failsafe will kill the script instantly.
- `Ctrl+C` in the terminal also works.

---

## Output

Screenshots are saved to a timestamped folder inside `output_dir`:

```
slides_output/
└── morning-standup_20250603_141200/
    ├── morning-standup_001.png
    ├── morning-standup_002.png
    ├── morning-standup_003.png
    └── ...
```

The session name comes from `"session_name"` in `config.json`. Spaces are replaced with hyphens automatically.

---

## Configuration

All settings live in `config.json` next to the script. No need to touch the Python file.

```json
{
  "session_name": "my-presentation",
  "output_dir":   "slides_output",
  "mode":         "auto",
  "auto": {
    "slide_delay": 0.3,
    "countdown":   5,
    "max_slides":  40
  },
  "watch": {
    "poll_interval":    0.2,
    "change_threshold": 8,
    "settle_delay":     0.3,
    "max_slides":       200
  },
  "image_format": "png",
  "stop_key":     "q"
}
```

### Top-level keys

| Key | Type | Description |
|---|---|---|
| `session_name` | string | Prefix for every screenshot filename and the output folder. Use something descriptive — `"q3-board-review"`, `"onboarding-deck"`. |
| `output_dir` | string | Root folder where session subfolders are created. Relative to the script location. |
| `mode` | `"auto"` \| `"watch"` | Which capture mode to run. |
| `image_format` | `"png"` \| `"jpg"` | Output image format. PNG is lossless and recommended. |
| `stop_key` | string | Key to press anywhere to abort immediately. Any single key name recognised by the `keyboard` library (e.g. `"q"`, `"esc"`, `"f12"`). |

### `auto` block

| Key | Type | Description |
|---|---|---|
| `slide_delay` | float (seconds) | How long to wait after pressing `→` before taking the next screenshot. Increase this if your slides have long animations or transitions — `0.8`–`1.5` is good for animated decks. |
| `countdown` | int (seconds) | Time between running the script and capture starting, so you can click into the presentation window. |
| `max_slides` | int | Safety cap. The script will also stop automatically when the end of the deck is detected, so this is a fallback. Raise it for long decks. |

### `watch` block

| Key | Type | Description |
|---|---|---|
| `poll_interval` | float (seconds) | How often the screen is sampled. `0.2` (5× per second) is a good balance between responsiveness and CPU use. |
| `change_threshold` | int | Perceptual hash Hamming distance needed to trigger a capture. The scale: `0–3` = noise/cursor, `4–7` = transition frames, `8+` = definite new content. Lower = more sensitive; raise to `10–12` if you're getting false positives from animated content. |
| `settle_delay` | float (seconds) | After detecting a change, how long to wait before saving — lets slide transitions finish so you get a clean frame. Increase to `0.6`–`1.0` for decks with slow transitions. |
| `max_slides` | int | Upper bound on the number of slides to capture in a session. |

---

## Function Reference

| Function | Signature | Description |
|---|---|---|
| `load_config` | `() → dict` | Reads and parses `config.json` from the same directory as the script. Raises `FileNotFoundError` if missing. |
| `countdown` | `(seconds: int) → None` | Prints an in-place countdown to the terminal, giving you time to click into the fullscreen presentation window. |
| `make_output_dir` | `(base: str, session: str) → Path` | Creates a timestamped session folder inside `base` (e.g. `slides_output/morning-standup_20250603_141200/`) and returns its `Path`. |
| `slide_filename` | `(folder: Path, session: str, index: int, fmt: str) → Path` | Builds the full output path for a slide, e.g. `morning-standup_003.png`. |
| `capture` | `(path: Path) → tuple[Image, ImageHash]` | Takes a full-screen screenshot, saves it to `path`, and returns both the PIL `Image` and its perceptual hash. |
| `phash_distance` | `(a: ImageHash, b: ImageHash) → int` | Returns the Hamming distance between two perceptual hashes. `0` = identical; higher = more different. Used by watch mode to decide whether a real slide change occurred. |
| `run_auto` | `(cfg: dict, output_folder: Path, session: str) → None` | Drives the slideshow: screenshot → `→` key → wait → repeat. Stops automatically on end-of-deck detection or `max_slides`. |
| `run_watch` | `(cfg: dict, output_folder: Path, session: str) → None` | Passively monitors the screen. Fires a screenshot whenever `phash_distance` exceeds `change_threshold`, after waiting `settle_delay` for transitions to finish. |
| `main` | `() → None` | Entry point. Loads config, prints the session summary, starts the stop-key listener thread, creates the output folder, and dispatches to `run_auto` or `run_watch`. |

---

## Tips & Troubleshooting

**Slides are being skipped (auto mode)**
Increase `slide_delay`. If your deck has animations, `0.3s` may not be long enough for the slide to fully render before the next `→` is pressed.

**Watch mode is triggering on animated content / video**
Raise `change_threshold` to `12`–`15`. This makes the detector less sensitive and only fires on large visual changes.

**Watch mode is missing fast transitions**
Lower `poll_interval` to `0.1`, and reduce `change_threshold` slightly.

**Duplicate slides at the end (auto mode)**
This shouldn't happen — the end-of-deck detector removes them automatically. If you do see extras, check that `MAX_IDENTICAL = 2` in the source is sufficient for your deck's behaviour.

**macOS: keyboard listener does nothing**
Go to *System Settings → Privacy & Security → Accessibility* and enable your terminal app. You may also need *Screen Recording* permission for `pyautogui` to capture the screen.

**Linux: `keyboard` raises a permissions error**
Run with `sudo`, or add your user to the `input` group:
```bash
sudo usermod -aG input $USER
# log out and back in
```

---

## Project structure

```
slides-capture/
├── slides_capture.py   # main script
├── config.json         # all configuration lives here
├── README.md
└── assets/
    ├── slides.png      # Google Slides icon
    └── powerpoint.png  # PowerPoint icon
```

---

## Licence

MIT
