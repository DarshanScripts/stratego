from typing import List
from stratego.strategies.base import Strategy

class AggressiveStrategy(Strategy):
    def get_context(self) -> str:
        return (
            "Play aggressively: prioritize attacking enemy pieces, "
            "especially those near your front line. "
            "Take calculated risks and pressure the opponent."
        )