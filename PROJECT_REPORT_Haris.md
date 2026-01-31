# Project Report: Stratego LLM Test-Based Games
**Student**: Haris  
**Branch**: Haris_Environment_Engineer  
**Repository**: github.com/davszi/Stratego  
**Submission Date**: January 30, 2026  

---

## Project Overview
The Stratego LLM project evaluates Large Language Models (LLMs) through strategic gameplay in an imperfect-information board game environment. The system compares models (Mistral, Gemma, Llama, Qwen) by analyzing win rates, behavioral patterns, strategic consistency, and computational efficiency.

## My Role: Environment Engineer
As the Environment Engineer, I was responsible for designing, implementing, and testing game environments, ensuring proper integration with LLM models, and establishing robust logging infrastructure for data collection.

## Technical Contributions

### 1. Core Environment Development
- **Implemented StrategoDuel Environment**: Developed a custom 6×6 board variant (484 lines of code) for accelerated testing and experimentation
- **Environment Architecture**: Created modular environment wrappers supporting multiple game variants (Stratego, StrategoDuel, StrategoCustom)
- **Bug Fixes**: Resolved critical issues including flag capture detection, repetitive move prevention, game termination logic, and boundary validation

### 2. Game Logic & Integration (`main.py`)
- **Major Refactoring**: Rewrote core game loop with 839 insertions and 398 deletions, improving code structure and maintainability
- **Player Management**: Implemented turn-based system with state tracking and proper error handling
- **Model Integration**: Enhanced LLM response processing with validation, fallback mechanisms, and invalid move memory

### 3. Logging & Data Collection System (`game_logger.py`)
- **Comprehensive Logger**: Built 728-line logging system tracking move history, piece types, repeated moves, and game states
- **CSV Export**: Implemented structured data export for statistical analysis and dataset creation
- **Benchmarking Support**: Integrated logging with performance metrics for model comparison studies

### 4. Documentation & Setup
- **README Enhancement**: Authored detailed installation guide covering virtual environments, dependency management, and server configuration (314 additions)
- **Installation Tools**: Contributed to automated environment setup utilities for team deployment

## Quantitative Achievements
- **Files Modified**: 63 files across the codebase
- **Code Contribution**: 7,932 insertions, 2,153 deletions
- **Commits**: 18 direct commits with multiple collaborative merges
- **Collaboration**: Successfully integrated work from 5+ team members across branches

## Benchmarking Work
Conducted comparative analysis of LLM models with documented results in:

- **Master Results Compilation**: Aggregated metrics across 1000+ game simulations. In which for benchmarking used below models and numbers. Out of 1740 Games, played 790 games for better benchmarking.
  - deepseek-r1:8b vs mistral:7b: 238 games
  - llama3.1:8b vs olmo-3:7b: 266 games
  - qwen3:8b vs mistral:7b: 286 games
  - Saved in logs > games.

- **Visual Analytics**: Compile all 1740 games and create comprehensive benchmarking graphs, including bar graphs and pie charts, specifically for project poster presentations and performance visualization.

## Key Technical Skills Demonstrated
- **Python Development**: Object-oriented programming, environment design, API integration
- **Version Control**: Git branching strategy, collaborative development, code reviews
- **System Design**: Modular architecture, logging frameworks, error handling
- **Testing & Validation**: Experimental design, data collection, performance analysis
- **Documentation**: Technical writing, setup guides, code documentation

## Impact & Future Work
My contributions established the foundational infrastructure for LLM evaluation in the Stratego environment. The logging system enables ongoing data collection for research papers, while the modular environment design allows easy integration of new game variants and rule modifications.

Future enhancements could include reinforcement learning integration, advanced opponent modeling, and expanded board size options for complexity analysis.

---

**Repository Status**: All work pushed to `Haris_Environment_Engineer` branch and available for review at github.com/davszi/Stratego
