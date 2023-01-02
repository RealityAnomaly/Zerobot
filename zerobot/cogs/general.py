import logging

import disnake.ext.commands
from disnake.ext.commands import Cog, Bot, slash_command
from disnake.interactions import ApplicationCommandInteraction

from zerobot.utils.beep import generate_beeps


logger = logging.getLogger(__name__)


class General(Cog):
    def __init__(self, bot: Bot):
        self.bot: Bot = bot

    @slash_command(description="Respond with a random beep")
    async def beep(self, inter: ApplicationCommandInteraction):
        await inter.response.send_message(generate_beeps())


def setup(bot: Bot):
    bot.add_cog(General(bot))
    logger.info(f"Extension {__name__} became ready")
