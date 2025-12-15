# Stratego

## Intro

- Write down intro...

## Initializing Project

* First of all, clone git from https://github.com/davszi/Stratego.git in your coding circumstances, e.g. VS Code.
* Then, pull proper branch of the project and make your own branch to work and establish.
* Working in virtual environment is recommended, but it is optional.
    * Windows (PowerShell)
        * `python -m venv .venv`
        * `.\\.venv\Scripts\Activate.ps1`
    * Windows (cmd)
        * `python -m venv .venv`
        * `.\\.venv\Scripts\activate.bat`
    * MacOS / Linux
        * `python3 -m venv .venv`
        * `source .venv/bin/activate.csh`
* If venv is successfully working, you could see (.venv) infront of your Terminal lines.
* You can deactivate virtual environment everytime with writing `deactivate`.
* Updating pip is recommended before installing with such codes: `python -m pip install --upgrade pip` or `python3 -m pip install --upgrade pip`
* Then, install packages using `pip install -e .`
* After a successful installation, you can use commands just like `stratego` and `stratego-install-env`, which paste the environment files of Stratego Duel and Stratego Custom and register them in textarena folder of your .venv folder.
* You can test after installing packages e.g. `stratego --p0 ollama:mistral:7b --p1 ollama:gemma3:1b --prompt base`
    * `--p0` means setting for player 0, `--p1` means setting for player 1, `--prompt` means which prompt to use for the game.
    * `ollama:mistral:7b` means using mistral model with 7b parameters in ollama client. You can change ollama to hf to use hugging face agent e.g. `--p0 hf:TinyLlama/TinyLlama-1.1B-Chat-v1.0`.
* Make sure turn on your ollama client before testing, when you use ollama as LLM agent.
* You can use `pip install -e ".[hf]"` to install additional dependencies for Hugging Face models.

## Important Things for Cache Problem in SSH Server
* First of all please use your own user name of TU Clausthal in {user}. Do followings in bash terminal, not in -bin/tsch terminal.
* Please make sure that you are in directory, `scratch/{user}` in the terminal
* `mkdir -p vs_cache` for creating VS code cache directory.
* `mkdir -p hf_cache` for creating Hugging Face cache directory.
* `mkdir -p pip_cache` for creating pip cache directory.
* `export VSCODE_SERVER_CACHE=/scratch/{user}/vs_cache` to set new saving place for the VS code cache.
* `export HF_HOME=/scratch/{user}/hf_cache` to set new saving place for the Hugging Face cache.
* `export HUGGINGFACE_HUB_CACHE=/scratch/{user}/hf_cache` to set new saving place for the Hugging Face Hub cache.
* `export TRANSFORMERS_CACHE=/scratch/{user}/hf_cache` to set new saving place for the Transformers cache.
* `export HF_DATASETS_CACHE=/scratch/{user}/hf_cache` to set new saving place for the Hugging Face Datasets cache.
* `export PIP_CACHE_DIR=/scratch/{user}/pip_cache` to set new saving place for the pip cache.
* Or you have another option to change the saving directory forcefully:
    * `nano ~/.cshrc` to open new cshrc file editor to redirect the cache files.
    * `setenv HF_HOME /scratch/{user}/hf_cache` write this way for all caches above each lines.
    * Then Ctrl+X to exit the edit program and save it.
* Make sure, to remove the cache directory which is in the directory of `/home/{user}`. You can delete it with `rm -r .cache`
* After all, you have to restart VS Code to apply changes.

## Using LLMs from SSH Server
* First of all, please be sure clean all of powershells.
* Open a VS Code for connecting ssh server of TU-Clausthal. Since we use cloud-247, you can use as `ssh -L 11437:localhost:11437 {user}@cloud-247.rz.tu-clausthal.de`. Please enter your password of TU-Clausthal account.
* If your login is successful, it means, you are connected to the ssh server of TU-Clausthal in port of 11437, which we used to open the Ollama server.
* If you want to open Ollama server on your own, you have to install Ollama in your virtual environment of your ssh directory.
    * `mkdir -p /scratch/{user}/ollama_bin` to make a directory to store Ollama binary files.
    * `mkdir -p /scratch/{user}/ollama_model` to make a directory to store Ollama model files.
    * `mkdir -p /scratch/{user}/ollama_tmp` to make a directory to store tmp files.
    * `cd /scratch/{user}/ollama_bin`
    * `curl -L https://ollama.com/download/ollama-linux-amd64.tgz -o ollama.tgz`
    * `tar -xzf ollama.tgz` to download Ollama client from its website in ollama_bin and launch.
    * `ln -sf /scratch/{user}/ollama_bin/bin/ollama /scratch/{user}/ollama_bin/ollama` to make a binary file of Ollama, which you can launch with `ollama` command. 
    * `export OLLAMA_MODELS=/scratch/{user}/ollama_model`
    * `export OLLAMA_TMPDIR=/scratch/{user}/ollama_tmp`
    * `export OLLAMA_HOST=0.0.0.0:{your_host}`
    * `export PATH="/scratch/{user}/ollama_bin:$PATH"` to set paths for running Ollama.
    * `/scratch/{user}/ollama_bin/ollama serve` to start the server.
* Once you are connected to Ollama running server, then you can with this command `curl -s http://127.0.0.1:{your_host}/api/tags` or `curl -s http://127.0.0.1:{your_host}/api/tags | jq -r '.models[].name'` to check what kind of LLMs are available now in the server.
* `curl -X POST http://127.0.0.1:{your_host}/api/pull -H 'Content-Type: application/json' -d '{"name":"{model_name}"}'` Use this command to request the server to download such LLM which are supported by Ollama.
* Those curl commands does not fully function or need extra words if you are going to run those in Powershell, so just open another terminal with Linux(you can use Ubuntu as well), connect to ssh -L, and execute those curl commands, for checking and pulling LLMs.
* You can kill the server with `kill $(cat /scratch/{user}/ollama_serve.pid)` or `pkill -f "/scratch/{user}/ollama_bin/ollama serve"`.
* When you have ConnectError: [WinError 10061], try `$env:OLLAMA_HOST = "http://127.0.0.1:{your_host}"` to set Ollama host as your address as well.

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

## Regarding using Huggingface Datasets
* First of all install Huggingface in your .venv or your local library with command: `pip install huggingface huggingface_hub datasets`. This allows you to use Huggingface functionalities in your circumstance as well as Huggingface client and its datasets.
* Second, please be a memeber of your own Huggingface organization and make a dataset repository to share with team members. Change the repository name of `./datasets/uploader.py` with your own repository name, which does uploading your log files to the Huggingface datasets.
* Thirdly, if you are able to be a member of the organization, make your own Huggingface token to use in your local authentication. Make sure to create this token as `WRITE`, not `FINE-GRAINED` and not `READ`. Since this token would be shown only once, make sure to save the token in your local repository as text file.
* Finally, login on your terminal with command, `hf auth login`. Enter your generated token and do not set token as credential. After all, you are able to upload your log data after gameplays automatically to your Huggingface repository.
