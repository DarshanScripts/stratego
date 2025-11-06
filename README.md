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
        * `python3 -m venv .venv`
        * `source .venv/bin/activate`
* If venv is successfully working, you could see (.venv) infront of your Terminal lines.
* You can deactivate virtual environment everytime with writing `deactivate`.
* Updating pip is recommended before installing with such codes: `python -m pip install --upgrade pip` or `python3 -m pip install --upgrade pip`
* Then, install packages using `pip install -e .`
* You can test after installing packages e.g. `stratego --p0 ollama:mistral:7b --p1 ollama:gemma3:1b --prompt base`
    * `--p0` means setting for player 0, `--p1` means setting for player 1, `--prompt` means which prompt to use for the game.
    * `ollama:mistral:7b` means using mistral model with 7b parameters in ollama client. You can change ollama to hf to use hugging face agent e.g. `--p0 hf:TinyLlama/TinyLlama-1.1B-Chat-v1.0`.
* Make sure turn on your ollama client before testing, when you use ollama as LLM agent.
* You can use `pip install -e ".[hf]"` to install additional dependencies for Hugging Face models.
    

## Regarding Using Different Large Language Models

* Write down your insights...