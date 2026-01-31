from typing import Protocol

class AgentLike(Protocol):
    model_name: str
    def __call__(self, observation: str) -> str: ...