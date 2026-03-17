"""
╔══════════════════════════════════════════╗
║  Utility Helpers                         ║
╚══════════════════════════════════════════╝
"""

import random
import string
from datetime import datetime, timezone, timedelta
from typing import Optional

from telegram import Update, Chat, ChatMember, User
from telegram.constants import ChatMemberStatus
from loguru import logger

from config import Roles, config


# ─── ID / NAME HELPERS ────────────────────────────────────────────────────────

def user_mention(user: User) -> str:
    """Return a Markdown mention for a user."""
    name = user.full_name or f"User#{user.id}"
    return f"[{name}](tg://user?id={user.id})"


def format_duration(seconds: int) -> str:
    """Convert seconds into human-readable duration."""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        return f"{seconds // 60}m"
    elif seconds < 86400:
        return f"{seconds // 3600}h"
    else:
        return f"{seconds // 86400}d"


def parse_time_arg(arg: str) -> Optional[int]:
    """
    Parse time argument like '10m', '2h', '1d' into seconds.
    Returns None if invalid.
    """
    units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    if not arg:
        return None
    unit = arg[-1].lower()
    if unit in units:
        try:
            return int(arg[:-1]) * units[unit]
        except ValueError:
            return None
    try:
        return int(arg)
    except ValueError:
        return None


def generate_code(length: int = 12) -> str:
    """Generate a random alphanumeric premium code."""
    chars = string.ascii_uppercase + string.digits
    return "".join(random.choices(chars, k=length))


def generate_captcha_math() -> tuple[str, str]:
    """Generate a simple math captcha question and answer."""
    ops = ["+", "-", "*"]
    a = random.randint(1, 20)
    b = random.randint(1, 10)
    op = random.choice(ops)
    if op == "+":
        answer = a + b
    elif op == "-":
        answer = max(a, b) - min(a, b)
        a, b = max(a, b), min(a, b)
    else:
        answer = a * b
    question = f"{a} {op} {b} = ?"
    return question, str(answer)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def expires_in(expiry: Optional[datetime]) -> str:
    """Return human-readable time until expiry."""
    if not expiry:
        return "Never"
    delta = expiry - now_utc()
    if delta.total_seconds() <= 0:
        return "Expired"
    return format_duration(int(delta.total_seconds()))


# ─── PERMISSION CHECKS ────────────────────────────────────────────────────────

async def is_chat_admin(update: Update, user_id: int = None) -> bool:
    """Check if user is admin/creator in the current chat."""
    chat = update.effective_chat
    uid = user_id or update.effective_user.id
    try:
        member = await chat.get_member(uid)
        return member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER)
    except Exception:
        return False


async def get_user_role(update: Update, user_id: int, db) -> str:
    """Determine user's effective role in a group."""
    from config import config
    from telegram.constants import ChatMemberStatus

    # Bot owner সবসময় owner
    if int(user_id) == int(config.OWNER_ID):
        return Roles.OWNER

    chat = update.effective_chat

    # Telegram-এর actual admin status চেক করো
    try:
        member = await chat.get_member(user_id)
        if member.status == ChatMemberStatus.OWNER:
            # গ্রুপের creator — DB-তে না থাকলেও owner
            return Roles.OWNER
        if member.status == ChatMemberStatus.ADMINISTRATOR:
            # Telegram admin — DB-তে না থাকলেও admin
            return Roles.ADMIN
    except Exception:
        pass

    # DB থেকে custom role চেক
    group = await db.get_group(chat.id)
    if group:
        if user_id == group.get("owner_id"):
            return Roles.OWNER
        if user_id in group.get("admins", []):
            return Roles.ADMIN
        if user_id in group.get("moderators", []):
            return Roles.MODERATOR

    # Premium চেক
    if await db.is_premium(user_id):
        return Roles.VIP

    return Roles.MEMBER


def requires_permission(permission: str):
    """Decorator factory for checking role permissions."""
    from functools import wraps
    from config import ROLE_PERMISSIONS

    def decorator(func):
        @wraps(func)
        async def wrapper(update: Update, context, *args, **kwargs):
            user = update.effective_user
            if not user:
                return

            role = await get_user_role(update, user.id, context.bot_data.get("db"))
            allowed = ROLE_PERMISSIONS.get(role, set())

            if permission not in allowed:
                await update.message.reply_text(
                    f"🚫 You don't have permission to do that.\n"
                    f"Required: `{permission}` | Your role: `{role}`",
                    parse_mode="Markdown",
                )
                return
            return await func(update, context, *args, **kwargs)
        return wrapper
    return decorator


# ─── MESSAGE FORMATTERS ───────────────────────────────────────────────────────

def build_warn_message(user: User, warns: int, warn_limit: int, reason: str = "") -> str:
    bars = "🟥" * warns + "⬜" * (warn_limit - warns)
    msg = (
        f"⚠️ *Warning Issued*\n\n"
        f"👤 User: {user_mention(user)}\n"
        f"📊 Warns: `{warns}/{warn_limit}` {bars}\n"
    )
    if reason:
        msg += f"📝 Reason: _{reason}_\n"
    if warns >= warn_limit:
        msg += f"\n🚨 *Auto-action triggered!* User has reached warn limit."
    return msg


def build_ban_message(user: User, reason: str = "", actor: User = None) -> str:
    msg = f"🔨 *User Banned*\n\n👤 User: {user_mention(user)}\n"
    if reason:
        msg += f"📝 Reason: _{reason}_\n"
    if actor:
        msg += f"👮 By: {user_mention(actor)}\n"
    return msg


def build_mute_message(user: User, duration: int = None, actor: User = None) -> str:
    msg = f"🔇 *User Muted*\n\n👤 User: {user_mention(user)}\n"
    if duration:
        msg += f"⏱ Duration: `{format_duration(duration)}`\n"
    if actor:
        msg += f"👮 By: {user_mention(actor)}\n"
    return msg


def build_welcome_message(user: User, group: Chat, settings: dict) -> str:
    template = settings.get("welcome_msg", "👋 Welcome {name} to {group}!")
    return template.format(
        name=user.first_name,
        full_name=user.full_name,
        username=f"@{user.username}" if user.username else user.first_name,
        group=group.title,
        id=user.id,
    )


def build_stats_message(stats: dict) -> str:
    return (
        f"📊 *Bot Statistics*\n\n"
        f"👥 Total Users: `{stats['total_users']:,}`\n"
        f"🏘️ Total Groups: `{stats['total_groups']:,}`\n"
        f"💎 Premium Users: `{stats['premium_users']:,}`\n"
        f"⚡ Actions Today: `{stats['actions_today']:,}`\n\n"
        f"📋 *All Time*\n"
        f"🔨 Bans: `{stats['total_bans']:,}`\n"
        f"⚠️ Warns: `{stats['total_warns']:,}`\n"
        f"🔇 Mutes: `{stats['total_mutes']:,}`\n"
    )
