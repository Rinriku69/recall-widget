"""Small always-on-top window that cycles through the facts in facts.md

Double-click this file to open it (.pyw = run with pythonw, so no console window)
- Left-click: reveal the answer / go to the next fact
- Left-drag: move the window (the position is remembered for next time)
- Right-click: menu (Next, Open notes file, Always on top, Close)
- Ctrl+Alt+N (works from any program): bring the window to the front
- Double-click the file again while it's running: brings up the running one instead of opening a second
"""

import ctypes
import json
import os
import queue
import random
import re
import socket
import sys
import threading
import tkinter as tk
from ctypes import wintypes
from pathlib import Path

# Find the folder that holds the notes file and the state file
# - Run as .pyw: __file__ is the script itself, so its folder is the right one
# - Run as an exe built with PyInstaller --onefile: the exe unpacks its code into a temp
#   folder before running, so __file__ points into temp, which is deleted on exit.
#   Use sys.executable (the path of the exe itself) instead, so the notes file lives
#   next to the exe where the user can edit it.
#   PyInstaller sets sys.frozen = True. getattr with a default of False is needed because
#   under normal Python the attribute doesn't exist at all (sys.frozen would raise AttributeError)
if getattr(sys, "frozen", False):
    HERE = Path(sys.executable).resolve().parent
else:
    HERE = Path(__file__).resolve().parent
FACTS_FILE = HERE / "facts.md"
STATE_FILE = HERE / ".recall_widget_state.json"  # remembers window position + topmost setting

# Single instance: the first instance holds this port. A later launch can't bind it,
# which is how it knows an instance is already running
SINGLE_INSTANCE_PORT = 47613

# Windows global hotkey: these numbers come from the Win32 RegisterHotKey docs
MOD_ALT, MOD_CONTROL, MOD_NOREPEAT = 0x0001, 0x0002, 0x4000  # NOREPEAT = holding the key doesn't fire repeatedly
VK_N = 0x4E  # virtual key = a physical key position, not a character, so it works in any keyboard layout
WM_HOTKEY = 0x0312
HOTKEY_LABEL = "Ctrl+Alt+N"

QUESTION_SECONDS = 10  # show the question first so you try to recall the answer yourself (active recall)
ANSWER_SECONDS = 20
WIDTH = 380

BG, FG, MUTED, ACCENT, CODE_BG = "#16181d", "#e6e6e6", "#8a8f98", "#e8b04b", "#262a33"
TEXT_FONT = ("Leelawadee UI", 11)  # ships with Windows; renders Latin and Thai text
CODE_FONT = ("Consolas", 10)


def load_facts(path: Path) -> list[tuple[str, str]]:
    """Read markdown → list of (question, answer), using '## ' as the separator"""
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)  # drop HTML comments
    facts = []
    # re.split with a capture group also returns the separators:
    # [before first heading, heading1, body1, heading2, body2, ...]
    parts = re.split(r"^## (.+)$", text, flags=re.M)
    for i in range(1, len(parts) - 1, 2):
        question, answer = parts[i].strip(), parts[i + 1].strip()
        if question:
            facts.append((question, answer))
    return facts


# ---------- Things that run in background threads ----------
# Tk isn't safe to call from multiple threads, so these threads never touch the window.
# They only put messages into a queue (a mailbox that many threads can safely put into
# and take from at the same time), and Tk's main thread picks them up (see _poll_events)

def claim_single_instance() -> tuple[bool, socket.socket | None]:
    """Return (is another instance already running, server socket if we're the first)"""
    server = socket.socket()
    # Stop other programs from binding the same port on top of us (Windows allows that in some cases by default)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
    try:
        server.bind(("127.0.0.1", SINGLE_INSTANCE_PORT))  # 127.0.0.1 = this machine only, so no firewall prompt
        server.listen()
        return False, server
    except OSError:
        server.close()
    # Couldn't bind → probably an instance is running. Ask it to show itself and wait for confirmation
    try:
        with socket.create_connection(("127.0.0.1", SINGLE_INSTANCE_PORT), timeout=1) as conn:
            conn.sendall(b"show\n")
            if conn.recv(16) == b"ok\n":
                return True, None
    except OSError:
        pass
    # Some other program (not us) holds the port → start normally, just without single-instance protection
    return False, None


def serve_show_requests(server: socket.socket, events: queue.Queue) -> None:
    """Wait for later launches to knock, then pass "show" to the main thread"""
    while True:
        conn, _addr = server.accept()  # blocks here, which is why it needs its own thread
        with conn:
            conn.settimeout(1)
            try:
                if conn.recv(16) == b"show\n":
                    conn.sendall(b"ok\n")
                    events.put("show")
            except OSError:
                pass


def listen_hotkey(events: queue.Queue) -> None:
    """Register the hotkey with Windows and wait. Each press sends "show" to the main thread"""
    user32 = ctypes.windll.user32
    # hwnd=None = Windows posts the hotkey message to this thread's own message queue.
    # If registered on the main thread, Tk's mainloop could grab and discard the message before we see it
    if not user32.RegisterHotKey(None, 1, MOD_CONTROL | MOD_ALT | MOD_NOREPEAT, VK_N):
        events.put("hotkey-failed")  # usually because another program already owns this hotkey
        return
    msg = wintypes.MSG()
    # GetMessageW blocks until a message arrives. Returns 0 on WM_QUIT, -1 on error
    while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
        if msg.message == WM_HOTKEY:
            events.put("show")


class RecallWidget:
    def __init__(self, server: socket.socket | None) -> None:
        self.root = tk.Tk()
        self.state = self._load_state()
        self.facts: list[tuple[str, str]] = []
        self.deck: list[int] = []  # shuffled order; every card is shown once before reshuffling (no back-to-back repeats)
        self.current: tuple[str, str] | None = None
        self.showing_answer = False
        self.facts_mtime = 0.0
        self.timer: str | None = None  # id from root.after, kept so it can be cancelled when the user clicks ahead
        self.drag_start: tuple[int, int] | None = None
        self.dragged = False
        self.notice: str | None = None  # warning appended to every card (e.g. the hotkey isn't available)
        self.events: queue.Queue[str] = queue.Queue()

        self._build_window()
        self._reload_if_changed()
        self.next_fact()

        # daemon=True = don't wait for these threads on exit (they loop forever and never finish on their own)
        threading.Thread(target=listen_hotkey, args=(self.events,), daemon=True).start()
        if server is not None:
            threading.Thread(target=serve_show_requests, args=(server, self.events), daemon=True).start()
        self._poll_events()

    # ---------- Window ----------
    def _build_window(self) -> None:
        root = self.root
        root.overrideredirect(True)  # no title bar / window border
        root.attributes("-alpha", 0.93)
        root.attributes("-topmost", self.state.get("topmost", True))
        root.configure(bg=BG)
        x, y = self.state.get("x", 40), self.state.get("y", 40)
        root.geometry(f"{WIDTH}x120+{x}+{y}")

        self.text = tk.Text(
            root, bg=BG, fg=FG, font=TEXT_FONT, wrap="word", bd=0, highlightthickness=0,
            padx=14, pady=12, cursor="hand2", spacing1=2, spacing3=2,
        )
        self.text.pack(fill="both", expand=True)
        self.text.tag_configure("q", foreground=ACCENT, font=(TEXT_FONT[0], 12, "bold"))
        self.text.tag_configure("code", font=CODE_FONT, background=CODE_BG)
        self.text.tag_configure("hint", foreground=MUTED, font=(TEXT_FONT[0], 9))

        # bind = attach a callback: "when this event happens, call this function". Tk calls it for us later
        self.text.bind("<ButtonPress-1>", self._on_press)
        self.text.bind("<B1-Motion>", self._on_drag)
        self.text.bind("<ButtonRelease-1>", self._on_release)
        self.text.bind("<Button-3>", self._show_menu)

        self.menu = tk.Menu(root, tearoff=0)
        self.menu.add_command(label="Next", command=self.next_fact)
        self.menu.add_command(label="Open notes file", command=lambda: os.startfile(FACTS_FILE))
        self.topmost_var = tk.BooleanVar(value=self.state.get("topmost", True))
        self.menu.add_checkbutton(label="Always on top", variable=self.topmost_var, command=self._toggle_topmost)
        self.menu.add_separator()
        self.menu.add_command(label="Close", command=self._quit)

    def _render(self) -> None:
        if self.current is None:
            question, answer = "No facts yet", f"Add a '## ...' heading to {FACTS_FILE.name}"
        else:
            question, answer = self.current
        t = self.text
        t.configure(state="normal")
        t.delete("1.0", "end")
        self._insert_with_code(question, "q")
        t.insert("end", "\n")
        if self.showing_answer:
            self._insert_with_code(answer, None)
        else:
            t.insert("end", "Recall the answer first… (click to reveal)", "hint")
        if self.notice:
            t.insert("end", f"\n{self.notice}", "hint")
        t.configure(state="disabled")  # read-only, can't type over it
        self._fit_height()

    def _insert_with_code(self, s: str, base_tag: str | None) -> None:
        # Split on `...`: odd-indexed chunks are the parts inside backticks → add the "code" tag
        for i, chunk in enumerate(re.split(r"`([^`]*)`", s)):
            tags = tuple(tag for tag in (base_tag, "code" if i % 2 else None) if tag)
            self.text.insert("end", chunk, tags)

    def _fit_height(self) -> None:
        # Let Tk compute line wrapping first, then count the displayed lines to size the window
        self.root.update_idletasks()
        lines = self.text.count("1.0", "end", "displaylines")
        lines = lines[0] if isinstance(lines, tuple) else (lines or 1)
        height = min(40 + lines * 24, 420)
        self.root.geometry(f"{WIDTH}x{height}+{self.root.winfo_x()}+{self.root.winfo_y()}")

    # ---------- Cycling facts ----------
    def _reload_if_changed(self) -> None:
        try:
            mtime = FACTS_FILE.stat().st_mtime
        except FileNotFoundError:
            self.facts, self.deck = [], []
            return
        if mtime != self.facts_mtime:  # the file changed since the last load → reload
            self.facts_mtime = mtime
            self.facts = load_facts(FACTS_FILE)
            self.deck = []

    def _schedule(self, seconds: int, callback) -> None:
        if self.timer:
            self.root.after_cancel(self.timer)
        # after = "call this callback in N ms". Unlike sleep, it doesn't freeze the window
        self.timer = self.root.after(seconds * 1000, callback)

    def next_fact(self) -> None:
        self._reload_if_changed()
        if not self.facts:
            self.current = None
        else:
            if not self.deck:
                self.deck = list(range(len(self.facts)))
                random.shuffle(self.deck)
            self.current = self.facts[self.deck.pop()]
        self.showing_answer = False
        self._render()
        self._schedule(QUESTION_SECONDS, self.reveal)

    def reveal(self) -> None:
        self.showing_answer = True
        self._render()
        self._schedule(ANSWER_SECONDS, self.next_fact)

    # ---------- Mouse ----------
    def _on_press(self, e: tk.Event) -> str:
        self.drag_start = (e.x_root - self.root.winfo_x(), e.y_root - self.root.winfo_y())
        self.dragged = False
        return "break"  # "break" = stop Text from doing its default behavior (e.g. selecting text)

    def _on_drag(self, e: tk.Event) -> str:
        if self.drag_start:
            self.dragged = True
            dx, dy = self.drag_start
            self.root.geometry(f"+{e.x_root - dx}+{e.y_root - dy}")
        return "break"

    def _on_release(self, _e: tk.Event) -> str:
        if self.dragged:
            self._save_state()
        elif self.showing_answer:
            self.next_fact()
        else:
            self.reveal()
        return "break"

    def _show_menu(self, e: tk.Event) -> None:
        self.menu.tk_popup(e.x_root, e.y_root)

    # ---------- Bringing the window back ----------
    def _poll_events(self) -> None:
        # Take the messages other threads left in the queue and handle them on the main thread (the only one allowed to touch Tk)
        try:
            while True:
                event = self.events.get_nowait()  # empty → raises queue.Empty, which ends the loop
                if event == "show":
                    self.bring_to_front()
                elif event == "hotkey-failed":
                    self.notice = f"Hotkey {HOTKEY_LABEL} unavailable (another program owns it)"
                    self._render()
        except queue.Empty:
            pass
        self.root.after(150, self._poll_events)  # schedule itself again in 150 ms, forever

    def bring_to_front(self) -> None:
        self.root.deiconify()
        self.root.lift()
        # overrideredirect windows aren't in Alt+Tab, and lift alone sometimes doesn't reach the front.
        # Reliable way: turn topmost on briefly to jump to the very top, then restore the user's setting.
        # When topmost is cleared, Windows places the window at the top of the non-topmost band, so it stays in front
        self.root.attributes("-topmost", True)
        # lambda = an unnamed function that wraps the call so after can run it later (passing it directly would run it now)
        self.root.after(100, lambda: self.root.attributes("-topmost", self.topmost_var.get()))

    def _toggle_topmost(self) -> None:
        self.root.attributes("-topmost", self.topmost_var.get())
        self._save_state()

    # ---------- State ----------
    def _load_state(self) -> dict:
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_state(self) -> None:
        state = {"x": self.root.winfo_x(), "y": self.root.winfo_y(), "topmost": self.topmost_var.get()}
        STATE_FILE.write_text(json.dumps(state), encoding="utf-8")

    def _quit(self) -> None:
        self._save_state()
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()  # keeps waiting for events (clicks, timers) until the window closes


if __name__ == "__main__":
    already_running, server = claim_single_instance()
    if already_running:
        sys.exit()  # the running instance got the message and will show itself; this one doesn't need to open
    RecallWidget(server).run()
