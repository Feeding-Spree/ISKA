import tkinter as tk
from tkinter import font as tkfont
import sqlite3
import threading
import time
import os
import subprocess
import pygame
import speech_recognition as sr
import socket
import pyaudio
import json
from PIL import Image, ImageTk
from vosk import Model, KaldiRecognizer
from backend import IskaBackend

# ============================================================
# MICROPHONE CONFIGURATION
# Set MIC_NAME to any part of your microphone's device name.
# Run the app once to see all detected devices in the terminal,
# then paste any unique substring of your mic's name here.
#
# Examples:
#   MIC_NAME = "8- USB"           -> Microphone (8- USB Audio Device)
#   MIC_NAME = "USB Audio Device" -> Microphone (USB Audio Device)
#   MIC_NAME = "Realtek"          -> Microphone (Realtek Audio)
#   MIC_NAME = None               -> Auto-detect (falls back to strategies)
# ============================================================
MIC_NAME = "8- USB"

# ============================================================
# EXIT PIN CONFIGURATION
# This PIN is required to exit the kiosk. Change it to
# something only your staff/admin team knows.
# The exit is triggered by tapping the PUP seal 5 times.
# ============================================================
EXIT_PIN = "1234"

# ─────────────────────────────────────────────────────────────────────────────
#  Palette
# ─────────────────────────────────────────────────────────────────────────────
BG_MAIN    = "#F5E6B8"
BG_CREAM   = "#FFF8E8"
MAROON     = "#7A0000"
MAROON_LT  = "#9A0000"
GOLD       = "#C9A84C"
GOLD_LT    = "#E8D5A3"
GOLD_DIM   = "#B09060"
BUBBLE_AI  = "#F0C040"
TEXT_DARK  = "#3A1A00"
TEXT_MID   = "#7A5A30"
TEXT_LIGHT = "#B09060"
GREEN_ON   = "#4CAF50"
RED_ERR    = "#CC4444"

# ─────────────────────────────────────────────────────────────────────────────
#  Asset configuration
# ─────────────────────────────────────────────────────────────────────────────
ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

FACE_FRAMES = {
    "warmup":    ["warmup 01.png"],
    "idle":      ["idle 01.png"],
    "listening": ["listen 01.png", "listen 02.png"],
    "capturing": ["capturing 01.png"],
    "thinking":  ["thinking 01.png", "thinking 02.png",
                  "thinking 03.png", "thinking 04.png"],
    "speaking":  ["speaking 01.png", "speaking 02.png", "speaking 03.png"],
    "error":     ["error 01.png"],
}

FRAME_DELAY = {
    "warmup":    700,
    "idle":      1400,
    "listening": 380,
    "capturing": 500,
    "thinking":  280,
    "speaking":  200,
    "error":     900,
}

FACE_W = 370
FACE_H = 222


# ─────────────────────────────────────────────────────────────────────────────
#  BmoFaceWidget
# ─────────────────────────────────────────────────────────────────────────────
class BmoFaceWidget(tk.Label):
    """
    Animated BMO face that cycles PNG frames per ISKA state.
    Falls back to a coloured placeholder if a PNG is missing.
    """
    def __init__(self, parent, **kw):
        super().__init__(parent, bg=BG_MAIN, bd=0, relief=tk.FLAT, **kw)
        self._state    = "idle"
        self._frames   = {}
        self._cur_idx  = 0
        self._after_id = None
        self._load_all_frames()
        self._animate()

    def _load_all_frames(self):
        for state, filenames in FACE_FRAMES.items():
            loaded = []
            for fname in filenames:
                path = os.path.join(ASSETS_DIR, fname)
                try:
                    img = Image.open(path).convert("RGBA")
                    img = img.resize((FACE_W, FACE_H), Image.LANCZOS)
                    loaded.append(ImageTk.PhotoImage(img))
                except Exception as e:
                    print(f"[BMO] Could not load '{path}': {e}")
                    loaded.append(self._placeholder(state))
            self._frames[state] = loaded

    def _placeholder(self, state):
        colors = {
            "idle": "#B8EDE0", "listening": "#FFF3A0",
            "capturing": "#A0E0FF", "thinking": "#C8EAFF",
            "speaking": "#B8EDE0", "error": "#FFD0D0", "warmup": "#E0FFE0",
        }
        img = Image.new("RGBA", (FACE_W, FACE_H), colors.get(state, "#B8EDE0"))
        return ImageTk.PhotoImage(img)

    def set_state(self, state: str):
        if state not in FACE_FRAMES:
            state = "idle"
        if state == self._state:
            return
        self._state   = state
        self._cur_idx = 0
        if self._after_id:
            try:
                self.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None
        self._animate()

    def _animate(self):
        frames = self._frames.get(self._state, [])
        if frames:
            frame = frames[self._cur_idx % len(frames)]
            self.config(image=frame)
            self._ref  = frame
            self._cur_idx = (self._cur_idx + 1) % len(frames)
        delay = FRAME_DELAY.get(self._state, 400)
        self._after_id = self.after(delay, self._animate)

    def destroy(self):
        if self._after_id:
            try:
                self.after_cancel(self._after_id)
            except Exception:
                pass
        super().destroy()


# ─────────────────────────────────────────────────────────────────────────────
#  ChatMessage
# ─────────────────────────────────────────────────────────────────────────────
class ChatMessage:
    @staticmethod
    def add(container, text: str, sender: str = "bot",
            timestamp: str = "") -> tk.Label:
        row = tk.Frame(container, bg=BG_CREAM)
        row.pack(fill=tk.X, padx=10, pady=5)

        if sender == "user":
            wrap = tk.Frame(row, bg=BG_CREAM)
            wrap.pack(side=tk.RIGHT)
            bubble = tk.Label(
                wrap, text=text,
                font=("Georgia", 13), wraplength=560,
                bg=MAROON, fg="white",
                padx=16, pady=10, justify=tk.LEFT,
                relief=tk.FLAT, bd=0)
            bubble.pack(anchor=tk.E)
            if timestamp:
                tk.Label(wrap, text=timestamp,
                         font=("Helvetica", 9),
                         bg=BG_CREAM, fg=TEXT_LIGHT).pack(anchor=tk.E, padx=4)
        else:
            wrap = tk.Frame(row, bg=BG_CREAM)
            wrap.pack(side=tk.LEFT)
            avatar = tk.Label(
                wrap, text="IS",
                font=("Helvetica", 9, "bold"),
                bg=GOLD, fg=MAROON,
                width=3, height=1, relief=tk.FLAT)
            avatar.pack(side=tk.LEFT, anchor=tk.N, padx=(0, 8), pady=4)
            bwrap = tk.Frame(wrap, bg=BG_CREAM)
            bwrap.pack(side=tk.LEFT)
            bubble = tk.Label(
                bwrap, text=text,
                font=("Georgia", 13), wraplength=560,
                bg=BUBBLE_AI, fg=TEXT_DARK,
                padx=16, pady=10, justify=tk.LEFT,
                relief=tk.FLAT, bd=0)
            bubble.pack(anchor=tk.W)
            if timestamp:
                tk.Label(bwrap, text=timestamp,
                         font=("Helvetica", 9),
                         bg=BG_CREAM, fg=TEXT_LIGHT).pack(anchor=tk.W, padx=4)

        container.update_idletasks()
        return bubble


# ─────────────────────────────────────────────────────────────────────────────
#  ISKA - Main Application
#  Merges IskaFrontend (UI + BMO face) with ISKA_Core (STT + backend)
# ─────────────────────────────────────────────────────────────────────────────
class ISKA(object):

    SCREEN_W = 1920
    SCREEN_H = 1080

    def __init__(self, root):
        self.root     = root
        self.language = "en"
        self._stream_bubble = None

        # --- State Variables ---
        self.is_idle            = True
        self.is_online          = True
        self.idle_timer         = None
        self.db_path            = 'iska_database.db'
        self.current_session_id = None
        self.announcement_index = 0

        # Hidden exit — tap the PUP seal 5 times to trigger PIN dialog
        self._seal_taps  = 0
        self._seal_timer = None

        # Event-based mic handoff between Vosk and STT
        self._mic_released = threading.Event()
        self._mic_released.set()  # Start as set so Vosk doesn't block on first run

        # Query lock - prevents pile-up on repeated taps
        self._query_lock = threading.Lock()

        # --- BACKEND ---
        self.backend = IskaBackend()

        # --- AUDIO HARDWARE ---
        self.audio_engine = pyaudio.PyAudio()
        self.mic_index    = self._get_mic_index()

        # --- VOSK WAKE WORD ---
        print("\n[Vosk] Loading wake word model...")
        try:
            self.vosk_model = Model("model")
        except Exception as e:
            print(f"[Vosk] CRITICAL: 'model' folder not found. ({e})")
            self.vosk_model = None
        self.is_waiting_for_wake_word = True

        # --- AUDIO MIXER ---
        pygame.mixer.init()

        # --- PERSISTENT MICROPHONE ---
        self._recognizer = sr.Recognizer()
        self._mic_source = sr.Microphone(device_index=self.mic_index)
        self._mic_source.__enter__()
        threading.Thread(target=self._warmup_mic, daemon=True).start()

        # --- BUILD UI ---
        self._build_window()
        self._build_ui()

        # Boot face animation
        self.face.set_state("warmup")
        self.root.after(2200, lambda: self.face.set_state("idle"))

        # --- BACKGROUND THREADS ---
        threading.Thread(target=self._network_monitor, daemon=True).start()
        if self.vosk_model:
            threading.Thread(target=self._wake_word_loop, daemon=True).start()

    # =========================================================================
    #  Window and UI construction
    # =========================================================================
    def _build_window(self):
        self.root.title("ISKA - Intelligent Standing Kiosk")
        self.root.configure(bg=BG_MAIN)
        self.root.geometry(f"{self.SCREEN_W}x{self.SCREEN_H}+0+0")
        self.root.attributes('-fullscreen', True)
        self.root.resizable(False, False)

    def _build_ui(self):
        self._build_topbar()
        self._build_welcome_banner()
        self._build_body()
        self._build_footer()

    def _build_topbar(self):
        bar = tk.Frame(self.root, bg=MAROON, height=70)
        bar.pack(fill=tk.X, side=tk.TOP)
        bar.pack_propagate(False)

        # PUP seal — logo image (hidden exit trigger: tap 5x)
        pup_img = Image.open(os.path.join(ASSETS_DIR, "pup_logo.png")).convert("RGBA")
        pup_img = pup_img.resize((50, 50), Image.LANCZOS)
        self._pup_logo = ImageTk.PhotoImage(pup_img)  # keep reference

        seal_lbl = tk.Label(bar, image=self._pup_logo, bg=MAROON,
                            cursor="hand2")
        seal_lbl.pack(side=tk.LEFT, padx=(20, 14), pady=11)
        seal_lbl.bind("<Button-1>", self._on_seal_tap)

        title_blk = tk.Frame(bar, bg=MAROON)
        title_blk.pack(side=tk.LEFT, pady=12)
        tk.Label(title_blk,
                 text="Polytechnic University of the Philippines",
                 font=("Georgia", 15, "bold"),
                 bg=MAROON, fg="white").pack(anchor=tk.W)
        tk.Label(title_blk, text="Biñan Campus",
                 font=("Helvetica", 10),
                 bg=MAROON, fg=GOLD).pack(anchor=tk.W)

        # Right side — status badge + network
        right_bar = tk.Frame(bar, bg=MAROON)
        right_bar.pack(side=tk.RIGHT, padx=20)

        badge = tk.Frame(right_bar, bg=GOLD_LT, padx=16, pady=7)
        badge.pack(side=tk.RIGHT, pady=18)
        self._dot = tk.Label(badge, text="●",
                             font=("Helvetica", 11),
                             bg=GOLD_LT, fg=GOLD)
        self._dot.pack(side=tk.LEFT)
        self.status_label = tk.Label(badge, text="ISKA ONLINE",
                                     font=("Helvetica", 10, "bold"),
                                     bg=GOLD_LT, fg=MAROON)
        self.status_label.pack(side=tk.LEFT, padx=(6, 0))

        # Network label kept as hidden element for programmatic updates
        # but not packed — only the ISKA ONLINE badge and state pill show status
        self._network_label = tk.Label(right_bar, text="● Online",
                                       font=("Helvetica", 10),
                                       bg=MAROON, fg=GREEN_ON)
        # Intentionally not packed — hidden from UI

    def _build_welcome_banner(self):
        banner = tk.Frame(self.root, bg=BG_CREAM,
                          highlightbackground=GOLD, highlightthickness=1)
        banner.pack(fill=tk.X, padx=24, pady=(12, 0))

        # Left accent bar
        tk.Frame(banner, bg=MAROON, width=5).pack(side=tk.LEFT, fill=tk.Y)

        tk.Label(banner, text="🎓",
                 font=("Helvetica", 20),
                 bg=BG_CREAM).pack(side=tk.LEFT, padx=(16, 10), pady=12)

        txt_blk = tk.Frame(banner, bg=BG_CREAM)
        txt_blk.pack(side=tk.LEFT, pady=10)
        tk.Label(txt_blk,
                 text="Welcome to ISKA",
                 font=("Georgia", 13, "bold"),
                 bg=BG_CREAM, fg=MAROON).pack(anchor=tk.W)
        tk.Label(txt_blk,
                 text=("Your Intelligent Student Knowledge Assistant for PUP Biñan Campus. "
                       "Ask about enrollments, offices, library hours, and more!"),
                 font=("Georgia", 11), bg=BG_CREAM, fg=TEXT_MID,
                 wraplength=1500, justify=tk.LEFT).pack(anchor=tk.W)

    def _build_body(self):
        body = tk.Frame(self.root, bg=BG_MAIN)
        body.pack(fill=tk.BOTH, expand=True, padx=24, pady=14)
        self._build_left(body)
        self._build_right(body)

    def _build_left(self, parent):
        left = tk.Frame(parent, bg=BG_MAIN, width=400)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 16))
        left.pack_propagate(False)

        # BMO face with gold border
        face_border = tk.Frame(left, bg=GOLD, padx=3, pady=3)
        face_border.pack(pady=(0, 10))
        face_inner = tk.Frame(face_border, bg=BG_MAIN)
        face_inner.pack()
        self.face = BmoFaceWidget(face_inner)
        self.face.pack()

        # State pill — rounded appearance via padx/pady
        self.state_pill = tk.Label(
            left, text="● IDLE",
            font=("Helvetica", 11, "bold"),
            bg=MAROON, fg=GOLD_LT,
            padx=20, pady=6)
        self.state_pill.pack(fill=tk.X, pady=(0, 10))

        # TAP TO SPEAK — gold background, prominent
        self.listen_btn = tk.Button(
            left,
            text="🎤   TAP TO SPEAK",
            font=("Georgia", 14, "bold"),
            bg=GOLD, fg=MAROON,
            activebackground=GOLD_DIM, activeforeground=MAROON,
            relief=tk.FLAT, bd=0,
            padx=20, pady=16,
            cursor="hand2",
            command=self.start_interaction)
        self.listen_btn.pack(fill=tk.X, pady=(0, 14))

        # Language toggle
        lang_row = tk.Frame(left, bg=BG_MAIN)
        lang_row.pack(fill=tk.X, pady=(0, 14))
        tk.Label(lang_row, text="Language:",
                 font=("Helvetica", 10),
                 bg=BG_MAIN, fg=TEXT_MID).pack(side=tk.LEFT, padx=(4, 8))
        self.btn_en = tk.Button(
            lang_row, text="EN",
            font=("Helvetica", 10, "bold"),
            bg=MAROON, fg=GOLD_LT, relief=tk.FLAT,
            padx=16, pady=5, cursor="hand2",
            command=lambda: self._set_lang("en"))
        self.btn_en.pack(side=tk.LEFT, padx=2)
        self.btn_tl = tk.Button(
            lang_row, text="FIL",
            font=("Helvetica", 10, "bold"),
            bg=GOLD_LT, fg=TEXT_MID, relief=tk.FLAT,
            padx=16, pady=5, cursor="hand2",
            command=lambda: self._set_lang("tl"))
        self.btn_tl.pack(side=tk.LEFT, padx=2)

        # Quick info cards
        cards_label = tk.Label(left, text="QUICK INFO",
                               font=("Helvetica", 9, "bold"),
                               bg=BG_MAIN, fg=TEXT_LIGHT)
        cards_label.pack(anchor=tk.W, padx=4, pady=(4, 6))

        cards_grid = tk.Frame(left, bg=BG_MAIN)
        cards_grid.pack(fill=tk.X)

        quick_info = [
            ("📚", "Library",       "8AM – 6PM",        "What are the library hours?"),
            ("🏛",  "Registrar",     "Ground Floor",     "Where is the Registrar's office?"),
            ("📝", "Enrollment",    "Check portal",     "How do I enroll at PUP Biñan?"),
            ("🌐", "Student Portal","my.pup.edu.ph",    "How do I access the student portal?"),
        ]

        for idx, (icon, title, subtitle, query) in enumerate(quick_info):
            row = idx // 2
            col = idx % 2

            card = tk.Frame(cards_grid, bg=BG_CREAM,
                            highlightbackground=GOLD_LT, highlightthickness=1,
                            cursor="hand2")
            card.grid(row=row, column=col, padx=4, pady=4, sticky="nsew")
            cards_grid.columnconfigure(col, weight=1)

            tk.Label(card, text=icon,
                     font=("Helvetica", 16),
                     bg=BG_CREAM).pack(anchor=tk.W, padx=10, pady=(8, 0))
            tk.Label(card, text=title,
                     font=("Helvetica", 10, "bold"),
                     bg=BG_CREAM, fg=MAROON).pack(anchor=tk.W, padx=10)
            tk.Label(card, text=subtitle,
                     font=("Helvetica", 9),
                     bg=BG_CREAM, fg=TEXT_MID).pack(anchor=tk.W, padx=10, pady=(0, 8))

            # Make the whole card clickable
            for widget in card.winfo_children():
                widget.bind("<Button-1>", lambda e, q=query: self._dispatch(q))
            card.bind("<Button-1>", lambda e, q=query: self._dispatch(q))

        # Exit is hidden — triggered by tapping the PUP seal 5 times

    def _build_right(self, parent):
        right = tk.Frame(parent, bg=BG_CREAM,
                         highlightbackground=GOLD, highlightthickness=1)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Chat header
        hdr = tk.Frame(right, bg=MAROON, height=60)
        hdr.pack(fill=tk.X)
        hdr.pack_propagate(False)

        # Circular avatar
        avatar_frame = tk.Frame(hdr, bg=GOLD_LT, width=38, height=38)
        avatar_frame.pack(side=tk.LEFT, padx=(16, 10), pady=11)
        avatar_frame.pack_propagate(False)
        tk.Label(avatar_frame, text="IS",
                 font=("Helvetica", 9, "bold"),
                 bg=GOLD_LT, fg=MAROON).place(
                     relx=0.5, rely=0.5, anchor=tk.CENTER)

        hdr_txt = tk.Frame(hdr, bg=MAROON)
        hdr_txt.pack(side=tk.LEFT, pady=10)
        tk.Label(hdr_txt, text="ISKA",
                 font=("Georgia", 13, "bold"),
                 bg=MAROON, fg="white").pack(anchor=tk.W)
        tk.Label(hdr_txt, text="Intelligent Student Knowledge Assistant",
                 font=("Helvetica", 9),
                 bg=MAROON, fg=GOLD_LT).pack(anchor=tk.W)

        # Scrollable chat area
        chat_wrap = tk.Frame(right, bg=BG_CREAM)
        chat_wrap.pack(fill=tk.BOTH, expand=True)
        self._chat_canvas = tk.Canvas(chat_wrap, bg=BG_CREAM,
                                      highlightthickness=0)
        vsb = tk.Scrollbar(chat_wrap, orient=tk.VERTICAL,
                           command=self._chat_canvas.yview)
        self._chat_canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self._chat_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._chat_frame = tk.Frame(self._chat_canvas, bg=BG_CREAM)
        self._chat_win = self._chat_canvas.create_window(
            (0, 0), window=self._chat_frame, anchor=tk.NW)
        self._chat_frame.bind("<Configure>",
            lambda e: self._chat_canvas.configure(
                scrollregion=self._chat_canvas.bbox("all")))
        self._chat_canvas.bind("<Configure>",
            lambda e: self._chat_canvas.itemconfig(
                self._chat_win, width=e.width))

        # Greeting bubble
        ChatMessage.add(self._chat_frame,
                        "Magandang araw! I'm ISKA, your campus guide.",
                        sender="bot")
        ChatMessage.add(self._chat_frame,
                        "Ask me anything about PUP Biñan — "
                        "type below or tap the mic to speak.",
                        sender="bot")
        self._scroll_bottom()

        # Quick-topic chips — pill style
        chips_bar = tk.Frame(right, bg=BG_CREAM,
                             highlightbackground=GOLD_LT, highlightthickness=1)
        chips_bar.pack(fill=tk.X, padx=0)
        for label, query in [
            ("Library hours?",      "What are the library hours?"),
            ("Tuition fees?",       "What are the tuition fees?"),
            ("Enrollment info?",    "How do I enroll at PUP Biñan?"),
            ("Registrar office?",   "Where is the Registrar's office?"),
        ]:
            tk.Button(chips_bar, text=label,
                      font=("Helvetica", 11),
                      bg=BG_CREAM, fg=MAROON,
                      activebackground=GOLD_LT, activeforeground=MAROON,
                      relief=tk.SOLID, bd=1,
                      padx=16, pady=6, cursor="hand2",
                      command=lambda q=query: self._dispatch(q)
                      ).pack(side=tk.LEFT, padx=6, pady=8)

        # Input bar with search icon
        inp_bar = tk.Frame(right, bg=BG_CREAM,
                           highlightbackground=GOLD, highlightthickness=1)
        inp_bar.pack(fill=tk.X)

        tk.Label(inp_bar, text="🔍",
                 font=("Helvetica", 14),
                 bg="white").pack(side=tk.LEFT, padx=(12, 0), pady=10)

        self._search_var = tk.StringVar()
        self._entry = tk.Entry(inp_bar,
                               textvariable=self._search_var,
                               font=("Georgia", 13),
                               bg="white", fg=TEXT_DARK,
                               insertbackground=MAROON,
                               relief=tk.FLAT, bd=0)
        self._entry.pack(side=tk.LEFT, fill=tk.X, expand=True,
                         padx=(6, 8), pady=14)
        self._entry.insert(0, "Type your question here...")
        self._entry.config(fg=TEXT_LIGHT)
        self._entry.bind("<FocusIn>",  self._ph_clear)
        self._entry.bind("<FocusOut>", self._ph_restore)
        self._entry.bind("<Return>",   lambda e: self._send_typed())

        tk.Button(inp_bar, text="➤  Send",
                  font=("Helvetica", 12, "bold"),
                  bg=MAROON, fg=GOLD_LT,
                  activebackground=MAROON_LT, activeforeground=GOLD_LT,
                  relief=tk.FLAT, bd=0,
                  padx=22, pady=10, cursor="hand2",
                  command=self._send_typed
                  ).pack(side=tk.RIGHT, padx=(0, 12), pady=10)

    def _build_footer(self):
        footer = tk.Frame(self.root, bg=MAROON, height=36)
        footer.pack(fill=tk.X, side=tk.BOTTOM)
        footer.pack_propagate(False)
        tk.Label(footer,
                 text=("ISKA — Intelligent Standing Kiosk for Announcements & "
                       "Inquiries  ·  PUP Biñan  ·  2025"),
                 font=("Helvetica", 9),
                 bg=MAROON, fg=GOLD_DIM).pack(side=tk.LEFT, expand=True)
        # Help button
        tk.Label(footer, text="?",
                 font=("Helvetica", 10, "bold"),
                 bg=GOLD_DIM, fg=MAROON,
                 width=2, cursor="hand2").pack(
                     side=tk.RIGHT, padx=12, pady=6)

    # =========================================================================
    #  UI Helpers
    # =========================================================================
    def _scroll_bottom(self):
        self.root.after(80, lambda: self._chat_canvas.yview_moveto(1.0))

    def _ph_clear(self, _):
        if self._entry.get() == "Type your question here...":
            self._entry.delete(0, tk.END)
            self._entry.config(fg=TEXT_DARK)

    def _ph_restore(self, _):
        if not self._entry.get().strip():
            self._entry.insert(0, "Type your question here...")
            self._entry.config(fg=TEXT_LIGHT)

    def _set_lang(self, lang):
        self.language = lang
        self.btn_en.config(bg=MAROON if lang == "en" else GOLD_LT,
                           fg=GOLD_LT if lang == "en" else TEXT_MID)
        self.btn_tl.config(bg=MAROON if lang == "tl" else GOLD_LT,
                           fg=GOLD_LT if lang == "tl" else TEXT_MID)

    def _set_state(self, state: str, label: str, dot_color: str = GOLD):
        self.root.after(0, self.face.set_state, state)
        self.root.after(0, self.state_pill.config,
                        {"text": f"● {label.upper()}"})
        self.root.after(0, self.status_label.config, {"text": label})
        self.root.after(0, self._dot.config, {"fg": dot_color})

    def _reset(self):
        self._set_state("idle", "ISKA ONLINE", GOLD)
        self.root.after(0, lambda: self.listen_btn.config(state=tk.NORMAL))

    def _send_typed(self):
        text = self._search_var.get().strip()
        if not text or text == "Type your question here...":
            return
        self._entry.delete(0, tk.END)
        self._dispatch(text)

    def _dispatch(self, query: str):
        """Common entry point for typed queries and quick-topic chips."""
        if self.listen_btn["state"] == tk.DISABLED:
            return
        self.listen_btn.config(state=tk.DISABLED)
        now = time.strftime("%I:%M %p")
        ChatMessage.add(self._chat_frame, query, sender="user", timestamp=now)
        self._scroll_bottom()
        self._set_state("thinking", "Thinking...", GOLD)
        self.wake_up()
        threading.Thread(target=self._run_query, args=(query,),
                         daemon=True).start()

    # =========================================================================
    #  Hidden exit — PUP seal tap sequence + PIN dialog
    # =========================================================================
    def _on_seal_tap(self, event=None):
        """
        Counts taps on the PUP seal. After 5 taps within 3 seconds,
        shows the staff PIN dialog. Resets if the timer expires.
        """
        self._seal_taps += 1

        # Cancel any existing reset timer
        if self._seal_timer:
            self.root.after_cancel(self._seal_timer)

        if self._seal_taps >= 5:
            self._seal_taps  = 0
            self._seal_timer = None
            self._show_exit_pin_dialog()
        else:
            # Reset tap count after 3 seconds of inactivity
            self._seal_timer = self.root.after(
                3000, self._reset_seal_taps)

    def _reset_seal_taps(self):
        self._seal_taps  = 0
        self._seal_timer = None

    def _show_exit_pin_dialog(self):
        """
        Modal PIN dialog. Only staff who know EXIT_PIN can close the kiosk.
        Three wrong attempts locks the dialog out for 30 seconds.
        """
        dialog = tk.Toplevel(self.root)
        dialog.title("")
        dialog.resizable(False, False)
        dialog.grab_set()  # Modal — blocks interaction with main window

        # Center on screen
        dw, dh = 340, 260
        sx = self.root.winfo_screenwidth()
        sy = self.root.winfo_screenheight()
        dialog.geometry(f"{dw}x{dh}+{(sx-dw)//2}+{(sy-dh)//2}")
        dialog.configure(bg=BG_CREAM)
        dialog.overrideredirect(True)  # No title bar

        # Header
        hdr = tk.Frame(dialog, bg=MAROON, height=50)
        hdr.pack(fill=tk.X)
        hdr.pack_propagate(False)
        tk.Label(hdr, text="Staff Access Required",
                 font=("Georgia", 13, "bold"),
                 bg=MAROON, fg="white").pack(expand=True)

        # Body
        body = tk.Frame(dialog, bg=BG_CREAM)
        body.pack(fill=tk.BOTH, expand=True, padx=30, pady=20)

        tk.Label(body, text="Enter PIN to exit kiosk:",
                 font=("Helvetica", 11),
                 bg=BG_CREAM, fg=TEXT_DARK).pack(anchor=tk.W, pady=(0, 8))

        pin_var = tk.StringVar()
        pin_entry = tk.Entry(body,
                             textvariable=pin_var,
                             font=("Helvetica", 18, "bold"),
                             show="●", width=12,
                             bg="white", fg=MAROON,
                             insertbackground=MAROON,
                             relief=tk.SOLID, bd=1,
                             justify=tk.CENTER)
        pin_entry.pack(fill=tk.X, pady=(0, 10))
        pin_entry.focus_set()

        msg_label = tk.Label(body, text="",
                             font=("Helvetica", 10),
                             bg=BG_CREAM, fg=RED_ERR)
        msg_label.pack()

        attempts = [0]  # Mutable container so inner functions can modify it

        def _attempt_exit(event=None):
            if attempts[0] >= 3:
                return

            entered = pin_var.get().strip()
            if entered == EXIT_PIN:
                dialog.destroy()
                self.root.destroy()
            else:
                attempts[0] += 1
                remaining = 3 - attempts[0]
                if remaining > 0:
                    msg_label.config(
                        text=f"Incorrect PIN. {remaining} attempt(s) remaining.")
                    pin_var.set("")
                    pin_entry.focus_set()
                else:
                    # Lock out for 30 seconds
                    msg_label.config(
                        text="Too many attempts. Locked for 30 seconds.")
                    pin_entry.config(state=tk.DISABLED)
                    confirm_btn.config(state=tk.DISABLED)
                    dialog.after(30000, dialog.destroy)

        # Buttons
        btn_row = tk.Frame(body, bg=BG_CREAM)
        btn_row.pack(fill=tk.X, pady=(12, 0))

        tk.Button(btn_row, text="Cancel",
                  font=("Helvetica", 10),
                  bg=GOLD_LT, fg=TEXT_DARK,
                  relief=tk.FLAT, padx=16, pady=8,
                  cursor="hand2",
                  command=dialog.destroy).pack(side=tk.LEFT)

        confirm_btn = tk.Button(btn_row, text="Confirm Exit",
                                font=("Helvetica", 10, "bold"),
                                bg=RED_ERR, fg="white",
                                relief=tk.FLAT, padx=16, pady=8,
                                cursor="hand2",
                                command=_attempt_exit)
        confirm_btn.pack(side=tk.RIGHT)

        # Allow Enter key to confirm
        pin_entry.bind("<Return>", _attempt_exit)

    # =========================================================================
    #  Microphone management
    # =========================================================================
    def _get_mic_index(self):
        print("\n--- Audio Hardware Scan ---")
        input_devices = []
        for i in range(self.audio_engine.get_device_count()):
            dev = self.audio_engine.get_device_info_by_index(i)
            if dev['maxInputChannels'] > 0:
                input_devices.append((i, dev))
                print(f"  Input Device {i}: {dev['name']} "
                      f"(channels: {int(dev['maxInputChannels'])}, "
                      f"rate: {int(dev['defaultSampleRate'])}Hz)")

        if not input_devices:
            print("CRITICAL: No input devices found.")
            return None

        if MIC_NAME:
            for i, dev in input_devices:
                if MIC_NAME.lower() in dev['name'].lower():
                    print(f"LOCKED [Config]: Device {i} - {dev['name']}")
                    print(f"  --> Matched MIC_NAME = '{MIC_NAME}'")
                    return i
            print(f"WARNING: MIC_NAME = '{MIC_NAME}' did not match any device.")

        for i, dev in input_devices:
            if "usb" in dev['name'].lower() and "mic" in dev['name'].lower():
                print(f"LOCKED [USB Mic]: Device {i} - {dev['name']}")
                return i

        for i, dev in input_devices:
            if "realtek" in dev['name'].lower() and "mic" in dev['name'].lower():
                print(f"LOCKED [Realtek Mic]: Device {i} - {dev['name']}")
                return i

        for i, dev in input_devices:
            if "microphone" in dev['name'].lower() or "mic" in dev['name'].lower():
                print(f"LOCKED [Generic Mic]: Device {i} - {dev['name']}")
                return i

        fallback_index = input_devices[0][0]
        print(f"WARNING: Falling back to Device {fallback_index}")
        return fallback_index

    def _warmup_mic(self):
        try:
            print("[MIC] Warming up microphone...")
            self._recognizer.adjust_for_ambient_noise(
                self._mic_source, duration=0.5)
            print(f"[MIC] Ready. Energy threshold: "
                  f"{self._recognizer.energy_threshold:.1f}")
        except Exception as e:
            print(f"[MIC ERROR] Warmup failed: {e}")

    def _recalibrate_mic(self):
        threading.Thread(
            target=lambda: self._recognizer.adjust_for_ambient_noise(
                self._mic_source, duration=0.5),
            daemon=True).start()
        print("[MIC] Recalibrating ambient noise threshold...")

    # =========================================================================
    #  Vosk wake word engine
    # =========================================================================
    def _wake_word_loop(self):
        FORMAT   = pyaudio.paInt16
        CHANNELS = 1
        RATE     = 16000
        CHUNK    = 4000

        # KaldiRecognizer created ONCE outside the loop
        rec = KaldiRecognizer(
            self.vosk_model, RATE,
            '["hello", "is", "car", "that", "[unk]"]')
        print("[Vosk] KaldiRecognizer initialized - wake word engine ready.")

        while True:
            if not self.is_waiting_for_wake_word:
                self._mic_released.wait()
                self._mic_released.clear()
                continue

            mic_stream    = None
            trigger_found = False

            try:
                mic_stream = self.audio_engine.open(
                    format=FORMAT, channels=CHANNELS, rate=RATE,
                    input=True, frames_per_buffer=CHUNK,
                    input_device_index=self.mic_index)

                while self.is_waiting_for_wake_word:
                    pcm = mic_stream.read(CHUNK, exception_on_overflow=False)
                    if not self.is_waiting_for_wake_word:
                        break
                    if rec.AcceptWaveform(pcm):
                        text = json.loads(rec.Result()).get("text", "")
                        if text in ["hello is car", "hello is that"]:
                            self.is_waiting_for_wake_word = False
                            trigger_found = True
                            break

            except Exception as e:
                print(f"[Wake Word Error] {e}")
                time.sleep(2)
            finally:
                if mic_stream:
                    try:
                        mic_stream.stop_stream()
                        mic_stream.close()
                        print("[Vosk] Mic stream closed - handing off to STT.")
                    except:
                        pass

            if trigger_found:
                self.root.after(0, lambda: self._add_bot_message(
                    "Hello! I'm listening. How can I help?"))
                self.start_interaction()

    # =========================================================================
    #  STT - tap to speak
    # =========================================================================
    def start_interaction(self):
        """Triggered by TAP TO SPEAK button or Vosk wake word."""
        self.listen_btn.config(state=tk.DISABLED)
        self._set_state("listening", "Listening...", GREEN_ON)
        threading.Thread(target=self._process_audio, daemon=True).start()

    def _process_audio(self):
        try:
            time.sleep(0.5)

            if not self.is_online:
                msg = ("I'm currently offline and cannot process voice input. "
                       "Please type your question instead.")
                self.root.after(0, lambda: self._add_bot_message(msg))
                threading.Thread(target=self._speak, args=(msg,),
                                 daemon=True).start()
                return

            # Release Vosk so it frees the mic device
            self._mic_released.clear()
            self.is_waiting_for_wake_word = False
            time.sleep(0.15)

            self._set_state("capturing", "Capturing...", GOLD)
            audio = self._recognizer.listen(
                self._mic_source, timeout=10, phrase_time_limit=12)

            self._set_state("thinking", "Thinking...", GOLD)

            spoken_text = None
            for attempt in range(2):
                try:
                    spoken_text = self._recognizer.recognize_google(
                        audio).lower()
                    break
                except sr.RequestError as e:
                    if attempt == 0:
                        print(f"[STT] Retrying... ({e})")
                        time.sleep(1.5)
                    else:
                        raise

            if spoken_text:
                print(f"[STT] Heard: '{spoken_text}'")
                now = time.strftime("%I:%M %p")
                self.root.after(0, lambda t=spoken_text:
                    ChatMessage.add(self._chat_frame, t,
                                    sender="user", timestamp=now))
                self.root.after(0, self._scroll_bottom)
                time.sleep(0.3)
                self._route_input(spoken_text)

        except sr.WaitTimeoutError:
            msg = "I didn't hear anything. Please tap and speak clearly."
            print("[STT] Timeout.")
            self._set_state("error", "Error", RED_ERR)
            self.root.after(0, lambda: self._add_bot_message(msg))
            def _speak_then_reset_timeout():
                self._speak(msg)
                self._reset()
            threading.Thread(target=_speak_then_reset_timeout, daemon=True).start()

        except sr.UnknownValueError:
            msg = "I heard you, but couldn't make out the words. Please try again."
            print("[STT] UnknownValueError.")
            self._set_state("error", "Error", RED_ERR)
            self.root.after(0, lambda: self._add_bot_message(msg))
            def _speak_then_reset_unknown():
                self._speak(msg)
                self._reset()
            threading.Thread(target=_speak_then_reset_unknown, daemon=True).start()

        except sr.RequestError as e:
            msg = "I couldn't connect to the speech service. Please check the internet."
            print(f"[STT] RequestError: {e}")
            self._set_state("error", "Error", RED_ERR)
            self.root.after(0, lambda: self._add_bot_message(msg))
            def _speak_then_reset_request():
                self._speak(msg)
                self._reset()
            threading.Thread(target=_speak_then_reset_request, daemon=True).start()

        except Exception as e:
            print(f"[STT] Unexpected error: {e}")
            self._set_state("error", "Error", RED_ERR)
            self.root.after(2500, self._reset)

        finally:
            self.is_waiting_for_wake_word = True
            self._mic_released.set()

    # =========================================================================
    #  Input routing and backend
    # =========================================================================
    def _route_input(self, text_input: str):
        self.wake_up()
        sleep_cues = [
            "thank you", "thanks", "goodbye", "bye", "go to sleep",
            "that's all", "salamat", "paalam"
        ]
        if any(cue in text_input.lower() for cue in sleep_cues):
            threading.Thread(target=self._sleep_sequence,
                             args=(text_input,), daemon=True).start()
            return
        threading.Thread(target=self._run_query,
                         args=(text_input,), daemon=True).start()

    def _run_query(self, text_input: str):
        """Runs backend query, streams to chat bubble, speaks result, logs."""
        if not self._query_lock.acquire(blocking=False):
            print("[ISKA] Query already in progress - ignoring duplicate.")
            self._reset()
            return

        try:
            now = time.strftime("%I:%M %p")
            self.root.after(0, self._start_stream_bubble, now)

            def on_stream(full_text: str):
                display = (full_text
                           .replace("ISKA AI:\n\n", "")
                           .replace("ISKA:\n\n", "")
                           .strip())
                self.root.after(0, self._update_stream_bubble, display)
                self.root.after(0, self._scroll_bottom)

            full_response = self.backend.process_query(
                user_input=text_input,
                lang=self.language,
                ui_callback=on_stream)

            self._speak(full_response)
            self._log_interaction(text_input, full_response)

        finally:
            self._query_lock.release()
            self._reset()

    # =========================================================================
    #  Chat bubble helpers
    # =========================================================================
    def _add_bot_message(self, text: str):
        now = time.strftime("%I:%M %p")
        ChatMessage.add(self._chat_frame, text, sender="bot", timestamp=now)
        self._scroll_bottom()

    def _start_stream_bubble(self, ts: str):
        self._stream_bubble = ChatMessage.add(
            self._chat_frame, "...", sender="bot", timestamp=ts)
        self._scroll_bottom()

    def _update_stream_bubble(self, text: str):
        if self._stream_bubble:
            self._stream_bubble.config(text=text or "...")
        self._scroll_bottom()

    def _clear_chat(self):
        """
        Wipes all chat bubbles and restores the greeting.
        Called after the farewell audio finishes in _sleep_sequence.
        The full conversation is already saved to query_logs per interaction,
        grouped by session_id — visible in the admin dashboard.
        """
        # Destroy all child widgets in the chat frame
        for widget in self._chat_frame.winfo_children():
            widget.destroy()

        self._stream_bubble = None

        # Restore the greeting bubbles for the next student
        ChatMessage.add(self._chat_frame,
                        "Magandang araw! I'm ISKA, your campus guide.",
                        sender="bot")
        ChatMessage.add(self._chat_frame,
                        "Ask me anything about PUP Biñan — "
                        "type below or tap the mic to speak.",
                        sender="bot")
        self._scroll_bottom()
        print(f"[UI] Chat cleared. Session {self.current_session_id} "
              f"archived in admin dashboard.")

    # =========================================================================
    #  Sleep sequence
    # =========================================================================
    def _sleep_sequence(self, text_input: str):
        msg = ("You are very welcome! Have a great day ahead."
               if self.language == 'en'
               else "Walang anuman! Magandang araw sa iyo.")
        self.root.after(0, lambda: self._add_bot_message(msg))
        self._log_interaction(text_input, msg)
        self._speak(msg)

        # Brief pause so the student sees the farewell bubble before wipe
        time.sleep(1.2)
        self.root.after(0, self._clear_chat)
        self.root.after(0, self._go_to_sleep)

    # =========================================================================
    #  TTS
    # =========================================================================
    def _speak(self, text: str):
        self._set_state("speaking", "Speaking...", GOLD)
        voice = ("fil-PH-AngeloNeural" if self.language == "tl"
                 else "en-US-ChristopherNeural")
        safe_text = (text
                     .replace("ISKA AI:", "")
                     .replace("ISKA:", "")
                     .replace("ISKA", "Isska")
                     .replace("PUP", "P. U. P.")
                     .replace('"', '\\"')
                     .replace('\n', ' '))
        filename = f"temp_res_{int(time.time())}.mp3"
        try:
            subprocess.run(
                ['python', '-m', 'edge_tts',
                 '--voice', voice, '--text', safe_text,
                 '--write-media', filename],
                check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            print(f"[TTS] edge-tts failed: {e.stderr.decode()}")
            self._set_state("error", "Error", RED_ERR)
            self.root.after(2500, self._reset)
            return
        try:
            if os.path.exists(filename):
                pygame.mixer.music.load(filename)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    time.sleep(0.1)
            else:
                print("[TTS] Audio file not created.")
        except Exception as e:
            print(f"[Pygame] {e}")
        finally:
            pygame.mixer.music.stop()
            pygame.mixer.music.unload()
            if os.path.exists(filename):
                os.remove(filename)

    # =========================================================================
    #  Logging
    # =========================================================================
    def _log_interaction(self, query: str, response: str):
        try:
            clean = (response
                     .replace("ISKA AI:\n\n", "")
                     .replace("ISKA:\n\n", ""))
            local_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            conn = sqlite3.connect(self.db_path)
            conn.execute(
                "INSERT INTO query_logs "
                "(student_query, ai_response, session_id, timestamp) "
                "VALUES (?, ?, ?, ?)",
                (query, clean, self.current_session_id, local_time))
            conn.commit()
            conn.close()
            print(f"[LOGGER] Saved at {local_time}")
        except Exception as e:
            print(f"[LOGGER] Failed: {e}")

    # =========================================================================
    #  Network monitor
    # =========================================================================
    def _network_monitor(self):
        while True:
            try:
                socket.create_connection(("8.8.8.8", 53), timeout=2)
                newly_online = not self.is_online
                self.is_online = True
                if newly_online:
                    # Reflect online status on the ISKA ONLINE badge
                    self.root.after(0, lambda: self.status_label.config(
                        text="ISKA ONLINE", fg=MAROON))
                    self.root.after(0, lambda: self._dot.config(fg=GOLD))
            except:
                newly_offline = self.is_online
                self.is_online = False
                if newly_offline:
                    # Reflect offline status on the ISKA ONLINE badge
                    self.root.after(0, lambda: self.status_label.config(
                        text="ISKA OFFLINE", fg=RED_ERR))
                    self.root.after(0, lambda: self._dot.config(fg=RED_ERR))
            time.sleep(5)

    # =========================================================================
    #  Idle and session management
    # =========================================================================
    def wake_up(self):
        if self.is_idle:
            self.current_session_id = f"session_{int(time.time())}"
        self.is_idle = False
        if self.idle_timer:
            self.root.after_cancel(self.idle_timer)
        self.idle_timer = self.root.after(30000, self._go_to_sleep)

    def _go_to_sleep(self):
        self.is_idle            = True
        self.current_session_id = None
        self.announcement_index = 0
        self._recalibrate_mic()
        self._reset()


# ─────────────────────────────────────────────────────────────────────────────
#  Entry point
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    app  = ISKA(root)
    root.mainloop()