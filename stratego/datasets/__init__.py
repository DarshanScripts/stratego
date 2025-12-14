# stratego/datasets/__init__.py
"""
Hugging Face Datasets integration for Stratego game logs.
"""

from .builder import GameDatasetBuilder, build_dataset_from_logs
from .uploader import push_to_hub, auto_push_after_game

__all__ = [
    "GameDatasetBuilder",
    "build_dataset_from_logs",
    "push_to_hub",
    "auto_push_after_game",
]
