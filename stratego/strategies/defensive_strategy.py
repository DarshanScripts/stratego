from typing import List
from stratego.strategies.base import Strategy

class DefensiveStrategy(Strategy):
    def get_context(self) -> str:
        return (
            "Play defensively: focus on protecting high-value pieces "
            "and controlling your territory. Avoid unnecessary risks."
        )