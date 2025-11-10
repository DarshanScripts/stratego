import random
from typing import List
from .base import Strategy

class RandomStrategy(Strategy):
    def get_context(self) -> str:
        return "Play randomly: mix offensive and defensive moves."

    def choose(self, legal_moves, observation):
        return random.choice(legal_moves)