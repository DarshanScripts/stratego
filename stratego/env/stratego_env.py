from typing import Optional
import textarena as ta

class StrategoEnv:
    def __init__(self, env_id: str = "Stratego-v0", size: int = 10, seed: Optional[int] = None):
        # TODO: make various option to play
        # Stratego original as default, if the user want to play duel mode, env_id = "Stratego-duel"
        # rule_opts: e.g. board_size=10, etc.
        # find a way to replace original init file, registration file and put more environment such as Stratego-duel
        # in original textarena library by running or installing the program.
        # You can see which file should be edited in backup folder.
        # Don't worry, this should be done with Package managing team.
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