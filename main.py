import os
import asyncio
import discord
from discord.ext import commands
from aiohttp import web

from config.config import Config
from utils.logger import setup_logger

logger = setup_logger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Bot Intents
# ─────────────────────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
intents.dm_messages = True
intents.guilds = True
intents.members = True

bot = commands.Bot(
    command_prefix=Config.PREFIX,
    intents=intents,
    help_command=None,  # We use our own !help
    description=Config.BOT_DESCRIPTION
)

loaded_cogs = []

# ─────────────────────────────────────────────────────────────────────────────
# Health Check Server (Railway requires an open port to keep the service alive)
# ─────────────────────────────────────────────────────────────────────────────
async def health_check(request):
    """Simple HTTP 200 so Railway knows the bot is alive."""
    return web.Response(
        text=f"{Config.BOT_NAME} v{Config.BOT_VERSION} is online!",
        status=200,
        content_type='text/plain'
    )

async def start_health_server():
    """Start a lightweight aiohttp server on the configured port."""
    app = web.Application()
    app.router.add_get('/', health_check)
    app.router.add_get('/health', health_check)

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, host='0.0.0.0', port=Config.HEALTH_CHECK_PORT)
    await site.start()
    logger.info(f"🌐 Health-check server listening on port {Config.HEALTH_CHECK_PORT}")

# ─────────────────────────────────────────────────────────────────────────────
# Cog Loading
# ─────────────────────────────────────────────────────────────────────────────
async def load_cogs():
    """Load all cogs from commands and events directories."""
    cogs_dir = [
        ('commands', 'commands'),
        ('events', 'events')
    ]

    for directory, prefix in cogs_dir:
        if not os.path.isdir(directory):
            logger.warning(f"Directory '{directory}' not found, skipping.")
            continue

        for filename in os.listdir(directory):
            if filename.endswith('.py') and not filename.startswith('_'):
                cog_name = filename[:-3]
                module_name = f"{prefix}.{cog_name}"

                try:
                    await bot.load_extension(module_name)
                    loaded_cogs.append(module_name)
                    logger.info(f"✅ Loaded cog: {module_name}")
                except Exception as e:
                    logger.error(f"❌ Failed to load cog {module_name}: {str(e)}")

# ─────────────────────────────────────────────────────────────────────────────
# Main Entry Point
# ─────────────────────────────────────────────────────────────────────────────
async def main():
    """Main async entry — validate config, load cogs, start bot + health server."""
    try:
        # Validate configuration
        Config.validate()
        logger.info("✅ Configuration validated")

        # Start health-check server (Railway requirement)
        await start_health_server()

        # Load cogs
        await load_cogs()
        logger.info(f"✅ Loaded {len(loaded_cogs)} cog(s)")

        # Start bot
        logger.info("🚀 Starting bot...")
        await bot.start(Config.TOKEN)

    except ValueError as e:
        logger.error(f"❌ Configuration error: {str(e)}")
        exit(1)
    except Exception as e:
        logger.error(f"❌ Fatal error: {str(e)}")
        exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Unhandled exception: {e}")
        exit(1)
