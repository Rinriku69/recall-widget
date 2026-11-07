"""จอเล็กวน fact จาก linux-facts.md

ดับเบิลคลิกไฟล์นี้เพื่อเปิด (.pyw = รันด้วย pythonw ไม่มีหน้าต่าง console)
- คลิกซ้าย: เปิดคำตอบ / ไป fact ถัดไป
- ลากด้วยเมาส์ซ้าย: ย้ายตำแหน่ง (จำตำแหน่งไว้รอบหน้า)
- คลิกขวา: เมนู (ถัดไป, เปิดไฟล์โน้ต, ลอยบนสุด, ปิด)
- Ctrl+Alt+N (กดได้จากทุกโปรแกรม): ดึงจอขึ้นมาหน้าสุด
- ดับเบิลคลิกไฟล์ซ้ำตอนเปิดอยู่แล้ว: ดึงตัวเดิมขึ้นมา ไม่เปิดตัวที่สอง
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

# หาโฟลเดอร์ที่เก็บไฟล์โน้ตกับไฟล์ state
# - รันเป็น .pyw: __file__ คือตัวสคริปต์ ใช้โฟลเดอร์ของมันได้เลย
# - รันเป็น exe จาก PyInstaller --onefile: ตอนรัน exe จะแตกโค้ดไปไว้ในโฟลเดอร์ temp
#   __file__ เลยชี้ไปที่ temp ซึ่งโดนลบทิ้งตอนปิดโปรแกรม ต้องใช้ sys.executable
#   (path ของตัว exe) แทน ไฟล์โน้ตจะได้อยู่ข้าง exe ให้ผู้ใช้แก้เองได้
#   PyInstaller ตั้ง sys.frozen = True ไว้ให้ ใช้ getattr ใส่ค่า default เป็น False
#   เพราะตอนรันด้วย Python ปกติจะไม่มี attribute นี้เลย
if getattr(sys, "frozen", False):
    HERE = Path(sys.executable).resolve().parent
else:
    HERE = Path(__file__).resolve().parent
FACTS_FILE = HERE / "linux-facts.md"
STATE_FILE = HERE / ".fact_widget_state.json"  # จำตำแหน่งหน้าต่าง + ค่า topmost

# กันเปิดซ้ำ: ตัวแรกจอง port นี้ไว้ ตัวที่เปิดทีหลังจองไม่ได้ ก็จะรู้ว่ามีตัวเดิมอยู่แล้ว
SINGLE_INSTANCE_PORT = 47613

# คีย์ลัดระดับ Windows: ค่าตัวเลขพวกนี้มาจากเอกสาร RegisterHotKey ของ Win32
MOD_ALT, MOD_CONTROL, MOD_NOREPEAT = 0x0001, 0x0002, 0x4000  # NOREPEAT = กดค้างไม่ยิงซ้ำ
VK_N = 0x4E  # virtual key = ตำแหน่งปุ่ม ไม่ใช่ตัวอักษร เลยใช้ได้แม้กำลังพิมพ์ไทย
WM_HOTKEY = 0x0312
HOTKEY_LABEL = "Ctrl+Alt+N"

QUESTION_SECONDS = 10  # โชว์คำถามก่อน ให้ลองนึกคำตอบเอง (active recall)
ANSWER_SECONDS = 20
WIDTH = 380

BG, FG, MUTED, ACCENT, CODE_BG = "#16181d", "#e6e6e6", "#8a8f98", "#e8b04b", "#262a33"
TEXT_FONT = ("Leelawadee UI", 11)  # ฟอนต์ที่มากับ Windows และแสดงภาษาไทยได้
CODE_FONT = ("Consolas", 10)


def load_facts(path: Path) -> list[tuple[str, str]]:
    """อ่าน markdown → list ของ (คำถาม, คำตอบ) โดยใช้ '## ' เป็นตัวแบ่ง"""
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)  # ตัดคอมเมนต์ HTML ทิ้ง
    facts = []
    # re.split ที่มีวงเล็บจับกลุ่ม จะคืนตัวคั่นมาด้วย: [ก่อนหัวข้อแรก, หัวข้อ1, เนื้อหา1, หัวข้อ2, ...]
    parts = re.split(r"^## (.+)$", text, flags=re.M)
    for i in range(1, len(parts) - 1, 2):
        question, answer = parts[i].strip(), parts[i + 1].strip()
        if question:
            facts.append((question, answer))
    return facts


# ---------- ของที่รันใน thread แยก ----------
# Tk ไม่ปลอดภัยถ้าถูกเรียกจากหลาย thread thread พวกนี้จึงไม่แตะหน้าต่างเลย
# แค่ใส่ข้อความลง queue (กล่องจดหมายที่หลาย thread ใส่/หยิบพร้อมกันได้ปลอดภัย)
# แล้วให้ thread หลักของ Tk มาหยิบไปทำเอง (ดู _poll_events)

def claim_single_instance() -> tuple[bool, socket.socket | None]:
    """คืน (มีตัวเดิมเปิดอยู่แล้วไหม, server socket ถ้าเราเป็นตัวแรก)"""
    server = socket.socket()
    # กันโปรแกรมอื่น bind port เดียวกันซ้อนได้ (ค่า default ของ Windows ยอมให้ซ้อนในบางกรณี)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
    try:
        server.bind(("127.0.0.1", SINGLE_INSTANCE_PORT))  # 127.0.0.1 = ในเครื่องเท่านั้น firewall ไม่ถาม
        server.listen()
        return False, server
    except OSError:
        server.close()
    # จองไม่ได้ → น่าจะมีตัวเดิมอยู่ ลองบอกให้มันโผล่ขึ้นมา แล้วรอคำตอบยืนยัน
    try:
        with socket.create_connection(("127.0.0.1", SINGLE_INSTANCE_PORT), timeout=1) as conn:
            conn.sendall(b"show\n")
            if conn.recv(16) == b"ok\n":
                return True, None
    except OSError:
        pass
    # port ถูกโปรแกรมอื่นที่ไม่ใช่เราใช้อยู่ → เปิดได้ตามปกติ แค่ไม่มีระบบกันเปิดซ้ำ
    return False, None


def serve_show_requests(server: socket.socket, events: queue.Queue) -> None:
    """รอตัวที่เปิดทีหลังมาเคาะ แล้วส่ง "show" ให้ thread หลัก"""
    while True:
        conn, _addr = server.accept()  # บล็อกรอตรงนี้ ถึงต้องอยู่ใน thread แยก
        with conn:
            conn.settimeout(1)
            try:
                if conn.recv(16) == b"show\n":
                    conn.sendall(b"ok\n")
                    events.put("show")
            except OSError:
                pass


def listen_hotkey(events: queue.Queue) -> None:
    """ลงทะเบียนคีย์ลัดกับ Windows แล้วรอ ทุกครั้งที่กดจะส่ง "show" ให้ thread หลัก"""
    user32 = ctypes.windll.user32
    # hwnd=None = ให้ Windows ส่งสัญญาณเข้าคิวข้อความของ thread นี้เอง
    # ถ้าลงทะเบียนใน thread หลัก mainloop ของ Tk อาจหยิบข้อความไปทิ้งก่อนเราเห็น
    if not user32.RegisterHotKey(None, 1, MOD_CONTROL | MOD_ALT | MOD_NOREPEAT, VK_N):
        events.put("hotkey-failed")  # มักเพราะโปรแกรมอื่นจองคีย์นี้ไปแล้ว
        return
    msg = wintypes.MSG()
    # GetMessageW บล็อกรอจนมีข้อความเข้า คืน 0 ตอนได้ WM_QUIT, -1 ตอน error
    while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
        if msg.message == WM_HOTKEY:
            events.put("show")


class FactWidget:
    def __init__(self, server: socket.socket | None) -> None:
        self.root = tk.Tk()
        self.state = self._load_state()
        self.facts: list[tuple[str, str]] = []
        self.deck: list[int] = []  # ลำดับที่สุ่มไว้ โชว์ครบทุกอันก่อนค่อยสุ่มรอบใหม่ (ไม่ซ้ำติดกัน)
        self.current: tuple[str, str] | None = None
        self.showing_answer = False
        self.facts_mtime = 0.0
        self.timer: str | None = None  # id ของ root.after ไว้ยกเลิกตอนผู้ใช้คลิกข้าม
        self.drag_start: tuple[int, int] | None = None
        self.dragged = False
        self.notice: str | None = None  # ข้อความเตือนที่แปะท้ายการ์ดทุกใบ (เช่น คีย์ลัดใช้ไม่ได้)
        self.events: queue.Queue[str] = queue.Queue()

        self._build_window()
        self._reload_if_changed()
        self.next_fact()

        # daemon=True = ไม่ต้องรอ thread พวกนี้จบตอนปิดโปรแกรม (มันวนรอตลอดไป ไม่มีวันจบเอง)
        threading.Thread(target=listen_hotkey, args=(self.events,), daemon=True).start()
        if server is not None:
            threading.Thread(target=serve_show_requests, args=(server, self.events), daemon=True).start()
        self._poll_events()

    # ---------- หน้าต่าง ----------
    def _build_window(self) -> None:
        root = self.root
        root.overrideredirect(True)  # ไม่มี title bar / ขอบหน้าต่าง
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

        # bind = ผูก callback: "เมื่อเกิด event นี้ ให้เรียกฟังก์ชันนี้" Tk เป็นคนเรียกให้ทีหลัง
        self.text.bind("<ButtonPress-1>", self._on_press)
        self.text.bind("<B1-Motion>", self._on_drag)
        self.text.bind("<ButtonRelease-1>", self._on_release)
        self.text.bind("<Button-3>", self._show_menu)

        self.menu = tk.Menu(root, tearoff=0)
        self.menu.add_command(label="ถัดไป", command=self.next_fact)
        self.menu.add_command(label="เปิดไฟล์โน้ต", command=lambda: os.startfile(FACTS_FILE))
        self.topmost_var = tk.BooleanVar(value=self.state.get("topmost", True))
        self.menu.add_checkbutton(label="ลอยบนสุด", variable=self.topmost_var, command=self._toggle_topmost)
        self.menu.add_separator()
        self.menu.add_command(label="ปิด", command=self._quit)

    def _render(self) -> None:
        if self.current is None:
            question, answer = "ยังไม่มี fact", f"เพิ่มหัวข้อ '## ...' ใน {FACTS_FILE.name}"
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
            t.insert("end", "นึกคำตอบก่อน… (คลิกเพื่อดู)", "hint")
        if self.notice:
            t.insert("end", f"\n{self.notice}", "hint")
        t.configure(state="disabled")  # อ่านอย่างเดียว พิมพ์ทับไม่ได้
        self._fit_height()

    def _insert_with_code(self, s: str, base_tag: str | None) -> None:
        # split ด้วย `...` : ช่องเลขคี่คือส่วนที่อยู่ใน backtick → ใส่ tag "code"
        for i, chunk in enumerate(re.split(r"`([^`]*)`", s)):
            tags = tuple(tag for tag in (base_tag, "code" if i % 2 else None) if tag)
            self.text.insert("end", chunk, tags)

    def _fit_height(self) -> None:
        # ให้ Tk คำนวณการตัดบรรทัดก่อน แล้วนับบรรทัดที่แสดงจริงเพื่อปรับความสูงหน้าต่าง
        self.root.update_idletasks()
        lines = self.text.count("1.0", "end", "displaylines")
        lines = lines[0] if isinstance(lines, tuple) else (lines or 1)
        height = min(40 + lines * 24, 420)
        self.root.geometry(f"{WIDTH}x{height}+{self.root.winfo_x()}+{self.root.winfo_y()}")

    # ---------- การวน fact ----------
    def _reload_if_changed(self) -> None:
        try:
            mtime = FACTS_FILE.stat().st_mtime
        except FileNotFoundError:
            self.facts, self.deck = [], []
            return
        if mtime != self.facts_mtime:  # ไฟล์ถูกแก้ตั้งแต่โหลดรอบก่อน → โหลดใหม่
            self.facts_mtime = mtime
            self.facts = load_facts(FACTS_FILE)
            self.deck = []

    def _schedule(self, seconds: int, callback) -> None:
        if self.timer:
            self.root.after_cancel(self.timer)
        # after = "อีก N ms ให้เรียก callback นี้" ไม่บล็อกหน้าจอเหมือน sleep
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

    # ---------- เมาส์ ----------
    def _on_press(self, e: tk.Event) -> str:
        self.drag_start = (e.x_root - self.root.winfo_x(), e.y_root - self.root.winfo_y())
        self.dragged = False
        return "break"  # "break" = ไม่ให้ Text ทำพฤติกรรมปกติต่อ (เช่นเลือกข้อความ)

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

    # ---------- เรียกหน้าต่างกลับมา ----------
    def _poll_events(self) -> None:
        # หยิบข้อความที่ thread อื่นฝากไว้ใน queue มาทำใน thread หลัก (ที่เดียวที่แตะ Tk ได้)
        try:
            while True:
                event = self.events.get_nowait()  # ไม่มีของ → โยน queue.Empty ออกจากลูป
                if event == "show":
                    self.bring_to_front()
                elif event == "hotkey-failed":
                    self.notice = f"คีย์ลัด {HOTKEY_LABEL} ใช้ไม่ได้ (โปรแกรมอื่นจองไว้)"
                    self._render()
        except queue.Empty:
            pass
        self.root.after(150, self._poll_events)  # นัดตัวเองอีกครั้งใน 150 ms วนไปเรื่อยๆ

    def bring_to_front(self) -> None:
        self.root.deiconify()
        self.root.lift()
        # หน้าต่างแบบ overrideredirect ไม่อยู่ใน Alt+Tab ใช้ lift อย่างเดียวบางทีไม่ขึ้นหน้าสุด
        # วิธีที่ชัวร์: เปิด topmost ชั่วคราวให้ทะลุขึ้นบนสุด แล้วคืนค่าที่ผู้ใช้ตั้งไว้
        # ตอนปิด topmost Windows จะวางหน้าต่างไว้บนสุดของกลุ่มที่ไม่ใช่ topmost จึงยังอยู่หน้าสุด
        self.root.attributes("-topmost", True)
        # lambda = ฟังก์ชันไม่มีชื่อ ห่อคำสั่งไว้ให้ after เรียกทีหลัง (ถ้าใส่ตรงๆ จะรันทันที)
        self.root.after(100, lambda: self.root.attributes("-topmost", self.topmost_var.get()))

    def _toggle_topmost(self) -> None:
        self.root.attributes("-topmost", self.topmost_var.get())
        self._save_state()

    # ---------- state ----------
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
        self.root.mainloop()  # วนรอ event (คลิก, timer) ไปเรื่อยๆ จนกว่าจะปิด


if __name__ == "__main__":
    already_running, server = claim_single_instance()
    if already_running:
        sys.exit()  # ตัวเดิมรับเรื่องแล้วและจะโผล่ขึ้นมาเอง ตัวนี้ไม่ต้องเปิด
    FactWidget(server).run()
