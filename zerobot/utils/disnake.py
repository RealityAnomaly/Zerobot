import disnake
import disnake.ui

from disnake.embeds import Embed
from disnake.interactions import ApplicationCommandInteraction

def _malfunction_embed(inter: ApplicationCommandInteraction, exc: Exception) -> Embed:
    emoji_map = {
        "PicklingError": "🥒"
    }

    name = exc.__class__.__name__
    emoji = emoji_map.get(name, "⚠️")

    embed = Embed(
        title="Malfunction detected",
        description="I'm sorry :(",
        color=16711680 # red
    )

    embed.set_thumbnail(url="https://f003.backblazeb2.com/file/reflector2/bot/malfunction.png")
    embed.add_field("Exception", f"{emoji} `{name}`")
    embed.set_footer(text="Contact a developer :)")

    return embed


async def malfunction_followup(inter: ApplicationCommandInteraction, exc: Exception):
    components = [
        disnake.ui.Button(
            style=disnake.ButtonStyle.gray,
            custom_id="investigate_exception",
            label="Investigate",
            emoji="❓"
        )
    ]

    await inter.followup.send(
        embed=_malfunction_embed(inter, exc),
        components=components
    )
