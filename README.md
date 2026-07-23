# ☁️ Cloudie

Cloudie is a personal, offline voice assistant for Windows — built as a side project to explore fully local AI (no cloud APIs, no data leaving your machine).

> **Status: Work in progress.** Core functionality (offline speech recognition, local LLM responses, app launching) is working. Currently paused while exploring ways to make Ollama more lightweight — actively planning next iteration.
---

## What it does

- **Listens** for your voice using [Vosk](https://alphacephei.com/vosk/) (offline speech recognition — no internet required)
- **Responds** using [Ollama](https://ollama.com/) running `llama3.2` locally, so all conversation stays on your device
- **Speaks back** using `pyttsx3` (offline text-to-speech)
- **Opens apps/websites** on command — say "open chrome", "open spotify", "open notepad", etc.
- Shows a small floating subtitle-style chat window (built with Tkinter) so you can see what it heard and how it responded

## Privacy by design

Cloudie is **not** always listening. It only activates when you press **`Ctrl + Shift + F9`**, and you press it again to pause. This was a deliberate choice — a lot of always-on voice assistants (phones included) keep a live mic buffer running in the background, and that's a trade-off I didn't want to make here. You control exactly when it's listening.

## Tech stack

| Component | Tool |
|---|---|
| Speech-to-text | Vosk (offline) |
| Language model | Ollama + llama3.2 (offline) |
| Text-to-speech | pyttsx3 |
| UI | Tkinter |
| Hotkey / app launching | `keyboard`, `subprocess`, `webbrowser` |

## Setup

1. Install [Ollama](https://ollama.com/) and pull the model:
   ```
   ollama pull llama3.2
   ```
2. Download a [Vosk model](https://alphacephei.com/vosk/models) (small English model recommended) and update `VOSK_MODEL_PATH` in `Cloudie.py` to point to it.
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Update the hardcoded paths in `Cloudie.py` (`VOSK_MODEL_PATH`) and `Cloudie_listener.py` (`CLOUDIE_PATH`, `PYTHON_PATH`) to match your machine.
5. Run:
   ```
   python Cloudie.py
   ```
   or run `Cloudie_listener.py` to have it sit silently in the background and launch on hotkey press.

## Known limitations / what's next

- Currently Windows-only (uses Windows-specific app paths)
- App launcher paths in `APP_MAP` are hardcoded to specific install locations — needs to be made more portable
- No persistent memory across sessions yet
- Planning to revisit and continue development soon

---

Built as a personal project to learn about offline-first AI tooling, with some help from Claude for debugging and structuring along the way.
