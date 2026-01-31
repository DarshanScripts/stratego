# stratego/datasets/__init__.py
"""
Hugging Face Datasets integration for Stratego game logs.
"""

"""Dataset generation and management for model training.

This package handles the creation and uploading of training datasets
from game logs. It converts CSV game logs into HuggingFace datasets
suitable for fine-tuning Stratego-playing models.

Features:
    - Automatic CSV scanning and parsing
    - Dataset building with game metadata
    - HuggingFace Hub integration for sharing datasets
    - Incremental updates after each game

Usage:
    auto_push_after_game(logs_dir="logs/games", repo_id="user/dataset")
"""
from .builder import GameDatasetBuilder, build_dataset_from_logs
from .uploader import push_to_hub, auto_push_after_game

__all__ = [
    "GameDatasetBuilder",
    "build_dataset_from_logs",
    "push_to_hub",
    "auto_push_after_game",
]
