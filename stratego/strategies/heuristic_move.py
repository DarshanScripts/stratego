# import random
# from .base import Strategy

# class RandomStrategy(BaseStrategy):
#     def decide_move(self, board_state, player):
#         moves = self._get_possible_moves(board_state, player)
#         return random.choice(moves) if moves else None

#     def _get_possible_moves(self, board_state, player):
#         # simulăm niște mutări posibile pentru exemplu
#         return [('A2', 'A3'), ('B4', 'B5'), ('C1', 'C2')]