import re
import random
from typing import Optional, Dict, Tuple, List, Any

import textarena as ta


class StrategoDuelEnv(ta.Env):
    """
    Stratego Duel (6x6) Environment for TextArena.

    - 2 Players: Player 0 (bottom), Player 1 (top)
    - Board: 6x6 (rows A-F, columns 0-5)
    - Lakes (blocked): (2,2), (2,3), (3,2), (3,3)
    - Win by: Capturing opponent Flag or eliminating all movable pieces
    - Special rules:
        * Bombs & Flags cannot move
        * Scout can move multiple squares in straight lines
        * Miner can defuse Bomb
        * Spy kills Marshal on attack
        * Two-Squares Rule: cannot move back & forth between two squares more than 3 times in a row
    """

    def __init__(self):
        # Piece counts (reduced for 6x6)
        self.piece_counts: Dict[str, int] = {
            "Flag": 1,
            "Bomb": 2,
            "Spy": 1,
            "Scout": 1,
            "Miner": 1,
            "General": 1,
            "Marshal": 1,
        }

        # Piece strength (higher = stronger)
        self.piece_ranks: Dict[str, int] = {
            "Flag": 0,
            "Bomb": 11,
            "Spy": 1,
            "Scout": 2,
            "Miner": 3,
            "General": 9,
            "Marshal": 10,
        }

        # Lake positions (blocked cells)
        self.lakes: List[Tuple[int, int]] = [(2, 2), (2, 3), (3, 2), (3, 3)]

        # Track piece positions for each player: {player_id: [(row, col), ...]}
        self.player_pieces: Dict[int, List[Tuple[int, int]]] = {0: [], 1: []}

        # 6x6 board, None / "~" / piece dict
        self.board: List[List[Optional[Dict[str, Any]]]] = [
            [None for _ in range(6)] for _ in range(6)
        ]

        # Turn counter (for turn limit)
        self.turn_count: int = 0

        # --- Two-Squares Rule (Repetition) ---
        # Stores last move for each player as (sr, sc, dr, dc)
        self.last_move: Dict[int, Optional[Tuple[int, int, int, int]]] = {
            0: None,
            1: None,
        }
        # Counts consecutive back-and-forth repetitions per player
        self.repetition_count: Dict[int, int] = {0: 0, 1: 0}

    # TextArena uses this key to render the final board in terminal
    @property
    def terminal_render_keys(self) -> List[str]:
        return ["rendered_board"]

    # -------------------------------------------------------------------------
    # Core TextArena interface
    # -------------------------------------------------------------------------
    def reset(self, num_players: int, seed: Optional[int] = None):
        """Reset environment for a new game."""
        self.state = ta.TwoPlayerState(num_players=num_players, seed=seed)
        self.turn_count = 0

        # Reset repetition tracking
        self.last_move = {0: None, 1: None}
        self.repetition_count = {0: 0, 1: 0}

        # Clear board / piece tracking
        self.board = [[None for _ in range(6)] for _ in range(6)]
        self.player_pieces = {0: [], 1: []}

        # Place pieces
        self.board = self._populate_board()

        # Render initial full board (for logging / God mode)
        rendered_board = self._render_board(player_id=None, full_board=True)

        game_state = {
            "board": self.board,
            "player_pieces": self.player_pieces,
            "rendered_board": rendered_board,
        }

        # Set initial game state & prompt function
        self.state.reset(
            game_state=game_state, player_prompt_function=self._generate_player_prompt
        )

        # Provide first observation for Player 0
        self._observe_current_state()

    def step(self, action: str) -> Tuple[bool, ta.Info]:
        """Process a player's action: validate, apply move, resolve battle, check win."""
        self.turn_count += 1
        pid = self.state.current_player_id

        # If no moves were available in previous observation, end game
        if self.state.game_state.get(f"available_moves_p{pid}", 1) == 0:
            # Opponent wins if they still have movable pieces
            winner = 1 - pid if self._has_movable_pieces(1 - pid) else -1
            self.state.set_winner(player_id=winner, reason="No moves/Stalemate")
            return self.state.step()

        # Log the player's raw action
        self.state.add_observation(
            from_id=pid,
            to_id=pid,
            message=action,
            observation_type=ta.ObservationType.PLAYER_ACTION,
        )

        # Parse move: [A0 B0]
        match = re.search(r"\[([A-F])([0-5]) ([A-F])([0-5])\]", action, re.IGNORECASE)
        if not match:
            self.state.set_invalid_move(
                reason=f"Invalid format '{action}'. Use [A0 B0]."
            )
        else:
            sr = ord(match.group(1).upper()) - 65
            sc = int(match.group(2))
            dr = ord(match.group(3).upper()) - 65
            dc = int(match.group(4))

            # Validate basic movement rules
            if self._validate_move(pid, sr, sc, dr, dc):
                # --- Two-Squares Rule (Back-and-forth repetition) ---
                is_repetition = False
                last = self.last_move[pid]

                # If current move is exact reverse of last move (A->B, then B->A)
                if last is not None:
                    last_sr, last_sc, last_dr, last_dc = last
                    if sr == last_dr and sc == last_dc and dr == last_sr and dc == last_sc:
                        is_repetition = True

                if is_repetition:
                    self.repetition_count[pid] += 1
                else:
                    # New path resets repetition count
                    self.repetition_count[pid] = 0

                self.last_move[pid] = (sr, sc, dr, dc)

                # If exceeded repetition limit, move is illegal
                if self.repetition_count[pid] >= 3:
                    self.state.set_invalid_move(
                        reason="Illegal Repetition: Cannot move back and forth more than 3 consecutive times."
                    )
                    return self.state.step()

                attacker = self.board[sr][sc]
                target = self.board[dr][dc]

                # --- Empty Target: Simple Move ---
                if target is None:
                    self.board[dr][dc], self.board[sr][sc] = attacker, None
                    self.player_pieces[pid].remove((sr, sc))
                    self.player_pieces[pid].append((dr, dc))

                    self.state.add_observation(
                        from_id=-1,
                        to_id=pid,
                        message="Move success.",
                        observation_type=ta.ObservationType.GAME_ACTION_DESCRIPTION,
                    )
                    self.state.add_observation(
                        from_id=-1,
                        to_id=1 - pid,
                        message="Opponent moved.",
                        observation_type=ta.ObservationType.GAME_ACTION_DESCRIPTION,
                    )

                # --- Battle ---
                else:
                    # Any battle breaks the repetition chain
                    self.repetition_count[pid] = 0
                    self.last_move[pid] = None

                    att_rank = self.piece_ranks[attacker["rank"]]
                    tgt_rank = self.piece_ranks[target["rank"]]

                    # 1) Equal ranks → both die
                    if att_rank == tgt_rank:
                        self.board[sr][sc] = None
                        self.board[dr][dc] = None
                        self.player_pieces[pid].remove((sr, sc))
                        self.player_pieces[1 - pid].remove((dr, dc))

                    # 2) Target is Bomb
                    elif target["rank"] == "Bomb":
                        if attacker["rank"] == "Miner":
                            # Miner defuses Bomb and moves in
                            self.board[dr][dc], self.board[sr][sc] = attacker, None
                            self.player_pieces[pid].remove((sr, sc))
                            self.player_pieces[pid].append((dr, dc))
                            self.player_pieces[1 - pid].remove((dr, dc))
                        else:
                            # Attacker dies
                            self.board[sr][sc] = None
                            self.player_pieces[pid].remove((sr, sc))

                    # 3) Target is Flag → Attacker wins game
                    elif target["rank"] == "Flag":
                        self.state.set_winner(player_id=pid, reason="Flag Captured!")
                        return self.state.step()

                    # 4) Spy vs Marshal (Spy attacks Marshal → Spy wins)
                    elif attacker["rank"] == "Spy" and target["rank"] == "Marshal":
                        self.board[dr][dc], self.board[sr][sc] = attacker, None
                        self.player_pieces[pid].remove((sr, sc))
                        self.player_pieces[pid].append((dr, dc))
                        self.player_pieces[1 - pid].remove((dr, dc))

                    # 5) Normal compare: higher rank wins
                    elif att_rank > tgt_rank:
                        # Attacker wins, moves in
                        self.board[dr][dc], self.board[sr][sc] = attacker, None
                        self.player_pieces[pid].remove((sr, sc))
                        self.player_pieces[pid].append((dr, dc))
                        self.player_pieces[1 - pid].remove((dr, dc))
                    else:
                        # Defender wins, attacker dies
                        self.board[sr][sc] = None
                        self.player_pieces[pid].remove((sr, sc))

                    msg = "Battle occurred."
                    self.state.add_observation(
                        from_id=-1,
                        to_id=pid,
                        message=msg,
                        observation_type=ta.ObservationType.GAME_ACTION_DESCRIPTION,
                    )
                    self.state.add_observation(
                        from_id=-1,
                        to_id=1 - pid,
                        message=msg,
                        observation_type=ta.ObservationType.GAME_ACTION_DESCRIPTION,
                    )

        # --- Global Win / Draw Conditions ---
        winner = self._check_winner()
        if winner is not None:
            self.state.set_winner(player_id=winner, reason="Elimination.")
        elif self._check_stalemate():
            self.state.set_winner(player_id=-1, reason="Stalemate.")
        elif self.turn_count > 1000:
            self.state.set_winner(player_id=-1, reason="Turn limit.")

        # Update full-board render into game_state (for terminal rendering)
        self.state.game_state["rendered_board"] = self._render_board(
            player_id=pid, full_board=True
        )

        # Let TextArena advance the state
        done, info = self.state.step()

        # If game is not over, give next player a fresh observation
        if not done:
            self._observe_current_state()

        return done, info

    # -------------------------------------------------------------------------
    # Observation / Prompt / Rendering
    # -------------------------------------------------------------------------
    def _generate_player_prompt(self, player_id: int, game_state: Dict[str, Any]) -> str:
        """Generate instruction prompt for the current player (LLM)."""
        prompt = (
            f"You are Player {player_id} in Stratego Duel (6x6).\n"
            "Goal: Capture the enemy Flag or eliminate all of the opponent's movable pieces.\n"
            "\n"
            "### BOARD\n"
            "- Grid: 6 rows (A-F) x 6 columns (0-5).\n"
            "- Lakes (~) are blocked and cannot be entered.\n"
            "\n"
            "### MOVE FORMAT\n"
            "- You MUST output exactly one move in the format: [Source Destination]\n"
            "- Example: `[A0 B0]` moves the piece at A0 to B0.\n"
            "\n"
            "### PIECE RULES\n"
            "- Flag (FL): Cannot move. If captured, you lose.\n"
            "- Bomb (BM): Cannot move. Defeats any attacker except Miner.\n"
            "- Spy (SP): If Spy attacks Marshal (MS), Spy wins.\n"
            "- Scout (SC): Can move any number of empty squares in a straight line.\n"
            "- Miner (MN): Can defuse Bombs.\n"
            "- General (GN), Marshal (MS): Stronger ranks defeat weaker ones.\n"
            "- Battles: Higher rank wins. Same rank → both pieces are removed.\n"
            "\n"
            "### TWO-SQUARES RULE\n"
            "- You may NOT move a piece back and forth between the same two squares\n"
            "  more than 3 times in a row (e.g., [A0 B0], [B0 A0], [A0 B0], [B0 A0] is illegal).\n"
            "\n"
            "Here is the current board:\n"
        )
        return prompt

    def _observe_current_state(self):
        """
        Compute all available moves for the current player and
        send a formatted board + move list observation.
        """
        BOARD_SIZE = 6
        player_id = self.state.current_player_id
        available_moves: List[str] = []

        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                piece = self.board[row][col]

                # Only consider current player's pieces
                if not (isinstance(piece, dict) and piece["player"] == player_id):
                    continue

                rank = piece["rank"].lower()
                # Bombs & Flags cannot move
                if rank in ["bomb", "flag"]:
                    continue

                is_scout = rank == "scout"

                # 4-directional movement
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    if is_scout:
                        # Scout: move multiple squares until blocked
                        distance = 1
                        while True:
                            new_row = row + dr * distance
                            new_col = col + dc * distance
                            if not (0 <= new_row < 6 and 0 <= new_col < 6):
                                break
                            if (new_row, new_col) in self.lakes:
                                break

                            target = self.board[new_row][new_col]

                            # Empty cell: can move, keep going
                            if target is None:
                                move_str = (
                                    f"[{chr(row + 65)}{col} "
                                    f"{chr(new_row + 65)}{new_col}]"
                                )
                                available_moves.append(move_str)
                                distance += 1
                            # Lake marker (string "~") – shouldn't normally happen, but be safe
                            elif target == "~":
                                break
                            # Enemy piece: can attack, but stop afterwards
                            elif isinstance(target, dict) and target["player"] != player_id:
                                move_str = (
                                    f"[{chr(row + 65)}{col} "
                                    f"{chr(new_row + 65)}{new_col}]"
                                )
                                available_moves.append(move_str)
                                break
                            # Own piece or anything else: blocked
                            else:
                                break
                    else:
                        # Normal piece: single-step move
                        new_row = row + dr
                        new_col = col + dc
                        if not (0 <= new_row < 6 and 0 <= new_col < 6):
                            continue
                        if (new_row, new_col) in self.lakes:
                            continue

                        target = self.board[new_row][new_col]
                        # Empty or enemy piece is allowed
                        if target is None or (
                            isinstance(target, dict) and target["player"] != player_id
                        ):
                            move_str = (
                                f"[{chr(row + 65)}{col} "
                                f"{chr(new_row + 65)}{new_col}]"
                            )
                            available_moves.append(move_str)

        # Save number of available moves into game_state
        self.state.game_state[f"available_moves_p{player_id}"] = len(available_moves)

        # Observation message: board in ``` block + move list
        obs_msg = (
            "Current Board:\n"
            "```\n"
            f"{self._render_board(player_id=player_id, full_board=False)}"
            "```\n"
            f"Available Moves: {', '.join(available_moves)}"
        )

        self.state.add_observation(
            message=obs_msg, observation_type=ta.ObservationType.GAME_BOARD
        )

    def _render_board(self, player_id: Optional[int], full_board: bool = False) -> str:
        """
        Render the 6x6 board as a text grid.

        - Column header: 0  1  2  3  4  5
        - Rows labeled A-F
        - Lakes: ~
        - Empty: .
        - full_board=True  → show all pieces with owner (P0 lower-case, P1 upper-case)
        - full_board=False → fog of war (only show current player's ranks, others '?')
        """
        BOARD_SIZE = 6
        abbr = {
            "Flag": "FL",
            "Bomb": "BM",
            "Spy": "SP",
            "Scout": "SC",
            "Miner": "MN",
            "General": "GN",
            "Marshal": "MS",
        }

        lines: List[str] = []

        # Column headers with 3-character spacing
        header = "   " + " ".join(f"{i:>3}" for i in range(BOARD_SIZE))
        lines.append(header + "\n")

        for r in range(BOARD_SIZE):
            row_label = chr(r + 65)  # A-F
            row_cells: List[str] = [f"{row_label:<3}"]  # left aligned

            for c in range(BOARD_SIZE):
                if (r, c) in self.lakes:
                    cell = "  ~ "
                else:
                    cell_data = self.board[r][c]
                    if cell_data is None:
                        cell = "  . "
                    elif cell_data == "~":
                        cell = "  ~ "
                    else:
                        # piece dict
                        code = abbr.get(cell_data["rank"], "??")
                        owner = cell_data["player"]

                        if full_board:
                            # P0 lower-case, P1 upper-case for debugging
                            cell = f" {code.lower() if owner == 0 else code.upper()} "
                        else:
                            # Fog of war
                            if player_id is not None and owner == player_id:
                                cell = f" {code.upper()} "
                            else:
                                cell = "  ? "
                row_cells.append(cell)

            lines.append("".join(row_cells) + "\n")

        return "".join(lines)

    # -------------------------------------------------------------------------
    # Game logic helpers
    # -------------------------------------------------------------------------
    def _populate_board(self) -> List[List[Optional[Dict[str, Any]]]]:
        """
        Place all pieces on the board for both players.

        - Player 0: rows 0-1
        - Player 1: rows 4-5
        - Flag placed randomly in those rows
        - Bombs placed preferably around the Flag
        - Remaining pieces placed randomly in own rows (not on lakes)
        """
        for player in range(2):
            rows = range(0, 2) if player == 0 else range(4, 6)

            # 1) Place Flag
            while True:
                r = random.choice(list(rows))
                c = random.randint(0, 5)
                if (r, c) not in self.lakes and self.board[r][c] is None:
                    self.board[r][c] = {"rank": "Flag", "player": player}
                    self.player_pieces[player].append((r, c))
                    flag_pos = (r, c)
                    break

            # 2) Place Bombs (prefer near Flag)
            bombs_remaining = self.piece_counts["Bomb"]
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                if bombs_remaining <= 0:
                    break
                br = flag_pos[0] + dr
                bc = flag_pos[1] + dc
                if (
                    0 <= br < 6
                    and 0 <= bc < 6
                    and br in rows
                    and (br, bc) not in self.lakes
                    and self.board[br][bc] is None
                ):
                    self.board[br][bc] = {"rank": "Bomb", "player": player}
                    self.player_pieces[player].append((br, bc))
                    bombs_remaining -= 1

            # 3) Build remaining piece list
            all_pieces: List[str] = []
            for rank, count in self.piece_counts.items():
                if rank == "Flag":
                    continue
                if rank == "Bomb":
                    # Only leftover bombs (if some not placed around flag)
                    if bombs_remaining > 0:
                        all_pieces.extend(["Bomb"] * bombs_remaining)
                else:
                    all_pieces.extend([rank] * count)

            # 4) Randomly place the remaining pieces
            for rank in all_pieces:
                while True:
                    r = random.choice(list(rows))
                    c = random.randint(0, 5)
                    if (r, c) not in self.lakes and self.board[r][c] is None:
                        self.board[r][c] = {"rank": rank, "player": player}
                        self.player_pieces[player].append((r, c))
                        break

        # Mark lakes explicitly on the board
        for r, c in self.lakes:
            self.board[r][c] = "~"

        return self.board

    def _validate_move(self, pid: int, sr: int, sc: int, dr: int, dc: int) -> bool:
        """Check if a move from (sr, sc) to (dr, dc) by player pid is legal."""
        # Bounds
        if not (0 <= sr < 6 and 0 <= sc < 6 and 0 <= dr < 6 and 0 <= dc < 6):
            return False

        # Must move own piece
        if self.board[sr][sc] is None or self.board[sr][sc]["player"] != pid:
            return False

        # Cannot move into lakes
        if (dr, dc) in self.lakes:
            return False

        # Cannot capture own piece
        if (
            self.board[dr][dc] is not None
            and self.board[dr][dc] != "~"
            and isinstance(self.board[dr][dc], dict)
            and self.board[dr][dc]["player"] == pid
        ):
            return False

        rank = self.board[sr][sc]["rank"]

        # Bombs & Flags cannot move
        if rank in ["Bomb", "Flag"]:
            return False

        # Scout: can move multiple squares in straight line
        if rank == "Scout":
            # Must be in same row or column
            if sr != dr and sc != dc:
                return False
            # Path-blocking checks can be added here if desired.
            # For now we assume _observe_current_state only generates valid paths.
            return True

        # Normal pieces: one-step orthogonal move
        if abs(sr - dr) + abs(sc - dc) != 1:
            return False

        return True

    def _check_winner(self) -> Optional[int]:
        """
        Check if a player has no movable pieces left.
        Returns:
            - 0 or 1 if that player has WON
            - None otherwise
        """
        for p in range(2):
            # If player p has NO movable pieces, opponent wins
            if not self._has_movable_pieces(p):
                return 1 - p
        return None

    def _has_movable_pieces(self, pid: int) -> bool:
        """True if player pid has at least one non-Bomb/Flag piece on the board."""
        for (r, c) in self.player_pieces[pid]:
            cell = self.board[r][c]
            if (
                cell
                and cell != "~"
                and isinstance(cell, dict)
                and cell["rank"] not in ["Bomb", "Flag"]
            ):
                return True
        return False

    def _check_stalemate(self) -> bool:
        """Stalemate if neither player has any movable pieces."""
        return not self._has_movable_pieces(0) and not self._has_movable_pieces(1)