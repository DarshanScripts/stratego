from __future__ import annotations

import os
import queue
import subprocess
import threading
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import tkinter as tk
from tkinter import ttk

from PIL import Image, ImageTk

from stratego.gui.cli_runner import run_match


def main() -> None:
    app = StrategoGUI()
    app.run()


class StrategoGUI:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("Stratego")
        self.root.configure(bg="#1a1a1a")
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._stop_event = threading.Event()
        self._queue: "queue.Queue[dict]" = queue.Queue()
        self._game_thread: Optional[threading.Thread] = None
        self._aborting = False

        self._models: List[str] = []

        self._lobby_frame = ttk.Frame(self.root, padding=16)
        self._game_frame = ttk.Frame(self.root, padding=8)

        self._build_lobby()
        self._build_game_view()

        self._lobby_frame.grid(row=0, column=0, sticky="nsew")
        self._game_frame.grid(row=0, column=0, sticky="nsew")
        self._game_frame.grid_remove()

        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        self.root.after(100, self._poll_queue)

    def run(self) -> None:
        self.root.mainloop()

    def _on_close(self) -> None:
        self._stop_event.set()
        try:
            self.root.destroy()
        except Exception:
            pass

    def _build_lobby(self) -> None:
        title = ttk.Label(self._lobby_frame, text="Stratego Lobby", font=("Consolas", 18, "bold"))
        title.grid(row=0, column=0, columnspan=3, pady=(0, 12), sticky="w")

        ttk.Label(self._lobby_frame, text="Player 0 Model").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Label(self._lobby_frame, text="Player 1 Model").grid(row=2, column=0, sticky="w", pady=4)

        ttk.Label(self._lobby_frame, text="Ollama Port").grid(row=1, column=2, sticky="w", padx=(16, 0))
        self._port_var = tk.StringVar(value="11434")
        self._port_entry = ttk.Entry(self._lobby_frame, textvariable=self._port_var, width=10)
        self._port_entry.grid(row=1, column=3, sticky="w")
        self._connect_btn = ttk.Button(self._lobby_frame, text="Connect", command=self._connect_ollama)
        self._connect_btn.grid(row=2, column=3, sticky="w", pady=(4, 0))
        self._connect_status = ttk.Label(self._lobby_frame, text="Not connected")
        self._connect_status.grid(row=3, column=2, columnspan=2, sticky="w", padx=(16, 0))

        self._p0_var = tk.StringVar(value="")
        self._p1_var = tk.StringVar(value="")

        self._p0_combo = ttk.Combobox(self._lobby_frame, textvariable=self._p0_var, values=self._models, state="normal", width=36)
        self._p1_combo = ttk.Combobox(self._lobby_frame, textvariable=self._p1_var, values=self._models, state="normal", width=36)
        self._p0_combo.grid(row=1, column=1, sticky="ew", padx=(8, 0))
        self._p1_combo.grid(row=2, column=1, sticky="ew", padx=(8, 0))

        ttk.Label(self._lobby_frame, text="Game Mode").grid(row=4, column=0, sticky="w", pady=8)
        self._mode_var = tk.StringVar(value="Custom")
        self._mode_combo = ttk.Combobox(
            self._lobby_frame,
            textvariable=self._mode_var,
            values=["Original", "Duel", "Custom"],
            state="readonly",
            width=18,
        )
        self._mode_combo.grid(row=4, column=1, sticky="w", padx=(8, 0))
        self._mode_combo.bind("<<ComboboxSelected>>", lambda _e: self._toggle_custom())

        self._size_label = ttk.Label(self._lobby_frame, text="Custom Size (4-9)")
        self._size_var = tk.IntVar(value=6)
        self._size_spin = ttk.Spinbox(self._lobby_frame, from_=4, to=9, textvariable=self._size_var, width=8)
        self._size_label.grid(row=5, column=0, sticky="w", pady=4)
        self._size_spin.grid(row=5, column=1, sticky="w", padx=(8, 0))

        ttk.Label(self._lobby_frame, text="Max Turns (50-1000)").grid(row=6, column=0, sticky="w", pady=4)
        self._max_turns_var = tk.StringVar(value="200")
        self._max_turns_entry = ttk.Entry(self._lobby_frame, textvariable=self._max_turns_var, width=12)
        self._max_turns_entry.grid(row=6, column=1, sticky="w", padx=(8, 0))

        self._start_btn = ttk.Button(self._lobby_frame, text="Start Game", command=self._start_game)
        self._start_btn.grid(row=7, column=0, columnspan=2, pady=(16, 0), sticky="w")

        self._lobby_frame.columnconfigure(1, weight=1)
        self._toggle_custom()

    def _build_game_view(self) -> None:
        self._board_frame = ttk.Frame(self._game_frame)
        self._side_frame = ttk.Frame(self._game_frame)

        self._board_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        self._side_frame.grid(row=0, column=1, sticky="nsew")

        self._board_canvas = tk.Canvas(self._board_frame, highlightthickness=0, bg="#1a1a1a")
        self._board_canvas.grid(row=0, column=0, sticky="nsew")
        self._board_frame.rowconfigure(0, weight=1)
        self._board_frame.columnconfigure(0, weight=1)
        self._board_canvas.bind("<Configure>", self._on_board_resize)

        self._board_items: List[List[Optional[int]]] = []
        self._board_size = 0
        self._board_cell_size = 0
        self._board_origin: Tuple[int, int] = (0, 0)
        self._board_bg_id: Optional[int] = None
        self._board_bg_size = 0
        self._board_image_raw = self._load_board_image()
        self._board_image: Optional[ImageTk.PhotoImage] = None
        self._lake_images_raw = self._load_lake_images()
        self._lake_images: Dict[str, ImageTk.PhotoImage] = {}
        self._lake_items: List[List[Optional[int]]] = []
        self._last_tokens: List[List[str]] = []
        self._model_display = {0: "Player 0", 1: "Player 1"}

        self._status_label = ttk.Label(self._side_frame, text="Waiting...", font=("Consolas", 12, "bold"))
        self._status_label.grid(row=0, column=0, sticky="w", pady=(0, 8))
        self._abort_btn = ttk.Button(self._side_frame, text="Abort Game", command=self._abort_game)
        self._abort_btn.grid(row=1, column=0, sticky="w", pady=(0, 8))

        self._turn_label = ttk.Label(self._side_frame, text="Turn: 0")
        self._turn_label.grid(row=2, column=0, sticky="w")

        ttk.Label(self._side_frame, text="Eliminated Pieces", font=("Consolas", 11, "bold")).grid(row=3, column=0, pady=(12, 4), sticky="w")

        self._p0_elim_label = ttk.Label(self._side_frame, text="Player 0:")
        self._p1_elim_label = ttk.Label(self._side_frame, text="Player 1:")
        self._p0_elim_label.grid(row=4, column=0, sticky="w")
        self._p1_elim_label.grid(row=6, column=0, sticky="w")

        self._p0_elim_box = tk.Listbox(self._side_frame, height=8, width=28)
        self._p1_elim_box = tk.Listbox(self._side_frame, height=8, width=28)
        self._p0_elim_box.grid(row=5, column=0, sticky="w")
        self._p1_elim_box.grid(row=7, column=0, sticky="w")

        self._game_frame.columnconfigure(0, weight=1)
        self._game_frame.columnconfigure(1, weight=0)
        self._game_frame.rowconfigure(0, weight=1)

    def _toggle_custom(self) -> None:
        is_custom = self._mode_var.get() == "Custom"
        if is_custom:
            self._size_label.grid()
            self._size_spin.grid()
        else:
            self._size_label.grid_remove()
            self._size_spin.grid_remove()

    def _start_game(self) -> None:
        p0_model = self._p0_var.get().strip()
        p1_model = self._p1_var.get().strip()
        max_turns_raw = self._max_turns_var.get().strip()
        if not p0_model or not p1_model:
            self._status_label.configure(text="Select both models.")
            return
        try:
            max_turns_val = int(max_turns_raw)
        except ValueError:
            self._show_error("Max Turns must be a number between 50 and 1000.")
            return
        if max_turns_val < 50 or max_turns_val > 1000:
            self._show_error("Max Turns must be a natural number between 50 and 1000.")
            return

        self._start_btn.configure(state="disabled")
        self._mode_combo.configure(state="disabled")
        self._p0_combo.configure(state="disabled")
        self._p1_combo.configure(state="disabled")
        self._max_turns_entry.configure(state="disabled")
        self._stop_event.clear()
        self._aborting = False

        mode = self._mode_var.get()
        size = int(self._size_var.get())

        self._lobby_frame.grid_remove()
        self._game_frame.grid()
        self._status_label.configure(text="Starting game...")

        args = {
            "p0_model": p0_model,
            "p1_model": p1_model,
            "mode": mode,
            "size": size,
            "max_turns": max_turns_val,
        }
        self._model_display = {0: p0_model, 1: p1_model}
        self._p0_elim_label.configure(text=f"{p0_model}:")
        self._p1_elim_label.configure(text=f"{p1_model}:")
        self._game_thread = threading.Thread(target=self._run_game, kwargs=args, daemon=True)
        self._game_thread.start()

    def _abort_game(self) -> None:
        self._aborting = True
        self._stop_event.set()
        self._status_label.configure(text="Aborting game...")
        self._abort_btn.configure(state="disabled")

    def _connect_ollama(self) -> None:
        port_raw = self._port_var.get().strip()
        if not port_raw.isdigit():
            self._show_error("Ollama port must be a number.")
            return
        host = f"http://127.0.0.1:{port_raw}"
        models = get_ollama_models(host)
        if not models:
            self._connect_status.configure(text="Not connected")
            self._show_error("Failed to connect to Ollama or no models found.")
            return

        self._models = models
        self._p0_combo.configure(values=models)
        self._p1_combo.configure(values=models)
        self._p0_var.set(models[0])
        self._p1_var.set(models[1] if len(models) > 1 else models[0])
        self._connect_status.configure(text="Connected")

    def _show_error(self, message: str) -> None:
        from tkinter import messagebox

        messagebox.showerror("Invalid Input", message)

    def _show_result_dialog(self, message: str) -> None:
        dialog = tk.Toplevel(self.root)
        dialog.title("Game Result")
        dialog.transient(self.root)
        dialog.grab_set()

        ttk.Label(dialog, text=message, padding=12, justify="left").grid(row=0, column=0, sticky="w")
        ttk.Button(dialog, text="Back to Lobby", command=lambda: self._close_result(dialog)).grid(
            row=1, column=0, sticky="e", padx=12, pady=12
        )
        dialog.update_idletasks()
        width = dialog.winfo_width()
        height = dialog.winfo_height()
        parent_x = self.root.winfo_rootx()
        parent_y = self.root.winfo_rooty()
        parent_w = self.root.winfo_width()
        parent_h = self.root.winfo_height()
        x = int(parent_x + (parent_w - width) / 2)
        y = int(parent_y + (parent_h - height) / 2)
        dialog.geometry(f"{width}x{height}+{x}+{y}")

    def _close_result(self, dialog: tk.Toplevel) -> None:
        try:
            dialog.destroy()
        finally:
            self._reset_to_lobby()

    def _run_game(self, p0_model: str, p1_model: str, mode: str, size: int, max_turns: int) -> None:
        def on_state(state: dict) -> None:
            if "type" in state:
                self._queue.put(state)
            else:
                self._queue.put({"type": "state", **state})

        try:
            run_match(
                p0_model=p0_model,
                p1_model=p1_model,
                mode=mode,
                size=size,
                prompt_name="base",
                max_turns=max_turns,
                on_state=on_state,
                stop_event=self._stop_event,
            )
            self._queue.put({"type": "done"})
        except Exception as exc:
            self._queue.put({"type": "error", "message": str(exc)})

    def _poll_queue(self) -> None:
        try:
            while True:
                item = self._queue.get_nowait()
                if item.get("type") == "state":
                    if self._aborting:
                        continue
                    self._render_board(item["board"])
                    self._turn_label.configure(text=f"Turn: {item['display_turn']}")
                    model = self._model_display.get(item["player_id"], f"Player {item['player_id']}")
                    self._status_label.configure(text=f"{model} to move")
                    self._render_eliminated(item["eliminated"])
                elif item.get("type") == "result":
                    if self._aborting:
                        self._show_result_dialog("Game aborted.")
                        continue
                    winner_model = item.get("winner_model", "draw")
                    reason = item.get("reason", "")
                    if winner_model == "draw":
                        message = "Result: Draw"
                    else:
                        message = f"Winner: {winner_model}"
                    if reason:
                        message = f"{message}\n{reason}"
                    self._show_result_dialog(message)
                elif item.get("type") == "done":
                    if self._aborting:
                        self._reset_to_lobby()
                    else:
                        self._status_label.configure(text="Game over.")
                elif item.get("type") == "error":
                    self._status_label.configure(text="Game failed.")
                    self._show_error(item.get("message", "Unknown error."))
                    self._reset_to_lobby()
        except queue.Empty:
            pass
        self.root.after(100, self._poll_queue)

    def _reset_to_lobby(self) -> None:
        self._aborting = False
        self._stop_event.clear()
        self._start_btn.configure(state="normal")
        self._mode_combo.configure(state="readonly")
        self._p0_combo.configure(state="normal")
        self._p1_combo.configure(state="normal")
        self._max_turns_entry.configure(state="normal")
        self._abort_btn.configure(state="normal")
        self._status_label.configure(text="Waiting...")
        self._p0_elim_label.configure(text="Player 0:")
        self._p1_elim_label.configure(text="Player 1:")
        self._lobby_frame.grid()
        self._game_frame.grid_remove()

    def _render_board(self, tokens: List[List[str]]) -> None:
        if not tokens:
            return
        self._last_tokens = tokens
        size = len(tokens)
        if size != self._board_size:
            self._board_size = size
            self._board_canvas.delete("piece")
            self._board_canvas.delete("lake")
            self._board_items = [[None for _ in range(size)] for _ in range(size)]
            self._lake_items = [[None for _ in range(size)] for _ in range(size)]
            self._refresh_board_background(force=True)
        else:
            self._refresh_board_background(force=False)

        cell = self._board_cell_size
        if cell <= 0:
            return
        origin_x, origin_y = self._board_origin
        font_size = max(10, int(cell * 0.45))

        for r in range(size):
            for c in range(size):
                token = tokens[r][c] if c < len(tokens[r]) else "."
                item_id = self._board_items[r][c]
                if token == "~":
                    if item_id:
                        self._board_canvas.delete(item_id)
                        self._board_items[r][c] = None
                    lake_id = self._lake_items[r][c]
                    lake_key = self._lake_key(tokens, r, c)
                    lake_image = self._lake_images.get(lake_key)
                    if not lake_image:
                        continue
                    x = origin_x + c * cell
                    y = origin_y + r * cell
                    if lake_id is None:
                        lake_id = self._board_canvas.create_image(
                            x,
                            y,
                            image=lake_image,
                            anchor="nw",
                            tags=("lake",),
                        )
                        self._lake_items[r][c] = lake_id
                    else:
                        self._board_canvas.itemconfigure(lake_id, image=lake_image)
                        self._board_canvas.coords(lake_id, x, y)
                    continue
                if token == ".":
                    if item_id:
                        self._board_canvas.delete(item_id)
                        self._board_items[r][c] = None
                    lake_id = self._lake_items[r][c]
                    if lake_id:
                        self._board_canvas.delete(lake_id)
                        self._lake_items[r][c] = None
                    continue

                lake_id = self._lake_items[r][c]
                if lake_id:
                    self._board_canvas.delete(lake_id)
                    self._lake_items[r][c] = None
                x = origin_x + c * cell + cell / 2
                y = origin_y + r * cell + cell / 2
                if item_id is None:
                    item_id = self._board_canvas.create_text(
                        x,
                        y,
                        text=token,
                        fill=_cell_fg(token),
                        font=("Consolas", font_size, "bold"),
                        tags=("piece",),
                    )
                    self._board_items[r][c] = item_id
                else:
                    self._board_canvas.coords(item_id, x, y)
                    self._board_canvas.itemconfigure(
                        item_id,
                        text=token,
                        fill=_cell_fg(token),
                        font=("Consolas", font_size, "bold"),
                    )

    def _load_board_image(self) -> Optional[Image.Image]:
        path = Path(__file__).resolve().parent / "sprites" / "board.png"
        if not path.exists():
            return None
        return Image.open(path)

    def _load_lake_images(self) -> Dict[str, Image.Image]:
        sprites_dir = Path(__file__).resolve().parent / "sprites"
        lake_files = {
            "tl": "lake_tl.png",
            "tr": "lake_tr.png",
            "bl": "lake_bl.png",
            "br": "lake_br.png",
        }
        images: Dict[str, Image.Image] = {}
        for key, filename in lake_files.items():
            path = sprites_dir / filename
            if not path.exists():
                continue
            images[key] = Image.open(path)
        return images

    def _lake_key(self, tokens: List[List[str]], row: int, col: int) -> str:
        up = row > 0 and col < len(tokens[row - 1]) and tokens[row - 1][col] == "~"
        left = col > 0 and tokens[row][col - 1] == "~"
        if not up and not left:
            return "tl"
        if not up and left:
            return "tr"
        if up and not left:
            return "bl"
        return "br"

    def _on_board_resize(self, _event: tk.Event) -> None:
        self._refresh_board_background(force=False)
        if self._last_tokens:
            self._render_board(self._last_tokens)

    def _refresh_board_background(self, force: bool) -> None:
        if not self._board_image_raw or self._board_size <= 0:
            return
        canvas_w = self._board_canvas.winfo_width()
        canvas_h = self._board_canvas.winfo_height()
        if canvas_w <= 1 or canvas_h <= 1:
            return
        cell = min(canvas_w // self._board_size, canvas_h // self._board_size)
        if cell <= 0:
            return
        board_px = cell * self._board_size
        if not force and board_px == self._board_bg_size:
            return
        self._board_cell_size = cell
        self._board_bg_size = board_px
        origin_x = (canvas_w - board_px) // 2
        origin_y = (canvas_h - board_px) // 2
        self._board_origin = (origin_x, origin_y)

        resized = self._board_image_raw.resize((board_px, board_px), Image.NEAREST)
        self._board_image = ImageTk.PhotoImage(resized)
        self._refresh_lake_images(cell)
        if self._board_bg_id is None:
            self._board_bg_id = self._board_canvas.create_image(
                origin_x,
                origin_y,
                image=self._board_image,
                anchor="nw",
            )
        else:
            self._board_canvas.itemconfigure(self._board_bg_id, image=self._board_image)
            self._board_canvas.coords(self._board_bg_id, origin_x, origin_y)

    def _refresh_lake_images(self, cell: int) -> None:
        if not self._lake_images_raw:
            return
        self._lake_images.clear()
        for key, image in self._lake_images_raw.items():
            resized = image.resize((cell, cell), Image.NEAREST)
            self._lake_images[key] = ImageTk.PhotoImage(resized)

    def _render_eliminated(self, eliminated: Dict[int, List[str]]) -> None:
        self._p0_elim_box.delete(0, tk.END)
        self._p1_elim_box.delete(0, tk.END)
        for item in eliminated.get(0, []):
            self._p0_elim_box.insert(tk.END, item)
        for item in eliminated.get(1, []):
            self._p1_elim_box.insert(tk.END, item)


def get_ollama_models(host: str) -> List[str]:
    try:
        env = dict(**os.environ)
        env["OLLAMA_HOST"] = host
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            check=True,
            env=env,
        )
    except Exception:
        return []
    lines = result.stdout.splitlines()
    models = []
    for line in lines[1:]:
        if not line.strip():
            continue
        models.append(line.split()[0])
    return sorted(models)


def _cell_fg(token: str) -> str:
    if token in ("FL", "BM"):
        return "#ffe6e6"
    if token == "?":
        return "#f0c6c6"
    return "#f2f2f2"
