import time
import platform
import discord
from discord.ext import commands

from config.config import Config
from utils.logger import setup_logger
from utils.helpers import build_embed, format_bytes

logger = setup_logger(__name__)


class Utility(commands.Cog):
    """General-purpose utility commands."""

    def __init__(self, bot):
        self.bot = bot
        self.start_time = time.time()

    # ──────────────────────────────────────────────────────────────────────────
    # !ping
    # ──────────────────────────────────────────────────────────────────────────
    @commands.command(name='ping', help='Check bot latency.')
    async def ping(self, ctx):
        """Display bot gateway latency."""
        latency_ms = round(self.bot.latency * 1000)

        embed = build_embed(
            title="🏓 Pong!",
            description=f"**Gateway Latency:** `{latency_ms} ms`",
            color=Config.EMBED_COLOR_SUCCESS,
            ctx=ctx
        )
        await ctx.reply(embed=embed, mention_author=False)

    # ──────────────────────────────────────────────────────────────────────────
    # !fileinfo
    # ──────────────────────────────────────────────────────────────────────────
    @commands.command(name='fileinfo', aliases=['finfo'], help='Show file transfer limits and info.')
    async def file_info(self, ctx):
        """Display current file transfer configuration."""
        max_mb = Config.MAX_FILE_SIZE / (1024 * 1024)
        exts = ", ".join(f"`{e}`" for e in Config.ALLOWED_FILE_EXTENSIONS)

        embed = build_embed(
            title="📋 File Transfer Info",
            color=Config.EMBED_COLOR_INFO,
            ctx=ctx
        )
        embed.add_field(name="📦 Max File Size", value=f"`{max_mb:.0f} MB`", inline=True)
        embed.add_field(name="📁 Max Per Command", value=f"`{Config.MAX_FILES_PER_COMMAND}`", inline=True)
        embed.add_field(name="⏳ Cooldown", value=f"`{Config.COOLDOWN_SECONDS}s`", inline=True)
        embed.add_field(name="✅ Allowed Extensions", value=exts, inline=False)
        embed.add_field(
            name="🛠 How to Use",
            value=(
                f"`{Config.PREFIX}sendfile @user` — attach file(s)\n"
                f"`{Config.PREFIX}sendmsg @user <msg>` — DM text\n"
                f"`{Config.PREFIX}sendrole @role <msg>` — DM everyone in a role"
            ),
            inline=False
        )
        await ctx.reply(embed=embed, mention_author=False)

    # ──────────────────────────────────────────────────────────────────────────
    # !info / !about
    # ──────────────────────────────────────────────────────────────────────────
    @commands.command(name='info', aliases=['about'], help='Show bot information.')
    async def info(self, ctx):
        """Display bot statistics and metadata."""
        uptime_sec = int(time.time() - self.start_time)
        hours, remainder = divmod(uptime_sec, 3600)
        minutes, seconds = divmod(remainder, 60)
        days, hours = divmod(hours, 24)
        uptime_str = f"{days}d {hours}h {minutes}m {seconds}s"

        embed = build_embed(
            title=f"🤖 {Config.BOT_NAME}",
            description=Config.BOT_DESCRIPTION,
            color=Config.EMBED_COLOR_PRIMARY,
            ctx=ctx
        )
        embed.add_field(name="Version", value=f"`{Config.BOT_VERSION}`", inline=True)
        embed.add_field(name="Library", value=f"`discord.py {discord.__version__}`", inline=True)
        embed.add_field(name="Python", value=f"`{platform.python_version()}`", inline=True)
        embed.add_field(name="Servers", value=f"`{len(self.bot.guilds)}`", inline=True)
        embed.add_field(name="Users", value=f"`{sum(g.member_count or 0 for g in self.bot.guilds)}`", inline=True)
        embed.add_field(name="Uptime", value=f"`{uptime_str}`", inline=True)
        if self.bot.user.display_avatar:
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        await ctx.reply(embed=embed, mention_author=False)

    # ──────────────────────────────────────────────────────────────────────────
    # !help [command]
    # ──────────────────────────────────────────────────────────────────────────
    @commands.command(name='help', aliases=['h', 'commands'], help='Show this help message.')
    async def help_command(self, ctx, *, command_name: str = None):
        """Show detailed help for all commands or a specific command."""
        if command_name:
            cmd = self.bot.get_command(command_name)
            if not cmd:
                embed = build_embed(
                    title="❌ Unknown Command",
                    description=f"No command named `{command_name}`.",
                    color=Config.EMBED_COLOR_ERROR,
                    ctx=ctx
                )
                await ctx.reply(embed=embed, mention_author=False)
                return

            embed = build_embed(
                title=f"📖 Help — {Config.PREFIX}{cmd.name}",
                description=cmd.help or "No description available.",
                color=Config.EMBED_COLOR_INFO,
                ctx=ctx
            )
            if cmd.aliases:
                embed.add_field(
                    name="Aliases",
                    value=", ".join(f"`{a}`" for a in cmd.aliases),
                    inline=False
                )
            embed.add_field(
                name="Usage",
                value=f"`{Config.PREFIX}{cmd.name}`",
                inline=False
            )
            await ctx.reply(embed=embed, mention_author=False)
            return

        # Full help menu
        embed = build_embed(
            title=f"📖 {Config.BOT_NAME} — Commands",
            description=f"Prefix: `{Config.PREFIX}` • Use `{Config.PREFIX}help <command>` for details.",
            color=Config.EMBED_COLOR_PRIMARY,
            ctx=ctx
        )

        # Group by cog
        for cog_name, cog in self.bot.cogs.items():
            cmds = [c for c in cog.get_commands() if not c.hidden]
            if not cmds:
                continue
            value = "\n".join(
                f"`{Config.PREFIX}{c.name}` — {(c.help or '').splitlines()[0]}"
                for c in cmds
            )
            embed.add_field(name=f"📂 {cog_name}", value=value, inline=False)

        embed.add_field(
            name="🔗 Invite Bot",
            value="[Click to invite](https://discord.com/oauth2/authorize?client_id="
                  f"{self.bot.user.id}&scope=bot&permissions=76864)",
            inline=False
        )

        await ctx.reply(embed=embed, mention_author=False)


async def setup(bot):
    await bot.add_cog(Utility(bot))
    logger.info("Utility cog loaded")
