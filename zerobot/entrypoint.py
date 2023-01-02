import disnake
import disnake.ext.commands
import disnake.ext.tasks
import logging

import os
import re
import toml
import asyncio
from datetime import datetime

import zerobot.mcache
from zerobot.mimic import Mimic
import zerobot.utils.beep
import zerobot.db.engine

config = None

bot = disnake.ext.commands.Bot(
    command_prefix="!",
    intents=disnake.Intents.all(),
    help_command=None,
    sync_commands_debug=True,
)

logger = logging.getLogger(__name__)
assets_dir = os.path.join(os.path.dirname(__name__), "assets")

BEEP_PATTERN = re.compile("b[eo]{2,10}p")

# suppresses the silly warning when we run tokenizers in a subprocess
# https://stackoverflow.com/questions/62691279/how-to-disable-tokenizers-parallelism-true-false-warning
os.environ["TOKENIZERS_PARALLELISM"] = "false"


@bot.event
async def on_ready():
    logger.info(f"Bot is now ready as {bot.user}")
    update_status.start()

    # kick off delta mcache backfill jobs for our guilds
    for guild in bot.guilds:
        asyncio.create_task(
            zerobot.mcache.deferred_backfill(bot, guild, datetime.now())
        )


@bot.event
async def on_message(message: disnake.Message):
    if message.author == bot.user:
        return

    # run the message through mcache
    await zerobot.mcache.update_message(message)

    content_lower = message.content.lower()

    if message.guild.id in config["authority"]["beep_allowed_servers"]:
        if BEEP_PATTERN.match(content_lower):
            await message.channel.send(zerobot.utils.beep.generate_beeps())
            return


@bot.event
async def on_message_delete(message: disnake.Message):
    if message.author == bot.user:
        return
    await zerobot.mcache.delete_message(message)


@bot.event
async def on_message_edit(before: disnake.Message, after: disnake.Message):
    if after.author == bot.user:
        return
    await zerobot.mcache.update_message(after)


@disnake.ext.tasks.loop(minutes=5.0)
async def update_status():
    await bot.change_presence(
        activity=disnake.Activity(type=disnake.ActivityType.watching, name="everyone")
    )


cogs_path = os.path.join(__package__, "cogs")
bot.load_extensions(cogs_path)


def configure_logging():
    _logger = logging.getLogger()
    _logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s")

    stderr_handler = logging.StreamHandler()
    stderr_handler.setFormatter(formatter)
    _logger.addHandler(stderr_handler)

    file_handler = logging.FileHandler(
        filename="zerobot.log", encoding="utf-8", mode="w"
    )
    file_handler.setFormatter(formatter)
    _logger.addHandler(file_handler)


def main():
    # set up logging output
    configure_logging()

    # initialise the database engine
    asyncio.run(zerobot.db.engine.init_engine())

    global config
    with open("config.toml", "r") as f:
        config = toml.load(f)
    bot.run(config["account"]["token"])
