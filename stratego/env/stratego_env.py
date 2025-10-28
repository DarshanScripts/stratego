import textarena as ta

class StrategoEnv:
    def __init__(self, env_id: str = "Stratego-v0", **rule_opts):
        # TODO: make various option to play
        # Stratego original as default, if the user want to play duel mode, env_id = "Stratego-duel"
        # rule_opts: e.g. board_size=10, etc.
        # find a way to replace original init file, registration file and put more environment such as Stratego-duel
        # in original textarena library by running or installing the program.
        # You can see which file should be edited in backup folder.
        # Don't worry, this should be done with Package managing team.
        self.env = ta.make(env_id=env_id)
        self.rule_opts = rule_opts

    def reset(self, num_players: int = 2):
        self.env.reset(num_players=num_players)

    def get_observation(self):
        return self.env.get_observation()

    def step(self, action: str):
        return self.env.step(action=action)

    def close(self):
        return self.env.close()
