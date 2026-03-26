#!/usr/bin/env python3
"""
Pametan Prostor – GUI za Blog & Carousel Generator
Pokretanje: python tools/gui.py
"""
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import subprocess
import threading
import os
import sys
import glob
import webbrowser
from PIL import Image, ImageTk

# Brand colors
BG        = "#09090b"
BG_CARD   = "#18181b"
BG_INPUT  = "#27272a"
GOLD      = "#c9973a"
GOLD_LITE = "#e4b84d"
WHITE     = "#ffffff"
GRAY      = "#a1a1aa"
GRAY_DIM  = "#52525b"
BORDER    = "#3f3f46"
GREEN     = "#22c55e"
RED       = "#f87171"

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR  = os.path.join(TOOLS_DIR, "..")


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Pametan Prostor – Generator")
        self.configure(bg=BG)
        self.geometry("960x780")
        self.minsize(720, 600)
        self.resizable(True, True)

        self._photo_refs = []  # Prevent GC of Tk images
        self._build_ui()
        self._check_api_key()

    # ──────────────────────────────────────────
    # UI BUILD
    # ──────────────────────────────────────────

    def _build_ui(self):
        # ── Header ──
        header = tk.Frame(self, bg=BG, padx=32, pady=20)
        header.pack(fill=tk.X)

        logo = tk.Frame(header, bg=BG)
        logo.pack(side=tk.LEFT)
        tk.Label(logo, text="Pametan", bg=BG, fg=WHITE,
                 font=("Georgia", 22, "bold")).pack(side=tk.LEFT)
        tk.Label(logo, text=" Prostor", bg=BG, fg=GOLD,
                 font=("Georgia", 22, "bold")).pack(side=tk.LEFT)
        tk.Label(logo, text="  ·  Generator", bg=BG, fg=GRAY_DIM,
                 font=("Georgia", 15)).pack(side=tk.LEFT)

        tk.Frame(self, bg=BORDER, height=1).pack(fill=tk.X)

        # ── Main scroll area ──
        outer = tk.Frame(self, bg=BG)
        outer.pack(fill=tk.BOTH, expand=True)

        self._canvas = tk.Canvas(outer, bg=BG, highlightthickness=0, bd=0)
        scrollbar = ttk.Scrollbar(outer, orient=tk.VERTICAL, command=self._canvas.yview)
        self._scroll_frame = tk.Frame(self._canvas, bg=BG)

        self._scroll_frame.bind("<Configure>",
            lambda e: self._canvas.configure(scrollregion=self._canvas.bbox("all")))

        self._canvas.create_window((0, 0), window=self._scroll_frame, anchor=tk.NW)
        self._canvas.configure(yscrollcommand=scrollbar.set)

        self._canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self._canvas.bind_all("<Button-4>", self._on_mousewheel)
        self._canvas.bind_all("<Button-5>", self._on_mousewheel)

        self._build_form(self._scroll_frame)

    def _build_form(self, parent):
        pad = dict(padx=32)

        # ── API Key notice (shown if missing) ──
        self.api_frame = tk.Frame(parent, bg="#1c1007", **pad)
        self.api_frame.pack(fill=tk.X, pady=(0, 0))
        tk.Label(
            self.api_frame,
            text="⚠  ANTHROPIC_API_KEY nije podešen. Postavi ga u terminalu: export ANTHROPIC_API_KEY='sk-ant-...'  pa restartuj GUI.",
            bg="#1c1007", fg="#fbbf24", font=("Inter", 10),
            pady=8, wraplength=860, justify=tk.LEFT
        ).pack(anchor=tk.W, padx=8)

        # ── Topic ──
        tk.Frame(parent, bg=BG, height=24).pack()
        tk.Label(parent, text="Tema blog posta", bg=BG, fg=GRAY,
                 font=("Inter", 11), **pad).pack(anchor=tk.W, pady=(0, 6))

        entry_frame = tk.Frame(parent, bg=BORDER, **pad)
        entry_frame.pack(fill=tk.X, pady=(0, 4))

        self.topic_var = tk.StringVar()
        self.topic_entry = tk.Entry(
            entry_frame, textvariable=self.topic_var,
            bg=BG_INPUT, fg=WHITE, insertbackground=GOLD,
            relief=tk.FLAT, font=("Inter", 13), bd=0
        )
        self.topic_entry.pack(fill=tk.X, ipady=11, padx=1, pady=1)
        self.topic_entry.bind("<Return>", lambda e: self._run())

        tk.Label(parent, text="Primeri: 'kako odabrati radnu površinu za kuhinju'  ·  'saveti za malu kuhinju po meri'",
                 bg=BG, fg=GRAY_DIM, font=("Inter", 9), **pad).pack(anchor=tk.W, pady=(0, 20))

        # ── Options ──
        opts = tk.Frame(parent, bg=BG, **pad)
        opts.pack(anchor=tk.W, pady=(0, 22))

        self.blog_var     = tk.BooleanVar(value=True)
        self.carousel_var = tk.BooleanVar(value=True)

        ck = dict(bg=BG, fg=WHITE, activebackground=BG, activeforeground=GOLD,
                  selectcolor=BG_INPUT, font=("Inter", 12), cursor="hand2")

        tk.Checkbutton(opts, text="Blog post", variable=self.blog_var, **ck
                       ).pack(side=tk.LEFT, padx=(0, 28))
        tk.Checkbutton(opts, text="Carousel slike (Instagram)", variable=self.carousel_var, **ck
                       ).pack(side=tk.LEFT)

        # ── Generate button ──
        btn_row = tk.Frame(parent, bg=BG, **pad)
        btn_row.pack(anchor=tk.W, pady=(0, 24))

        self.btn = tk.Button(
            btn_row, text="  Generiši  ",
            bg=GOLD, fg=BG_CARD, font=("Inter", 13, "bold"),
            relief=tk.FLAT, padx=32, pady=11,
            cursor="hand2", command=self._run,
            activebackground=GOLD_LITE, activeforeground=BG
        )
        self.btn.pack(side=tk.LEFT)

        self.status_lbl = tk.Label(btn_row, text="", bg=BG, fg=GRAY, font=("Inter", 11))
        self.status_lbl.pack(side=tk.LEFT, padx=(18, 0))

        tk.Frame(parent, bg=BORDER, height=1, **pad).pack(fill=tk.X, pady=(0, 16))

        # ── Terminal output ──
        tk.Label(parent, text="Izlaz", bg=BG, fg=GRAY_DIM,
                 font=("Inter", 10), **pad).pack(anchor=tk.W, pady=(0, 4))

        term_frame = tk.Frame(parent, bg=BORDER, **pad)
        term_frame.pack(fill=tk.X, pady=(0, 20))

        self.terminal = scrolledtext.ScrolledText(
            term_frame, bg="#0a0a0c", fg=GREEN,
            font=("DejaVu Sans Mono", 10), relief=tk.FLAT,
            height=14, insertbackground=WHITE, bd=0,
            state=tk.DISABLED
        )
        self.terminal.pack(fill=tk.X, padx=1, pady=1)
        # Tag for errors
        self.terminal.tag_config("err", foreground=RED)

        # ── Results area ──
        self.results_frame = tk.Frame(parent, bg=BG)
        self.results_frame.pack(fill=tk.X, **pad, pady=(0, 32))

    # ──────────────────────────────────────────
    # API KEY CHECK
    # ──────────────────────────────────────────

    def _check_api_key(self):
        if os.environ.get("ANTHROPIC_API_KEY"):
            self.api_frame.pack_forget()

    # ──────────────────────────────────────────
    # GENERATE
    # ──────────────────────────────────────────

    def _run(self):
        topic = self.topic_var.get().strip()
        if not topic:
            messagebox.showwarning("Pametan Prostor", "Unesite temu blog posta.")
            return
        if not self.blog_var.get() and not self.carousel_var.get():
            messagebox.showwarning("Pametan Prostor", "Izaberite barem jednu opciju (Blog post ili Carousel).")
            return

        # Clear
        for w in self.results_frame.winfo_children():
            w.destroy()
        self._photo_refs.clear()
        self._clear_terminal()

        self.btn.config(state=tk.DISABLED, text="  Generišem...  ", bg=GRAY_DIM, fg=GRAY)
        self.status_lbl.config(text="Claude piše sadržaj...", fg=GRAY)

        args = [sys.executable, "-u",
                os.path.join(TOOLS_DIR, "generate.py"),
                "--topic", topic]
        if self.blog_var.get() and not self.carousel_var.get():
            args.append("--blog-only")
        elif self.carousel_var.get() and not self.blog_var.get():
            args.append("--carousel-only")

        thread = threading.Thread(target=self._run_process, args=(args,), daemon=True)
        thread.start()

    def _run_process(self, args):
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        try:
            proc = subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=ROOT_DIR,
                env=env,
                bufsize=1
            )
            for line in proc.stdout:
                self.after(0, self._append_terminal, line)
            proc.wait()
            success = proc.returncode == 0
        except Exception as e:
            self.after(0, self._append_terminal, f"\nGREŠKA: {e}\n", is_err=True)
            success = False

        self.after(0, self._on_done, success)

    def _on_done(self, success: bool):
        self.btn.config(state=tk.NORMAL, text="  Generiši  ", bg=GOLD, fg=BG_CARD)

        if not success:
            self.status_lbl.config(text="Greška. Pogledaj izlaz.", fg=RED)
            return

        self.status_lbl.config(text="Gotovo!", fg=GREEN)

        # Find most recent carousel folder
        carousel_base = os.path.join(TOOLS_DIR, "output", "carousels")
        carousel_dir  = None
        if os.path.exists(carousel_base):
            dirs = [os.path.join(carousel_base, d)
                    for d in os.listdir(carousel_base)
                    if os.path.isdir(os.path.join(carousel_base, d))]
            if dirs:
                carousel_dir = max(dirs, key=os.path.getmtime)

        # Find most recent blog post
        blog_dir  = os.path.join(ROOT_DIR, "blog")
        blog_file = None
        if os.path.exists(blog_dir):
            files = [os.path.join(blog_dir, f)
                     for f in os.listdir(blog_dir)
                     if f.endswith(".html") and f != ".gitkeep"]
            if files:
                blog_file = max(files, key=os.path.getmtime)

        self._show_results(carousel_dir, blog_file)

    # ──────────────────────────────────────────
    # RESULTS
    # ──────────────────────────────────────────

    def _show_results(self, carousel_dir, blog_file):
        frame = self.results_frame

        tk.Frame(frame, bg=BORDER, height=1).pack(fill=tk.X, pady=(0, 18))

        # Blog post link
        if blog_file and self.blog_var.get():
            row = tk.Frame(frame, bg=BG)
            row.pack(fill=tk.X, pady=(0, 14))

            tk.Label(row, text="Blog post:", bg=BG, fg=GRAY,
                     font=("Inter", 11)).pack(side=tk.LEFT, padx=(0, 10))

            rel = os.path.relpath(blog_file, ROOT_DIR)
            link = tk.Label(row, text=rel, bg=BG, fg=GOLD,
                            font=("Inter", 11, "underline"), cursor="hand2")
            link.pack(side=tk.LEFT)
            link.bind("<Button-1>", lambda e, p=blog_file: webbrowser.open(f"file://{p}"))

            tk.Label(row, text=" (otvori u browser-u)", bg=BG, fg=GRAY_DIM,
                     font=("Inter", 10)).pack(side=tk.LEFT)

        # Carousel images
        if carousel_dir and self.carousel_var.get():
            pngs = sorted(glob.glob(os.path.join(carousel_dir, "slide-*.png")))
            if pngs:
                hdr = tk.Frame(frame, bg=BG)
                hdr.pack(fill=tk.X, pady=(0, 10))

                tk.Label(hdr, text=f"Carousel slike  ({len(pngs)} slajdova)",
                         bg=BG, fg=GRAY, font=("Inter", 11)).pack(side=tk.LEFT)

                open_btn = tk.Button(
                    hdr, text="Otvori folder",
                    bg=BG_INPUT, fg=GRAY, font=("Inter", 10),
                    relief=tk.FLAT, padx=12, pady=4, cursor="hand2",
                    command=lambda: subprocess.Popen(["xdg-open", carousel_dir]),
                    activebackground=BORDER, activeforeground=WHITE
                )
                open_btn.pack(side=tk.RIGHT)

                # Thumbnail row
                thumb_outer = tk.Frame(frame, bg=BG)
                thumb_outer.pack(fill=tk.X, pady=(0, 8))

                canvas = tk.Canvas(thumb_outer, bg=BG, height=178, highlightthickness=0)
                hscroll = ttk.Scrollbar(thumb_outer, orient=tk.HORIZONTAL, command=canvas.xview)
                canvas.configure(xscrollcommand=hscroll.set)
                hscroll.pack(side=tk.BOTTOM, fill=tk.X)
                canvas.pack(side=tk.TOP, fill=tk.X)

                thumb_frame = tk.Frame(canvas, bg=BG)
                canvas.create_window((0, 0), window=thumb_frame, anchor=tk.NW)
                thumb_frame.bind("<Configure>",
                    lambda e, c=canvas: c.configure(scrollregion=c.bbox("all")))

                for i, png in enumerate(pngs, 1):
                    self._add_thumbnail(thumb_frame, png, i)

                # Caption
                cap_path = os.path.join(carousel_dir, "caption.txt")
                if os.path.exists(cap_path):
                    cap_row = tk.Frame(frame, bg=BG)
                    cap_row.pack(fill=tk.X, pady=(4, 0))
                    tk.Label(cap_row, text="Instagram caption:", bg=BG, fg=GRAY,
                             font=("Inter", 11)).pack(side=tk.LEFT, padx=(0, 10))
                    cap_link = tk.Label(cap_row,
                                        text=os.path.relpath(cap_path, ROOT_DIR),
                                        bg=BG, fg=GOLD,
                                        font=("Inter", 11, "underline"), cursor="hand2")
                    cap_link.pack(side=tk.LEFT)
                    cap_link.bind("<Button-1>", lambda e, p=cap_path: webbrowser.open(f"file://{p}"))

        # Scroll to bottom so results are visible
        self.after(100, lambda: self._canvas.yview_moveto(1.0))

    def _add_thumbnail(self, parent, png_path: str, num: int):
        try:
            img = Image.open(png_path)
            img.thumbnail((152, 152), Image.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            self._photo_refs.append(photo)

            cell = tk.Frame(parent, bg=BG_CARD, padx=3, pady=3)
            cell.pack(side=tk.LEFT, padx=(0, 8))

            # Gold border on hover
            lbl = tk.Label(cell, image=photo, bg=BG_CARD, cursor="hand2",
                           highlightthickness=2, highlightbackground=BG_CARD)
            lbl.pack()
            lbl.bind("<Enter>",  lambda e, l=lbl: l.config(highlightbackground=GOLD))
            lbl.bind("<Leave>",  lambda e, l=lbl: l.config(highlightbackground=BG_CARD))
            lbl.bind("<Button-1>", lambda e, p=png_path: webbrowser.open(f"file://{p}"))

            tk.Label(cell, text=f"Slajd {num}", bg=BG_CARD, fg=GRAY_DIM,
                     font=("Inter", 9)).pack(pady=(2, 0))
        except Exception as e:
            tk.Label(parent, text=f"[{num}]", bg=BG_CARD, fg=GRAY_DIM).pack(side=tk.LEFT)

    # ──────────────────────────────────────────
    # TERMINAL HELPERS
    # ──────────────────────────────────────────

    def _clear_terminal(self):
        self.terminal.config(state=tk.NORMAL)
        self.terminal.delete("1.0", tk.END)
        self.terminal.config(state=tk.DISABLED)

    def _append_terminal(self, text: str, is_err: bool = False):
        self.terminal.config(state=tk.NORMAL)
        if is_err:
            self.terminal.insert(tk.END, text, "err")
        else:
            self.terminal.insert(tk.END, text)
        self.terminal.see(tk.END)
        self.terminal.config(state=tk.DISABLED)

    def _on_mousewheel(self, event):
        if event.num == 4:
            self._canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self._canvas.yview_scroll(1, "units")
        else:
            self._canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")


if __name__ == "__main__":
    app = App()
    app.mainloop()
