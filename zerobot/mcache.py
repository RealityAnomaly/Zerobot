from datetime import datetime
import disnake
import disnake.ext.commands
import logging
import re

import sqlalchemy
import sqlalchemy.future
from sqlalchemy.ext.asyncio import AsyncSession

from zerobot.db.engine import get_session
from zerobot.db.models import UserMessage, Guild


logger = logging.getLogger(__name__)
EMOJI_SUBSTITUTER = re.compile(r"<(:\s*(.*?):\s*)([0-9]+)>")


class BackfillJobStats:
    processed: int = 0
    updated: int = 0


async def deferred_backfill(bot: disnake.ext.commands.Bot, guild: disnake.Guild, before):
    stats = await backfill(bot, guild, before)
    logger.info(
        f"Deferred backfill completed for guild {guild.id} ({stats.updated}/{stats.processed})"
    )


# backfill every message in the guild
async def backfill(bot: disnake.ext.commands.Bot, guild: disnake.Guild, before=None, force=False) -> BackfillJobStats:
    stats = BackfillJobStats()

    async with get_session() as session:
        # locate the after time
        after = None
        if not force:
            query = sqlalchemy.future.select(Guild)
            query = query.add_columns(Guild.last_backfill)
            query = query.where(Guild.id == guild.id)
            query = await session.execute(query)
            result: Guild = query.scalar_one_or_none()

            if result:
                after = result.last_backfill

        for channel in guild.channels:
            try:
                if channel.type != disnake.ChannelType.text:
                    # don't support anything other than this for now
                    continue
                async for message in channel.history(before=before, after=after, limit=None):
                    # skip our own messages
                    if message.author == bot.user:
                        continue

                    await _update_internal(message, session)
                    stats.processed += 1
            except disnake.errors.Forbidden:
                # we can't read the channel, so ignore
                continue
        
        stats.updated = len(session.dirty)
        await session.commit()

        # set the guild's last backfill time to now
        await session.merge(Guild(id=guild.id, last_backfill=datetime.now()))
        await session.commit()

    return stats


async def _update_internal(message: disnake.Message, session: AsyncSession):
    processed_content = message.clean_content
    #processed_content = EMOJI_SUBSTITUTER.sub(r"\1", processed_content)

    if message.guild is None:
        guild_id = -1
    else:
        guild_id = message.guild.id

    # check if the message exists
    model = UserMessage(
        id=message.id,
        author=message.author.id,
        content=processed_content,
        channel=message.channel.id,
        guild=guild_id,
        edited=message.edited_at,
        deleted=False,
    )

    await session.merge(model)


async def update_message(message: disnake.Message):
    async with get_session() as session:
        await _update_internal(message, session)
        await session.commit()


async def delete_message(message: disnake.Message):
    async with get_session() as session:
        query = sqlalchemy.future.select(sqlalchemy.text("count(*)"))
        query = query.select_from(UserMessage)
        query = query.where(UserMessage.id == message.id)
        query = await session.execute(query)
        if query.scalar() <= 0:
            return
        
        model = UserMessage(
            id=message.id,
            deleted=True
        )

        await session.merge(model)
