from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
import logging
import os
from pathlib import Path
from urllib.parse import urlsplit

import discord
import httpx
from discord import app_commands
from dotenv import load_dotenv

from backend_client import BackendClient


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Config:
    token: str
    guild_id: int | None
    backend_url: str
    api_key: str


def load_config() -> Config:
    """Read local configuration without overriding deployment environment variables."""
    load_dotenv(Path(__file__).with_name(".env"))
    token = os.getenv("DISCORD_TOKEN", "").strip()
    if not token or token == "your_bot_token_here":
        raise ValueError("Set DISCORD_TOKEN in .env or your environment before starting.")

    guild_value = os.getenv("DISCORD_GUILD_ID", "").strip()
    if guild_value and (not guild_value.isascii() or not guild_value.isdecimal() or int(guild_value) <= 0):
        raise ValueError("DISCORD_GUILD_ID must be a positive server ID, or blank.")
    backend_url = os.getenv("BACKEND_URL", "").strip().rstrip("/")
    api_key = os.getenv("SPORT_REPORTER_API_KEY", "").strip()
    if bool(backend_url) != bool(api_key):
        raise ValueError("Set both BACKEND_URL and SPORT_REPORTER_API_KEY to enable API commands.")
    if backend_url:
        parsed = urlsplit(backend_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("BACKEND_URL must be an HTTP(S) URL without embedded credentials.")
        if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
            raise ValueError("BACKEND_URL must be the API origin, without a path, query or fragment.")
    return Config(token, int(guild_value) if guild_value else None, backend_url, api_key)


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


def match_embed(match: dict) -> discord.Embed:
    first, second = match["team1"], match["team2"]
    starts_at = datetime.fromisoformat(match["start_time_utc"].replace("Z", "+00:00"))
    if starts_at.utcoffset() is None:
        raise ValueError("Backend match time must include a timezone")
    embed = discord.Embed(
        title=f"{first['name']} vs {second['name']}"[:256],
        description="Fictional demo data." if match.get("is_demo") else "Sports match",
        color=discord.Color.blue(),
    )
    embed.add_field(name="Competition", value=f"{match['sport']} / {match['league']}"[:1024])
    embed.add_field(name="Status", value=str(match["status"])[:1024])
    embed.add_field(name="Starts", value=discord.utils.format_dt(starts_at, style="F"), inline=False)
    if first.get("score") is not None and second.get("score") is not None:
        embed.add_field(name="Score", value=f"{first['score']} - {second['score']}"[:1024])
    embed.add_field(name="Format", value=f"Best of {match['best_of']}")
    embed.set_footer(text="Sport Reporter | Demo only" if match.get("is_demo") else "Sport Reporter")
    return embed


class SportReporterBot(discord.Client):
    def __init__(self, config: Config) -> None:
        super().__init__(intents=discord.Intents.default(), allowed_mentions=discord.AllowedMentions.none())
        self.guild_id = config.guild_id
        self.config = config
        self.backend: BackendClient | None = None
        self.tree = app_commands.CommandTree(self)
        self.tree.command(name="ping", description="Check whether Sport Reporter is online.")(self.ping)
        self.tree.command(name="sample", description="Show a fictional sports notification.")(self.sample)
        self.tree.command(name="upcoming", description="Get upcoming matches from the backend.")(self.upcoming)
        self.tree.command(name="results", description="Get recent match results from the backend.")(self.results)

    async def setup_hook(self) -> None:
        if self.config.backend_url:
            self.backend = BackendClient(self.config.backend_url, self.config.api_key)
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

    async def show_matches(self, interaction: discord.Interaction, route: str, hours: int, leagues: str | None) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        if self.backend is None:
            await interaction.followup.send("Configure BACKEND_URL and SPORT_REPORTER_API_KEY on the bot service.", ephemeral=True)
            return
        try:
            if route == "upcoming":
                matches = await self.backend.upcoming(hours, leagues)
            else:
                since = datetime.now(timezone.utc) - timedelta(hours=hours)
                matches = await self.backend.results(since, leagues)
            # Discord permits up to 10 embeds, with 6000 combined characters.
            embeds = []
            for match in matches[:10]:
                embed = match_embed(match)
                if sum(len(e) for e in embeds) + len(embed) > 6000:
                    break
                embeds.append(embed)
        except httpx.HTTPStatusError as exc:
            logger.warning("Backend returned HTTP %s", exc.response.status_code)
            message = (
                "Backend authentication failed. Check SPORT_REPORTER_API_KEY on both services."
                if exc.response.status_code in {401, 403}
                else "The backend returned an error. Check the backend logs and try again."
            )
            await interaction.followup.send(message, ephemeral=True)
            return
        except (httpx.RequestError, ValueError, KeyError, TypeError):
            logger.warning("Backend request failed or returned invalid match data")
            await interaction.followup.send("Cannot load matches. Check backend readiness, networking, and logs.", ephemeral=True)
            return
        if not embeds:
            await interaction.followup.send("No matches found in this time window.", ephemeral=True)
            return
        text = f"Showing {len(embeds)} of {len(matches)} matches returned by the API."
        await interaction.followup.send(text, embeds=embeds, ephemeral=True)

    async def upcoming(self, interaction: discord.Interaction, hours: app_commands.Range[int, 1, 168] = 24, leagues: str | None = None) -> None:
        await self.show_matches(interaction, "upcoming", hours, leagues)

    async def results(self, interaction: discord.Interaction, hours: app_commands.Range[int, 1, 168] = 24, leagues: str | None = None) -> None:
        await self.show_matches(interaction, "results", hours, leagues)

    async def close(self) -> None:
        if self.backend is not None:
            await self.backend.close()
        await super().close()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    try:
        config = load_config()
    except ValueError as exc:
        raise SystemExit(str(exc)) from None
    bot = SportReporterBot(config)
    try:
        bot.run(config.token, log_handler=None)
    except discord.LoginFailure:
        raise SystemExit("Discord rejected DISCORD_TOKEN. Check your bot token.") from None


if __name__ == "__main__":
    main()
