"""Defensive gameplay strategy for Stratego.

This strategy prioritizes piece safety and defensive positioning.
It guides agents to protect valuable pieces and maintain strong
defensive formations.
"""
from typing import List
from stratego.strategies.base import Strategy

class DefensiveStrategy(Strategy):
    """Strategy focused on defensive play and piece protection.
    
    Guidance provided:
    - Protect high-value pieces (Marshal, General)
    - Maintain defensive formations
    - Only attack when safe and advantageous
    - Avoid unnecessary risks
    """
    def get_context(self) -> str:
        return (
            "Play defensively: focus on protecting high-value pieces "
            "and controlling your territory. Avoid unnecessary risks."
        )