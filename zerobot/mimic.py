import asyncio
import aiofiles
import sys
import json
import re
import random

import disnake
import sqlalchemy.future

import zerobot.entrypoint
from zerobot.db.engine import get_session
from zerobot.db.models import UserMessage
from zerobot.utils.state import state_path

EMOJI_SUBSTITUTER = re.compile(r"<(:\s*(.*?):\s*)([0-9]+)>")


def _model_path(server_id: int, user_id: int) -> str:
    # uncomment for per-server per-user
    #return f"servers/{server_id}/{user_id}"

    # per-user global messages
    return f"servers/{server_id}"


class ModelOperationException(Exception):
    pass


class Mimic:
    @staticmethod
    async def train(guild_id: int, user_id: int) -> dict:
        """
        Blocking function to train a model. Should run in a subprocess only.
        """

        # build the model state path
        state_dir = state_path().joinpath("mimic", "models", "gpt2")
        state_dir.mkdir(exist_ok=True, parents=True)

        state_model_dir = state_dir.joinpath(_model_path(guild_id, user_id))
        state_model_dir.mkdir(exist_ok=True, parents=True)

        cache_dir = state_dir.joinpath("cache")
        cache_dir.mkdir(exist_ok=True)

        async with aiofiles.tempfile.NamedTemporaryFile("w", suffix=".txt") as f:
            # 1. write out the cached messages to temporary file
            async with get_session() as session:
                query = sqlalchemy.future.select(UserMessage)
                query = query.filter(UserMessage.guild == guild_id)
                #query = query.filter(UserMessage.author == user)
                query = query.filter(UserMessage.deleted != True)
                result = await session.execute(query)

                results = result.scalars()

                user_name_cache = {}
                message_count = 0

                for i, message in enumerate(results):
                    content = str(message.content).strip()

                    # skip any empty messages
                    if content == "" or content.isspace():
                        continue

                    # skip code blocks as they screw up the dataset
                    if content.startswith("```") or content.endswith("```"):
                        continue

                    if not message.author in user_name_cache:
                        try:
                            user = await zerobot.entrypoint.bot.fetch_user(message.author)
                        except disnake.NotFound:
                            user = None
                        except disnake.HTTPException:
                            user = None
                        user_name_cache[message.author] = user
                    else:
                        user = user_name_cache[message.author]
                    
                    if user:
                        user_name = user.name
                    else:
                        user_name = str(message.author)

                    # if i != 0:
                    #     f.write("<|endoftext|>\n")
                    await f.write(f"{user_name}: ")
                    await f.write(content)
                    await f.write("\n")

                    message_count += 1
                
                if message_count <= 0:
                    raise ModelOperationException("No messages stored for this user")

            await f.flush()

            # 2. begin the training session
            # WANDB_API_KEY can be set here
            process = await asyncio.create_subprocess_exec(
                "python3", "-m", "zerobot.cmd.hf_run_clm",
                "--model_name_or_path", "gpt2",
                "--cache_dir", cache_dir,
                "--output_dir", state_model_dir,
                "--do_train", "--train_file", f.name, "--do_eval",
                "--per_device_eval_batch_size", "1",
                "--per_device_train_batch_size", "1",
                "--num_train_epochs", "10",
                "--overwrite_output_dir",

                # takes about an hour on our hardware, a reasonable limit
                #"--max_train_samples", "5000",

                # don't checkpoint models as they can be absolutely huge
                "--save_strategy", "no",

                # send output to the right place
                stdout=asyncio.subprocess.PIPE,
                stderr=sys.stderr,
            )

            result = await process.wait()
            if result != 0:
                raise ModelOperationException(f"Executor failed with exit code {result}")
            
        # now read and return back the model statistics
        all_results = None
        all_results_file = state_model_dir.joinpath("all_results.json")
        if all_results_file.exists():
            with open(all_results_file, "r") as f:
                all_results = json.load(f)
        return all_results
    
    @staticmethod
    async def run(guild_id: int, user_id: int, prompt: str) -> str:
        # build the model state path
        state_dir = state_path().joinpath("mimic", "models", "gpt2")
        state_model_dir = state_dir.joinpath(_model_path(guild_id, user_id))
        if not state_model_dir.exists():
            raise ModelOperationException("The model does not exist!")

        if prompt is None:
            raise ModelOperationException("Prompt cannot be None")

        # generate 25 sequences and pick the longest one
        process = await asyncio.create_subprocess_exec(
            "python3", "-m", "zerobot.cmd.hf_run_gen",
            "--model_type", "gpt2",
            "--model_name_or_path", state_model_dir,
            "--prompt", prompt,
            "--length", "150",
            "--num_return_sequences", "1",
            "--stop_token", "<|endoftext|>",
            "--seed", str(random.randint(0, 2**32)),
            stdout=asyncio.subprocess.PIPE,
            stderr=sys.stderr,
        )

        stdout, _ = await process.communicate()
        result = process.returncode
        if result != 0:
            raise ModelOperationException(f"Executor failed with exit code {result}")

        sequences: list[str] = json.loads(stdout.decode())
        sequences = [text.strip() for text in sequences]
        sequences = [text for text in sequences if not text == "" and not text.isspace()]
        if len(sequences) <= 0:
            raise ModelOperationException("No responses returned that weren't blank!")

        # sort by length
        sequences = list(sorted(sequences, key=len))

        # pick a random message out of the 10 longest messages
        # print(sequences)
        # print(sequences[-10:])
        sequence = random.choice(sequences[-10:])

        # truncate the last line of the sequence
        sequence_spl = sequence.split("\n")
        sequence_spl.pop()
        sequence_spl = [" ".join(line.split()) for line in sequence_spl]
        sequence = "\n".join(sequence_spl)

        # try to remove blank whitespace
        # sequence = " ".join(sequence.split())

        # remove all but the last line of the prompt
        prompt_less_last = "\n".join(prompt.split("\n")[:-1])
        sequence = sequence.removeprefix(prompt_less_last).removeprefix("\n")

        return sequence

    @staticmethod
    async def run_contextual(source: disnake.Message, user: disnake.User):
        # grab last 5 messages from the channel to use as context
        # limit 25 and clamp to 5 just in case most are from our bot user
        # texts = []
        # async for message in source.channel.history(limit=50):
        #     if message.author == zerobot.entrypoint.bot.user:
        #         continue
        #     content = message.clean_content
        #     content = str(content).strip()
        #     content = EMOJI_SUBSTITUTER.sub(r"\1", content)
            
        #     if content == "" or content.isspace():
        #         continue
        #     if content.startswith("```") or content.endswith("```"):
        #         continue
        #     if "xz, mimic" in content.lower():
        #         continue
        #     texts.append(content)
        # texts = texts[:5]

        # # wtf? we don't have anything??? just use a blank text
        # if len(texts) > 0:
        #     prompt = "\n".join(texts)
        # else:
        #     prompt = " "

        result = await Mimic.run(source.id, user.id, " ")
        await source.channel.send(result)
