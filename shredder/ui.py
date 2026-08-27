"""Shredder GUI — files/folder, passes, shred."""

from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog

from . import __version__
from .core import shred_path

BG = "#111111"
FG = "#ffffff"
MUTED = "#999999"
LINE = "#333333"
ERR = "#f87171"
OK = "#86efac"


class ShredderApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"Shredder {__version__}")
        self.geometry("420x320")
        self.minsize(380, 300)
        self.configure(bg=BG)
        self.resizable(False, False)
        self._paths: list[Path] = []
        self._busy = False

        pad = tk.Frame(self, bg=BG)
        pad.pack(fill="both", expand=True, padx=24, pady=20)

        tk.Label(pad, text="Shredder", bg=BG, fg=FG, font=("Segoe UI Semibold", 16)).pack(anchor="w")
        tk.Label(pad, text="Удаление с перезаписью. Отмены нет.", bg=BG, fg=MUTED, font=("Segoe UI", 9)).pack(
            anchor="w", pady=(4, 16)
        )

        row1 = tk.Frame(pad, bg=BG)
        row1.pack(fill="x")
        self._mk_btn(row1, "Выбрать файлы", self._add_files).pack(side="left")
        self._mk_btn(row1, "Выбрать папку", self._add_folder).pack(side="left", padx=(8, 0))

        self._choice = tk.Label(pad, text="ничего не выбрано", bg=BG, fg=MUTED, font=("Segoe UI", 9), anchor="w")
        self._choice.pack(fill="x", pady=(12, 16))

        row2 = tk.Frame(pad, bg=BG)
        row2.pack(fill="x")
        tk.Label(row2, text="Сколько раз перезаписать:", bg=BG, fg=FG, font=("Segoe UI", 10)).pack(side="left")
        self._passes = tk.Spinbox(
            row2,
            from_=1,
            to=10,
            width=4,
            font=("Segoe UI", 11),
            bg="#1a1a1a",
            fg=FG,
            buttonbackground=LINE,
            relief="flat",
            insertbackground=FG,
        )
        self._passes.delete(0, "end")
        self._passes.insert(0, "3")
        self._passes.pack(side="left", padx=(10, 0))

        self._status = tk.Label(pad, text="", bg=BG, fg=MUTED, font=("Segoe UI", 9), anchor="w")
        self._status.pack(fill="x", pady=(16, 8))

        self._mk_btn(pad, "Уничтожить", self._shred, primary=True, big=True).pack(fill="x", pady=(8, 0))

    def _mk_btn(self, parent, text, cmd, primary=False, big=False) -> tk.Label:
        lbl = tk.Label(
            parent,
            text=text,
            bg=FG if primary else "#1a1a1a",
            fg=BG if primary else FG,
            font=("Segoe UI Semibold", 12) if big else ("Segoe UI", 10),
            padx=28 if big else 14,
            pady=14 if big else 7,
            cursor="hand2",
        )
        lbl.bind("<Button-1>", lambda _e: cmd())
        return lbl

    def _set_choice(self) -> None:
        n = len(self._paths)
        if n == 0:
            self._choice.configure(text="ничего не выбрано", fg=MUTED)
        elif n == 1:
            self._choice.configure(text=str(self._paths[0]), fg=FG)
        else:
            self._choice.configure(text=f"выбрано объектов: {n}", fg=FG)

    def _add_files(self) -> None:
        if self._busy:
            return
        files = filedialog.askopenfilenames(title="Файлы")
        if not files:
            return
        self._paths = [Path(f) for f in files]
        self._set_choice()
        self._status.configure(text="", fg=MUTED)

    def _add_folder(self) -> None:
        if self._busy:
            return
        d = filedialog.askdirectory(title="Папка")
        if not d:
            return
        self._paths = [Path(d)]
        self._set_choice()
        self._status.configure(text="", fg=MUTED)

    def _passes_value(self) -> int:
        try:
            return max(1, min(10, int(self._passes.get())))
        except ValueError:
            return 3

    def _shred(self) -> None:
        if self._busy or not self._paths:
            self._status.configure(text="сначала выберите файлы или папку", fg=ERR)
            return

        passes = self._passes_value()
        overlay = tk.Frame(self, bg="#000000")
        overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        box = tk.Frame(overlay, bg="#1a1a1a", padx=20, pady=16)
        box.place(relx=0.5, rely=0.5, anchor="center")
        tk.Label(box, text="Уничтожить безвозвратно?", bg="#1a1a1a", fg=FG, font=("Segoe UI Semibold", 11)).pack()
        tk.Label(
            box,
            text=f"{len(self._paths)} объект(ов), {passes} раз(а)",
            bg="#1a1a1a",
            fg=MUTED,
            font=("Segoe UI", 9),
        ).pack(pady=(6, 14))
        row = tk.Frame(box, bg="#1a1a1a")
        row.pack()

        def cancel():
            overlay.destroy()

        def ok():
            overlay.destroy()
            self._run(passes)

        self._mk_btn(row, "Отмена", cancel).pack(side="left", padx=4)
        self._mk_btn(row, "Да", ok, primary=True).pack(side="left", padx=4)

    def _run(self, passes: int) -> None:
        self._busy = True
        paths = list(self._paths)
        self._status.configure(text="идёт уничтожение…", fg=MUTED)

        def work():
            errors = 0
            done = 0
            for p in paths:
                try:
                    shred_path(p, passes=passes)
                    done += 1
                except Exception:
                    errors += 1

            def finish():
                self._busy = False
                self._paths.clear()
                self._set_choice()
                if errors:
                    self._status.configure(text=f"готово: {done}, ошибок: {errors}", fg=ERR)
                else:
                    self._status.configure(text=f"уничтожено: {done}", fg=OK)

            self.after(0, finish)

        threading.Thread(target=work, daemon=True).start()


def run() -> None:
    app = ShredderApp()
    app.mainloop()
