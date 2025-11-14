import random
import re
import textarena as ta
from textarena.Stratego.env import StrategoEnv as BaseEnv


class CustomStrategoEnv(BaseEnv):
    """
    A size-configurable Stratego environment that extends the original TextArena implementation.
    It overrides only what depends on board size and initial setup, while keeping all battle
    and rules logic exactly as in the original engine.
    """

    def __init__(self, size: int = 10):
        self.size = size            # store board dimension
        super().__init__()          # calls original StrategoEnv constructor

        # Replace the default 10×10 board with custom size
        self.board = [[None for _ in range(size)] for _ in range(size)]

        # Generate lakes suitable for the given board size
        self.lakes = self._generate_lakes()

        # Scale piece counts to size
        self.piece_counts = self._generate_piece_counts()

        # Reinitialize containers
        self.player_pieces = {0: [], 1: []}


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


    # -------------------------------------------------------------------------
    # 3) RESET (override because original uses fixed 10×10 rows)
    # -------------------------------------------------------------------------
    def reset(self, num_players: int = 2, seed=None):
        """Reset but repopulate board using our custom placement logic."""
        self.state = ta.TwoPlayerState(num_players=num_players, seed=seed)
        self.player_pieces = {0: [], 1: []}

        # custom board population
        self.board = self._populate_board()

        rendered = self._render_board(player_id=None, full_board=True)
        state_info = {
            "board": self.board,
            "player_pieces": self.player_pieces,
            "rendered_board": rendered,
        }

        self.state.reset(
            game_state=state_info,
            player_prompt_function=self._generate_player_prompt
        )
        self._observe_current_state()


    # -------------------------------------------------------------------------
    # 4) POPULATE BOARD (size-aware)
    # -------------------------------------------------------------------------
    def _populate_board(self):
        """
        Simplified placement:
        - Top `setup_rows` belong to Player 0
        - Bottom `setup_rows` belong to Player 1
        - No lakes on player's starting rows
        - Random placement within each player's zone
        """
        size = self.size
        setup_rows = max(2, size // 4)

        # clear board
        board = [[None for _ in range(size)] for _ in range(size)]

        for player in (0, 1):
            if player == 0:
                rows_allowed = range(0, setup_rows)
            else:
                rows_allowed = range(size - setup_rows, size)

            # place flag
            placed_flag = False
            while not placed_flag:
                r = random.choice(list(rows_allowed))
                c = random.randint(0, size - 1)
                if (r, c) not in self.lakes and board[r][c] is None:
                    board[r][c] = {"rank": "Flag", "player": player}
                    self.player_pieces[player].append((r, c))
                    placed_flag = True

            # place bombs
            bombs_to_place = self.piece_counts["Bomb"]
            while bombs_to_place > 0:
                r = random.choice(list(rows_allowed))
                c = random.randint(0, size - 1)
                if (r, c) not in self.lakes and board[r][c] is None:
                    board[r][c] = {"rank": "Bomb", "player": player}
                    self.player_pieces[player].append((r, c))
                    bombs_to_place -= 1

            # place remaining pieces
            for piece, count in self.piece_counts.items():
                if piece in ("Flag", "Bomb"):
                    continue
                for _ in range(count):
                    while True:
                        r = random.choice(list(rows_allowed))
                        c = random.randint(0, size - 1)
                        if (r, c) not in self.lakes and board[r][c] is None:
                            board[r][c] = {"rank": piece, "player": player}
                            self.player_pieces[player].append((r, c))
                            break

        # place lakes
        for r, c in self.lakes:
            board[r][c] = "~"

        return board


    # -------------------------------------------------------------------------
    # 5) VALIDATION OVERRIDE (only size-boundaries change)
    # -------------------------------------------------------------------------
    def _validate_move(self, player_id, src_r, src_c, dst_r, dst_c):
        size = self.size

        if not (0 <= src_r < size and 0 <= src_c < size and
                0 <= dst_r < size and 0 <= dst_c < size):
            self.state.set_invalid_move("Invalid: out of board.")
            return False

        return super()._validate_move(player_id, src_r, src_c, dst_r, dst_c)
