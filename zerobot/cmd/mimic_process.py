import sys
import json
import argparse
import tempfile
from pathlib import Path

import aitextgen
import aitextgen.utils
import aitextgen.tokenizers
import aitextgen.TokenDataset

from zerobot.utils.state import state_path

def _train_internal(input_file: str, cache_dir: Path, state_model_dir: Path):
    ai = aitextgen.aitextgen(
        tf_gpt2="124M",
        to_gpu=True,
        cache_dir=str(cache_dir)
    )

    ai.train(
        input_file,
        line_by_line=True,
        from_cache=False,
        num_steps=3000,
        generate_every=1000,
        learning_rate=1e-3,
        batch_size=1,
        output_dir=str(state_model_dir)
    )

    # print(ai.generate(10, prompt="Ness"))


def _run_internal(prompt: str, cache_dir: Path, state_model_dir: Path) -> str:
    ai = aitextgen.aitextgen(
        to_gpu=True,
        model_folder=str(state_model_dir)
    )

    #ai.generate()

    return ai.generate(
        n=1,
        prompt="ness is a robot",
        temperature=0.9,
        max_length=120,
    )

    #return ai.generate_one(prompt=prompt, max_length=60)


def main():
    parser = argparse.ArgumentParser(prog="mimic_process", description="Mimic subprocess executor for aitextgen")
    parser.add_argument("--user", required=True, help="The user ID to use")
    parser.add_argument("--guild", required=True, help="The guild ID to use")

    subparsers = parser.add_subparsers(dest="command")

    train = subparsers.add_parser("train", help="train the model")
    train.add_argument("--data", required=True, help="training source data")

    run = subparsers.add_parser("run", help="run the model")
    run.add_argument("--prompt", required=True, help="the prompt to use to generate text")

    args = parser.parse_args()

    # find the model state dir
    state_dir = state_path().joinpath("mimic", "models", "gpt2")
    state_dir.mkdir(exist_ok=True, parents=True)

    cache_dir = state_dir.joinpath("cache")
    cache_dir.mkdir(exist_ok=True)

    state_model_dir = state_dir.joinpath(f"servers/{args.guild}/{args.user}")
    state_model_dir.mkdir(exist_ok=True, parents=True)

    if args.command == "train":
        _train_internal(args.data, cache_dir, state_model_dir)
    elif args.command == "run":
        print(_run_internal(args.prompt, cache_dir, state_model_dir))

if __name__ == "__main__":
    main()
