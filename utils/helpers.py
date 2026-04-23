import discord
from discord.ext import commands
from config.config import Config


def is_owner():
    """
    Check if the command author is in OWNER_IDS.
    If no owners are configured, fallback to guild owner (safer default).
    """
    async def predicate(ctx):
        if not Config.OWNER_IDS:
            # If no owners configured, allow only if guild owner
            if ctx.guild and ctx.author.id == ctx.guild.owner_id:
                return True
            raise commands.NotOwner(
                "This command is restricted to bot owners. "
                "Set OWNER_IDS in your environment variables."
            )
        if ctx.author.id not in Config.OWNER_IDS:
            raise commands.NotOwner("This command is restricted to bot owners.")
        return True
    return commands.check(predicate)


def format_bytes(size):
    """Human-readable byte formatter."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} PB"


def build_embed(title=None, description=None, color=None, ctx=None, footer_override=None):
    """Factory for consistent, professional embed styling."""
    embed = discord.Embed(
        title=title,
        description=description,
        color=color or Config.EMBED_COLOR_PRIMARY,
        timestamp=discord.utils.utcnow()
    )
    if footer_override:
        embed.set_footer(text=footer_override)
    elif ctx:
        embed.set_footer(
            text=f"{Config.BOT_NAME} v{Config.BOT_VERSION} • {ctx.author}",
            icon_url=ctx.author.display_avatar.url if ctx.author.display_avatar else None
        )
    else:
        embed.set_footer(text=f"{Config.BOT_NAME} v{Config.BOT_VERSION}")
    return embed
