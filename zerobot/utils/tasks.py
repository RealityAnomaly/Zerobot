import asyncio
import logging
from typing import Coroutine, Union
from concurrent.futures import ProcessPoolExecutor, Future

from disnake.interactions import ApplicationCommandInteraction
from disnake.embeds import Embed

from zerobot.utils.disnake import malfunction_followup


logger = logging.getLogger(__name__)


async def _run_deferred_interaction(coro, inter: ApplicationCommandInteraction):
    try:
        # if we respond with something, use it to easily respond to the interaction
        result: Union[str, Embed] = await coro
        if isinstance(result, str):
            await inter.followup.send(result)
        elif isinstance(result, Embed):
            await inter.followup.send(embed=result)
    except Exception as e:
        logger.exception("background task returned exception: %s" % e)
        await malfunction_followup(inter, e)


def create_deferred_interaction(
    coro, inter: ApplicationCommandInteraction
) -> asyncio.Task:
    return asyncio.create_task(_run_deferred_interaction(coro, inter))


def create_deferred_interaction_mp(
    coro, args, inter: ApplicationCommandInteraction
) -> Future:
    loop = asyncio.get_event_loop()
    future = loop.run_in_executor(ProcessPoolExecutor(), coro, *args)
    return asyncio.create_task(_run_deferred_interaction(future, inter))
