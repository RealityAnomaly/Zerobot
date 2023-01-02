import asyncio
import logging

import sqlalchemy

import disnake
import disnake.ui
import disnake.ext.commands

from disnake.ext.commands import Cog, Bot, Param, slash_command
from disnake.interactions import ApplicationCommandInteraction

import zerobot.entrypoint
import zerobot.db.engine
import zerobot.db.models
from zerobot.mimic import Mimic
from zerobot.utils.tasks import create_deferred_interaction


logger = logging.getLogger(__name__)


class MimicCog(Cog):
    def __init__(self, bot: Bot):
        self.bot: Bot = bot

        # is a job currently active?
        self.current_job: asyncio.Task = None
    
    async def _training_job(
        self,
        inter: ApplicationCommandInteraction,
        guild: int,
        user: disnake.User,
    ):
        stats = await Mimic.train(guild, user.id)

        embed = disnake.Embed(
            title="Success", description="✅ Training completed", color=65280
        )

        def to_code(text: str):
            return f"`{text}`"

        embed.add_field("Epoch", to_code(str(stats.get("epoch", -1))))
        embed.add_field("Loss", to_code(str(stats.get("train_loss", -1))))
        embed.add_field("Runtime", to_code(str(stats.get("train_runtime", -1))))
        embed.add_field("Perplexity", to_code(str(stats.get("perplexity", -1))))
        embed.add_field("Samples", to_code(str(stats.get("train_samples", -1))))

        await inter.followup.send(embed=embed)


    async def _running_job(
        self, inter: ApplicationCommandInteraction, guild: int, user: disnake.User, prompt: str
    ):
        result = await Mimic.run(guild, user.id, f"{prompt}")

        # indent everything
        result_indented = result.split("\n")
        result_indented = [f"> {line}" for line in result_indented]
        result_indented = "\n".join(result_indented)

        # return f"{user.display_name}: {result}"
        message = await inter.followup.send(
            result_indented, wait=True, view=MimicResponseView(self)
        )

        # now create the entry in the MimicFrontendResponse table for this job
        async with zerobot.db.engine.get_session() as session:
            model = zerobot.db.models.MimicFrontendResponse(
                id=message.id, content=result, deleted=False
            )

            await session.merge(model)
            await session.commit()

    @slash_command(
        # no point on giving DM access, there's no useful history to train on
        dm_permission=False
    )
    async def mimic(self, _: ApplicationCommandInteraction):
        pass

    @mimic.sub_command(
        description="Start training the RCX Mimic model for the specified user"
    )
    async def train(
        self,
        inter: ApplicationCommandInteraction,
        user: disnake.User = Param(description="The user to train the model on"),
    ):
        if inter.user.id != zerobot.entrypoint.config["authority"]["admin"]:
            await inter.followup.send("This command is only executable by the RCX Administrator")
            return

        # components = [
        #     disnake.ui.Select()
        # ]

        # modal = disnake.ui.Modal(
        #     title="Training Parameters"
        #     components=[],
        #     custom_id="mimic_train"
        # )

        # await inter.response.send_modal()

        if self.current_job and not self.current_job.done():
            await inter.response.send_message("The bot is already busy running a job!")
            return

        self.current_job = create_deferred_interaction(
            self._training_job(inter, inter.guild_id, user), inter
        )

        await inter.response.defer()

    @mimic.sub_command(description="Run the RCX Mimic model for the specified user")
    async def run(
        self,
        inter: ApplicationCommandInteraction,
        user: disnake.User = Param(description="The user to run the model on"),
        prompt: str = Param(description="The prompt to pass to the model"),
    ):
        if self.current_job and not self.current_job.done():
            await inter.response.send_message("The bot is already busy running a job!")
            return

        prompt = f"{user.name}: {prompt}"
        self.current_job = create_deferred_interaction(
            self._running_job(inter, inter.guild_id, user, prompt), inter
        )

        await inter.response.defer()


class MimicResponseView(disnake.ui.View):
    def __init__(self, cog: MimicCog):
        super().__init__(timeout=None)
        self._cog = cog

    @disnake.ui.button(
        label="Continue",
        style=disnake.ButtonStyle.blurple,
        custom_id="mimic_response_view:continue",
    )
    async def _continue(self, _: disnake.ui.Button, inter: disnake.MessageInteraction):
        # fetch the original response
        async with zerobot.db.engine.get_session() as session:
            query = sqlalchemy.future.select(zerobot.db.models.MimicFrontendResponse)
            query = query.where(
                zerobot.db.models.MimicFrontendResponse.id == inter.message.id
            )
            query = await session.execute(query)
            result: zerobot.db.models.MimicFrontendResponse = query.scalar_one_or_none()

        if not result:
            print("No Result")
            return

        # truncate to the last 16 lines
        content = "\n".join(result.content.split("\n")[-16:])

        # execute the model
        if self._cog.current_job and not self._cog.current_job.done():
            await inter.response.send_message("The bot is already busy running a job!")
            return

        self._cog.current_job = create_deferred_interaction(
            self._cog._running_job(inter, inter.guild_id, inter.user, content), inter
        )

        await inter.response.defer()

    @disnake.ui.button(
        label="Delete",
        style=disnake.ButtonStyle.danger,
        custom_id="mimic_response_view:delete",
    )
    async def delete(self, _: disnake.ui.Button, inter: disnake.MessageInteraction):
        await inter.message.delete()


def setup(bot: Bot):
    bot.add_cog(MimicCog(bot))
    logger.info(f"extension {__name__} is ready")
