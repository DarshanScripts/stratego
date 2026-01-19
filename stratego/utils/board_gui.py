from __future__ import annotations

from typing import List, Optional

from stratego.utils.parsing import extract_board_block_lines


class BoardGUI:
    def __init__(self, title: str = "Stratego") -> None:
        try:
            import tkinter as tk
        except Exception as exc:
            raise RuntimeError("tkinter is required for GUI mode") from exc

        self._tk = tk
        self._root = tk.Tk()
        self._root.title(title)
        self._root.configure(bg="#1a1a1a")
        self._root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._closed = False
        self._size: Optional[int] = None
        self._cells: List[List[tk.Label]] = []
        self._row_labels: List[tk.Label] = []
        self._col_labels: List[tk.Label] = []

    def _on_close(self) -> None:
        self._closed = True
        try:
            self._root.destroy()
        except Exception:
            pass

    def _build_grid(self, size: int) -> None:
        if self._cells:
            for row in self._cells:
                for label in row:
                    label.destroy()
        for label in self._row_labels + self._col_labels:
            label.destroy()

        self._cells = []
        self._row_labels = []
        self._col_labels = []
        self._size = size

        font = ("Consolas", 12, "bold")
        header_font = ("Consolas", 11, "bold")
        bg = "#1a1a1a"
        fg = "#e6e6e6"

        for c in range(size):
            label = self._tk.Label(
                self._root, text=str(c), font=header_font, bg=bg, fg=fg, padx=6, pady=3
            )
            label.grid(row=0, column=c + 1, sticky="nsew")
            self._col_labels.append(label)

        for r in range(size):
            row_label = self._tk.Label(
                self._root, text=chr(ord("A") + r), font=header_font, bg=bg, fg=fg, padx=6, pady=3
            )
            row_label.grid(row=r + 1, column=0, sticky="nsew")
            self._row_labels.append(row_label)

            row_cells: List[self._tk.Label] = []
            for c in range(size):
                label = self._tk.Label(
                    self._root,
                    text=".",
                    font=font,
                    width=3,
                    height=1,
                    bg="#2b2b2b",
                    fg="#ffffff",
                    relief="ridge",
                    borderwidth=1,
                )
                label.grid(row=r + 1, column=c + 1, sticky="nsew")
                row_cells.append(label)
            self._cells.append(row_cells)

        for i in range(size + 1):
            self._root.grid_rowconfigure(i, weight=1)
            self._root.grid_columnconfigure(i, weight=1)

    def update_from_observation(self, observation: str, size_hint: int = 10) -> None:
        if self._closed:
            return

        block = extract_board_block_lines(observation, size_hint)
        if not block:
            return

        rows = block[1:]
        size = len(rows)
        if self._size != size:
            self._build_grid(size)

        for r, line in enumerate(rows):
            parts = line.split()
            if len(parts) < 2:
                continue
            tokens = parts[1:]
            if len(tokens) < size:
                tokens.extend(["?"] * (size - len(tokens)))
            for c, token in enumerate(tokens[:size]):
                label = self._cells[r][c]
                label.configure(text=token, bg=_cell_bg(token), fg=_cell_fg(token))

        try:
            self._root.update_idletasks()
            self._root.update()
        except Exception:
            self._closed = True


def _cell_bg(token: str) -> str:
    if token == "~":
        return "#243b55"
    if token == ".":
        return "#2b2b2b"
    if token == "?":
        return "#3a2b2b"
    if token in ("FL", "BM"):
        return "#5c1e1e"
    if token in ("SC", "MN", "SP"):
        return "#1f3b2d"
    return "#3b3b1f"


def _cell_fg(token: str) -> str:
    if token in ("FL", "BM"):
        return "#ffe6e6"
    if token == "?":
        return "#f0c6c6"
    return "#f2f2f2"
