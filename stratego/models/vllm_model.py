"""
vLLM Model Wrapper for HuggingFace Models
This file creates an AI agent that uses vLLM to run large language models from HuggingFace.
vLLM provides fast GPU-accelerated inference for LLMs.
"""

# Import Python's operating system module to interact with environment variables
import os
# Import random module for fallback random move selection
import random
# Import Optional type hint for parameters that can be None
from typing import Optional
# Import vLLM's main classes: LLM for model loading, SamplingParams for generation settings
from vllm import LLM, SamplingParams

# Import the base protocol that defines what an agent should look like
from .base import AgentLike
# Import utility functions for parsing game observations and moves
from ..utils.parsing import (
    extract_legal_moves,      # Function: gets list of valid moves from observation text
    extract_forbidden,         # Function: gets list of forbidden moves
    slice_board_and_moves,     # Function: creates compact version of board state
    strip_think,               # Function: removes thinking text from model output
    MOVE_RE                    # Regular expression: pattern to find moves like "[A0 B0]"
)
# Import prompt management classes
from ..prompts import PromptPack, get_prompt_pack


class VLLMAgent(AgentLike):
    """
    Agent class powered by vLLM for fast GPU inference.
    This agent can load any HuggingFace model and use it to play Stratego.
    
    Inherits from: AgentLike (protocol defining agent interface)
    """
    
    def __init__(
        self,
        model_name: str,                          # String: HuggingFace model ID (e.g., "google/gemma-2-2b-it")
        system_prompt: Optional[str] = None,      # String or None: custom system prompt override
        prompt_pack: Optional[PromptPack | str] = None,  # PromptPack object or string: prompt configuration
        temperature: float = 0.2,                 # Float: controls randomness (0.0=deterministic, 1.0=creative)
        top_p: float = 0.9,                       # Float: nucleus sampling threshold
        max_tokens: int = 64,                     # Integer: maximum tokens to generate per response
        gpu_memory_utilization: float = 0.3,      # Check Check checking Float: fraction of GPU memory to use (0.0-1.0)
        tensor_parallel_size: int = 1,            # Integer: number of GPUs to use for this model
        download_dir: str = "/scratch/hm24/.cache/huggingface",  # String: where to cache model files
        **kwargs,                                 # Dictionary: additional vLLM arguments
    ):
        """
        Initialize the vLLM agent by loading a model from HuggingFace.
        
        This constructor:
        1. Sets up prompt configuration
        2. Configures cache directories
        3. Loads the model into GPU memory using vLLM
        4. Configures generation parameters
        """
        
        # Store the model name as an instance variable (self.model_name)
        # This is used later for displaying which model made a move
        self.model_name = model_name
        
        # Handle prompt_pack parameter which can be a string name or PromptPack object
        if isinstance(prompt_pack, str) or prompt_pack is None:
            # If it's a string or None, load the prompt pack by name
            # get_prompt_pack() returns a PromptPack object with system prompts and guidance
            self.prompt_pack: PromptPack = get_prompt_pack(prompt_pack)
        else:
            # If it's already a PromptPack object, use it directly
            self.prompt_pack = prompt_pack
        
        # Set system prompt: use custom if provided, otherwise use from prompt pack
        # The system prompt tells the model how to behave (e.g., "You are a Stratego player")
        self.system_prompt = system_prompt if system_prompt is not None else self.prompt_pack.system
        
        # Force HuggingFace to cache models in /scratch instead of home directory
        # Environment variables control where transformers library saves downloaded models
        os.environ["HF_HOME"] = download_dir
        os.environ["TRANSFORMERS_CACHE"] = download_dir
        
        # Print status messages to show progress
        print(f"🤖 Loading {model_name} with vLLM...")
        print(f"📁 Cache directory: {download_dir}")
        
        # Create vLLM engine instance
        # This loads the model from HuggingFace and prepares it for inference
        self.llm = LLM(
            model=model_name,                      # Which model to load
            download_dir=download_dir,             # Where to save/load model files
            gpu_memory_utilization=gpu_memory_utilization,  # How much GPU memory to use
            tensor_parallel_size=tensor_parallel_size,      # How many GPUs to split model across
            trust_remote_code=True,                # Allow custom model code from HuggingFace
            **kwargs                               # Pass any additional vLLM parameters
        )
        
        # Create sampling parameters object
        # This controls how the model generates text (temperature, length, etc.)
        self.sampling_params = SamplingParams(
            temperature=temperature,               # Randomness in generation
            top_p=top_p,                          # Nucleus sampling parameter
            max_tokens=max_tokens,                # Maximum length of generated response
            stop=["\n\n", "Player", "Legal moves:"],  # List of strings that stop generation
        )
        
        # Print success message
        print(f"✅ Model loaded successfully!")

    def _llm_once(self, prompt: str) -> str:
        """
        Generate a single response from the model.
        
        This is a private method (starts with _) used internally.
        
        Args:
            prompt (str): The input text to send to the model
            
        Returns:
            str: The model's response text, cleaned of thinking markers
        """
        # Combine system prompt and user prompt into full prompt
        # Format: "System: <system_prompt>\n\nUser: <prompt>"
        full_prompt = f"{self.system_prompt}\n\n{prompt}"
        
        # Call vLLM to generate response
        # Returns a list of output objects (we only generate 1, so index [0])
        outputs = self.llm.generate([full_prompt], self.sampling_params)
        
        # Extract text from first output's first completion
        # Structure: outputs[request_index].outputs[completion_index].text
        response = outputs[0].outputs[0].text.strip()
        
        # Remove any thinking markers (like <think>...</think>) from response
        # strip_think() is a utility function that cleans the text
        return strip_think(response)

    def __call__(self, observation: str) -> str:
        """
        Main method called when agent needs to make a move.
        This makes the agent callable like a function: agent(observation)
        
        Args:
            observation (str): The current game state as text from TextArena
            
        Returns:
            str: A move in format "[A0 B0]" representing from-square to-square
        """
        # Step 1: Extract list of legal moves from observation text
        # Returns list like ["[A0 B0]", "[A1 B1]", ...]
        legal = extract_legal_moves(observation)
        
        # If no legal moves exist, return empty string (game might be over)
        if not legal:
            return ""
        
        # Step 2: Get forbidden moves (moves that were already tried and failed)
        # Returns set of move strings to avoid
        forbidden = set(extract_forbidden(observation))
        
        # Filter legal moves to remove forbidden ones
        # List comprehension: keep only moves NOT in forbidden set
        # If all moves forbidden, fall back to full legal list
        legal_filtered = [m for m in legal if m not in forbidden] or legal[:]
        
        # Step 3: Create compact version of observation for model
        # slice_board_and_moves() removes unnecessary text to save tokens
        slim = slice_board_and_moves(observation)
        
        # Get guidance prompt from prompt pack
        # This wraps the slim observation with instructions
        guidance = self.prompt_pack.guidance(slim)
        
        # Step 4: Try to get valid move with retry loop (max 3 attempts)
        for attempt in range(3):
            # First strategy: Use guidance prompt
            # Call model with full game context and instructions
            raw = self._llm_once(guidance)
            
            # Search for move pattern in response using regex
            # MOVE_RE.search() looks for pattern like "[A0 B0]"
            m = MOVE_RE.search(raw)
            
            # If regex found a match
            if m:
                # Extract the matched move string
                mv = m.group(0)
                
                # Check if this move is in our legal filtered list
                if mv in legal_filtered:
                    # Valid move found! Return it
                    return mv
            
            # Second strategy (attempts 1 and 2): Direct instruction
            if attempt > 0:
                # Ask model directly for move without game context
                raw2 = self._llm_once("Output exactly one legal move [A0 B0].")
                
                # Search for move pattern in this response
                m2 = MOVE_RE.search(raw2)
                
                if m2:
                    mv2 = m2.group(0)
                    
                    # Check validity
                    if mv2 in legal_filtered:
                        return mv2
        
        # Step 5: Fallback - all attempts failed
        # Choose random legal move to ensure game continues
        # random.choice() picks one item from list randomly
        return random.choice(legal_filtered)
    
    def cleanup(self):
        """
        Free GPU memory by deleting model.
        Call this when done with agent to release resources.
        """
        # Delete the LLM object, freeing VRAM
        del self.llm
        
        # Import torch to access CUDA functions
        import torch
        
        # Force PyTorch to release all unused GPU memory
        torch.cuda.empty_cache()