import random
import re
from typing import Any, Dict, Optional, Tuple
import textarena as ta


class StrategoCustomEnv(ta.Env):
    

    """
    A size-configurable Stratego environment that extends the original TextArena implementation.
    It overrides only what depends on board size and initial setup, while keeping all battle
    and rules logic exactly as in the original engine.
    """

    def __init__(self, size: int = 10):
        self.size = size            # store board dimension
        # super().__init__()        # calls original StrategoEnv constructor
        
        # Replace the default 10×10 board with custom size
        self.board = [[None for _ in range(size)] for _ in range(size)]

        # Generate lakes suitable for the given board size
        self.lakes = self._generate_lakes()

        # Scale piece counts to size
        self.piece_counts = self._generate_piece_counts()
        
        self.piece_ranks = {
            'Flag': 0, 'Bomb': 11, 'Spy': 1, 'Scout': 2, 'Miner': 3,
            'Sergeant': 4, 'Lieutenant': 5, 'Captain': 6, 'Major': 7,
            'Colonel': 8, 'General': 9, 'Marshal': 10
        }

        # Reinitialize containers
        self.player_pieces = {0: [], 1: []}

    @property
    def terminal_render_keys(self):
        return ["rendered_board"]

    # 1) LAKES
    def _generate_lakes(self):
        size = self.size

        # special case (6x6), only 2 lakes
        if size == 6:
            mid = size // 2
            return [(mid-1, mid), (mid, mid-1)]


        # rows for pawns
        if size == 7:
            setup_rows = 2
        elif size == 8:
            setup_rows = 2
        elif size == 9:
            setup_rows = 3
        elif size == 10:
            setup_rows = 4
        else:
            setup_rows = max(2, size // 4)

        # neutral zone
        neutral_start = setup_rows
        neutral_end = size - setup_rows - 1
        mid_row = (neutral_start + neutral_end) // 2

        lakes = set()

        # horizontal offset
        mid_col = size // 2
        delta = max(2, size // 4)   # distance between clusters

        # left cluster 2x2
        for r in [mid_row - 1, mid_row]:
            for c in [mid_col - delta - 1, mid_col - delta]:
                lakes.add((r, c))

        # right cluster 2x2
        for r in [mid_row - 1, mid_row]:
            for c in [mid_col + delta, mid_col + delta + 1]:
                lakes.add((r, c))

        # ensure lakes do not enter player zones
        lakes_final = [
            (r,c) for (r,c) in lakes
            if not (r < setup_rows or r >= size - setup_rows)
        ]

        return lakes_final






    #2) PIECE COUNTS
    def _generate_piece_counts(self):
        ranks = [
            'Flag','Bomb','Spy','Scout','Miner',
            'Sergeant','Lieutenant','Captain','Major',
            'Colonel','General','Marshal'
        ]

        setup_rows = max(2, self.size // 4)
        slots = self.size * setup_rows   # available slots per player

        # start with one of each
        counts = {r: 1 for r in ranks}

        # total number of pieces
        total = len(ranks)

        # reduce pieces if too many
        if total > slots:
            print("WARNING: too many ranks, trimming")

        # preferential strategies for removing pieces
        remove_priority = ['Spy','General','Colonel','Major','Captain']

        i = 0
        while total > slots:
            p = remove_priority[i % len(remove_priority)]
            if counts[p] > 0:
                counts[p] -= 1
                total -= 1
            i += 1

        # if there is still space — add bombs and scouts
        filler = ['Bomb','Scout','Miner','Sergeant']
        i = 0
        while total < slots:
            p = filler[i % len(filler)]
            counts[p] += 1
            total += 1
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

        ## check if the game is over
        if self._check_winner():
            reason=f"Player {self._check_winner()} wins! Player {1 - self._check_winner()} has no more movable pieces."
            self.state.set_winner(player_id=self._check_winner(), reason=reason)

        ## update the rendered board
        self.state.game_state["rendered_board"] = self._render_board(player_id=player_id, full_board=True)

        result = self.state.step()
        self._observe_current_state()
        return result
    
    # 3) RESET (override because original uses fixed 10×10 rows)
    
    def reset(self, num_players: int, seed: Optional[int]=None):
        """Reset but repopulate board using our custom placement logic."""
        self.state = ta.TwoPlayerState(num_players=num_players, seed=seed)

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

    def _generate_player_prompt(self, player_id: int, game_state: Dict[str, Any]):
        """
        Generates the player prompt for the current player.

        Args:
            player_id (int): The ID of the current player.
            game_state (Dict[str, Any]): The current game state.
        """
        prompt = (
            f"You are Player {player_id} in Stratego.\n"
            "Your goal is to capture your opponent's Flag or eliminate all of their movable pieces.\n"
            "Your army has been placed for you on the board, including your Flag, Bombs, and other pieces of varying ranks.\n"
            "\n"
            "### Gameplay Instructions\n"
            "1. **Movement Rules:**\n"
            "   - On your turn, you can move one piece by one step to an adjacent square (up, down, left, or right) that is already occupied with your pieces.\n"
            "   - Example: A piece can move from A1 to B1 or A1 to A2 if B1 and A2 are not placed with the player's own pieces.\n"
            "   - If the selected piece is a Bomb or a Flag, it cannot be moved.\n"
            # "   - **Scout Movement:** Scouts, on the other hand, can move multiple steps in a straight line (horizontally or vertically), but strictly only on one condition.\n"
            # "       - The condition is that Scouts cannot jump over any piece (your own or your opponent's).\n"
            # "       - Example: If there is a piece between the Scout and its destination, the Scout cannot move to the destination.\n"
            # "       - This will be indicated as an invalid move which makes you lose the game.\n"
            "2. **Battles:**\n"
            "   - If you move onto a square occupied by an opponent's piece, then a battle will occur:\n"
            "     - The piece with the higher rank wins and eliminates the opponent's piece.\n"
            "     - If the ranks are equal, both pieces are removed from the board.\n"
            "     - **Special Cases:**\n"
            "       - Bombs eliminate most attacking pieces except Miners, which defuse Bombs.\n"
            "       - Spies can defeat the Marshal if the Spy attacks first but lose to all other pieces.\n"
            "3. **Strategic Goals:**\n"
            "   - Identify your opponent's pieces through their movements and battles.\n"
            "   - Protect your Flag while attempting to capture your opponent's Flag.\n"
            "   - Use Scouts strategically to gain information about your opponent's pieces and attack weak ones.\n"
            "\n"
            "### How to Make a Move:\n"
            "1. Specify the coordinates of the piece you want to move and its destination.\n"
            "2. Use the format: [A0 B0], where A0 is the source position, and B0 is the destination.\n"
            "   - Example: To move a piece from row 0, column 0 to row 1, column 0, input [A0 B0].\n"
            "3. Ensure the destination is valid according to the movement rules above.\n"
            "\n"
            "### Important Notes:\n"
            "- The board will show your pieces and their positions, e.g. MN, MS.\n"
            "- The board will also show known positions of your opponent's pieces without revealing their ranks, e.g. ?.\n"
            "- Grids with ~ are lakes and cannot be moved onto.\n"
            "- As a suggestion, start your game by moving your pieces that are on the front lines to gain information about your opponent's pieces. Player 0 and player 1's frontlines are row D and G respectively.\n"
            "\n"
            "Here is the current board state:\n"
        )
        return prompt

    def _observe_current_state(self):
        """
        Observe the current state of the game and update the state with the rendered board
        and gives the available moves for the current player.
        """
        player_id = self.state.current_player_id
        available_moves = []

        for row in range(self.size):
            for col in range(self.size):
                piece = self.board[row][col]
                if isinstance(piece, dict) and piece['player'] == player_id:
                    # Skip immovable pieces
                    if piece['rank'].lower() in ['bomb', 'flag']:
                        continue

                    # Check if this is a scout (can move multiple squares)
                    is_scout = piece['rank'].lower() == 'scout'
                    
                    # Check all four directions
                    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        if is_scout:
                            # Scout can move multiple squares in this direction
                            distance = 1
                            while True:
                                new_row = row + (dr * distance)
                                new_col = col + (dc * distance)
                                
                                # Check if still within board bounds
                                if not (0 <= new_row < self.size and 0 <= new_col < self.size):
                                    break
                                
                                target = self.board[new_row][new_col]
                                
                                if target is None:
                                    # Empty square - scout can move here and continue
                                    available_moves.append(f"[{chr(row + 65)}{col} {chr(new_row + 65)}{new_col}]")
                                    distance += 1
                                elif isinstance(target, dict) and target['player'] != player_id:
                                    # Enemy piece - scout can attack but cannot continue past
                                    available_moves.append(f"[{chr(row + 65)}{col} {chr(new_row + 65)}{new_col}]")
                                    break
                                else:
                                    # Own piece or other obstacle - scout cannot move here or past
                                    break
                        else:
                            # Regular piece - can only move one square
                            new_row, new_col = row + dr, col + dc
                            if 0 <= new_row < self.size and 0 <= new_col < self.size:
                                target = self.board[new_row][new_col]
                                if (target is None or
                                    (isinstance(target, dict) and target['player'] != player_id)):
                                    available_moves.append(f"[{chr(row + 65)}{col} {chr(new_row + 65)}{new_col}]")

        self.state.add_observation(
            message=f"Current Board:\n\n{self._render_board(player_id=player_id, full_board=False)}\nAvailable Moves: " + ", ".join(available_moves),
            observation_type=ta.ObservationType.GAME_BOARD
        )
    
    def _render_board(self, player_id, full_board: bool = False):
        piece_abbreviations = {
            'Flag': 'FL', 'Bomb': 'BM', 'Spy': 'SP', 'Scout': 'SC', 'Miner': 'MN',
            'Sergeant': 'SG', 'Lieutenant': 'LT', 'Captain': 'CP', 'Major': 'MJ',
            'Colonel': 'CL', 'General': 'GN', 'Marshal': 'MS'
        }

        res = []
        # header
        res.append("   " + " ".join(f"{i:>3}" for i in range(self.size)) + "\n")

        for row in range(self.size):
            label = chr(row + 65)
            row_str = f"{label:<3}"

            for col in range(self.size):
                pos = (row, col)

                if pos in self.lakes:
                    row_str += "  ~ "
                    continue

                cell = self.board[row][col]

                if cell is None:
                    row_str += "  . "
                    continue

                # cell contains a piece dict
                if full_board:
                    # show EVERYTHING
                    ab = piece_abbreviations[cell['rank']]
                    if cell['player'] == 0:
                        row_str += f" {ab.lower()} "
                    else:
                        row_str += f" {ab.upper()} "
                else:
                    # player sees only their own pieces
                    if cell['player'] == player_id:
                        ab = piece_abbreviations[cell['rank']]
                        row_str += f" {ab.upper()} "
                    else:
                        row_str += "  ? "

            res.append(row_str + "\n")

        return "".join(res)



    # 4) POPULATE BOARD (size-aware)
    def _populate_board(self):
        size = self.size

        # number of rows each player has based on board size
        if size == 6:
            setup_rows = 2
        elif size == 7:
            setup_rows = 2
        elif size == 8:
            setup_rows = 2
        elif size == 9:
            setup_rows = 3
        elif size == 10:
            setup_rows = 4
        else:
            setup_rows = max(2, size // 3)

        board = [[None for _ in range(size)] for _ in range(size)]

        # populate each player separately
        for player in (0, 1):
            counts = self._generate_piece_counts()  # each player gets their own pieces
            half = max(1, setup_rows // 2)

            if player == 0:
                back_rows = range(0, half)
                front_rows = range(half, setup_rows)
            else:
                back_start = size - setup_rows
                back_rows = range(back_start, back_start + half)
                front_rows = range(back_start + half, size)

            free_back = [(r, c) for r in back_rows for c in range(size)
                        if (r, c) not in self.lakes]
            free_front = [(r, c) for r in front_rows for c in range(size)
                        if (r, c) not in self.lakes]

            random.shuffle(free_back)
            random.shuffle(free_front)

            # ---------------- FLAG ALWAYS ON OUTERMOST ROW ----------------
            if player == 0:
                flag_row = 0
            else:
                flag_row = size - 1

            # valid flag positions on outermost row
            flag_candidates = [(flag_row, c) for c in range(size)
                            if (flag_row, c) not in self.lakes
                            and board[flag_row][c] is None]

            if not flag_candidates:
                # emergency fallback
                flag_candidates = free_back[:]

            fx, fy = random.choice(flag_candidates)
            board[fx][fy] = {"rank": "Flag", "player": player}
            self.player_pieces[player].append((fx, fy))

            if (fx, fy) in free_back: free_back.remove((fx, fy))
            if (fx, fy) in free_front: free_front.remove((fx, fy))

            # ---------------- BOMBS: PROTECT FLAG IF POSSIBLE ----------------
            bombs_to_place = counts.get("Bomb", 0)

            for r, c in [(fx + 1, fy), (fx - 1, fy), (fx, fy + 1), (fx, fy - 1)]:
                if bombs_to_place == 0:
                    break
                if 0 <= r < size and 0 <= c < size and (r, c) not in self.lakes:
                    if board[r][c] is None:
                        board[r][c] = {"rank": "Bomb", "player": player}
                        self.player_pieces[player].append((r, c))
                        if (r, c) in free_back: free_back.remove((r, c))
                        if (r, c) in free_front: free_front.remove((r, c))
                        bombs_to_place -= 1

            while bombs_to_place > 0 and (free_back or free_front):
                if free_back and random.random() < 0.5:
                    r, c = free_back.pop()
                elif free_front:
                    r, c = free_front.pop()
                else:
                    break
                board[r][c] = {"rank": "Bomb", "player": player}
                self.player_pieces[player].append((r, c))
                bombs_to_place -= 1

            counts.pop("Flag", None)
            counts.pop("Bomb", None)

            # ---------------- SPY (in the front) ----------------
            if counts.get("Spy", 0) > 0:
                if free_front:
                    r, c = free_front.pop()
                else:
                    r, c = free_back.pop()
                board[r][c] = {"rank": "Spy", "player": player}
                self.player_pieces[player].append((r, c))
            counts.pop("Spy", None)

            # ---------------- MARSHAL & GENERAL (defensive middle) ----------------
            for rank in ("Marshal", "General"):
                if counts.get(rank, 0) > 0 and free_back:
                    placed = False
                    if size < 6:
                        mid_cols = [size // 2]
                    else:
                        mid_cols = [max(0, size // 2 - 1),
                                    size // 2,
                                    min(size - 1, size // 2 + 1)]

                    for row in back_rows:
                        for col in mid_cols:
                            pos = (row, col)
                            if pos in free_back:
                                board[row][col] = {"rank": rank, "player": player}
                                self.player_pieces[player].append((row, col))
                                free_back.remove(pos)
                                placed = True
                                break
                        if placed:
                            break
                counts.pop(rank, None)

            # ---------------- REST OF THE PIECES ----------------
            slots = free_front + free_back
            ranks_left = []
            for rnk, cnt in counts.items():
                ranks_left.extend([rnk] * cnt)
            random.shuffle(ranks_left)

            while slots and ranks_left:
                r, c = slots.pop()
                rank = ranks_left.pop()
                board[r][c] = {"rank": rank, "player": player}
                self.player_pieces[player].append((r, c))

            while slots:
                r, c = slots.pop()
                board[r][c] = {"rank": "Scout", "player": player}
                self.player_pieces[player].append((r, c))

        # ---------------- LAKES ----------------
        for r, c in self.lakes:
            board[r][c] = "~"

        return board


    # 5) VALIDATION OVERRIDE (only size-boundaries change)
    def _validate_move(self, player_id, src_r, src_c, dst_r, dst_c):
        
        if not (0 <= src_r < self.size and 0 <= src_c < self.size and 0 <= dst_r < self.size and 0 <= dst_c < self.size):
            reason=f"Invalid action format. Player {player_id} did not input valid coordinates."
            self.state.set_invalid_move(reason=reason)
            return False
        
        if self.board[src_r][src_c] is None or self.board[src_r][src_c]['player'] != player_id:
            reason=f"Invalid action format. Player {player_id} must move one of their own pieces."
            self.state.set_invalid_move(reason=reason)
            return False
        
        if abs(src_r - dst_r) + abs(src_c - dst_c) != 1 and self.board[src_r][src_c]['rank'].lower() == 'scout':
            ## check if there's a piece in between the source and destination
            if src_r == dst_r:
                for col in range(min(src_c, dst_c) + 1, max(src_c, dst_c)):
                    if self.board[src_r][col] is not None:
                        reason=f"Invalid action format. Player {player_id} cannot move a scout through other pieces."
                        self.state.set_invalid_move(reason=reason)
                        return False
            elif src_c == dst_c:
                for row in range(min(src_r, dst_r) + 1, max(src_r, dst_r)):
                    if self.board[row][src_c] is not None:
                        reason=f"Invalid action format. Player {player_id} cannot move a scout through other pieces."
                        self.state.set_invalid_move(reason=reason)
                        return False
            else:
                reason=f"Invalid action format. Player {player_id} cannot move a scout diagonally."
                self.state.set_invalid_move(reason=reason)
                return False
            
        if abs(src_r - dst_r) + abs(src_c - dst_c) != 1 and self.board[src_r][src_c]['rank'].lower() != 'scout':
            ## !  - by right, only scouts can move more than one square at a time but we are not implementing that yet
            reason=f"Invalid action format. Pieces, apart from scouts, can only move one square at a time."
            self.state.set_invalid_move(reason=reason)
            return False
        
        if self.board[dst_r][dst_c] is not None:
            if (dst_r, dst_c) in self.lakes:
                reason=f"Invalid action format. Player {player_id} cannot move into the lake."
                self.state.set_invalid_move(reason=reason)
                return False
            
            elif self.board[dst_r][dst_c]['player'] == player_id:
                reason=f"Invalid action format. Player {player_id} cannot move onto their own piece."
                self.state.set_invalid_move(reason=reason)
                return False
        
        if self.board[src_r][src_c]['rank'].lower() in ['bomb','flag']:
            reason=f"Invalid action format. Player {player_id} cannot move a bomb or flag."
            self.state.set_invalid_move(reason=reason)
            return False
        size = self.size

        if not (0 <= src_r < size and 0 <= src_c < size and
                0 <= dst_r < size and 0 <= dst_c < size):
            self.state.set_invalid_move("Invalid: out of board.")
            return False

        return True


    def _check_winner(self):
        """
        determine which player has no more pieces that are not bombs or flags.
        """
        for player in range(2):
            if all([self.board[row][col]['rank'] in ['Bomb', 'Flag'] for row, col in self.player_pieces[player]]):
                return 1 - player
        return None