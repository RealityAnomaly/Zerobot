from pathlib import Path

path_init = False
def state_path() -> Path:
    global path_init

    path = Path.joinpath(Path.cwd(), "state")
    if not path_init:
        path.mkdir(exist_ok=True)
        path_init = True
    return path
