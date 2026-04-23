import discord
from discord.ext import commands
from utils.logger import setup_logger
from config.config import Config

logger = setup_logger(__name__)


class BotEvents(commands.Cog):
    """Handle bot lifecycle events."""

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        """Called when the bot has connected and is ready."""
        logger.info(f"✅ Bot logged in as {self.bot.user}")
        logger.info(f"   Bot ID:    {self.bot.user.id}")
        logger.info(f"   Name:      {Config.BOT_NAME} v{Config.BOT_VERSION}")
        logger.info(f"   Guilds:    {len(self.bot.guilds)}")
        logger.info(f"   Users:     {sum(g.member_count or 0 for g in self.bot.guilds)}")

        # Set presence
        activity = discord.Activity(
            type=discord.ActivityType.playing,
            name=f"{Config.BOT_NAME} v{Config.BOT_VERSION}"
        )
        await self.bot.change_presence(activity=activity)
        logger.info("✅ Bot is ready and online!")

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        """Log when the bot joins a new server."""
        logger.info(f"📥 Joined guild: {guild.name} (ID: {guild.id}, Members: {guild.member_count})")

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        """Log when the bot is removed from a server."""
        logger.warning(f"📤 Removed from guild: {guild.name} (ID: {guild.id})")


async def setup(bot):
    await bot.add_cog(BotEvents(bot))
    logger.info("BotEvents cog loaded")
