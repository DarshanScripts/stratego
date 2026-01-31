"""AI agent models for Stratego gameplay.

This package provides various LLM-based agent implementations that can
play Stratego by processing observations and generating valid moves.

Supported Models:
    - OllamaAgent: Local Ollama models with full customization
    - HFLocalAgent: HuggingFace transformers with GPU acceleration
    - VLLMAgent: High-performance vLLM inference (planned)
    - SGLangAgent: SGLang-based agents (planned)

All agents implement the AgentLike protocol defined in base.py,
ensuring consistent interface across different model backends.
"""
