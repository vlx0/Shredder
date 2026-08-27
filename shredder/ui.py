"""Shredder GUI — pick files, overwrite, delete."""

from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog

from . import __version__
from .core import shred_path

BG = "#000000"
FG = "#ffffff"
MUTED = "#888888"
LINE = "#2a2a2a"
CARD = "#111111"
ERR = "#f87171"
OK = "#86efac"
TITLEBAR = "#0a0a0a"


class ShredderApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"Shredder {__version__}")
        self.geometry("640x520")
        self.minsize(480, 400)
        self.configure(bg=BG)
        self.overrideredirect(True)
        self._paths: list[Path] = []
        self._busy = False
        self._drag_x = 0
        self._drag_y = 0

        self._build_titlebar()
        self._build_body()
        self.after(20, self._place_on_primary)

    def _build_titlebar(self) -> None:
        bar = tk.Frame(self, bg=TITLEBAR, height=36)
        bar.pack(fill="x", side="top")
        bar.pack_propagate(False)

        title = tk.Label(bar, text="Shredder", bg=TITLEBAR, fg=MUTED, font=("Segoe UI", 10))
        title.pack(side="left", padx=14)

        def hit(lbl, hover_bg, cmd):
            lbl.bind("<Enter>", lambda _e: lbl.configure(bg=hover_bg))
            lbl.bind("<Leave>", lambda _e: lbl.configure(bg=TITLEBAR))
            lbl.bind("<Button-1>", lambda _e: cmd())

        close = tk.Label(bar, text="✕", bg=TITLEBAR, fg=FG, font=("Segoe UI", 11), width=4, cursor="hand2")
        close.pack(side="right", fill="y")
        hit(close, "#e81123", self.destroy)

        mini = tk.Label(bar, text="—", bg=TITLEBAR, fg=FG, font=("Segoe UI", 11), width=4, cursor="hand2")
        mini.pack(side="right", fill="y")
        hit(mini, "#222222", self._minimize)

        for w in (bar, title):
            w.bind("<ButtonPress-1>", self._start_move)
            w.bind("<B1-Motion>", self._on_move)

    def _start_move(self, event) -> None:
        self._drag_x = event.x_root - self.winfo_x()
        self._drag_y = event.y_root - self.winfo_y()

    def _on_move(self, event) -> None:
        self.geometry(f"+{event.x_root - self._drag_x}+{event.y_root - self._drag_y}")

    def _minimize(self) -> None:
        self.overrideredirect(False)
        self.iconify()
        self.bind("<Map>", self._on_restore)

    def _on_restore(self, _event=None) -> None:
        if self.state() == "normal":
            self.overrideredirect(True)
            self.unbind("<Map>")

    def _place_on_primary(self) -> None:
        self.update_idletasks()
        w, h = self.winfo_width() or 640, self.winfo_height() or 520
        try:
            import ctypes
            from ctypes import wintypes

            class RECT(ctypes.Structure):
                _fields_ = [("left", wintypes.LONG), ("top", wintypes.LONG),
                            ("right", wintypes.LONG), ("bottom", wintypes.LONG)]

            class MONITORINFO(ctypes.Structure):
                _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", RECT),
                            ("rcWork", RECT), ("dwFlags", wintypes.DWORD)]

            class POINT(ctypes.Structure):
                _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]

            user32 = ctypes.windll.user32
            mon = user32.MonitorFromPoint(POINT(0, 0), 1)
            mi = MONITORINFO()
            mi.cbSize = ctypes.sizeof(MONITORINFO)
            if user32.GetMonitorInfoW(mon, ctypes.byref(mi)):
                px, py = mi.rcWork.left, mi.rcWork.top
                pw = mi.rcWork.right - mi.rcWork.left
                ph = mi.rcWork.bottom - mi.rcWork.top
                self.geometry(f"{w}x{h}+{px + (pw - w)//2}+{py + (ph - h)//2}")
                return
        except Exception:
            pass
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw - w)//2}+{(sh - h)//2}")

    def _btn(self, parent, text, cmd, primary=False) -> tk.Label:
        lbl = tk.Label(
            parent,
            text=text,
            bg=FG if primary else BG,
            fg=BG if primary else FG,
            font=("Segoe UI", 10),
            padx=14,
            pady=6,
            cursor="hand2",
        )
        lbl.bind("<Button-1>", lambda _e: cmd())
        return lbl

    def _build_body(self) -> None:
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=20, pady=16)

        tk.Label(body, text="Shredder", bg=BG, fg=FG, font=("Segoe UI Semibold", 20)).pack(anchor="w")
        tk.Label(
            body,
            text="Перезапись файла случайными данными, затем удаление.\nИз корзины не восстановить.",
            bg=BG,
            fg=MUTED,
            font=("Segoe UI", 10),
            justify="left",
        ).pack(anchor="w", pady=(6, 14))

        tools = tk.Frame(body, bg=BG)
        tools.pack(fill="x")
        self._btn(tools, "+ файлы", self._add_files, primary=True).pack(side="left", padx=(0, 8))
        self._btn(tools, "+ папка", self._add_folder).pack(side="left", padx=(0, 8))
        self._btn(tools, "очистить список", self._clear_list).pack(side="left")

        passes_row = tk.Frame(body, bg=BG)
        passes_row.pack(fill="x", pady=(14, 6))
        tk.Label(passes_row, text="проходы:", bg=BG, fg=MUTED, font=("Segoe UI", 10)).pack(side="left")
        self._passes = tk.IntVar(value=3)
        for n, tip in ((1, "быстро"), (3, "надёжно"), (7, "максимум")):
            rb = tk.Radiobutton(
                passes_row,
                text=f"{n} ({tip})",
                variable=self._passes,
                value=n,
                bg=BG,
                fg=FG,
                selectcolor=CARD,
                activebackground=BG,
                activeforeground=FG,
                font=("Segoe UI", 9),
            )
            rb.pack(side="left", padx=(10, 0))

        list_wrap = tk.Frame(body, bg=LINE, padx=1, pady=1)
        list_wrap.pack(fill="both", expand=True, pady=(8, 8))
        inner = tk.Frame(list_wrap, bg=CARD)
        inner.pack(fill="both", expand=True)

        self._list = tk.Listbox(
            inner,
            bg=CARD,
            fg=FG,
            selectbackground="#333",
            selectforeground=FG,
            relief="flat",
            highlightthickness=0,
            font=("Consolas", 10),
            activestyle="none",
        )
        scroll = tk.Scrollbar(inner, command=self._list.yview)
        self._list.configure(yscrollcommand=scroll.set)
        self._list.pack(side="left", fill="both", expand=True, padx=4, pady=4)
        scroll.pack(side="right", fill="y")

        self._status = tk.Label(body, text="", bg=BG, fg=MUTED, font=("Segoe UI", 9), anchor="w")
        self._status.pack(fill="x", pady=(0, 8))

        self._progress = tk.Label(body, text="", bg=BG, fg=MUTED, font=("Segoe UI", 9), anchor="w")
        self._progress.pack(fill="x")

        actions = tk.Frame(body, bg=BG)
        actions.pack(fill="x", pady=(12, 0))
        self._btn(actions, "уничтожить", self._confirm_shred, primary=True).pack(side="right")
        self._btn(actions, "убрать из списка", self._remove_selected).pack(side="right", padx=(0, 8))

    def _refresh_list(self) -> None:
        self._list.delete(0, tk.END)
        for p in self._paths:
            self._list.insert(tk.END, str(p))
        n = len(self._paths)
        self._status.configure(text=f"в списке: {n}" if n else "добавьте файлы или папку")

    def _add_files(self) -> None:
        if self._busy:
            return
        files = filedialog.askopenfilenames(title="Файлы для уничтожения")
        for f in files:
            p = Path(f)
            if p not in self._paths:
                self._paths.append(p)
        self._refresh_list()

    def _add_folder(self) -> None:
        if self._busy:
            return
        d = filedialog.askdirectory(title="Папка для уничтожения")
        if not d:
            return
        p = Path(d)
        if p not in self._paths:
            self._paths.append(p)
        self._refresh_list()

    def _clear_list(self) -> None:
        if self._busy:
            return
        self._paths.clear()
        self._refresh_list()
        self._progress.configure(text="")

    def _remove_selected(self) -> None:
        if self._busy:
            return
        sel = list(self._list.curselection())
        for i in reversed(sel):
            if 0 <= i < len(self._paths):
                self._paths.pop(i)
        self._refresh_list()

    def _confirm_shred(self) -> None:
        if self._busy or not self._paths:
            return
        self._show_confirm()

    def _show_confirm(self) -> None:
        overlay = tk.Frame(self, bg="#000000")
        overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        card = tk.Frame(overlay, bg=CARD, padx=24, pady=20)
        card.place(relx=0.5, rely=0.45, anchor="center")

        tk.Label(card, text="Уничтожить безвозвратно?", bg=CARD, fg=FG, font=("Segoe UI Semibold", 12)).pack()
        tk.Label(
            card,
            text=f"{len(self._paths)} объект(ов), {self._passes.get()} проход(ов).\nОтменить будет нельзя.",
            bg=CARD,
            fg=MUTED,
            font=("Segoe UI", 9),
            justify="center",
        ).pack(pady=(8, 16))

        row = tk.Frame(card, bg=CARD)
        row.pack()

        def cancel():
            overlay.destroy()

        def ok():
            overlay.destroy()
            self._start_shred()

        self._btn(row, "отмена", cancel).pack(side="left", padx=6)
        self._btn(row, "уничтожить", ok, primary=True).pack(side="left", padx=6)

    def _start_shred(self) -> None:
        self._busy = True
        paths = list(self._paths)
        passes = self._passes.get()

        def work():
            errors: list[str] = []
            done = 0
            for i, p in enumerate(paths):
                try:

                    def prog(name: str, frac: float, idx: int = i) -> None:
                        self.after(
                            0,
                            lambda n=name, f=frac, ix=idx: self._progress.configure(
                                text=f"[{ix + 1}/{len(paths)}] {n} — {int(f * 100)}%"
                            ),
                        )

                    shred_path(p, passes=passes, on_progress=prog)
                    done += 1
                except Exception as e:
                    errors.append(f"{p}: {e}")

            def finish():
                self._busy = False
                self._paths.clear()
                self._refresh_list()
                if errors:
                    self._progress.configure(text="", fg=MUTED)
                    self._status.configure(
                        text=f"готово: {done}, ошибок: {len(errors)}. {errors[0]}",
                        fg=ERR,
                    )
                else:
                    self._status.configure(text=f"уничтожено: {done}", fg=OK)
                    self._progress.configure(text="готово", fg=OK)

            self.after(0, finish)

        threading.Thread(target=work, daemon=True).start()


def run() -> None:
    app = ShredderApp()
    app.mainloop()
