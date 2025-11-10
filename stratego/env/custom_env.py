import random

class CustomStrategoEnv:
    """
    Versiune simplificată de Stratego cu simboluri reale.
    Tabla se poate redimensiona, iar piesele sunt distribuite automat.
    """

    def __init__(self, env_id="Stratego-v0", board_size=10, **kwargs):
        self.env_id = env_id
        self.board_size = board_size
        self.turn = 0
        self.done = False
        self.players = [0, 1]
        self.symbols = ["A", "B"]
        self.board = []
        self.reset()

    # ---------------------- BOARD SETUP ----------------------
    def _generate_board(self):
        n = self.board_size
        board = [["." for _ in range(n)] for _ in range(n)]

        # Lista de piese tipice Stratego
        piece_types = ["BM", "FL", "MN", "SG", "LT", "CP", "MJ", "SP", "GN", "CL"]

        # numărul de piese per jucător crește odată cu dimensiunea tablei
        num_pieces = max(6, n * n // 6)

        # selectăm piese aleatoriu, cu repetiție
        p0_pieces = [random.choice(piece_types) for _ in range(num_pieces)]
        p1_pieces = [random.choice(piece_types) for _ in range(num_pieces)]

        # jumătate superioară — player 0
        for i in range(num_pieces):
            row = i // n
            col = i % n
            if row < n // 2:
                board[row][col] = p0_pieces[i]

        # jumătate inferioară — player 1
        for i in range(num_pieces):
            row = n - 1 - (i // n)
            col = i % n
            if row >= n // 2:
                board[row][col] = p1_pieces[i]

        # adăugăm câteva lacuri (~) dacă tabla e suficient de mare
        if n >= 8:
            for i in range(n // 3, n // 3 + 2):
                for j in range(n // 3, n // 3 + 2):
                    board[i][j] = "~"
                    board[n - i - 1][n - j - 1] = "~"

        return board

    # ---------------------- API METHODS ----------------------
    def reset(self, num_players=2):
        self.turn = 0
        self.done = False
        self.board = self._generate_board()
        return self.get_observation()

    def get_observation(self):
        player = self.turn % 2
        board_text = "\n".join([" ".join(row) for row in self.board])
        legal_moves = self._get_legal_moves(player)
        obs = (
            f"Player {player} ({self.symbols[player]}) turn.\n"
            f"Board:\n{board_text}\n\n"
            f"Legal moves:\n{', '.join(legal_moves)}"
        )
        return player, obs

    def step(self, action):
        moved = self._apply_move(action)
        if not moved:
            pass  # dacă mutarea e invalidă, doar trecem rândul

        # verificăm dacă un jucător mai are piese
        half = self.board_size // 2
        top_pieces = sum(cell not in [".", "~"] for row in self.board[:half] for cell in row)
        bottom_pieces = sum(cell not in [".", "~"] for row in self.board[half:] for cell in row)

        if top_pieces == 0 or bottom_pieces == 0:
            self.done = True

        self.turn += 1
        return self.done, {}

    def close(self):
        rewards = {0: 0, 1: 0}
        info = {"board_size": self.board_size}
        return rewards, info

    # ---------------------- MOVE LOGIC ----------------------
    def _get_legal_moves(self, player):
        n = self.board_size
        moves = []
        sym = self.symbols[player]
        dirs = [(-1, 0), (1, 0), (0, -1), (0, 1)]

        for i in range(n):
            for j in range(n):
                cell = self.board[i][j]
                if cell != "." and cell != "~":  # piesă reală
                    for di, dj in dirs:
                        ni, nj = i + di, j + dj
                        if 0 <= ni < n and 0 <= nj < n:
                            if self.board[ni][nj] == ".":
                                move = f"{self._pos_to_label(i, j)} {self._pos_to_label(ni, nj)}"
                                moves.append(move)
        random.shuffle(moves)
        return moves[:10]

    def _apply_move(self, action):
        parts = action.strip().split()
        if len(parts) != 2:
            return False
        src_label, dst_label = parts
        si, sj = self._label_to_pos(src_label)
        di, dj = self._label_to_pos(dst_label)

        n = self.board_size
        if not (0 <= si < n and 0 <= sj < n and 0 <= di < n and 0 <= dj < n):
            return False
        if self.board[si][sj] in [".", "~"]:
            return False

        self.board[di][dj] = self.board[si][sj]
        self.board[si][sj] = "."
        return True

    # ---------------------- UTILS ----------------------
    def _pos_to_label(self, i, j):
        return f"{chr(65 + i)}{j}"

    def _label_to_pos(self, label):
        try:
            row = ord(label[0].upper()) - 65
            col = int(label[1:])
            return row, col
        except Exception:
            return -1, -1
