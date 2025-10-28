import random
from typing import List
from .base import Strategy
class RandomStrategy(Strategy):
    def choose(self, legal_moves: List[str], observation: str) -> str:
        return random.choice(legal_moves) if legal_moves else ""