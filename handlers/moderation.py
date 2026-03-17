"""
╔══════════════════════════════════════════╗
║  Moderation Handlers                     ║
║  ban/unban/kick/mute/warn/purge          ║
╚══════════════════════════════════════════╝
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple

from telegram import Update, ChatPermissions
from telegram.constants import ChatMemberStatus, ChatType, ParseMode
from telegram.ext import ContextTypes
from telegram.error import TelegramError
from loguru import logger

from config import config, Roles, ROLE_PERMISSIONS
from database.db import db
from utils.helpers import (
    user_mention, parse_time_arg, format_duration,
    get_user_role, build_warn_message, build_ban_message, build_mute_message,
)
from locales.strings import get_string


# ─── HELPERS ─────────────────────────────────────────────────────────────────

async def _resolve_target(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Tuple[Optional[int], Optional[str]]:
    """
    Resolve target user from reply or @username/ID argument.
    Returns (user_id, error_message).
    """
    msg = update.message

    # From reply
    if msg.reply_to_message:
        target = msg.reply_to_message.from_user
        return target.id, None

    # From argument
    if context.args:
        arg = context.args[0]
        try:
            return int(arg), None
        except ValueError:
            username = arg.lstrip("@")
            user = await context.bot.get_chat(username)
            return user.id, None

    return None, "❌ Please reply to a user or provide their ID/username."


async def _check_permission(update: Update, context: ContextTypes.DEFAULT_TYPE, permission: str) -> bool:
    """Check if invoking user has required permission."""
    user_id = update.effective_user.id
    role = await get_user_role(update, user_id, db)
    if permission in ROLE_PERMISSIONS.get(role, set()):
        return True
    await update.message.reply_text(
        f"🚫 *Permission denied!*\nRequired: `{permission}` | Your role: `{role}`",
        parse_mode=ParseMode.MARKDOWN,
    )
    return False


async def _send_log(context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    """Send action log to configured log channel."""
    if config.LOG_CHANNEL_ID:
        try:
            await context.bot.send_message(config.LOG_CHANNEL_ID, text, parse_mode=ParseMode.MARKDOWN)
        except TelegramError as e:
            logger.warning(f"Log send failed: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
#  BAN / UNBAN
# ═══════════════════════════════════════════════════════════════════════════════

async def cmd_ban(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /ban [@user|id] [reason]
    Ban a user from the group.
    """
    if not await _check_permission(update, context, "can_ban"):
        return

    target_id, err = await _resolve_target(update, context)
    if err:
        await update.message.reply_text(err)
        return

    actor = update.effective_user
    chat  = update.effective_chat

    # Protect bot owner
    if target_id == config.OWNER_ID:
        await update.message.reply_text("🚫 Cannot ban the bot owner.")
        return

    # Reason: args after username
    reason_start = 2 if context.args and (context.args[0].startswith("@") or context.args[0].isdigit()) else 1
    reason = " ".join(context.args[reason_start:]) if context.args else ""

    try:
        target_member = await chat.get_member(target_id)
        target_user   = target_member.user

        await context.bot.ban_chat_member(chat.id, target_id)
        await db.ban_user(target_id, chat.id, reason, actor.id)

        msg = build_ban_message(target_user, reason, actor)
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
        await _send_log(context, f"🔨 *BAN* | Group: `{chat.title}` ({chat.id})\n" + msg)

    except TelegramError as e:
        await update.message.reply_text(f"❌ Failed to ban: `{e}`", parse_mode=ParseMode.MARKDOWN)


async def cmd_unban(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /unban [@user|id]
    Unban a user.
    """
    if not await _check_permission(update, context, "can_ban"):
        return

    target_id, err = await _resolve_target(update, context)
    if err:
        await update.message.reply_text(err)
        return

    chat  = update.effective_chat
    actor = update.effective_user

    try:
        await context.bot.unban_chat_member(chat.id, target_id, only_if_banned=True)
        await db.unban_user(target_id, chat.id, actor.id)
        await update.message.reply_text(f"✅ User `{target_id}` has been *unbanned*.", parse_mode=ParseMode.MARKDOWN)
    except TelegramError as e:
        await update.message.reply_text(f"❌ Failed to unban: `{e}`", parse_mode=ParseMode.MARKDOWN)


# ═══════════════════════════════════════════════════════════════════════════════
#  KICK
# ═══════════════════════════════════════════════════════════════════════════════

async def cmd_kick(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /kick [@user|id] [reason]
    Kick (remove without ban) a user.
    """
    if not await _check_permission(update, context, "can_kick"):
        return

    target_id, err = await _resolve_target(update, context)
    if err:
        await update.message.reply_text(err)
        return

    chat  = update.effective_chat
    actor = update.effective_user

    if target_id == config.OWNER_ID:
        await update.message.reply_text("🚫 Cannot kick the bot owner.")
        return

    try:
        target_member = await chat.get_member(target_id)
        target_user   = target_member.user

        await context.bot.ban_chat_member(chat.id, target_id)
        await context.bot.unban_chat_member(chat.id, target_id)
        await db.log_action("kick", target_id, chat.id, actor_id=actor.id)

        await update.message.reply_text(
            f"👢 {user_mention(target_user)} has been *kicked* by {user_mention(actor)}.",
            parse_mode=ParseMode.MARKDOWN,
        )
    except TelegramError as e:
        await update.message.reply_text(f"❌ Failed to kick: `{e}`", parse_mode=ParseMode.MARKDOWN)


# ═══════════════════════════════════════════════════════════════════════════════
#  MUTE / UNMUTE
# ═══════════════════════════════════════════════════════════════════════════════

async def cmd_mute(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /mute [@user|id] [duration: 10m, 2h, 1d]
    Mute a user (restrict all messages).
    """
    if not await _check_permission(update, context, "can_mute"):
        return

    target_id, err = await _resolve_target(update, context)
    if err:
        await update.message.reply_text(err)
        return

    chat  = update.effective_chat
    actor = update.effective_user

    # Parse duration from args
    duration = config.MUTE_DURATION_DEFAULT
    if context.args:
        for arg in context.args:
            parsed = parse_time_arg(arg)
            if parsed:
                duration = parsed
                break

    until_date = datetime.now(timezone.utc) + timedelta(seconds=duration)

    try:
        target_member = await chat.get_member(target_id)
        target_user   = target_member.user

        await context.bot.restrict_chat_member(
            chat.id,
            target_id,
            permissions=ChatPermissions(
                can_send_messages=False,
                can_send_media_messages=False,
                can_send_other_messages=False,
                can_add_web_page_previews=False,
            ),
            until_date=until_date,
        )
        await db.mute_user(target_id, chat.id, until_date, actor.id)

        msg = build_mute_message(target_user, duration, actor)
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
        await _send_log(context, f"🔇 *MUTE* | Group: `{chat.title}` ({chat.id})\n" + msg)

    except TelegramError as e:
        await update.message.reply_text(f"❌ Failed to mute: `{e}`", parse_mode=ParseMode.MARKDOWN)


async def cmd_unmute(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /unmute [@user|id]
    Restore all user permissions.
    """
    if not await _check_permission(update, context, "can_mute"):
        return

    target_id, err = await _resolve_target(update, context)
    if err:
        await update.message.reply_text(err)
        return

    chat  = update.effective_chat
    actor = update.effective_user

    try:
        target_member = await chat.get_member(target_id)
        target_user   = target_member.user

        await context.bot.restrict_chat_member(
            chat.id,
            target_id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
            ),
        )
        await db.unmute_user(target_id, chat.id, actor.id)

        await update.message.reply_text(
            f"🔊 {user_mention(target_user)} has been *unmuted*.",
            parse_mode=ParseMode.MARKDOWN,
        )
    except TelegramError as e:
        await update.message.reply_text(f"❌ Failed to unmute: `{e}`", parse_mode=ParseMode.MARKDOWN)


# ═══════════════════════════════════════════════════════════════════════════════
#  WARN / CLEARWARN
# ═══════════════════════════════════════════════════════════════════════════════

async def cmd_warn(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /warn [@user|id] [reason]
    Issue a warning. Auto-action at warn limit.
    """
    if not await _check_permission(update, context, "can_warn"):
        return

    target_id, err = await _resolve_target(update, context)
    if err:
        await update.message.reply_text(err)
        return

    chat  = update.effective_chat
    actor = update.effective_user

    if target_id == config.OWNER_ID:
        await update.message.reply_text("🚫 Cannot warn the bot owner.")
        return

    reason_args = context.args[1:] if context.args and not context.args[0].isdigit() else context.args
    reason = " ".join(reason_args) if reason_args else ""

    # Get warn limit from group settings
    warn_limit = await db.get_group_setting(chat.id, "warn_limit", config.WARN_LIMIT)
    mute_first = await db.get_group_setting(chat.id, "mute_first", True)

    try:
        target_member = await chat.get_member(target_id)
        target_user   = target_member.user

        warns = await db.add_warn(target_id, chat.id, reason)
        msg = build_warn_message(target_user, warns, warn_limit, reason)
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

        # Auto-action on limit
        if warns >= warn_limit:
            if mute_first:
                # Mute for 24h first, then escalate
                until = datetime.now(timezone.utc) + timedelta(hours=24)
                await context.bot.restrict_chat_member(
                    chat.id, target_id,
                    permissions=ChatPermissions(can_send_messages=False),
                    until_date=until,
                )
                await update.message.reply_text(
                    f"🚨 {user_mention(target_user)} auto-muted for 24h (warn limit reached).",
                    parse_mode=ParseMode.MARKDOWN,
                )
            else:
                await context.bot.ban_chat_member(chat.id, target_id)
                await db.ban_user(target_id, chat.id, "Auto-ban: warn limit reached", actor.id)
                await update.message.reply_text(
                    f"🔨 {user_mention(target_user)} auto-banned (warn limit reached).",
                    parse_mode=ParseMode.MARKDOWN,
                )

        await _send_log(context, f"⚠️ *WARN* | Group: `{chat.title}` ({chat.id})\n" + msg)

    except TelegramError as e:
        await update.message.reply_text(f"❌ Failed to warn: `{e}`", parse_mode=ParseMode.MARKDOWN)


async def cmd_clearwarn(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /clearwarn [@user|id]
    Reset user warning count.
    """
    if not await _check_permission(update, context, "can_warn"):
        return

    target_id, err = await _resolve_target(update, context)
    if err:
        await update.message.reply_text(err)
        return

    chat = update.effective_chat

    try:
        target_member = await chat.get_member(target_id)
        target_user   = target_member.user
        await db.clear_warns(target_id, chat.id)
        await update.message.reply_text(
            f"✅ Warnings cleared for {user_mention(target_user)}.",
            parse_mode=ParseMode.MARKDOWN,
        )
    except TelegramError as e:
        await update.message.reply_text(f"❌ Error: `{e}`", parse_mode=ParseMode.MARKDOWN)


# ═══════════════════════════════════════════════════════════════════════════════
#  PURGE
# ═══════════════════════════════════════════════════════════════════════════════

async def cmd_purge(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /purge [count]
    Delete multiple messages. If reply, purge from that message.
    Max: 100 messages.
    """
    if not await _check_permission(update, context, "can_purge"):
        return

    chat    = update.effective_chat
    count   = 20  # default
    start_id = update.message.message_id

    if context.args:
        try:
            count = min(int(context.args[0]), 100)
        except ValueError:
            pass

    if update.message.reply_to_message:
        start_id = update.message.reply_to_message.message_id
        count = update.message.message_id - start_id + 1

    # Build list of message IDs to delete
    message_ids = list(range(start_id, start_id + count))
    deleted = 0

    # Delete in chunks of 100
    for i in range(0, len(message_ids), 100):
        chunk = message_ids[i:i+100]
        try:
            await context.bot.delete_messages(chat.id, chunk)
            deleted += len(chunk)
        except TelegramError:
            for mid in chunk:
                try:
                    await context.bot.delete_message(chat.id, mid)
                    deleted += 1
                except TelegramError:
                    pass

    # Also delete the purge command itself
    try:
        await update.message.delete()
    except TelegramError:
        pass

    confirm = await context.bot.send_message(
        chat.id,
        f"🗑️ Deleted `{deleted}` messages.",
        parse_mode=ParseMode.MARKDOWN,
    )

    # Auto-delete confirmation after 5s
    import asyncio
    await asyncio.sleep(5)
    try:
        await confirm.delete()
    except TelegramError:
        pass


# ═══════════════════════════════════════════════════════════════════════════════
#  ROLE MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════

async def cmd_promote(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /promote [@user|id]
    Promote a member to Admin role.
    """
    if not await _check_permission(update, context, "can_promote"):
        return

    target_id, err = await _resolve_target(update, context)
    if err:
        await update.message.reply_text(err)
        return

    chat = update.effective_chat

    try:
        target_member = await chat.get_member(target_id)
        target_user   = target_member.user

        await db.add_group_admin(chat.id, target_id)
        await db.set_user_role(target_id, Roles.ADMIN, chat.id)

        await update.message.reply_text(
            f"✅ {user_mention(target_user)} has been *promoted to Admin*.",
            parse_mode=ParseMode.MARKDOWN,
        )
    except TelegramError as e:
        await update.message.reply_text(f"❌ Error: `{e}`", parse_mode=ParseMode.MARKDOWN)


async def cmd_demote(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /demote [@user|id]
    Remove Admin role.
    """
    if not await _check_permission(update, context, "can_demote"):
        return

    target_id, err = await _resolve_target(update, context)
    if err:
        await update.message.reply_text(err)
        return

    chat = update.effective_chat

    try:
        target_member = await chat.get_member(target_id)
        target_user   = target_member.user

        await db.remove_group_admin(chat.id, target_id)
        await db.set_user_role(target_id, Roles.MEMBER, chat.id)

        await update.message.reply_text(
            f"✅ {user_mention(target_user)} has been *demoted*.",
            parse_mode=ParseMode.MARKDOWN,
        )
    except TelegramError as e:
        await update.message.reply_text(f"❌ Error: `{e}`", parse_mode=ParseMode.MARKDOWN)


async def cmd_addmod(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /addmod [@user|id]
    Grant Moderator role.
    """
    if not await _check_permission(update, context, "can_promote"):
        return

    target_id, err = await _resolve_target(update, context)
    if err:
        await update.message.reply_text(err)
        return

    chat = update.effective_chat

    try:
        target_member = await chat.get_member(target_id)
        target_user   = target_member.user

        await db.add_group_moderator(chat.id, target_id)
        await db.set_user_role(target_id, Roles.MODERATOR, chat.id)

        await update.message.reply_text(
            f"✅ {user_mention(target_user)} is now a *Moderator*.",
            parse_mode=ParseMode.MARKDOWN,
        )
    except TelegramError as e:
        await update.message.reply_text(f"❌ Error: `{e}`", parse_mode=ParseMode.MARKDOWN)
