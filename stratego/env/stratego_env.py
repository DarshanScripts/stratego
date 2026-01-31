from typing import Optional
import textarena as ta

class StrategoEnv:
    """Wrapper for TextArena Stratego environment with multi-variant support.
    
    Supports multiple game modes:
    - Stratego-v0: Standard 10x10 game
    - Stratego-duel: 6x6 quick game
    - Stratego-custom: Custom board sizes (4x4 to 9x9)
    
    Note: Environment registration and initialization is handled by the textarena package.
    See backup folder for reference implementations of custom environments.
    """
    def __init__(self, env_id: str = "Stratego-v0", size: int = 10, seed: Optional[int] = None):
        # Environment setup with dynamic board size support
        if size != 10:
            self.env = ta.make(env_id=env_id, size=size)
        else:
            self.env = ta.make(env_id=env_id)
        seed = seed

    def reset(self, num_players: int = 2, seed: Optional[int] = None):
        self.env.reset(num_players=num_players, seed=seed)

    def get_observation(self):
        return self.env.get_observation()

    def step(self, action: str):
        return self.env.step(action=action)

    def close(self):
        return self.env.close()

    def get_state(self):
        return self.env.state

    def repetition_count(self):
        return self.env.repetition_count