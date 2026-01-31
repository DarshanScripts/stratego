"""Configuration constants for Stratego game.

This module contains all configuration values used throughout the application.
Modify these values to adjust game behavior, model parameters, and logging settings.
"""

# ============================
# Environment Configuration
# ============================
DEFAULT_ENV = "Stratego-v0"
DUEL_ENV = "Stratego-duel"
CUSTOM_ENV = "Stratego-custom"

DEFAULT_BOARD_SIZE = 10
DUEL_BOARD_SIZE = 6
CUSTOM_BOARD_SIZE_MIN = 4
CUSTOM_BOARD_SIZE_MAX = 9

# ============================
# Model Configuration
# ============================
DEFAULT_TEMPERATURE = 0.2
DEFAULT_TOP_P = 0.9
DEFAULT_REPEAT_PENALTY = 1.05
DEFAULT_NUM_PREDICT = 128

# Agent retry settings
MAX_AGENT_ATTEMPTS = 3

# ============================
# Game Flow Configuration
# ============================
# Turn thresholds for aggressive warnings
STALLING_WARNING_TURN = 20
CRITICAL_WARNING_TURN = 50

# Move history limits
MAX_MOVE_HISTORY = 10
MAX_PROMPT_IMPROVEMENTS = 20
MAX_TRACKER_ENTRIES = 20

# ============================
# Logging Configuration
# ============================
DEFAULT_LOG_DIR = "logs"
DEFAULT_GAMES_DIR = "logs/games"
MASTER_EXCEL_FILE = "Master_Game_Results.xlsx"

# Analysis model for prompt improvement
ANALYSIS_MODEL = "mistral:7b"

# ============================
# Ollama Configuration
# ============================
DEFAULT_OLLAMA_HOST = "http://localhost:11435"

# ============================
# Dataset Configuration
# ============================
DEFAULT_DATASET_REPO = "STRATEGO-LLM-TRAINING/stratego"
