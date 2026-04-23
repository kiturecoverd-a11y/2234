"""
Simple in-memory tracker for DM interactions.
Used to detect when a user replies to a bot DM so we can notify a log channel.
"""
import time
from collections import defaultdict
from config.config import Config

# user_id -> timestamp of last bot DM sent
_recent_dms = {}
# user_id -> whether we've already notified for this "session"
_notified = set()

# How long to watch for a reply after sending a DM (seconds)
WATCH_WINDOW = 3600  # 1 hour


def mark_dm_sent(user_id):
    """Call this when the bot sends a DM to a user."""
    _recent_dms[user_id] = time.time()
    _notified.discard(user_id)


def should_notify(user_id):
    """Check if a user reply warrants a notification."""
    last_sent = _recent_dms.get(user_id)
    if not last_sent:
        return False
    if time.time() - last_sent > WATCH_WINDOW:
        # Expired, clean up
        _recent_dms.pop(user_id, None)
        _notified.discard(user_id)
        return False
    if user_id in _notified:
        return False
    return True


def mark_notified(user_id):
    """Mark that we've already sent the notification for this user."""
    _notified.add(user_id)


def get_log_channel(bot):
    """Fetch the configured log channel, if any."""
    channel_id = getattr(Config, 'LOG_CHANNEL_ID', None)
    if not channel_id:
        return None
    return bot.get_channel(channel_id)
