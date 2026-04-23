import asyncio
import discord
from discord.ext import commands

from config.config import Config
from utils.logger import setup_logger
from utils.file_utils import send_attachment_to_dm, validate_file, send_to_dm_with_retry, _get_or_create_dm
from utils.helpers import is_owner, build_embed, format_bytes
from utils.dm_tracker import mark_dm_sent

logger = setup_logger(__name__)


class FileHandler(commands.Cog):
    """Commands for securely forwarding files and messages to user DMs."""

    def __init__(self, bot):
        self.bot = bot

    # ──────────────────────────────────────────────────────────────────────────
    # !sendfile @user [@user2 ...]  (attach one or more files)
    # ──────────────────────────────────────────────────────────────────────────
    @commands.command(
        name='sendfile',
        aliases=['sf', 'send', 'dmfile'],
        help='Send attached file(s) to one or more users via DM.\n'
             'Usage: !sendfile @user1 [@user2 ...] (attach files)'
    )
    @commands.cooldown(1, Config.COOLDOWN_SECONDS, commands.BucketType.user)
    @is_owner()
    async def send_file(self, ctx, users: commands.Greedy[discord.User]):
        """Send attached files to the mentioned users."""

        # ── Validate inputs ──
        if not ctx.message.attachments:
            embed = build_embed(
                title="❌ No File Attached",
                description="Please attach at least one file with this command.",
                color=Config.EMBED_COLOR_ERROR,
                ctx=ctx
            )
            await ctx.reply(embed=embed, mention_author=False)
            return

        if not users:
            embed = build_embed(
                title="❌ No User Specified",
                description=f"Usage: `{Config.PREFIX}sendfile @user1 [@user2 ...]` with attached files.",
                color=Config.EMBED_COLOR_ERROR,
                ctx=ctx
            )
            await ctx.reply(embed=embed, mention_author=False)
            return

        if len(ctx.message.attachments) > Config.MAX_FILES_PER_COMMAND:
            embed = build_embed(
                title="❌ Too Many Files",
                description=f"Max **{Config.MAX_FILES_PER_COMMAND}** files per command. "
                            f"You sent {len(ctx.message.attachments)}.",
                color=Config.EMBED_COLOR_ERROR,
                ctx=ctx
            )
            await ctx.reply(embed=embed, mention_author=False)
            return

        # Deduplicate users
        unique_users = list({u.id: u for u in users}.values())

        # ── Working indicator ──
        status_embed = build_embed(
            title="⏳ Processing…",
            description=f"Sending **{len(ctx.message.attachments)}** file(s) "
                        f"to **{len(unique_users)}** user(s). Please wait…",
            color=Config.EMBED_COLOR_WARNING,
            ctx=ctx
        )
        status_msg = await ctx.reply(embed=status_embed, mention_author=False)

        # ── Pre-validate all files once ──
        valid_attachments = []
        rejected = []
        for att in ctx.message.attachments:
            ok, err = await validate_file(att)
            if ok:
                valid_attachments.append(att)
            else:
                rejected.append((att.filename, err))

        if not valid_attachments:
            lines = "\n".join(f"• `{n}` — {e.splitlines()[0]}" for n, e in rejected)
            embed = build_embed(
                title="❌ All Files Rejected",
                description=lines,
                color=Config.EMBED_COLOR_ERROR,
                ctx=ctx
            )
            await status_msg.edit(embed=embed)
            return

        # ── Send loop ──
        results = {
            "success": [],   # list of (user, filename)
            "failed": [],    # list of (user, filename, reason)
        }

        for user in unique_users:
            for att in valid_attachments:
                ok, msg, fname = await send_attachment_to_dm(
                    user, att,
                    bot_user=self.bot.user,
                    sender=ctx.author
                )
                if ok:
                    results["success"].append((user, fname))
                else:
                    results["failed"].append((user, fname, msg))
                # Small delay to avoid rate limits
                await asyncio.sleep(0.3)

        # Add rejected pre-validation failures to the failed list
        for fname, reason in rejected:
            results["failed"].append((None, fname, reason.splitlines()[0]))

        # ── Final report ──
        total_success = len(results["success"])
        total_failed = len(results["failed"])

        if total_failed == 0:
            color = Config.EMBED_COLOR_SUCCESS
            title = "✅ All Files Delivered"
        elif total_success == 0:
            color = Config.EMBED_COLOR_ERROR
            title = "❌ Delivery Failed"
        else:
            color = Config.EMBED_COLOR_WARNING
            title = "⚠️ Partial Delivery"

        desc_parts = [
            f"**Delivered:** {total_success}",
            f"**Failed:** {total_failed}",
            f"**Recipients:** {len(unique_users)}",
            f"**Files:** {len(valid_attachments)}",
        ]

        report = build_embed(
            title=title,
            description="\n".join(desc_parts),
            color=color,
            ctx=ctx
        )

        if results["success"]:
            preview = "\n".join(
                f"✅ `{f}` → {u.mention}" for u, f in results["success"][:10]
            )
            if len(results["success"]) > 10:
                preview += f"\n… and {len(results['success']) - 10} more"
            report.add_field(name="Delivered", value=preview, inline=False)

        if results["failed"]:
            preview_lines = []
            for item in results["failed"][:10]:
                u, f, r = item
                target = u.mention if u else "—"
                preview_lines.append(f"❌ `{f}` → {target} — {r}")
            if len(results["failed"]) > 10:
                preview_lines.append(f"… and {len(results['failed']) - 10} more")
            report.add_field(name="Failed", value="\n".join(preview_lines), inline=False)

        await status_msg.edit(embed=report)
        logger.info(
            f"sendfile by {ctx.author} → success={total_success} failed={total_failed}"
        )

    # ──────────────────────────────────────────────────────────────────────────
    # !sendmsg @user [@user2 ...] <message>
    # ──────────────────────────────────────────────────────────────────────────
    @commands.command(
        name='sendmsg',
        aliases=['sm', 'dm', 'senddm'],
        help='Send a text message to one or more users via DM.\n'
             'Usage: !sendmsg @user1 [@user2 ...] <message>'
    )
    @commands.cooldown(1, Config.COOLDOWN_SECONDS, commands.BucketType.user)
    @is_owner()
    async def send_msg(self, ctx, users: commands.Greedy[discord.User], *, message: str = None):
        """Send a text DM to one or more users."""

        if not users:
            embed = build_embed(
                title="❌ No User Specified",
                description=f"Usage: `{Config.PREFIX}sendmsg @user <message>`",
                color=Config.EMBED_COLOR_ERROR,
                ctx=ctx
            )
            await ctx.reply(embed=embed, mention_author=False)
            return

        if not message or not message.strip():
            embed = build_embed(
                title="❌ No Message Provided",
                description=f"Usage: `{Config.PREFIX}sendmsg @user <message>`",
                color=Config.EMBED_COLOR_ERROR,
                ctx=ctx
            )
            await ctx.reply(embed=embed, mention_author=False)
            return

        if len(message) > 2000:
            embed = build_embed(
                title="❌ Message Too Long",
                description=f"Discord limits messages to **2000 characters**. Yours: {len(message)}.",
                color=Config.EMBED_COLOR_ERROR,
                ctx=ctx
            )
            await ctx.reply(embed=embed, mention_author=False)
            return

        unique_users = list({u.id: u for u in users}.values())

        dm_embed = discord.Embed(
            description=message,
            color=Config.EMBED_COLOR_PRIMARY,
            timestamp=discord.utils.utcnow()
        )
        dm_embed.set_author(
            name=f"Sent by {Config.BOT_NAME}",
            icon_url=self.bot.user.display_avatar.url if self.bot.user.display_avatar else None
        )
        dm_embed.set_footer(text=f"{Config.BOT_NAME} v{Config.BOT_VERSION}")

        success = []
        failed = []

        for user in unique_users:
            try:
                dm = await _get_or_create_dm(user, self.bot.user)
                await dm.send(embed=dm_embed)
                success.append(user)
                mark_dm_sent(user.id)
                logger.info(f"Message sent to {user} ({user.id}) by {ctx.author}")
            except discord.Forbidden:
                failed.append((user, "DMs disabled or bot blocked"))
            except Exception as exc:
                failed.append((user, str(exc)))
                logger.error(f"sendmsg failure for {user}: {exc}")
            await asyncio.sleep(0.3)

        if not failed:
            color = Config.EMBED_COLOR_SUCCESS
            title = "✅ Message Delivered"
        elif not success:
            color = Config.EMBED_COLOR_ERROR
            title = "❌ Delivery Failed"
        else:
            color = Config.EMBED_COLOR_WARNING
            title = "⚠️ Partial Delivery"

        report = build_embed(
            title=title,
            description=f"**Delivered:** {len(success)}\n**Failed:** {len(failed)}",
            color=color,
            ctx=ctx
        )

        if success:
            report.add_field(
                name="Sent to",
                value=", ".join(u.mention for u in success[:15]) +
                      (f" … +{len(success) - 15} more" if len(success) > 15 else ""),
                inline=False
            )
        if failed:
            lines = "\n".join(f"❌ {u.mention} — {r}" for u, r in failed[:10])
            report.add_field(name="Failed", value=lines, inline=False)

        await ctx.reply(embed=report, mention_author=False)

    # ──────────────────────────────────────────────────────────────────────────
    # !sendrole @role <message>  — Broadcast DM to all members of a role
    # ──────────────────────────────────────────────────────────────────────────
    @commands.command(
        name='sendrole',
        help='Send a message to every member of a role via DM.\n'
             'Usage: !sendrole @role <message>'
    )
    @commands.cooldown(1, 30, commands.BucketType.user)
    @commands.guild_only()
    @is_owner()
    async def send_role(self, ctx, role: discord.Role, *, message: str):
        """Send a DM to every member of a role."""

        members = [m for m in role.members if not m.bot]
        if not members:
            embed = build_embed(
                title="❌ Role Empty",
                description=f"Role {role.mention} has no (non-bot) members.",
                color=Config.EMBED_COLOR_ERROR,
                ctx=ctx
            )
            await ctx.reply(embed=embed, mention_author=False)
            return

        confirm = build_embed(
            title="⚠️ Confirm Broadcast",
            description=f"About to DM **{len(members)}** members of {role.mention}.\n"
                        f"React ✅ within 20s to confirm.",
            color=Config.EMBED_COLOR_WARNING,
            ctx=ctx
        )
        msg = await ctx.reply(embed=confirm, mention_author=False)
        await msg.add_reaction("✅")
        await msg.add_reaction("❌")

        def check(reaction, user):
            return (
                user == ctx.author
                and reaction.message.id == msg.id
                and str(reaction.emoji) in ("✅", "❌")
            )

        try:
            reaction, _ = await self.bot.wait_for("reaction_add", timeout=20.0, check=check)
        except asyncio.TimeoutError:
            await msg.edit(embed=build_embed(
                title="⏱️ Broadcast Cancelled",
                description="No confirmation received in time.",
                color=Config.EMBED_COLOR_ERROR,
                ctx=ctx
            ))
            return

        if str(reaction.emoji) == "❌":
            await msg.edit(embed=build_embed(
                title="🛑 Broadcast Cancelled",
                description="Cancelled by user.",
                color=Config.EMBED_COLOR_ERROR,
                ctx=ctx
            ))
            return

        dm_embed = discord.Embed(
            description=message,
            color=Config.EMBED_COLOR_PRIMARY,
            timestamp=discord.utils.utcnow()
        )
        dm_embed.set_author(
            name=f"Sent by {Config.BOT_NAME}",
            icon_url=self.bot.user.display_avatar.url if self.bot.user.display_avatar else None
        )
        dm_embed.set_footer(text=f"{Config.BOT_NAME} v{Config.BOT_VERSION}")

        sent, failed = 0, 0
        for member in members:
            try:
                await (await member.create_dm()).send(embed=dm_embed)
                mark_dm_sent(member.id)
                sent += 1
            except Exception:
                failed += 1
            await asyncio.sleep(0.5)  # be kind to rate limits

        result = build_embed(
            title="📢 Broadcast Complete",
            description=f"**Sent:** {sent}\n**Failed:** {failed}\n**Total:** {len(members)}",
            color=Config.EMBED_COLOR_SUCCESS if failed == 0 else Config.EMBED_COLOR_WARNING,
            ctx=ctx
        )
        await msg.edit(embed=result)
        logger.info(f"sendrole by {ctx.author} → sent={sent} failed={failed}")


    # ──────────────────────────────────────────────────────────────────────────
    # !sendfileid <user_id> [<user_id2> ...]  (attach one or more files)
    # ──────────────────────────────────────────────────────────────────────────
    @commands.command(
        name='sendfileid',
        aliases=['sfid'],
        help='Send attached file(s) to user(s) by their raw Discord ID.\n'
             'Usage: !sendfileid 123456789 [987654321 ...] (attach files)'
    )
    @commands.cooldown(1, Config.COOLDOWN_SECONDS, commands.BucketType.user)
    @is_owner()
    async def send_file_id(self, ctx, *user_ids: str):
        """Send attached files to users specified by raw Discord IDs."""

        if not ctx.message.attachments:
            embed = build_embed(
                title="❌ No File Attached",
                description="Please attach at least one file with this command.",
                color=Config.EMBED_COLOR_ERROR,
                ctx=ctx
            )
            await ctx.reply(embed=embed, mention_author=False)
            return

        # Parse raw IDs (strip non-digits)
        parsed_ids = []
        for uid_str in user_ids:
            digits = ''.join(ch for ch in uid_str if ch.isdigit())
            if digits:
                parsed_ids.append(int(digits))

        if not parsed_ids:
            embed = build_embed(
                title="❌ No Valid User ID",
                description=f"Usage: `{Config.PREFIX}sendfileid 123456789` with attached files.",
                color=Config.EMBED_COLOR_ERROR,
                ctx=ctx
            )
            await ctx.reply(embed=embed, mention_author=False)
            return

        if len(ctx.message.attachments) > Config.MAX_FILES_PER_COMMAND:
            embed = build_embed(
                title="❌ Too Many Files",
                description=f"Max **{Config.MAX_FILES_PER_COMMAND}** files per command.",
                color=Config.EMBED_COLOR_ERROR,
                ctx=ctx
            )
            await ctx.reply(embed=embed, mention_author=False)
            return

        # Fetch users by ID (works even if not in a shared server)
        users = []
        failed_ids = []
        for uid in set(parsed_ids):
            try:
                user = await self.bot.fetch_user(uid)
                users.append(user)
            except discord.NotFound:
                failed_ids.append(uid)
            except Exception as exc:
                logger.error(f"fetch_user failed for {uid}: {exc}")
                failed_ids.append(uid)

        if not users:
            embed = build_embed(
                title="❌ No Users Found",
                description=f"Could not resolve any of the provided IDs.\nFailed: `{failed_ids}`",
                color=Config.EMBED_COLOR_ERROR,
                ctx=ctx
            )
            await ctx.reply(embed=embed, mention_author=False)
            return

        # ── Working indicator ──
        status_embed = build_embed(
            title="⏳ Processing…",
            description=f"Sending **{len(ctx.message.attachments)}** file(s) "
                        f"to **{len(users)}** user(s) by ID. Please wait…",
            color=Config.EMBED_COLOR_WARNING,
            ctx=ctx
        )
        status_msg = await ctx.reply(embed=status_embed, mention_author=False)

        # ── Pre-validate all files once ──
        valid_attachments = []
        rejected = []
        for att in ctx.message.attachments:
            ok, err = await validate_file(att)
            if ok:
                valid_attachments.append(att)
            else:
                rejected.append((att.filename, err))

        if not valid_attachments:
            lines = "\n".join(f"• `{n}` — {e.splitlines()[0]}" for n, e in rejected)
            embed = build_embed(
                title="❌ All Files Rejected",
                description=lines,
                color=Config.EMBED_COLOR_ERROR,
                ctx=ctx
            )
            await status_msg.edit(embed=embed)
            return

        # ── Send loop ──
        results = {"success": [], "failed": []}

        for user in users:
            for att in valid_attachments:
                ok, msg, fname = await send_attachment_to_dm(
                    user, att,
                    bot_user=self.bot.user,
                    sender=ctx.author
                )
                if ok:
                    results["success"].append((user, fname))
                else:
                    results["failed"].append((user, fname, msg))
                await asyncio.sleep(0.3)

        for fname, reason in rejected:
            results["failed"].append((None, fname, reason.splitlines()[0]))

        if failed_ids:
            for fid in failed_ids[:10]:
                results["failed"].append((None, f"ID:{fid}", "User not found"))

        total_success = len(results["success"])
        total_failed = len(results["failed"])

        if total_failed == 0:
            color = Config.EMBED_COLOR_SUCCESS
            title = "✅ All Files Delivered"
        elif total_success == 0:
            color = Config.EMBED_COLOR_ERROR
            title = "❌ Delivery Failed"
        else:
            color = Config.EMBED_COLOR_WARNING
            title = "⚠️ Partial Delivery"

        desc_parts = [
            f"**Delivered:** {total_success}",
            f"**Failed:** {total_failed}",
            f"**Recipients:** {len(users)}",
            f"**Files:** {len(valid_attachments)}",
        ]

        report = build_embed(title=title, description="\n".join(desc_parts), color=color, ctx=ctx)

        if results["success"]:
            preview = "\n".join(f"✅ `{f}` → {u.mention}" for u, f in results["success"][:10])
            if len(results["success"]) > 10:
                preview += f"\n… and {len(results['success']) - 10} more"
            report.add_field(name="Delivered", value=preview, inline=False)

        if results["failed"]:
            preview_lines = []
            for item in results["failed"][:10]:
                u, f, r = item
                target = u.mention if u else "—"
                preview_lines.append(f"❌ `{f}` → {target} — {r}")
            if len(results["failed"]) > 10:
                preview_lines.append(f"… and {len(results['failed']) - 10} more")
            report.add_field(name="Failed", value="\n".join(preview_lines), inline=False)

        await status_msg.edit(embed=report)
        logger.info(f"sendfileid by {ctx.author} → success={total_success} failed={total_failed}")

    # ──────────────────────────────────────────────────────────────────────────
    # !sendmsgid <user_id> [<user_id2> ...] <message>
    # ──────────────────────────────────────────────────────────────────────────
    @commands.command(
        name='sendmsgid',
        aliases=['smid'],
        help='Send a text message to user(s) by their raw Discord ID.\n'
             'Usage: !sendmsgid 123456789 [987654321 ...] <message>'
    )
    @commands.cooldown(1, Config.COOLDOWN_SECONDS, commands.BucketType.user)
    @is_owner()
    async def send_msg_id(self, ctx, *args):
        """Send a text DM to users specified by raw Discord IDs."""

        if not args:
            embed = build_embed(
                title="❌ No Arguments",
                description=f"Usage: `{Config.PREFIX}sendmsgid 123456789 Hello!`",
                color=Config.EMBED_COLOR_ERROR,
                ctx=ctx
            )
            await ctx.reply(embed=embed, mention_author=False)
            return

        # Separate IDs from message text
        parsed_ids = []
        message_parts = []
        for arg in args:
            digits = ''.join(ch for ch in arg if ch.isdigit())
            if digits and len(digits) >= 17:  # Discord IDs are 17-19 digits
                parsed_ids.append(int(digits))
            else:
                message_parts.append(arg)

        if not parsed_ids:
            embed = build_embed(
                title="❌ No Valid User ID",
                description=f"Please provide at least one valid Discord User ID.\n"
                            f"Usage: `{Config.PREFIX}sendmsgid 123456789 Hello!`",
                color=Config.EMBED_COLOR_ERROR,
                ctx=ctx
            )
            await ctx.reply(embed=embed, mention_author=False)
            return

        message = ' '.join(message_parts).strip()
        if not message:
            embed = build_embed(
                title="❌ No Message Provided",
                description=f"Usage: `{Config.PREFIX}sendmsgid 123456789 Hello!`",
                color=Config.EMBED_COLOR_ERROR,
                ctx=ctx
            )
            await ctx.reply(embed=embed, mention_author=False)
            return

        if len(message) > 2000:
            embed = build_embed(
                title="❌ Message Too Long",
                description=f"Discord limits messages to **2000 characters**. Yours: {len(message)}.",
                color=Config.EMBED_COLOR_ERROR,
                ctx=ctx
            )
            await ctx.reply(embed=embed, mention_author=False)
            return

        # Fetch users by ID
        users = []
        failed_ids = []
        for uid in set(parsed_ids):
            try:
                user = await self.bot.fetch_user(uid)
                users.append(user)
            except discord.NotFound:
                failed_ids.append(uid)
            except Exception as exc:
                logger.error(f"fetch_user failed for {uid}: {exc}")
                failed_ids.append(uid)

        if not users:
            embed = build_embed(
                title="❌ No Users Found",
                description=f"Could not resolve any of the provided IDs.\nFailed: `{failed_ids}`",
                color=Config.EMBED_COLOR_ERROR,
                ctx=ctx
            )
            await ctx.reply(embed=embed, mention_author=False)
            return

        dm_embed = discord.Embed(
            description=message,
            color=Config.EMBED_COLOR_PRIMARY,
            timestamp=discord.utils.utcnow()
        )
        dm_embed.set_author(
            name=f"Sent by {Config.BOT_NAME}",
            icon_url=self.bot.user.display_avatar.url if self.bot.user.display_avatar else None
        )
        dm_embed.set_footer(text=f"{Config.BOT_NAME} v{Config.BOT_VERSION}")

        success = []
        failed = []

        for user in users:
            try:
                dm = await _get_or_create_dm(user, self.bot.user)
                await dm.send(embed=dm_embed)
                success.append(user)
                mark_dm_sent(user.id)
                logger.info(f"Message sent to {user} ({user.id}) by {ctx.author}")
            except discord.Forbidden:
                failed.append((user, "DMs disabled or bot blocked"))
            except Exception as exc:
                failed.append((user, str(exc)))
                logger.error(f"sendmsgid failure for {user}: {exc}")
            await asyncio.sleep(0.3)

        if not failed and not failed_ids:
            color = Config.EMBED_COLOR_SUCCESS
            title = "✅ Message Delivered"
        elif not success:
            color = Config.EMBED_COLOR_ERROR
            title = "❌ Delivery Failed"
        else:
            color = Config.EMBED_COLOR_WARNING
            title = "⚠️ Partial Delivery"

        report = build_embed(
            title=title,
            description=f"**Delivered:** {len(success)}\n**Failed:** {len(failed) + len(failed_ids)}",
            color=color,
            ctx=ctx
        )

        if success:
            report.add_field(
                name="Sent to",
                value=", ".join(u.mention for u in success[:15]) +
                      (f" … +{len(success) - 15} more" if len(success) > 15 else ""),
                inline=False
            )
        if failed:
            lines = "\n".join(f"❌ {u.mention} — {r}" for u, r in failed[:10])
            report.add_field(name="Failed", value=lines, inline=False)
        if failed_ids:
            lines = "\n".join(f"❌ `ID:{fid}` — User not found" for fid in failed_ids[:10])
            report.add_field(name="Not Found", value=lines, inline=False)

        await ctx.reply(embed=report, mention_author=False)


async def setup(bot):
    await bot.add_cog(FileHandler(bot))
    logger.info("FileHandler cog loaded")
