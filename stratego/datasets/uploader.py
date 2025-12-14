# stratego/datasets/uploader.py
"""
Upload Stratego datasets to Hugging Face Hub.
"""

from __future__ import annotations
import os
from typing import Optional

try:
    from datasets import Dataset
    from huggingface_hub import HfApi
    HF_AVAILABLE = True
except ImportError:
    HF_AVAILABLE = False


# Default repository - change this to your repo
DEFAULT_REPO_ID = "STRATEGO-LLM-TRAINING/stratego"


def push_to_hub(
    dataset: "Dataset",
    repo_id: str = DEFAULT_REPO_ID,
    private: bool = False,
    token: Optional[str] = None,
) -> str:
    """
    Push a dataset to Hugging Face Hub.
    
    Args:
        dataset: The dataset to upload
        repo_id: Hub repo ID like "username/stratego-games"
        private: Whether to make the dataset private
        token: HF token (optional, uses cached login)
        
    Returns:
        URL to the dataset on the Hub
    """
    if not HF_AVAILABLE:
        raise ImportError("Run: pip install datasets huggingface_hub")
    
    print(f"Pushing dataset to: {repo_id}")
    
    # Ensure repo exists
    try:
        api = HfApi()
        api.create_repo(repo_id, repo_type="dataset", exist_ok=True, private=private)
    except Exception as e:
        print(f"Note: {e}")
    
    dataset.push_to_hub(repo_id, private=private, token=token)
    
    url = f"https://huggingface.co/datasets/{repo_id}"
    print(f"Dataset uploaded: {url}")
    
    return url


def auto_push_after_game(
    logs_dir: str = "logs/games",
    repo_id: str = DEFAULT_REPO_ID,
    silent: bool = False,
) -> bool:
    """
    Automatically push all game logs to Hugging Face Hub.
    Called after each game ends.
    
    Args:
        logs_dir: Path to game logs directory
        repo_id: Hugging Face repo ID
        silent: If True, suppress print messages on errors
        
    Returns:
        True if successful, False otherwise
    """
    if not HF_AVAILABLE:
        if not silent:
            print("HuggingFace not installed. Skipping auto-push.")
        return False
    
    try:
        from .builder import build_dataset_from_logs
        
        # Build dataset from all logs
        dataset = build_dataset_from_logs(logs_dir)
        
        # Push to hub
        push_to_hub(dataset, repo_id=repo_id)
        
        return True
        
    except Exception as e:
        if not silent:
            print(f"Auto-push failed: {e}")
        return False
