"""Strategic gameplay patterns for Stratego agents.

This package provides various strategy implementations that can guide
agent behavior during gameplay. Strategies can be composed with LLM
agents to create more sophisticated decision-making patterns.

Available Strategies:
    - AggressiveStrategy: Prioritizes attacking and forward movement
    - DefensiveStrategy: Focuses on piece protection and safe positioning
    - RandomMove: Simple random move selection (baseline)
    - HeuristicMove: Rule-based tactical decisions

Strategies implement the Strategy protocol from base.py and can be
mixed with LLM reasoning for hybrid approaches.
"""
