import threading
import queue
import time
import math
import tkinter as tk
import pyttsx3
import requests
import keyboard
import vosk
import sounddevice as sd
import json
import sys

# ── CONFIG ──────────────────────────────────────────────────────────────────
VOSK_MODEL_PATH = r"C:\Users\Acer\OneDrive\ドキュメント\Desktop\vosk-model-small-en-us-0.15"
OLLAMA_URL      = "http://localhost:11434/api/generate"
OLLAMA_MODEL    = "llama3.2"
SAMPLE_RATE     = 16000
# ────────────────────────────────────────────────────────────────────────────

# ── STATE ────────────────────────────────────────────────────────────────────
is_listening   = False
is_speaking    = False
subtitles_on   = True
subtitle_queue = queue.Queue()
dot_state      = "idle"   # idle | listening | speaking
# ────────────────────────────────────────────────────────────────────────────


# ════════════════════════════════════════════════════════════════════════════
#  TTS  — runs in its own thread so it never blocks the UI
# ════════════════════════════════════════════════════════════════════════════
tts_queue = queue.Queue()

def tts_worker():
    engine = pyttsx3.init()
    engine.setProperty("rate", 165)
    while True:
        text = tts_queue.get()
        if text is None:
            break
        global is_speaking, dot_state
        is_speaking = True
        dot_state   = "speaking"
        engine.say(text)
        engine.runAndWait()
        is_speaking = False
        dot_state   = "idle"

threading.Thread(target=tts_worker, daemon=True).start()


def speak(text):
    tts_queue.put(text)


# ════════════════════════════════════════════════════════════════════════════
#  OLLAMA — ask the local LLM
# ════════════════════════════════════════════════════════════════════════════
def ask_ollama(prompt):
    try:
        resp = requests.post(OLLAMA_URL, json={
            "model":  OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False
        }, timeout=60)
        return resp.json().get("response", "I couldn't get a response.")
    except Exception as e:
        return f"Ollama error: {e}"


# ════════════════════════════════════════════════════════════════════════════
#  VOSK — speech recognition
# ════════════════════════════════════════════════════════════════════════════
print("Loading Vosk model…")
try:
    vosk_model = vosk.Model(VOSK_MODEL_PATH)
    print("Vosk model loaded ✓")
except Exception as e:
    print(f"Failed to load Vosk model: {e}")
    sys.exit(1)


def listen_once():
    """Record until silence, return recognised text."""
    global is_listening, dot_state
    recognizer = vosk.KaldiRecognizer(vosk_model, SAMPLE_RATE)
    result_text = ""

    is_listening = True
    dot_state    = "listening"
    push_subtitle("🎙 Listening…", "user")

    with sd.RawInputStream(samplerate=SAMPLE_RATE, blocksize=8000,
                            dtype="int16", channels=1) as stream:
        silence_count = 0
        while True:
            data, _ = stream.read(4000)
            if recognizer.AcceptWaveform(bytes(data)):
                res = json.loads(recognizer.Result())
                text = res.get("text", "").strip()
                if text:
                    result_text = text
                    break
                else:
                    silence_count += 1
                    if silence_count > 3:
                        break

    is_listening = False
    dot_state    = "idle"
    return result_text


def handle_f9():
    """Called when F9 is pressed."""
    if is_listening or is_speaking:
        return

    def _run():
        text = listen_once()
        if not text:
            push_subtitle("(nothing heard)", "user")
            return

        push_subtitle(f"You: {text}", "user")
        reply = ask_ollama(text)
        push_subtitle(f"Cloudie: {reply}", "cloudie")
        speak(reply)

    threading.Thread(target=_run, daemon=True).start()


# ════════════════════════════════════════════════════════════════════════════
#  SUBTITLE WINDOW  (top-right, semi-transparent, always on top)
# ════════════════════════════════════════════════════════════════════════════
MAX_LINES = 6   # how many lines to keep visible

subtitle_lines = []   # list of (text, tag)

def push_subtitle(text, tag):
    subtitle_queue.put((text, tag))


class SubtitleWindow:
    def __init__(self, root):
        self.root    = root
        self.visible = True

        # ── window style ────────────────────────────────────────────────────
        root.overrideredirect(True)          # no title bar
        root.attributes("-topmost", True)
        root.attributes("-alpha", 0.88)
        root.configure(bg="#0d0d0d")
        root.resizable(False, False)

        # ── position: top-right, 60 px down, 20 px from right ───────────────
        sw = root.winfo_screenwidth()
        root.geometry(f"380x220+{sw - 410}+60")

        # ── header ──────────────────────────────────────────────────────────
        header = tk.Frame(root, bg="#0d0d0d")
        header.pack(fill="x", padx=10, pady=(8, 2))
        tk.Label(header, text="◉ CLOUDIE", font=("Consolas", 9, "bold"),
                 fg="#4fc3f7", bg="#0d0d0d").pack(side="left")
        tk.Label(header, text="Ctrl+S = hide/show",
                 font=("Consolas", 7), fg="#444", bg="#0d0d0d").pack(side="right")

        # ── separator ───────────────────────────────────────────────────────
        tk.Frame(root, bg="#1e1e1e", height=1).pack(fill="x", padx=6)

        # ── text area ───────────────────────────────────────────────────────
        self.text = tk.Text(
            root, bg="#0d0d0d", fg="#cccccc",
            font=("Consolas", 10), wrap="word",
            state="disabled", bd=0, highlightthickness=0,
            padx=10, pady=6, height=10
        )
        self.text.pack(fill="both", expand=True)

        # colour tags
        self.text.tag_config("user",    foreground="#80cbc4")   # teal  — you
        self.text.tag_config("cloudie", foreground="#ce93d8")   # purple — Cloudie
        self.text.tag_config("system",  foreground="#555555")   # grey

        # ── drag support ─────────────────────────────────────────────────────
        root.bind("<Button-1>",        self._start_drag)
        root.bind("<B1-Motion>",       self._do_drag)
        self.text.bind("<Button-1>",   self._start_drag)
        self.text.bind("<B1-Motion>",  self._do_drag)

        # ── start polling queue ──────────────────────────────────────────────
        self._poll()

    # ── drag ────────────────────────────────────────────────────────────────
    def _start_drag(self, e):
        self._dx = e.x_root - self.root.winfo_x()
        self._dy = e.y_root - self.root.winfo_y()

    def _do_drag(self, e):
        self.root.geometry(f"+{e.x_root - self._dx}+{e.y_root - self._dy}")

    # ── toggle ───────────────────────────────────────────────────────────────
    def toggle(self):
        self.visible = not self.visible
        if self.visible:
            self.root.deiconify()
        else:
            self.root.withdraw()

    # ── add a subtitle line ──────────────────────────────────────────────────
    def add_line(self, text, tag):
        self.text.configure(state="normal")
        self.text.insert("end", text + "\n", tag)
        # keep only last MAX_LINES
        lines = int(self.text.index("end-1c").split(".")[0])
        if lines > MAX_LINES:
            self.text.delete("1.0", f"{lines - MAX_LINES}.0")
        self.text.see("end")
        self.text.configure(state="disabled")

    # ── poll queue every 100 ms ──────────────────────────────────────────────
    def _poll(self):
        while not subtitle_queue.empty():
            text, tag = subtitle_queue.get_nowait()
            self.add_line(text, tag)
        self.root.after(100, self._poll)


# ════════════════════════════════════════════════════════════════════════════
#  DOT-ARC OVERLAY  (top & bottom edges, pulsing dots)
# ════════════════════════════════════════════════════════════════════════════
DOT_COUNT  = 28       # dots per arc
ARC_RADIUS = 260      # how wide the arc spreads (pixels)
DOT_R      = 4        # dot radius at rest
COLORS = {
    "idle":      "#1a3a4a",
    "listening": "#4fc3f7",
    "speaking":  "#ce93d8",
}

class DotArcOverlay:
    def __init__(self, root):
        self.root = root
        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()

        root.overrideredirect(True)
        root.attributes("-topmost", True)
        root.attributes("-transparentcolor", "#000001")
        root.configure(bg="#000001")
        root.geometry(f"{sw}x{sh}+0+0")
        root.lift()

        self.canvas = tk.Canvas(root, width=sw, height=sh,
                                bg="#000001", highlightthickness=0)
        self.canvas.pack()

        self.sw = sw
        self.sh = sh
        self.phase = 0.0
        self.dots_top    = []
        self.dots_bottom = []
        self._build_dots()
        self._animate()

    def _build_dots(self):
        cx   = self.sw // 2
        half = DOT_COUNT // 2

        for i in range(DOT_COUNT):
            # spread dots evenly over a half-ellipse
            angle = math.pi * i / (DOT_COUNT - 1)   # 0 → π

            x = cx + ARC_RADIUS * math.cos(math.pi - angle)   # left→right
            dy = 18 * math.sin(angle)                           # arc depth

            # top arc  (curves downward into screen)
            yt = 14 + dy
            dt = self.canvas.create_oval(x - DOT_R, yt - DOT_R,
                                         x + DOT_R, yt + DOT_R,
                                         fill=COLORS["idle"], outline="")
            self.dots_top.append((dt, x, yt))

            # bottom arc (curves upward into screen)
            yb = self.sh - 14 - dy
            db = self.canvas.create_oval(x - DOT_R, yb - DOT_R,
                                         x + DOT_R, yb + DOT_R,
                                         fill=COLORS["idle"], outline="")
            self.dots_bottom.append((db, x, yb))

    def _animate(self):
        self.phase += 0.07
        state = dot_state
        color = COLORS[state]

        for idx, (dot_id, x, y) in enumerate(self.dots_top + self.dots_bottom):
            if state == "idle":
                pulse = 0.3 + 0.15 * math.sin(self.phase + idx * 0.3)
            else:
                pulse = 0.6 + 0.4 * math.abs_like(math.sin(self.phase + idx * 0.25))
                # glow ripple outward from centre
                pulse = 0.5 + 0.5 * math.sin(self.phase - idx * 0.18)

            r = max(1, DOT_R * pulse)
            self.canvas.coords(dot_id, x - r, y - r, x + r, y + r)
            self.canvas.itemconfig(dot_id, fill=color)

        self.root.after(40, self._animate)   # ~25 fps


# math helper (abs for pulse)
math.abs_like = lambda v: abs(v)


# ════════════════════════════════════════════════════════════════════════════
#  MAIN
# ════════════════════════════════════════════════════════════════════════════
def main():
    # ── subtitle window ──────────────────────────────────────────────────────
    sub_root = tk.Tk()
    sub_win  = SubtitleWindow(sub_root)

    # ── dot arc overlay ──────────────────────────────────────────────────────
    arc_root = tk.Toplevel(sub_root)
    DotArcOverlay(arc_root)

    # ── hotkeys ──────────────────────────────────────────────────────────────
    keyboard.add_hotkey("f9",          handle_f9,        suppress=True)
    keyboard.add_hotkey("ctrl+s",      sub_win.toggle,   suppress=False)
    keyboard.add_hotkey("ctrl+shift+q",sub_root.destroy, suppress=True)

    push_subtitle("Cloudie is ready. Press F9 to talk.", "system")

    sub_root.mainloop()


if __name__ == "__main__":
    main()
