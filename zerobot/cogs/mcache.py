import asyncio
import logging
from typing import Mapping

import disnake
import disnake.ext.tasks
import disnake.ext.commands

from disnake.ext.commands import Cog, Bot, slash_command, default_member_permissions
from disnake.interactions import ApplicationCommandInteraction

import zerobot.entrypoint
import zerobot.mcache
from zerobot.utils.tasks import create_deferred_interaction


logger = logging.getLogger(__name__)


class McacheCog(Cog):
    def __init__(self, bot: Bot):
        self.bot: Bot = bot
        self.current_jobs: Mapping[int, asyncio.Task] = {}

    async def _backfill_job(self, inter: ApplicationCommandInteraction):
        # run the job
        stats = await zerobot.mcache.backfill(self.bot, inter.guild)

        # complete
        embed = disnake.Embed(
            title="I did it",
            description="✅ Backfill job completed!",
            color=65280, # green
        )

        embed.add_field("Processed", str(stats.processed))
        embed.add_field("Updated", str(stats.updated))

        await inter.followup.send(embed=embed)

    @slash_command(dm_permission=False)
    @default_member_permissions(administrator=True)
    async def mcache(self, _: ApplicationCommandInteraction):
        pass

    @mcache.sub_command(
        description="Initiate a manual backfill of messages seen by RCX MCache"
    )
    async def backfill(self, inter: ApplicationCommandInteraction):
        if inter.user.id != zerobot.entrypoint.config["authority"]["admin"]:
            await inter.followup.send("This command is only executable by the RCX Administrator")
            return

        current_job = self.current_jobs.get(inter.guild_id)
        if current_job and not current_job.done():
            # only one job per guild ID can be running at once
            await inter.response.send_message("The bot is already busy running a job!")
            return

        self.current_jobs[inter.guild_id] = create_deferred_interaction(
            self._backfill_job(inter), inter
        )

        await inter.response.defer()


def setup(bot: Bot):
    bot.add_cog(McacheCog(bot))
    logger.info(f"extension {__name__} is ready")
