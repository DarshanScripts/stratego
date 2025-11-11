# Stratego

## Intro

* Write down intro...

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
        * `python3 -m venv .venv --without-pip`
        * `source .venv/bin/activate.csh`
* If venv is successfully working, you could see (.venv) infront of your Terminal lines.
* You can deactivate virtual environment everytime with writing `deactivate`.
* Updating pip is recommended before installing with such codes: `python -m pip install --upgrade pip` or `python3 -m pip install --upgrade pip`
* Then, install packages using `pip install -e .`
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

## Regarding Using Different Large Language Models

* Write down your insights...