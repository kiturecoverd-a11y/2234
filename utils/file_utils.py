import io
import os
import aiohttp
import discord
from config.config import Config
from utils.logger import setup_logger
from utils.dm_tracker import mark_dm_sent

logger = setup_logger(__name__)


async def validate_file(attachment):
    """
    Validate a Discord attachment against configured rules.

    Returns:
        tuple: (is_valid: bool, error_message: str or None)
    """
    filename = getattr(attachment, 'filename', 'unknown')
    size = getattr(attachment, 'size', 0)

    # ── Check extension ──
    file_ext = os.path.splitext(filename)[1].lower()
    if file_ext not in Config.ALLOWED_FILE_EXTENSIONS:
        allowed = ', '.join(Config.ALLOWED_FILE_EXTENSIONS)
        return False, (
            f"**File type not allowed.**\n"
            f"Allowed: `{allowed}`\n"
            f"Yours: `{file_ext or 'none'}`"
        )

    # ── Check size ──
    if size > Config.MAX_FILE_SIZE:
        max_mb = Config.MAX_FILE_SIZE / (1024 * 1024)
        actual_mb = size / (1024 * 1024)
        return False, (
            f"**File too large.**\n"
            f"Max: `{max_mb:.1f} MB`\n"
            f"Yours: `{actual_mb:.1f} MB`"
        )

    return True, None


async def _get_or_create_dm(user, bot_user=None):
    """
    Create a fresh DM channel for the user.
    This always works even if the user 'closed' their previous DM.
    """
    try:
        return await user.create_dm()
    except discord.Forbidden:
        raise RuntimeError("Cannot create DM: User has DMs disabled or has blocked the bot.")
    except discord.HTTPException as exc:
        if exc.code == 50007:
            raise RuntimeError("Cannot create DM: User has DMs disabled or has blocked the bot.")
        raise RuntimeError(f"Cannot create DM: {exc.text}")


async def send_to_dm_with_retry(user, send_callback, bot_user=None):
    """
    Attempt to send a message/file to a user's DM.
    If the cached DM channel is closed/invalid, creates a new one and retries.

    Args:
        user: discord.User to send to
        send_callback: async function(dm_channel) that performs the send
        bot_user: the bot's user object

    Returns:
        tuple: (success: bool, error_message: str or None)
    """
    dm_channel = None

    # ── Attempt 1: try cached DM channel ──
    if bot_user:
        for ch in bot_user.private_channels:
            if isinstance(ch, discord.DMChannel) and ch.recipient and ch.recipient.id == user.id:
                dm_channel = ch
                break

    if dm_channel:
        try:
            await send_callback(dm_channel)
            return True, None
        except (discord.Forbidden, discord.HTTPException) as exc:
            # Cached DM is closed or invalid — fall through to create a new one
            logger.warning(f"Cached DM closed for {user.id}, creating new DM channel...")
            dm_channel = None

    # ── Attempt 2: create a fresh DM channel and send ──
    try:
        dm_channel = await _get_or_create_dm(user, bot_user)
        await send_callback(dm_channel)
        return True, None
    except (discord.Forbidden, discord.HTTPException) as exc:
        if getattr(exc, 'code', None) == 50007 or "Cannot send messages to this user" in str(exc):
            return False, "User has DMs disabled or has blocked the bot."
        return False, str(exc)
    except RuntimeError as exc:
        return False, str(exc)


async def send_attachment_to_dm(user, attachment, bot_user=None, sender=None):
    """
    Stream a Discord attachment directly to a user's DM without touching disk.
    Handles closed DMs by re-creating the channel and retrying.

    Returns:
        tuple: (success: bool, message: str, filename: str)
    """
    filename = getattr(attachment, 'filename', 'unknown')

    # ── Validate ──
    is_valid, error_msg = await validate_file(attachment)
    if not is_valid:
        return False, error_msg, filename

    # ── Prepare file in memory ──
    file_bytes = await attachment.read()
    file_buffer = io.BytesIO(file_bytes)
    discord_file = discord.File(fp=file_buffer, filename=filename)

    # ── Build embed ──
    embed = None
    if bot_user:
        embed = discord.Embed(
            description=f"📁 **File received** via {bot_user.mention}",
            color=Config.EMBED_COLOR_PRIMARY
        )
        embed.set_author(
            name=f"Sent by {Config.BOT_NAME}",
            icon_url=bot_user.display_avatar.url if bot_user.display_avatar else None
        )
        embed.set_footer(text=f"{Config.BOT_NAME} v{Config.BOT_VERSION}")

    # ── Send with retry logic ──
    async def _do_send(channel):
        if embed:
            await channel.send(embed=embed, file=discord_file)
        else:
            await channel.send(file=discord_file)

    ok, err = await send_to_dm_with_retry(user, _do_send, bot_user)

    if ok:
        mark_dm_sent(user.id)
        logger.info(
            f"Sent '{filename}' ({len(file_bytes)} bytes) to {user} ({user.id})"
            f" by {sender or 'unknown'}"
        )
        return True, f"Sent `{filename}` to {user.mention}", filename
    else:
        logger.error(f"Failed to send '{filename}' to {user}: {err}")
        return False, f"Failed to send `{filename}`: {err}", filename
