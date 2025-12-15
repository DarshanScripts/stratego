from __future__ import annotations
import shutil
from pathlib import Path
import textarena
import textarena.envs.registration as _reg
from textarena.wrappers import LLMObservationWrapper, ActionFormattingWrapper, GameMessagesAndCurrentBoardObservationWrapper, GameMessagesObservationWrapper, GameBoardObservationWrapper, ClipCharactersActionWrapper, SettlersOfCatanObservationWrapper


def get_textarena_env_dir() -> Path:
    ta_root = Path(textarena.__file__).resolve().parent
    env_root = ta_root / "envs"
    if env_root.exists():
        return env_root
    
def install_strategos():
    stratego_directory = Path(__file__).resolve().parent
    src_dir = stratego_directory / "env" / "backup" / "edited_env"
    # reg = src_dir / "__init__.txt"
    
    for path in ["Stratego", "StrategoDuel", "StrategoCustom"]:
        env = src_dir / path / "env.py"
        init = src_dir / path / "__init__.py"
        if not env.exists():
            raise FileNotFoundError(f"{env} file not found!")
        if not init.exists():
            raise FileNotFoundError(f"{init} file not found!")
        ta_dir = get_textarena_env_dir()
        dst_dir = ta_dir / path
        dst_dir.mkdir(parents=True, exist_ok=True)
        dst_env = dst_dir / "env.py"
        shutil.copy2(env, dst_env)
        dst_init = dst_dir / "__init__.py"
        shutil.copy2(init, dst_init)
        print(f"{path} env installed!")
    
    ta_init = ta_dir / "__init__.py"
    if not ta_init.exists():
        raise FileNotFoundError("Init file of textarena env is not found!")
    
    # registration_code = reg.read_text(encoding="utf-8")
    
    # marker = "#--- Initializing StrategoDuel ---#"
    # if marker in ta_init.read_text(encoding="utf-8"):
    #     print("Stratego duel arleady exists in init file")
    #     return
    
    # with ta_init.open("a", encoding="utf-8") as f:
    #     f.write("\n\n" + marker + "\n")
    #     f.write(registration_code + "\n")
    DEFAULT_WRAPPERS = [LLMObservationWrapper, ActionFormattingWrapper]
    BOARDGAME_WRAPPERS = [GameMessagesAndCurrentBoardObservationWrapper, ActionFormattingWrapper]
    try:
        _reg.register_with_versions(id="Stratego-duel", entry_point="textarena.envs.StrategoDuel.env:StrategoDuelEnv", wrappers={"default": DEFAULT_WRAPPERS, "-train": BOARDGAME_WRAPPERS})
        _reg.register_with_versions(id="Stratego-custom", entry_point="textarena.envs.StrategoCustom.env:StrategoCustomEnv", wrappers={"default": DEFAULT_WRAPPERS, "-train": BOARDGAME_WRAPPERS})
        print("Stratego Games are newly registered!")
    except ValueError:
        print("Stratego Games are already registered!")
        pass
def main():
    install_strategos()