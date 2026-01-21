
# Project: Stratego LLM Test Based Games

## 1. Introduction

Stratego LLM is a research framework designed to evaluate the strategic reasoning and behavioral characteristics of Large Language Models (LLMs) in an imperfect-information game setting.

Unlike static benchmarks, this project pits models (e.g., Mistral, Gemma, Llama, Qwen) against each other in the board game Stratego to analyze dynamic performance. The primary goal is to determine which model performs better by measuring:

Win Rates & Dominance: Quantitative analysis of Win/Loss/Draw ratios across 100+ match simulations.

Behavioral Profiling: Classifying models as Stable (consistent, rule-abiding) vs. Aggressive (high attack frequency, risky plays).

Efficiency: Measuring time-to-move and token consumption to determine the "cost of intelligence."

Strategic Consistency: Analyzing how often models hallucinate invalid moves versus making logically sound decisions.

The system includes an automated arena for batch matchmaking, a custom logger for dataset creation, and a prompt-optimizer that refines strategies based on match outcomes.

## 2. Project Initialization (Local Setup)

Follow these steps to set up the development environment on your local machine.

### Prerequisites

* **Git**: Ensure Git is installed.
* **Python**: Python 3.8+ is recommended.

### Installation Steps

1. **Clone the Repository**
Clone the project to your local machine (e.g., in VS Code).
```bash
git clone https://github.com/davszi/Stratego.git
cd Stratego

```


2. **Create and Activate Virtual Environment**
It is highly recommended to work within a virtual environment.
* **Windows (PowerShell)**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1

```


* **Windows (CMD)**
```cmd
python -m venv .venv
.\.venv\Scripts\activate.bat

```


* **macOS / Linux**
```bash
python3 -m venv .venv
source .venv/bin/activate

```




> **Note:** If successful, you will see `(.venv)` at the start of your terminal line. To exit later, simply type `deactivate`.


3. **Install Dependencies**
Update pip and install the package in editable mode.
```bash
python -m pip install --upgrade pip
pip install -e .

```


*To install additional dependencies for Hugging Face models:*
```bash
pip install -e ".[hf]"

```


4. **Verify Installation**
Use the following commands to install environment files for Stratego Duel and Custom into the `textarena` folder.
```bash
stratego-install-env

```



---

## 3. Server Configuration (TU Clausthal SSH)

These steps are specific to the TU Clausthal cloud environment to manage disk quota and cache locations.

### Connecting via SSH

Connect to the server using port forwarding for Ollama (Port 11437 in this example).

```bash
ssh -L 11437:localhost:11437 {user}@cloud-247.rz.tu-clausthal.de

```

### Managing Cache (Critical)

To avoid filling up your home directory, redirect caches to the `/scratch` directory. Run these commands in your **Bash** terminal on the server.

1. **Create Cache Directories:**
```bash
mkdir -p /scratch/{user}/vs_cache
mkdir -p /scratch/{user}/hf_cache
mkdir -p /scratch/{user}/pip_cache

```


2. **Export Environment Variables:**
Run the following to set the paths for the current session:
```bash
export VSCODE_SERVER_CACHE=/scratch/{user}/vs_cache
export HF_HOME=/scratch/{user}/hf_cache
export HUGGINGFACE_HUB_CACHE=/scratch/{user}/hf_cache
export TRANSFORMERS_CACHE=/scratch/{user}/hf_cache
export HF_DATASETS_CACHE=/scratch/{user}/hf_cache
export PIP_CACHE_DIR=/scratch/{user}/pip_cache

```


3. **Permanent Configuration (Optional):**
To make these changes permanent, edit your `.cshrc` file:
```bash
nano ~/.cshrc

```


Add lines such as `setenv HF_HOME /scratch/{user}/hf_cache` for each variable listed above. Press `Ctrl+X` to save and exit.
4. **Cleanup:**
If you have existing cache in your home directory, clear it to free up space:
```bash
rm -r ~/.cache

```


*Restart VS Code to apply these changes.*

---

## 4. Setting up Ollama on SSH Server

If you wish to host your own Ollama instance on the server:

### Installation

1. **Prepare Directories:**
```bash
mkdir -p /scratch/{user}/ollama_bin
mkdir -p /scratch/{user}/ollama_model
mkdir -p /scratch/{user}/ollama_tmp
cd /scratch/{user}/ollama_bin

```


2. **Download and Extract:**
```bash
curl -fL -o ollama-linux-amd64.tar.zst https://github.com/ollama/ollama/releases/download/v0.14.0/ollama-linux-amd64.tar.zst
tar --use-compress-program=unzstd -xvf ollama-linux-amd64.tar.zst

```


3. **Configure Environment:**
Set the paths so Ollama knows where to store models and temporary files.
```bash
export OLLAMA_MODELS=/scratch/{user}/ollama_model
export OLLAMA_TMPDIR=/scratch/{user}/ollama_tmp
export OLLAMA_HOST=0.0.0.0:{your_host_port}
export PATH="/scratch/{user}/ollama_bin/bin:$PATH"

```



### Running the Server

It is recommended to run the server inside a `tmux` session so it persists after you disconnect.

1. Start a new session: `tmux new -s ollama_server`
2. Start Ollama: `ollama serve`
3. Detach: Press `Ctrl+B` then `D`.

### Managing Models

Open a **new** local terminal (connected via SSH) to interact with the running server.

* **Check available models:**
```bash
curl -s http://127.0.0.1:{your_host_port}/api/tags | jq -r '.models[].name'

```


* **Pull (Download) a new model:**
```bash
curl -X POST http://127.0.0.1:{your_host_port}/api/pull \
     -H 'Content-Type: application/json' \
     -d '{"name":"mistral:7b"}'

```



---

## 5. Usage & Gameplay

You can run the game using the `stratego` command. Ensure your Ollama client is running if using local LLMs.

**Basic Command:**

```bash
stratego --p0 ollama:mistral:7b --p1 ollama:gemma3:1b --prompt base

```

**Arguments:**

* `--p0`: Agent for Player 0 (e.g., `ollama:mistral:7b` or `hf:TinyLlama/TinyLlama-1.1B-Chat-v1.0`).
* `--p1`: Agent for Player 1.
* `--prompt`: The prompt strategy to use.
* `--size`: Board size (NxN). Default is 10.
```bash
# Example for a smaller board
stratego --p0 ollama:mistral:7b --p1 ollama:mistral:7b --size 6

```



---

## 6. Dataset & Prompt Optimization

The system includes automated logging and prompt improvement mechanisms implemented in `main.py`.

### Logging (GameLogger)

Every move, prompt, and metadata is saved to CSV logs. The `cli()` function initializes a `GameLogger`:

* **Log Directory:** Controlled via `--log-dir` (default: `logs`).
* **Initial Prompt Logging:** The logger captures the exact initial prompt used by the agent to ensure reproducibility.

### Automated Prompt Improvement

The system automatically attempts to improve the System Prompt based on gameplay data.

* **Mechanism:** The runner checks the number of CSV logs in the log directory.
* **Trigger:** Every **3 games**, `improve_prompt()` is called.
* **Logic:** It analyzes recent games and updates `stratego/prompts/current_prompt.txt`.

### Hugging Face Dataset Integration

To upload your game logs to Hugging Face:

1. **Install Libraries:**
```bash
pip install huggingface huggingface_hub datasets

```


2. **Configuration:**
* Join your HF Organization.
* Update `./datasets/uploader.py` with your repository name.


3. **Authentication:**
* Create a **WRITE** token in your Hugging Face settings.
* Run `hf auth login` in your terminal and paste the token (do not save as git credential).


4. **Upload:**
Once authenticated, use the uploader script to push logs to the dataset repository.

---

## 7. Benchmarking

Use the built-in benchmark tool to evaluate model performance over multiple games.

**Command:**

```bash
benchmark --p0 {model_A} --p1 {model_B} --size {N} --game {count}

```

**Example:**

```bash
benchmark --p0 llama3.2:1b --p1 gemma3:1b --size 6 --game 4

```