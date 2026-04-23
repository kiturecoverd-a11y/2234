import discord
from discord.ext import commands
from utils.logger import setup_logger
from config.config import Config
from utils.helpers import build_embed

logger = setup_logger(__name__)


class MessageEvents(commands.Cog):
    """Handle message and command error events."""

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        """Log messages for audit trail; ignore bot messages and DMs."""
        if message.author == self.bot.user:
            return

        if isinstance(message.channel, discord.DMChannel):
            logger.info(f"📨 DM from {message.author}: {message.content[:200]}")
            return

        logger.debug(f"💬 {message.author} in #{message.channel}: {message.content[:200]}")

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
