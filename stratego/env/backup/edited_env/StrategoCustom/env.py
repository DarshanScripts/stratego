import random
import re
from typing import Any, Dict, Optional, Tuple, List

import textarena as ta
class StrategoCustomEnv(ta.Env):
    """
    Custom Stratego environment supporting board sizes 6–9.

    Features:
    - Board sizes: 6x6, 7x7, 8x8, 9x9
    - Full Stratego rules:
        * Movement restrictions
        * Battle resolution
        * Spy vs Marshal special rule
        * Miner defuses Bombs
    - Custom features:
        * Balanced piece counts based on board size
        * Size-aware initial layout (back rows / front rows)
        * Automatically generated lakes in the neutral zone
        * Two-Squares Rule (anti-repetition): cannot move back and forth
          between the same two squares more than 3 times in a row
        * No-legal-moves rule (like DuelEnv): if a player has 0 legal moves
          when their turn starts, they lose (unless both are blocked → draw).
    """

    def __init__(self, size: int = 9):
        if size < 6 or size > 9:
            raise ValueError("StrategoCustomEnv supports only board sizes 6–9.")

        self.size = size

        # Board and lake structures
        self.board: List[List[Optional[Dict[str, Any]]]] = [
            [None for _ in range(size)] for _ in range(size)
        ]
        self.lakes: List[Tuple[int, int]] = self._generate_lakes()

        # Piece counts are derived from board size
        self.piece_counts: Dict[str, int] = self._generate_piece_counts()

        # Rank mapping for battle resolution
        self.piece_ranks: Dict[str, int] = {
            "Flag": 0,
            "Bomb": 11,
            "Spy": 1,
            "Scout": 2,
            "Miner": 3,
            "Sergeant": 4,
            "Lieutenant": 5,
            "Captain": 6,
            "Major": 7,
            "Colonel": 8,
            "General": 9,
            "Marshal": 10,
        }

        # Track positions of pieces for each player
        # {player_id: [(row, col), ...]}
        self.player_pieces: Dict[int, List[Tuple[int, int]]] = {0: [], 1: []}

        # Turn counter (optional, for turn limit)
        self.turn_count: int = 0

        # --- Two-Squares Rule tracking (back-and-forth repetition) ---
        # last_move[player_id] = (src_r, src_c, dst_r, dst_c)
        self.last_move: Dict[int, Optional[Tuple[int, int, int, int]]] = {
            0: None,
            1: None,
        }
        # repetition_count[player_id] = number of consecutive back-and-forth reversals
        self.repetition_count: Dict[int, int] = {0: 0, 1: 0}

    # ------------------------------------------------------------------
    # TextArena API
    # ------------------------------------------------------------------
    @property
    def terminal_render_keys(self):
        return ["rendered_board"]

    # -------------------------------------------------------------------------
    # 1) LAKES
    # -------------------------------------------------------------------------
    def _generate_lakes(self):
        """Small boards: one lake in the center. Large boards: a 2×2 lake block."""
        mid = self.size // 2

        if self.size >= 8:
            return [
                (mid - 1, mid - 1), (mid - 1, mid),
                (mid,     mid - 1), (mid,     mid)
            ]
        else:
            return [(mid, mid)]

    # -------------------------------------------------------------------------
    # 2) PIECE COUNTS
    # -------------------------------------------------------------------------
    def _generate_piece_counts(self):
        """Ensure ≥1 of each rank, then scale to board size."""
        ranks = [
            'Flag', 'Bomb', 'Spy', 'Scout', 'Miner',
            'Sergeant', 'Lieutenant', 'Captain', 'Major',
            'Colonel', 'General', 'Marshal'
        ]

        counts = {r: 1 for r in ranks}   # minimum one of each

        target = (self.size * self.size) // 4
        current = len(ranks)

        filler = ['Scout', 'Miner', 'Sergeant', 'Bomb']
        i = 0
        while current < target:
            p = filler[i % len(filler)]
            counts[p] += 1
            current += 1
            i += 1

        return counts

    def step(self, action: str) -> Tuple[bool, ta.Info]:
        """ Execute an action in the environment """
        player_id = self.state.current_player_id

        ## update the observation
        self.state.add_observation(from_id=player_id, to_id=player_id, message=action, observation_type=ta.ObservationType.PLAYER_ACTION)

        ## action search pattern
        action_search_pattern = re.compile(r"\[([A-J])([0-9]) ([A-J])([0-9])\]", re.IGNORECASE)
        match = action_search_pattern.search(action)

        if match is None:
            reason=f"Invalid action format. Player {player_id} did not input a move in the format [A0 B0]."
            self.state.set_invalid_move(reason=reason)
            try:
                self.state.game_info[player_id]["invalid_move"] = True
            except Exception:
                pass
            self.state.set_winner(player_id=(1 - player_id), reason=reason)
            return self.state.step()

        else:
            src_row, src_col, dest_row, dest_col = match.groups()
            src_row, dest_row = src_row.upper(), dest_row.upper()
            source = f"{src_row}{src_col}"
            dest = f"{dest_row}{dest_col}"
            src_row, src_col = ord(src_row) - 65, int(src_col)
            dest_row, dest_col = ord(dest_row) - 65, int(dest_col)
             

            ## check if the source and destination are valid
            if self._validate_move(player_id=player_id, src_r=src_row, src_c=src_col, dst_r=dest_row, dst_c=dest_col):

                attacking_piece = self.board[src_row][src_col]
                target_piece = self.board[dest_row][dest_col]

                if target_piece is None:
                    ## move to an empty square
                    self.board[dest_row][dest_col] = attacking_piece
                    self.board[src_row][src_col] = None
                    self.player_pieces[player_id].remove((src_row, src_col))
                    self.player_pieces[player_id].append((dest_row, dest_col))
                    
                    ## add the observation to both players separately
                    message=f"You have moved your piece from {source} to {dest}."
                    self.state.add_observation(from_id=-1, to_id=player_id, message=message, observation_type=ta.ObservationType.GAME_ACTION_DESCRIPTION)

                    message=f"Player {player_id} has moved a piece from {source} to {dest}."
                    self.state.add_observation(from_id=-1, to_id=1-player_id, message=message, observation_type=ta.ObservationType.GAME_ACTION_DESCRIPTION)

                else:
                    ## battle
                    attacking_rank = self.piece_ranks[attacking_piece['rank']]
                    target_rank = self.piece_ranks[target_piece['rank']]
                    if attacking_rank == target_rank:
                        ## both pieces are removed
                        self.board[src_row][src_col] = None
                        self.board[dest_row][dest_col] = None
                        self.player_pieces[player_id].remove((src_row, src_col))
                        self.player_pieces[1 - player_id].remove((dest_row, dest_col))

                        ## add the observation to both players separately
                        message=f"You have moved your piece from {source} to {dest}. The attacking piece was {attacking_piece['rank']} and the destination piece was {target_piece['rank']}. As the ranks are the same, both pieces lost."
                        self.state.add_observation(from_id=-1, to_id=player_id, message=message, observation_type=ta.ObservationType.GAME_ACTION_DESCRIPTION)

                        message=f"Player {player_id} has moved a piece from {source} to {dest}. The attacking piece was {attacking_piece['rank']} and the destination piece was {target_piece['rank']}. As the ranks are the same, both pieces lost."
                        self.state.add_observation(from_id=-1, to_id=1 - player_id, message=message, observation_type=ta.ObservationType.GAME_ACTION_DESCRIPTION)

                    elif target_piece['rank'] == 'Bomb':
                        if attacking_piece['rank'] == 'Miner':
                            ## Miner defuses the bomb
                            self.board[dest_row][dest_col] = attacking_piece
                            self.board[src_row][src_col] = None
                            self.player_pieces[player_id].remove((src_row, src_col))
                            self.player_pieces[player_id].append((dest_row, dest_col))

                            ## add the observation to both players separately
                            message=f"You have moved your piece from {source} to {dest}. The attacking piece was {attacking_piece['rank']} and the destination piece was {target_piece['rank']}. As miners can defuse bombs, you won the battle."
                            self.state.add_observation(from_id=-1, to_id=player_id, message=message, observation_type=ta.ObservationType.GAME_ACTION_DESCRIPTION)

                            message=f"Player {player_id} has moved a piece from {source} to {dest}. The attacking piece was {attacking_piece['rank']} and the destination piece was {target_piece['rank']}. As miners can defuse bombs, you lost the battle."
                            self.state.add_observation(from_id=-1, to_id=1-player_id, message=message, observation_type=ta.ObservationType.GAME_ACTION_DESCRIPTION)

                        else:
                            ## attacking piece is destroyed
                            self.board[src_row][src_col] = None
                            self.player_pieces[player_id].remove((src_row, src_col))

                            ## add the observation to both players separately
                            message=f"You have moved your piece from {source} to {dest}. The attacking piece was {attacking_piece['rank']} and the destination piece was {target_piece['rank']}. As the attacker is not a miner, you lost the battle."
                            self.state.add_observation(from_id=-1, to_id=player_id, message=message, observation_type=ta.ObservationType.GAME_ACTION_DESCRIPTION)

                            message=f"Player {player_id} has moved a piece from {source} to {dest}. The attacking piece was {attacking_piece['rank']} and the destination piece was {target_piece['rank']}. As the attacker is not a miner, you won the battle."
                            self.state.add_observation(from_id=-1, to_id=1-player_id, message=message, observation_type=ta.ObservationType.GAME_ACTION_DESCRIPTION)

                    elif target_piece['rank'] == 'Flag':
                        self.board[dest_row][dest_col] = attacking_piece
                        self.board[src_row][src_col] = None
                        self.player_pieces[player_id].remove((src_row, src_col))
                        self.player_pieces[player_id].append((dest_row, dest_col))
                        self.player_pieces[1 - player_id].remove((dest_row, dest_col))
                        ## game over
                        self.state.set_winner(player_id=player_id,reason=[f"Player {player_id} has captured the opponent's flag!"])
                    elif attacking_piece['rank'] == 'Spy' and target_piece['rank'] == 'Marshal':
                        ## Spy beats Marshal only if spy attacks first
                        self.board[dest_row][dest_col] = attacking_piece
                        self.board[src_row][src_col] = None
                        self.player_pieces[player_id].remove((src_row, src_col))
                        self.player_pieces[player_id].append((dest_row, dest_col))
                        self.player_pieces[1 - player_id].remove((dest_row, dest_col))

                        ## add the observation to both players separately
                        message=f"You have moved your piece from {source} to {dest}. The attacking piece was {attacking_piece['rank']} and the destination piece was {target_piece['rank']}. As the attacker is a spy and the destination is a marshall, you won the battle."
                        self.state.add_observation(from_id=-1, to_id=player_id, message=message, observation_type=ta.ObservationType.GAME_ACTION_DESCRIPTION)

                        message=f"Player {player_id} has moved a piece from {source} to {dest}. The attacking piece was {attacking_piece['rank']} and the destination piece was {target_piece['rank']}. As the attacker is a spy and the destination is a marshall, you lost the battle."
                        self.state.add_observation(from_id=-1, to_id=1-player_id, message=message, observation_type=ta.ObservationType.GAME_ACTION_DESCRIPTION)

                    elif attacking_rank > target_rank:
                        ## attacker wins
                        self.board[dest_row][dest_col] = attacking_piece
                        self.board[src_row][src_col] = None
                        self.player_pieces[player_id].remove((src_row, src_col))
                        self.player_pieces[player_id].append((dest_row, dest_col))
                        self.player_pieces[1 - player_id].remove((dest_row, dest_col))

                        ## add the observation to both players separately
                        message=f"You have moved your piece from {source} to {dest}. The attacking piece was {attacking_piece['rank']} and the destination piece was {target_piece['rank']}. As the attacker is a higher rank than the destination, you won the battle."
                        self.state.add_observation(from_id=-1, to_id=player_id, message=message, observation_type=ta.ObservationType.GAME_ACTION_DESCRIPTION)

                        message=f"Player {player_id} has moved a piece from {source} to {dest}. The attacking piece was {attacking_piece['rank']} and the destination piece was {target_piece['rank']}. As the attacker is a higher rank than the destination, you lost the battle."
                        self.state.add_observation(from_id=-1, to_id=1-player_id, message=message, observation_type=ta.ObservationType.GAME_ACTION_DESCRIPTION)

            else:
                ## defender wins
                self.board[src_row][src_col] = None
                self.player_pieces[player_id].remove((src_row, src_col))

                ## add the observation to both players separately
                message=f"You have moved your piece from {source} to {dest}. The attacking piece was {attacking_piece['rank']} and the destination piece was {target_piece['rank']}. As the attacker is a lower rank than the destination, you lost the battle."
                self.state.add_observation(from_id=-1, to_id=player_id, message=message, observation_type=ta.ObservationType.GAME_ACTION_DESCRIPTION)

                message=f"Player {player_id} has moved a piece from {source} to {dest}. The attacking piece was {attacking_piece['rank']} and the destination piece was {target_piece['rank']}. As the attacker is a lower rank than the destination, you won the battle."
                self.state.add_observation(from_id=-1, to_id=1-player_id, message=message, observation_type=ta.ObservationType.GAME_ACTION_DESCRIPTION)
        else:
            try:
                self.state.game_info[player_id]["invalid_move"] = True
            except Exception:
                pass
            self.state.set_winner(player_id=(1 - player_id), reason="Illegal move.")
            return self.state.step()

        ## check if the game is over
        if self._check_winner():
            reason=f"Player {self._check_winner()} wins! Player {1 - self._check_winner()} has no more movable pieces."
            self.state.set_winner(player_id=self._check_winner(), reason=reason)

        ## update the rendered board
        self.state.game_state["rendered_board"] = self._render_board(player_id=player_id, full_board=True)

        result = self.state.step()
        self._observe_current_state()
        return result
    
    # -------------------------------------------------------------------------
    # 3) RESET (override because original uses fixed 10×10 rows)
    # -------------------------------------------------------------------------
    def reset(self, num_players: int, seed: Optional[int]=None):
        """Reset but repopulate board using our custom placement logic."""
        self.state = ta.TwoPlayerState(num_players=num_players, seed=seed)
        self.turn_count = 0

        # Reset repetition tracking
        self.last_move = {0: None, 1: None}
        self.repetition_count = {0: 0, 1: 0}

        # Fresh board & lakes
        self.board = [[None for _ in range(self.size)] for _ in range(self.size)]
        self.lakes = self._generate_lakes()
        self.player_pieces = {0: [], 1: []}

        # Populate board with initial piece layout
        self.board = self._populate_board()

        rendered = self._render_board(player_id=None, full_board=True)
        state_info = {
            "board": self.board,
            "player_pieces": self.player_pieces,
            "rendered_board": rendered,
        }

        self.state.reset(
            game_state=state_info,
            player_prompt_function=self._generate_player_prompt,
        )

        # First observation for Player 0
        self._observe_current_state()

    # ------------------------------------------------------------------
    # Lake generation
    # ------------------------------------------------------------------
    def _generate_lakes(self) -> List[Tuple[int, int]]:
        """
        Generate lake positions depending on board size.

        - 6×6 → two diagonal lakes in the central area.
        - 7×7, 8×8, 9×9 → two symmetric 2×2 lake clusters in the neutral zone
          (between the two players' setup areas).
        """

        size = self.size

        # For 6x6 use a simple symmetric pattern in the middle
        if size == 6:
            return [(2, 2), (3, 3)]

        # Setup rows for mid-size boards
        if size == 7:
            setup_rows = 2
        elif size == 8:
            setup_rows = 3
        elif size == 9:
            setup_rows = 3
        else:
            # Fallback (not used with current constraints)
            setup_rows = max(2, size // 4)

        neutral_start = setup_rows
        neutral_end = size - setup_rows - 1
        mid_row = (neutral_start + neutral_end) // 2

        lakes = set()
        mid_col = size // 2
        delta = max(2, size // 4)

        # Left 2×2 cluster
        for r in [mid_row - 1, mid_row]:
            for c in [mid_col - delta - 1, mid_col - delta]:
                if 0 <= r < size and 0 <= c < size:
                    lakes.add((r, c))

        # Right 2×2 cluster
        for r in [mid_row - 1, mid_row]:
            for c in [mid_col + delta, mid_col + delta + 1]:
                if 0 <= r < size and 0 <= c < size:
                    lakes.add((r, c))

        # Ensure lakes do not overlap the setup rows
        filtered = [
            (r, c)
            for (r, c) in lakes
            if not (r < setup_rows or r >= size - setup_rows)
        ]
        return filtered

    # ------------------------------------------------------------------
    # Piece count generation
    # ------------------------------------------------------------------
    def _generate_piece_counts(self) -> Dict[str, int]:
        """
        Compute how many pieces of each rank each player receives.

        Logic:
        - Start with 1 of each rank.
        - If we have more pieces than slots in the setup area, remove pieces
          following a priority.
        - If we have fewer pieces than slots, fill remaining slots using
          a balanced filler pattern:
            Sergeant → Scout → Miner → Bomb
        """

        ranks = [
            "Flag", "Bomb", "Spy", "Scout", "Miner",
            "Sergeant", "Lieutenant", "Captain", "Major",
            "Colonel", "General", "Marshal",
        ]

        # Setup rows based on board size
        if self.size in (6, 7):
            setup_rows = 2
        elif self.size in (8, 9):
            setup_rows = 3
        else:
            setup_rows = max(2, self.size // 4)

        slots = self.size * setup_rows  # slots per player
        counts = {r: 1 for r in ranks}
        total = len(ranks)

        # Remove ranks if too many pieces for available slots
        removal_priority = ["Spy", "General", "Colonel", "Major", "Captain"]
        i = 0
        while total > slots:
            r = removal_priority[i % len(removal_priority)]
            if counts[r] > 0:
                counts[r] -= 1
                total -= 1
            i += 1

        # Fill remaining slots with balanced filler
        filler = ["Sergeant", "Scout", "Miner", "Bomb"]
        i = 0
        while total < slots:
            p = filler[i % len(filler)]
            counts[p] += 1
            total += 1
            i += 1

        return counts

    # ------------------------------------------------------------------
    # Prompt generation
    # ------------------------------------------------------------------
    def _generate_player_prompt(self, player_id: int, game_state: Dict[str, Any]):
        return (
            f"You are Player {player_id} in Stratego (custom board size {self.size}x{self.size}).\n"
            "Your goal is to capture the enemy Flag or eliminate all of their movable pieces.\n"
            "\n"
            "Movement rules:\n"
            "- You may move one piece per turn.\n"
            "- Most pieces move exactly one square orthogonally (up, down, left, right).\n"
            "- Scouts may move multiple empty squares in a straight line.\n"
            "- Bombs and Flags cannot move.\n"
            "\n"
            "Battle rules:\n"
            "- Higher rank defeats lower rank.\n"
            "- Equal ranks eliminate both pieces.\n"
            "- Miner defeats Bomb.\n"
            "- Spy defeats Marshal when the Spy attacks.\n"
            "\n"
            "Two-Squares Rule (repetition):\n"
            "- You may not move back and forth between the same two squares\n"
            "  more than 3 times in a row (e.g., [A0 B0], [B0 A0], [A0 B0], [B0 A0] is illegal).\n"
            "\n"
            "Move format:\n"
            "- You MUST output exactly one move: [Source Destination]\n"
            "- Example: [C2 C3]\n"
            "\n"
            "Legend:\n"
            "- Your pieces: uppercase abbreviations.\n"
            "- Enemy unknown pieces: ?\n"
            "- Lakes (impassable): ~\n"
            "\n"
            "Here is the current board:\n"
        )

    # ------------------------------------------------------------------
    # Observation & move generation
    # ------------------------------------------------------------------
    def _observe_current_state(self):
        """Compute all legal moves for the current player and send them to the agent."""

        player_id = self.state.current_player_id
        moves: List[str] = []

        for r in range(self.size):
            for c in range(self.size):
                piece = self.board[r][c]
                if not (isinstance(piece, dict) and piece["player"] == player_id):
                    continue

                rank = piece["rank"].lower()
                if rank in ["bomb", "flag"]:
                    continue

                is_scout = rank == "scout"

                # Directions: N, S, W, E
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    if is_scout:
                        dist = 1
                        while True:
                            nr = r + dr * dist
                            nc = c + dc * dist
                            if not (0 <= nr < self.size and 0 <= nc < self.size):
                                break
                            if (nr, nc) in self.lakes:
                                break

                            target = self.board[nr][nc]
                            if target is None:
                                moves.append(f"[{chr(65 + r)}{c} {chr(65 + nr)}{nc}]")
                                dist += 1
                            elif isinstance(target, dict) and target["player"] != player_id:
                                moves.append(f"[{chr(65 + r)}{c} {chr(65 + nr)}{nc}]")
                                break
                            else:
                                break
                    else:
                        nr = r + dr
                        nc = c + dc
                        if not (0 <= nr < self.size and 0 <= nc < self.size):
                            continue
                        if (nr, nc) in self.lakes:
                            continue

                        target = self.board[nr][nc]
                        if target is None or (
                            isinstance(target, dict) and target["player"] != player_id
                        ):
                            moves.append(f"[{chr(65 + r)}{c} {chr(65 + nr)}{nc}]")

        # Save number of available moves like in DuelEnv
        self.state.game_state[f"available_moves_p{player_id}"] = len(moves)

        msg = (
            "Current Board:\n\n"
            f"{self._render_board(player_id, full_board=False)}\n"
            "Available Moves: " + (", ".join(moves) if moves else "NONE")
        )

        self.state.add_observation(
            message=msg,
            observation_type=ta.ObservationType.GAME_BOARD,
        )

    # ------------------------------------------------------------------
    # Board rendering
    # ------------------------------------------------------------------
    def _render_board(self, player_id: Optional[int], full_board: bool = False) -> str:
        abbreviations = {
            "Flag": "FL", "Bomb": "BM", "Spy": "SP", "Scout": "SC",
            "Miner": "MN", "Sergeant": "SG", "Lieutenant": "LT",
            "Captain": "CP", "Major": "MJ", "Colonel": "CL",
            "General": "GN", "Marshal": "MS",
        }

        lines: List[str] = []
        # Header with column indices
        lines.append("   " + " ".join(f"{i:>3}" for i in range(self.size)) + "\n")

        for r in range(self.size):
            row_label = chr(65 + r)
            row_str = f"{row_label:<3}"
            for c in range(self.size):
                pos = (r, c)

                if pos in self.lakes:
                    row_str += "  ~ "
                    continue

                cell = self.board[r][c]
                if cell is None:
                    row_str += "  . "
                else:
                    code = abbreviations[cell["rank"]]
                    owner = cell["player"]
                    if full_board or (player_id is not None and owner == player_id):
                        row_str += f" {code.upper()} "
                    else:
                        row_str += "  ? "
            lines.append(row_str + "\n")

        return "".join(lines)

    # ------------------------------------------------------------------
    # Initial board population
    # ------------------------------------------------------------------
    def _populate_board(self) -> List[List[Optional[Dict[str, Any]]]]:
        """
        Create a complete initial board setup.

        Strategy:
        - Each player has a setup area (back rows + front rows).
        - Flag is placed on the outermost row.
        - Bombs are placed around the Flag when possible.
        - Spy is placed in front rows if possible.
        - Marshal & General are placed centrally in back rows.
        - Remaining pieces are distributed randomly.
        """

        size = self.size

        if size in (6, 7):
            setup_rows = 2
        elif size in (8, 9):
            setup_rows = 3
        else:
            setup_rows = max(2, size // 3)

        board = [[None for _ in range(size)] for _ in range(size)]

        for player in (0, 1):
            counts = self._generate_piece_counts()

            half = max(1, setup_rows // 2)

            if player == 0:
                back_rows = range(0, half)
                front_rows = range(half, setup_rows)
            else:
                start = size - setup_rows
                back_rows = range(start, start + half)
                front_rows = range(start + half, start + setup_rows)

            free_back = [
                (r, c)
                for r in back_rows
                for c in range(size)
                if (r, c) not in self.lakes
            ]
            free_front = [
                (r, c)
                for r in front_rows
                for c in range(size)
                if (r, c) not in self.lakes
            ]

            random.shuffle(free_back)
            random.shuffle(free_front)

            # --------------------- FLAG placement ---------------------
            flag_row = 0 if player == 0 else size - 1
            flag_candidates = [
                (flag_row, c)
                for c in range(size)
                if (flag_row, c) not in self.lakes and board[flag_row][c] is None
            ]

            if not flag_candidates:
                flag_candidates = free_back[:]

            fx, fy = random.choice(flag_candidates)
            board[fx][fy] = {"rank": "Flag", "player": player}
            self.player_pieces[player].append((fx, fy))

            if (fx, fy) in free_back:
                free_back.remove((fx, fy))
            if (fx, fy) in free_front:
                free_front.remove((fx, fy))

            counts.pop("Flag", None)

            # --------------------- BOMB placement ---------------------
            bombs = counts.pop("Bomb", 0)

            # Prefer bombs adjacent to flag
            for r, c in [(fx + 1, fy), (fx - 1, fy), (fx, fy + 1), (fx, fy - 1)]:
                if bombs <= 0:
                    break
                if (
                    0 <= r < size
                    and 0 <= c < size
                    and (r, c) not in self.lakes
                    and board[r][c] is None
                ):
                    board[r][c] = {"rank": "Bomb", "player": player}
                    self.player_pieces[player].append((r, c))
                    bombs -= 1
                    if (r, c) in free_back:
                        free_back.remove((r, c))
                    if (r, c) in free_front:
                        free_front.remove((r, c))

            # Remaining bombs in back/front slots
            while bombs > 0 and (free_back or free_front):
                if free_back:
                    r, c = free_back.pop()
                else:
                    r, c = free_front.pop()
                board[r][c] = {"rank": "Bomb", "player": player}
                self.player_pieces[player].append((r, c))
                bombs -= 1

            # --------------------- SPY placement ----------------------
            if counts.get("Spy", 0) > 0:
                if free_front:
                    r, c = free_front.pop()
                else:
                    r, c = free_back.pop()
                board[r][c] = {"rank": "Spy", "player": player}
                self.player_pieces[player].append((r, c))
            counts.pop("Spy", None)

            # --------- DEFENSIVE Marshal & General placement ---------
            for rank_name in ("Marshal", "General"):
                if counts.get(rank_name, 0) > 0:
                    mid_cols = (
                        [size // 2]
                        if size <= 6
                        else [
                            max(0, size // 2 - 1),
                            size // 2,
                            min(size - 1, size // 2 + 1),
                        ]
                    )
                    placed = False
                    for r in back_rows:
                        for c in mid_cols:
                            if (r, c) in free_back:
                                board[r][c] = {"rank": rank_name, "player": player}
                                self.player_pieces[player].append((r, c))
                                free_back.remove((r, c))
                                placed = True
                                break
                        if placed:
                            break
                counts.pop(rank_name, None)

            # --------------------- Remaining pieces -------------------
            slots = free_front + free_back
            remaining_ranks: List[str] = []
            for rnk, cnt in counts.items():
                remaining_ranks.extend([rnk] * cnt)

            random.shuffle(remaining_ranks)

            # Fill with remaining defined ranks
            while slots and remaining_ranks:
                r, c = slots.pop()
                rank_name = remaining_ranks.pop()
                board[r][c] = {"rank": rank_name, "player": player}
                self.player_pieces[player].append((r, c))

            # Any extra free slot: fill with Scouts (mobile pieces)
            while slots:
                r, c = slots.pop()
                board[r][c] = {"rank": "Scout", "player": player}
                self.player_pieces[player].append((r, c))

        # Apply lakes as "~"
        for r, c in self.lakes:
            board[r][c] = "~"

        return board

    # ------------------------------------------------------------------
    # Move validation
    # ------------------------------------------------------------------
    def _validate_move(
        self, player_id: int, src_r: int, src_c: int, dst_r: int, dst_c: int
    ) -> bool:
        """Validate movement rules for a single move."""

        size = self.size

        # Bounds
        if not (
            0 <= src_r < size and 0 <= src_c < size and
            0 <= dst_r < size and 0 <= dst_c < size
        ):
            self.state.set_invalid_move("Coordinates out of bounds.")
            return False

        piece = self.board[src_r][src_c]
        if not (isinstance(piece, dict) and piece["player"] == player_id):
            self.state.set_invalid_move("You must move one of your own pieces.")
            return False

        rank = piece["rank"].lower()

        # Bomb / Flag cannot move
        if rank in ["bomb", "flag"]:
            self.state.set_invalid_move("Bombs and Flags cannot move.")
            return False

        # Cannot move into a lake
        if (dst_r, dst_c) in self.lakes:
            self.state.set_invalid_move("Cannot move into a lake.")
            return False

        dst_piece = self.board[dst_r][dst_c]

        # Cannot move onto own piece
        if isinstance(dst_piece, dict) and dst_piece["player"] == player_id:
            self.state.set_invalid_move("Cannot move onto your own piece.")
            return False

        # Scout long movement
        if rank == "scout":
            if not (src_r == dst_r or src_c == dst_c):
                self.state.set_invalid_move("Scouts must move in a straight line.")
                return False

            # Path must be clear
            if src_r == dst_r:
                for c in range(min(src_c, dst_c) + 1, max(src_c, dst_c)):
                    if self.board[src_r][c] is not None:
                        self.state.set_invalid_move("Scout path is blocked.")
                        return False
            if src_c == dst_c:
                for r in range(min(src_r, dst_r) + 1, max(src_r, dst_r)):
                    if self.board[r][src_c] is not None:
                        self.state.set_invalid_move("Scout path is blocked.")
                        return False

        else:
            # Non-scout: exactly one orthogonal step
            if abs(src_r - dst_r) + abs(src_c - dst_c) != 1:
                self.state.set_invalid_move(
                    "Non-scout pieces must move exactly one square orthogonally."
                )
                return False

        return True

    # ------------------------------------------------------------------
    # Step: apply action
    # ------------------------------------------------------------------
    def step(self, action: str) -> Tuple[bool, ta.Info]:
        """
        Execute a player's action:
        - Check no-move condition (like DuelEnv)
        - Parse move
        - Validate movement rules
        - Apply Two-Squares Rule
        - Resolve combat
        - Check win conditions
        """

        self.turn_count += 1
        player_id = self.state.current_player_id

        # --- No-move rule (same idea as DuelEnv) ---
        # If the previous observation said we had 0 legal moves, we immediately end.
        if self.state.game_state.get(f"available_moves_p{player_id}", 1) == 0:
            # Opponent wins if they still have movable pieces, otherwise draw
            if self._has_movable_pieces(1 - player_id):
                winner = 1 - player_id
                reason = "No moves available. Opponent still has movable pieces."
            else:
                winner = -1
                reason = "No moves for either player. Stalemate."
            self.state.set_winner(player_id=winner, reason=reason)
            return self.state.step()

        # Log the raw action from the current player
        self.state.add_observation(
            from_id=player_id,
            to_id=player_id,
            message=action,
            observation_type=ta.ObservationType.PLAYER_ACTION,
        )

        # Parse move of the form [A0 B0] (dynamic letters/numbers, bounds checked later)
        match = re.search(
            r"\[([A-Z])(\d+) ([A-Z])(\d+)\]", action, re.IGNORECASE
        )
        if not match:
            self.state.set_invalid_move("Invalid move format. Expected: [A0 B0].")
            return self.state.step()

        src_row, src_col, dst_row, dst_col = match.groups()
        src_r = ord(src_row.upper()) - 65
        src_c = int(src_col)
        dst_r = ord(dst_row.upper()) - 65
        dst_c = int(dst_col)

        # Validate movement rules
        if not self._validate_move(player_id, src_r, src_c, dst_r, dst_c):
            return self.state.step()

        # ------------------------------------------------------
        # Two-Squares Rule (back-and-forth repetition) — same logic as DuelEnv
        # ------------------------------------------------------
        is_repetition = False
        last = self.last_move[player_id]

        # If current move is exact reverse of last move (A->B, then B->A)
        if last is not None:
            last_sr, last_sc, last_dr, last_dc = last
            if (
                src_r == last_dr and src_c == last_dc and
                dst_r == last_sr and dst_c == last_sc
            ):
                is_repetition = True

        if is_repetition:
            self.repetition_count[player_id] += 1
        else:
            # New path → reset repetition count
            self.repetition_count[player_id] = 0

        # Store current move as last move
        self.last_move[player_id] = (src_r, src_c, dst_r, dst_c)

        # If repetition exceeds allowed limit, move is illegal
        if self.repetition_count[player_id] >= 3:
            self.state.set_invalid_move(
                "Illegal Repetition: Cannot move back and forth between the same "
                "two squares more than 3 consecutive times."
            )
            return self.state.step()

        # ------------------------------------------------------
        # APPLY MOVE + RESOLVE BATTLE
        # ------------------------------------------------------
        attacker = self.board[src_r][src_c]
        defender = self.board[dst_r][dst_c]

        # Remove attacker from original position
        self.board[src_r][src_c] = None
        self.player_pieces[player_id].remove((src_r, src_c))

        # Case 1: Moving into an empty square
        if defender is None:
            self.board[dst_r][dst_c] = attacker
            self.player_pieces[player_id].append((dst_r, dst_c))

        else:
            # Any battle resets repetition tracking for that player
            self.repetition_count[player_id] = 0
            self.last_move[player_id] = None

            atk_rank_val = self.piece_ranks[attacker["rank"]]
            def_rank_val = self.piece_ranks[defender["rank"]]

            # Flag capture → immediate win
            if defender["rank"] == "Flag":
                self.board[dst_r][dst_c] = attacker
                self.player_pieces[player_id].append((dst_r, dst_c))
                self.player_pieces[1 - player_id].remove((dst_r, dst_c))
                reason = f"Player {player_id} captured the enemy Flag!"
                self.state.set_winner(player_id=player_id, reason=reason)
                self.state.game_state["rendered_board"] = self._render_board(
                    player_id=player_id, full_board=True
                )
                return self.state.step()

            # Spy vs Marshal special rule
            if attacker["rank"] == "Spy" and defender["rank"] == "Marshal":
                self.board[dst_r][dst_c] = attacker
                self.player_pieces[player_id].append((dst_r, dst_c))
                self.player_pieces[1 - player_id].remove((dst_r, dst_c))

            # Defender is Bomb
            elif defender["rank"] == "Bomb":
                if attacker["rank"] == "Miner":
                    # Miner defuses Bomb
                    self.board[dst_r][dst_c] = attacker
                    self.player_pieces[player_id].append((dst_r, dst_c))
                    self.player_pieces[1 - player_id].remove((dst_r, dst_c))
                else:
                    # Bomb wins, attacker is simply removed
                    pass

            # Normal numeric comparison
            else:
                if atk_rank_val == def_rank_val:
                    # Both pieces are removed
                    self.board[dst_r][dst_c] = None
                    self.player_pieces[1 - player_id].remove((dst_r, dst_c))
                elif atk_rank_val > def_rank_val:
                    # Attacker wins and occupies the square
                    self.board[dst_r][dst_c] = attacker
                    self.player_pieces[player_id].append((dst_r, dst_c))
                    self.player_pieces[1 - player_id].remove((dst_r, dst_c))
                else:
                    # Defender wins, attacker already removed above
                    pass

        # ------------------------------------------------------
        # Victory check: no movable pieces left / stalemate / turn limit
        # ------------------------------------------------------
        winner = self._check_winner()
        if winner is not None:
            self.state.set_winner(
                player_id=winner,
                reason=f"Player {winner} wins! Opponent has no movable pieces left.",
            )
        elif self._check_stalemate():
            self.state.set_winner(player_id=-1, reason="Stalemate: no movable pieces.")
        elif self.turn_count > 1000:
            self.state.set_winner(player_id=-1, reason="Turn limit reached.")

        # Update rendered board
        self.state.game_state["rendered_board"] = self._render_board(
            player_id=player_id, full_board=True
        )

        done, info = self.state.step()

        # If the game is not over, give a fresh observation to the next player
        if not done:
            self._observe_current_state()

        return done, info

    # ------------------------------------------------------------------
    # Winner detection & helpers
    # ------------------------------------------------------------------
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

    def _check_winner(self) -> Optional[int]:
        """
        A player loses if they have no movable pieces left
        (i.e., they only have Bombs and/or Flag or nothing).
        """
<<<<<<< HEAD
        for player in range(2):
            if all([self.board[row][col]['rank'] in ['Bomb', 'Flag'] for row, col in self.player_pieces[player]]):
                return 1 - player
        return None

        for pid in (0, 1):
            if not self._has_movable_pieces(pid):
                return 1 - pid
        return None

    def _check_stalemate(self) -> bool:
        """Stalemate if neither player has any movable pieces."""
        return not self._has_movable_pieces(0) and not self._has_movable_pieces(1)