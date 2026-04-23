import discord
from discord.ext import commands
from utils.logger import setup_logger
from config.config import Config
from utils.helpers import build_embed
from utils.dm_tracker import should_notify, mark_notified, get_log_channel

logger = setup_logger(__name__)


class MessageEvents(commands.Cog):
    """Handle message and command error events."""

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        """
        Log messages for audit trail.
        Detect DM replies from users who received a bot DM and notify log channel.
        """
        if message.author == self.bot.user:
            return

        # ── DM from a user ──
        if isinstance(message.channel, discord.DMChannel):
            logger.info(f"📨 DM from {message.author}: {message.content[:200]}")

            # Check if this user recently received a DM from us
            if should_notify(message.author.id):
                mark_notified(message.author.id)
                await self._notify_dm_opened(message.author)
            return

        logger.debug(f"💬 {message.author} in #{message.channel}: {message.content[:200]}")

    async def _notify_dm_opened(self, user):
        """Send a notification to the configured log channel that user opened/replied to DM."""
        channel = get_log_channel(self.bot)
        if not channel:
            return

        try:
            embed = discord.Embed(
                title="📬 DM Interaction Detected",
                description=f"{user.mention} (`{user}`) has opened or replied to a DM.",
                color=Config.EMBED_COLOR_INFO,
                timestamp=discord.utils.utcnow()
            )
            embed.set_thumbnail(url=user.display_avatar.url if user.display_avatar else None)
            embed.set_footer(text=f"{Config.BOT_NAME} v{Config.BOT_VERSION}")
            await channel.send(embed=embed)
            logger.info(f"DM-open notification sent for {user} ({user.id})")
        except Exception as exc:
            logger.error(f"Failed to send DM-open notification: {exc}")

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """Global command error handler with user-friendly embeds."""
        # Ignore CommandNotFound to reduce noise
        if isinstance(error, commands.CommandNotFound):
            return

        # Log the error
        logger.error(f"Command error in '{ctx.command}' by {ctx.author}: {str(error)}")

        # ── Cooldown errors ──
        if isinstance(error, commands.CommandOnCooldown):
            embed = build_embed(
                title="⏳ Cooldown",
                description=f"Please wait `{error.retry_after:.1f}s` before using this command again.",
                color=Config.EMBED_COLOR_WARNING,
                ctx=ctx
            )
            await ctx.reply(embed=embed, mention_author=False, delete_after=10)
            return

        # ── NotOwner ──
        if isinstance(error, commands.NotOwner):
            embed = build_embed(
                title="🚫 Access Denied",
                description="You don't have permission to use this command.",
                color=Config.EMBED_COLOR_ERROR,
                ctx=ctx
            )
            await ctx.reply(embed=embed, mention_author=False, delete_after=10)
            return

        # ── MissingRequiredArgument ──
        if isinstance(error, commands.MissingRequiredArgument):
            embed = build_embed(
                title="❌ Missing Argument",
                description=f"Please provide: `{error.param.name}`\n\n"
                            f"Use `{Config.PREFIX}help {ctx.command}` for usage.",
                color=Config.EMBED_COLOR_ERROR,
                ctx=ctx
            )
            await ctx.reply(embed=embed, mention_author=False, delete_after=15)
            return

        # ── BadArgument ──
        if isinstance(error, commands.BadArgument):
            embed = build_embed(
                title="❌ Invalid Argument",
                description="One of the arguments you provided is invalid.",
                color=Config.EMBED_COLOR_ERROR,
                ctx=ctx
            )
            await ctx.reply(embed=embed, mention_author=False, delete_after=10)
            return

        # ── MissingPermissions ──
        if isinstance(error, commands.MissingPermissions):
            perms = ", ".join(f"`{p}`" for p in error.missing_permissions)
            embed = build_embed(
                title="🚫 Missing Permissions",
                description=f"You need: {perms}",
                color=Config.EMBED_COLOR_ERROR,
                ctx=ctx
            )
            await ctx.reply(embed=embed, mention_author=False, delete_after=10)
            return

        # ── BotMissingPermissions ──
        if isinstance(error, commands.BotMissingPermissions):
            perms = ", ".join(f"`{p}`" for p in error.missing_permissions)
            embed = build_embed(
                title="🚫 Bot Missing Permissions",
                description=f"I need: {perms} to do that.",
                color=Config.EMBED_COLOR_ERROR,
                ctx=ctx
            )
            await ctx.reply(embed=embed, mention_author=False, delete_after=10)
            return

        # ── GuildOnly ──
        if isinstance(error, commands.NoPrivateMessage):
            embed = build_embed(
                title="❌ Server Only",
                description="This command can only be used inside a server.",
                color=Config.EMBED_COLOR_ERROR,
                ctx=ctx
            )
            await ctx.reply(embed=embed, mention_author=False, delete_after=10)
            return

        # ── Generic fallback ──
        embed = build_embed(
            title="❌ Error",
            description=f"An unexpected error occurred:\n```\n{str(error)[:500]}\n```",
            color=Config.EMBED_COLOR_ERROR,
            ctx=ctx
        )
        await ctx.reply(embed=embed, mention_author=False, delete_after=30)


async def setup(bot):
    await bot.add_cog(MessageEvents(bot))
    logger.info("MessageEvents cog loaded")
