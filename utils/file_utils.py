import io
import os
import aiohttp
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
    Get an existing DM channel or create a new one.
    Handles the case where the DM was 'closed' by the user.
    """
    # Try to find an existing DM channel the bot already knows about
    if bot_user:
        for ch in bot_user.private_channels:
            if isinstance(ch, __import__('discord').DMChannel) and ch.recipient and ch.recipient.id == user.id:
                return ch

    # Create (or re-open) the DM channel
    try:
        return await user.create_dm()
    except discord.Forbidden:
        raise RuntimeError("Cannot create DM: User has DMs disabled or has blocked the bot.")
    except discord.HTTPException as exc:
        if exc.code == 50007:
            raise RuntimeError("Cannot create DM: User has DMs disabled or has blocked the bot.")
        raise RuntimeError(f"Cannot create DM: {exc.text}")


async def send_attachment_to_dm(user, attachment, bot_user=None, sender=None):
    """
    Stream a Discord attachment directly to a user's DM without touching disk.

    Args:
        user:        discord.User target
        attachment:  discord.Attachment to forward
        bot_user:    Optional bot user for attribution embed
        sender:      Optional discord.User who triggered the send (for logging)

    Returns:
        tuple: (success: bool, message: str, filename: str)
    """
    filename = getattr(attachment, 'filename', 'unknown')

    try:
        # ── Validate ──
        is_valid, error_msg = await validate_file(attachment)
        if not is_valid:
            return False, error_msg, filename

        # ── Open DM (handles closed DMs by re-creating the channel) ──
        dm_channel = await _get_or_create_dm(user, bot_user)

        # ── Stream bytes into memory (no temp files) ──
        file_bytes = await attachment.read()
        file_buffer = io.BytesIO(file_bytes)

        # ── Build discord.File ──
        discord_file = __import__('discord').File(fp=file_buffer, filename=filename)

        # ── Send with attribution ──
        if bot_user:
            embed = __import__('discord').Embed(
                description=f"📁 **File received** via {bot_user.mention}",
                color=Config.EMBED_COLOR_PRIMARY
            )
            embed.set_author(
                name=f"Sent by {Config.BOT_NAME}",
                icon_url=bot_user.display_avatar.url if bot_user.display_avatar else None
            )
            embed.set_footer(text=f"{Config.BOT_NAME} v{Config.BOT_VERSION}")
            await dm_channel.send(embed=embed, file=discord_file)
        else:
            await dm_channel.send(file=discord_file)

        # Track that we sent a DM so we can detect when they open/reply
        mark_dm_sent(user.id)

        logger.info(
            f"Sent '{filename}' ({len(file_bytes)} bytes) to {user} ({user.id})"
            f" by {sender or 'unknown'}"
        )
        return True, f"Sent `{filename}` to {user.mention}", filename

    except Exception as exc:
        error_str = str(exc)
        if "Cannot send messages to this user" in error_str:
            error_str = "User has DMs disabled or has blocked the bot."
        elif "rate limit" in error_str.lower():
            error_str = "Discord rate limit hit. Please wait a moment."

        logger.error(f"Failed to send '{filename}' to {user}: {error_str}")
        return False, f"Failed to send `{filename}`: {error_str}", filename
