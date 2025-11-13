# Stratego

## Intro

- Write down intro...

## Initializing Project

- First of all, clone git from https://github.com/davszi/Stratego.git in your coding circumstances, e.g. VS Code.
- Then, pull proper branch of the project and make your own branch to work and establish.
- Working in virtual environment is recommended, but it is optional.
  - Windows (PowerShell)
    - `python -m venv .venv`
    - `.\\.venv\Scripts\Activate.ps1`
  - Windows (cmd)
    - `python -m venv .venv`
    - `.\\.venv\Scripts\activate.bat`
  - MacOS / Linux
    - `python3 -m venv .venv`
    - `source .venv/bin/activate`
- If venv is successfully working, you could see (.venv) infront of your Terminal lines.
- You can deactivate virtual environment everytime with writing `deactivate`.
- Updating pip is recommended before installing with such codes: `python -m pip install --upgrade pip` or `python3 -m pip install --upgrade pip`
- Then, install packages using `pip install -e .`
- You can test after installing packages e.g. `stratego --p0 ollama:mistral:7b --p1 ollama:gemma3:1b --prompt base`
- Make sure turn on your ollama client before testing.

## Regarding Using Different Large Language Models

- Write down your insights...

## Dataset and prompt optimization

#In the main.py file:

- Added imports:
  -Saves every move, prompt, and metadata to CSV logs in logs/:
  `from stratego.game_logger import GameLogger`
  `import os`
  -After every 3 games, automatically improves the LLM’s system prompt:
  `from stratego.prompt_optimizer import improve_prompt`
  -Place these imports at the top of the extended script.

-In the cli() function:

- Additional arguments:
  -Add arguments inside the cli() function
  -Put them right after p = argparse.ArgumentParser()
  -cli() is responsible for reading input parameters and configuring the full game:
  `p.add_argument("--log-dir", default="logs")`
  `p.add_argument("--game-id", default=None)`

-Logger:
-In order to implement the dataset, a GameLogger is created into the cli() function which records moves, timestamps each turn, records the original prompt etc:

"""
with GameLogger(out_dir=args.log_dir, game_id=args.game_id) as logger:
for pid in (0, 1):
if hasattr(agents[pid], "logger"):
agents[pid].logger = logger
agents[pid].player_id = pid
initial = getattr(agents[pid], "initial_prompt", None)
if initial:
logger.log_prompt(player=pid,
model_name=getattr(agents[pid], "model_name", "unknown"),
prompt=initial,
role="initial")
"""
-What this does:

- `with GameLogeer(...) as logger:` creates a new GameLogger instance which prepares a csv log file to store moves and prompts for the entire match.
- `agents[pid].logger = logger`: a game logger is attached to the agent
  - `initial = getattr(agents[pid], "initial_prompt", None)`: retrieves the initial system prompt used by the agent because we want tostore it into tha database
- ````logger.log_prompt(player=pid,
                    model_name=getattr(agents[pid], "model_name", "unknown"),
                    prompt=initial,
                    role="initial")
  ```: Writes the initial prompt into the CSV log. It ensures every game records EXACTLY which prompt the LLM played with.

  ````

- `````num_games = len([f for f in os.listdir(args.log_dir) if f.endswith(".csv")])
      if num_games % 3 == 0:
          print("Running prompt improvement based on recent games...")
          from stratego.prompt_optimizer import improve_prompt
          improve_prompt("logs", "stratego/prompts/current_prompt.txt", model_name="mistral:7b")
    ```` : After each match, the runner counts how many game logs (CSV files) exist.
  Every 3 games, it automatically calls improve_prompt() to update the Stratego system prompt based on recent gameplay.
  This allows the agent’s prompt to gradually improve over time using real match data.
  `````

- Downsizing the board:
  -In order to do that, firstly we introduce the argument in the `cli()` function:
  ` p.add_argument("--size", type=int, default=10, help="Board size NxN")`
