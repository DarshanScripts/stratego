from typing import Protocol, List

class Strategy(Protocol):
    """
    Base implementation of the Strategy interface.
    All strategies must define a 'choose' method and a 'get_context' method.
    """

    def get_context(self) -> str:
        """Returns a textual description of the strategic mindset."""
        pass

    def choose(self, legal_moves: List[str], observation: str) -> str:
        """
        Default implementation: return a neutral choice (for LLM integration).
        The LLM will use this context to make the final decision.
        """
        # Let the LLM choose externally; this function may be overridden by AI-guided strategies
        return ""