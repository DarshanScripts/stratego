from typing import Protocol, List

class Strategy(Protocol):
    def choose(self, legal_moves: List[str], observation: str) -> str: ...