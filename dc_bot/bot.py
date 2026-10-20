from datetime import datetime, timedelta, timezone
import logging
import os
from pathlib import Path

import discord
from discord import app_commands
from dotenv import load_dotenv


logger = logging.getLogger(__name__)


def load_config() -> tuple[str, int | None]:
    """Read local configuration without overriding deployment environment variables."""
    load_dotenv(Path(__file__).with_name(".env"))
    token = os.getenv("DISCORD_TOKEN", "").strip()
    if not token or token == "your_bot_token_here":
        raise ValueError("Set DISCORD_TOKEN in .env or your environment before starting.")

    guild_value = os.getenv("DISCORD_GUILD_ID", "").strip()
    if guild_value and (not guild_value.isascii() or not guild_value.isdecimal() or int(guild_value) <= 0):
        raise ValueError("DISCORD_GUILD_ID must be a positive server ID, or blank.")
    return token, int(guild_value) if guild_value else None


def sample_match_embed() -> discord.Embed:
    """Build fictional data until the sports backend is connected."""
    starts_at = datetime.now(timezone.utc) + timedelta(minutes=30)
    embed = discord.Embed(
        title="Team Blue vs Team Red",
        description="Sample upcoming match notification. This is fictional data.",
        color=discord.Color.blue(),
    )
    embed.add_field(name="Competition", value="League of Legends - Demo League", inline=False)
    embed.add_field(name="Format", value="Best of 3")
    embed.add_field(name="Starts", value=discord.utils.format_dt(starts_at, style="F"))
    embed.set_footer(text="Sport Reporter | Demo only")
    return embed


class SportReporterBot(discord.Client):
    def __init__(self, guild_id: int | None = None) -> None:
        super().__init__(intents=discord.Intents.default(), allowed_mentions=discord.AllowedMentions.none())
        self.guild_id = guild_id
        self.tree = app_commands.CommandTree(self)
        self.tree.command(name="ping", description="Check whether Sport Reporter is online.")(self.ping)
        self.tree.command(name="sample", description="Show a fictional sports notification.")(self.sample)

    async def setup_hook(self) -> None:
        # Sync once on login, rather than every gateway reconnect.
        if self.guild_id is not None:
            guild = discord.Object(id=self.guild_id)
            self.tree.copy_global_to(guild=guild)
            commands = await self.tree.sync(guild=guild)
        else:
            commands = await self.tree.sync()
        logger.info("Synced %d slash commands", len(commands))

    async def on_ready(self) -> None:
        logger.info("Sport Reporter is online as %s", self.user)

    async def ping(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message("Pong! Sport Reporter is online.", ephemeral=True)

    async def sample(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(embed=sample_match_embed())


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    try:
        token, guild_id = load_config()
    except ValueError as exc:
        raise SystemExit(str(exc)) from None
    bot = SportReporterBot(guild_id)
    try:
        bot.run(token, log_handler=None)
    except discord.LoginFailure:
        raise SystemExit("Discord rejected DISCORD_TOKEN. Check your bot token.") from None


if __name__ == "__main__":
    main()
