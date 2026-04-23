import os
from dotenv import load_dotenv

# Load environment variables from .env file (if present)
load_dotenv()


def _safe_int(env_var, default):
    """Safely parse an integer from an environment variable.
    Handles accidental copy-paste issues like '=500', tabs, quotes, etc."""
    value = os.getenv(env_var, str(default))
    if not value or not value.strip():
        return default

    # Aggressively clean the value:
    # 1. Strip whitespace (spaces, tabs, newlines)
    # 2. Strip leading '=' (common when copying from .env files)
    # 3. Strip quotes
    cleaned = value.strip().lstrip('=').strip().strip('"').strip("'")

    try:
        return int(cleaned)
    except ValueError:
        # Fallback: extract the first contiguous block of digits
        digits = []
        started = False
        for ch in cleaned:
            if ch.isdigit():
                digits.append(ch)
                started = True
            elif started:
                break
        if digits:
            return int(''.join(digits))

        # If nothing works, return default so the bot doesn't crash
        return default


class Config:
    """
    Centralized, validated configuration for the Discord File Bot.
    All settings are loaded from environment variables with sensible defaults.
    """

    # ─── Bot Identity ────────────────────────────────────────────────────────
    BOT_NAME = "DM File Bot"
    BOT_VERSION = "2.1.0"
    BOT_DESCRIPTION = (
        "A professional Discord bot for securely sending files and messages "
        "directly to users' DMs. Supports .rar, .zip, .apk, .msg and more."
    )

    # ─── Discord Token (REQUIRED) ────────────────────────────────────────────
    TOKEN = os.getenv('DISCORD_TOKEN')

    # ─── Command Prefix ──────────────────────────────────────────────────────
    PREFIX = os.getenv('COMMAND_PREFIX', '!')

    # ─── Owner / Admin IDs (comma-separated) ─────────────────────────────────
    OWNER_IDS = [
        int(uid.strip())
        for uid in os.getenv('OWNER_IDS', '').split(',')
        if uid.strip().isdigit()
    ]

    # ─── Allowed File Extensions ─────────────────────────────────────────────
    ALLOWED_FILE_EXTENSIONS = [
        '.rar', '.zip', '.7z', '.tar', '.gz', '.bz2',
        '.apk', '.ipa',
        '.msg', '.eml',
        '.exe', '.msi', '.bin', '.iso', '.dmg',
        '.pdf', '.doc', '.docx', '.xls', '.xlsx',
        '.txt', '.json', '.xml', '.csv',
        '.mp4', '.mov', '.avi', '.mkv',
        '.jpg', '.jpeg', '.png', '.gif', '.webp',
        '.mp3', '.wav', '.flac', '.aac',
    ]

    # ─── File Size Limits ────────────────────────────────────────────────────
    # Discord Nitro Classic  = 50  MB
    # Discord Nitro          = 500 MB
    # Default to 500 MB since user mentioned having Nitro
    MAX_FILE_SIZE = _safe_int('MAX_FILE_SIZE_MB', 500) * 1024 * 1024

    # ─── Rate Limits ─────────────────────────────────────────────────────────
    COOLDOWN_SECONDS = _safe_int('COOLDOWN_SECONDS', 3)
    MAX_FILES_PER_COMMAND = _safe_int('MAX_FILES_PER_COMMAND', 10)

    # ─── Logging ─────────────────────────────────────────────────────────────
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_DIR = 'logs'

    # ─── Embed Colors ────────────────────────────────────────────────────────
    EMBED_COLOR_PRIMARY = 0x5865F2   # Discord Blurple
    EMBED_COLOR_SUCCESS = 0x57F287   # Green
    EMBED_COLOR_ERROR = 0xED4245     # Red
    EMBED_COLOR_WARNING = 0xFEE75C   # Yellow
    EMBED_COLOR_INFO = 0xEB459E      # Pink

    # ─── Health Check Server (for Railway) ───────────────────────────────────
    HEALTH_CHECK_PORT = _safe_int('PORT', 8080)

    # ─── Log Channel ─────────────────────────────────────────────────────────
    # Discord channel ID where DM-open notifications are sent
    LOG_CHANNEL_ID = _safe_int('LOG_CHANNEL_ID', 0) or None

    @staticmethod
    def validate():
        """
        Validate that all required configuration is present.
        Raises ValueError with a descriptive message if anything is missing.
        """
        missing = []

        if not Config.TOKEN:
            missing.append(
                "DISCORD_TOKEN  →  Get your token from "
                "https://discord.com/developers/applications"
            )

        if not Config.OWNER_IDS:
            missing.append(
                "OWNER_IDS  →  Add at least one owner Discord User ID "
                "so the bot has an admin."
            )

        if missing:
            raise ValueError(
                "❌ Missing required environment variables:\n\n"
                + "\n".join(f"  • {m}" for m in missing)
                + "\n\nPlease set them in Railway Variables or your .env file."
            )

        return True

    @classmethod
    def as_dict(cls):
        """Return a safe subset of config for debug / info commands."""
        return {
            'bot_name': cls.BOT_NAME,
            'bot_version': cls.BOT_VERSION,
            'prefix': cls.PREFIX,
            'max_file_size_mb': cls.MAX_FILE_SIZE / (1024 * 1024),
            'max_files_per_command': cls.MAX_FILES_PER_COMMAND,
            'cooldown_seconds': cls.COOLDOWN_SECONDS,
            'allowed_extensions_count': len(cls.ALLOWED_FILE_EXTENSIONS),
            'owner_count': len(cls.OWNER_IDS),
            'log_level': cls.LOG_LEVEL,
        }
