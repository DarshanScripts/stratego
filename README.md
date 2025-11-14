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
        * `source .venv/bin/activate.csh`
* If venv is successfully working, you could see (.venv) infront of your Terminal lines.
* You can deactivate virtual environment everytime with writing `deactivate`.
* Updating pip is recommended before installing with such codes: `python -m pip install --upgrade pip` or `python3 -m pip install --upgrade pip`
* Then, install packages using `pip install -e .`
* After a successful installation, you can use commands just like `stratego` and `stratego-install-env`, which paste the environment files of Stratego Duel and register it in textarena folder of your .venv folder.
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
* Once you are connected to Ollama running server, then you can with this command `curl -s http://127.0.0.1:{your_host}/api/tags` to check what kind of LLMs are available now in the server.
* `curl -X POST http://127.0.0.1:{your_host}/api/pull -H 'Content-Type: application/json' -d '{"name":"{model_name}"}'` Use this command to request the server to download such LLM which are supported by Ollama.
* Those curl commands does not fully function or need extra words if you are going to run those in Powershell, so just open another terminal with Linux(you can use Ubuntu as well), connect to ssh -L, and execute those curl commands, for checking and pulling LLMs.
* You can kill the server with `kill $(cat /scratch/{user}/ollama_serve.pid)` or `pkill -f "/scratch/{user}/ollama_bin/ollama serve"`.
* When you have ConnectError: [WinError 10061], try `$env:OLLAMA_HOST = "http://127.0.0.1:{your_host}"` to set Ollama host as your address as well.

## Regarding Using Different Large Language Models

* If you want to use big LLMs, then make sure, that you are not going to run the game in ssh connected VS Code direclty; it causes freezing problem, because of big usage of GPU of the TU-Calusthal's server. So, pleas run the game local VS Code, but make sure one of the terminal of the VS Code is connected to your own ssh env.
* If you use big, such as gpt-oss:120b, around 40~50 GB of GPU of the TU-Clausthal's would be taken, which freezes your VS Code terminal. To solve this, you have to find the running task of your own with command, `ps -u {user} -o pid,rss,vsz,cmd --sort -rss` and kill the PID of the task. Probably it is the largest rss one.