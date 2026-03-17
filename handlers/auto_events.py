"""
╔══════════════════════════════════════════╗
║  Auto Event Handlers                     ║
║  Welcome · Goodbye · Captcha             ║
║  Anti-Link · Anti-Spam · Anti-Raid       ║
║  Keyword Replies · Banned Words          ║
╚══════════════════════════════════════════╝
"""

import asyncio
from datetime import datetime, timedelta, timezone

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
from telegram.constants import ChatType, ParseMode
from telegram.ext import ContextTypes
from telegram.error import TelegramError
from loguru import logger

from config import config
from database.db import db
from utils.helpers import (
    user_mention, generate_captcha_math, build_welcome_message, format_duration
)
from utils.ai_moderation import (
    spam_tracker, raid_tracker,
    contains_link, analyze_toxicity, analyze_spam, estimate_spam_probability
)


# ═══════════════════════════════════════════════════════════════════════════════
#  MEMBER JOIN / LEAVE EVENTS
# ═══════════════════════════════════════════════════════════════════════════════

async def on_member_join(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle new member joins.
    - Anti-raid check
    - Captcha verification
    - Welcome message
    - Auto-role assignment
    """
    chat = update.effective_chat
    message = update.message

    if not message or not message.new_chat_members:
        return

    group = await db.get_group(chat.id)
    if not group:
        return

    settings = group.get("settings", {})

    for member in message.new_chat_members:
        if member.is_bot:
            continue

        # ── Anti-Raid Check ───────────────────────────────────────────────────
        if settings.get("anti_raid", True):
            join_count = raid_tracker.record_join(chat.id)
            if join_count >= config.ANTI_RAID_THRESHOLD:
                # Activate raid mode
                if not await db.is_raid_active(chat.id):
                    await db.set_raid_mode(chat.id, config.ANTI_RAID_DURATION)
                    await message.reply_text(
                        f"🚨 *RAID DETECTED!*\n\n"
                        f"Group locked for `{format_duration(config.ANTI_RAID_DURATION)}` "
                        f"due to join flood (`{join_count}` joins/min).",
                        parse_mode=ParseMode.MARKDOWN,
                    )
                    # Lock the group
                    try:
                        await context.bot.set_chat_permissions(
                            chat.id,
                            ChatPermissions(can_send_messages=False),
                        )
                        # Schedule unlock
                        context.job_queue.run_once(
                            _unlock_group_job,
                            config.ANTI_RAID_DURATION,
                            data={"chat_id": chat.id},
                        )
                    except TelegramError as e:
                        logger.warning(f"Anti-raid lock failed: {e}")

                # Kick the joining user during raid
                try:
                    await context.bot.ban_chat_member(chat.id, member.id)
                    await context.bot.unban_chat_member(chat.id, member.id)
                except TelegramError:
                    pass
                continue

        # Register user in DB
        await db.get_or_create_user(member.id, member.username or "", member.full_name)

        # ── Captcha Verification ──────────────────────────────────────────────
        if settings.get("captcha", True) and config.ENABLE_CAPTCHA:
            await _send_captcha(update, context, member, chat)
        else:
            # Send welcome message
            if settings.get("welcome", True):
                await _send_welcome(update, context, member, chat, settings)


async def _send_captcha(update, context, member, chat) -> None:
    """Send a math captcha to a new member and mute them until verified."""
    question, answer = generate_captcha_math()
    await db.set_captcha_pending(member.id, chat.id, answer)

    # Mute user until verified
    try:
        await context.bot.restrict_chat_member(
            chat.id,
            member.id,
            permissions=ChatPermissions(can_send_messages=False),
        )
    except TelegramError:
        pass

    # Send captcha prompt with timeout
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton(f"✏️ Answer: _{question}_", callback_data=f"captcha_prompt_{member.id}"),
    ]])
    msg = await update.message.reply_text(
        f"🔐 *Verification Required*\n\n"
        f"Welcome {user_mention(member)}!\n\n"
        f"Solve this captcha to join:\n"
        f"📊 `{question}`\n\n"
        f"Reply with your answer within `{config.CAPTCHA_TIMEOUT}s`.",
        parse_mode=ParseMode.MARKDOWN,
    )

    # Schedule auto-kick if no response
    context.job_queue.run_once(
        _captcha_timeout_job,
        config.CAPTCHA_TIMEOUT,
        data={"user_id": member.id, "chat_id": chat.id, "msg_id": msg.message_id},
    )


async def _send_welcome(update, context, member, chat, settings: dict) -> None:
    """Send the configured welcome message."""
    text = build_welcome_message(member, chat, settings)
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("📋 Rules", callback_data="show_rules"),
    ]])
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)


async def on_member_leave(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle member leaving — send goodbye message."""
    chat    = update.effective_chat
    message = update.message

    if not message or not message.left_chat_member:
        return

    member = message.left_chat_member
    if member.is_bot:
        return

    group = await db.get_group(chat.id)
    if not group:
        return

    settings = group.get("settings", {})
    if not settings.get("goodbye", True):
        return

    goodbye_template = settings.get("goodbye_msg", "👋 {name} has left the group.")
    text = goodbye_template.format(
        name=member.first_name,
        full_name=member.full_name,
        username=f"@{member.username}" if member.username else member.first_name,
        group=chat.title,
        id=member.id,
    )
    await message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


# ═══════════════════════════════════════════════════════════════════════════════
#  CAPTCHA RESPONSE HANDLER
# ═══════════════════════════════════════════════════════════════════════════════

async def on_captcha_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Process captcha answers sent as text messages.
    """
    chat = update.effective_chat
    user = update.effective_user
    message = update.message

    if chat.type == ChatType.PRIVATE:
        return

    # Check if user has a pending captcha
    pending = await db.captcha.find_one({"user_id": user.id, "group_id": chat.id})
    if not pending:
        return

    correct = await db.verify_captcha(user.id, chat.id, message.text or "")

    # Delete user's answer message
    try:
        await message.delete()
    except TelegramError:
        pass

    if correct:
        # Restore permissions
        try:
            await context.bot.restrict_chat_member(
                chat.id,
                user.id,
                permissions=ChatPermissions(
                    can_send_messages=True,
                    can_send_media_messages=True,
                    can_send_other_messages=True,
                    can_add_web_page_previews=True,
                ),
            )
        except TelegramError:
            pass

        group    = await db.get_group(chat.id)
        settings = group.get("settings", {}) if group else {}

        notify = await context.bot.send_message(
            chat.id,
            f"✅ {user_mention(user)} passed verification! Welcome!",
            parse_mode=ParseMode.MARKDOWN,
        )

        # Send welcome after captcha
        if settings.get("welcome", True):
            await _send_welcome_direct(context, user, chat, settings)

        # Auto-delete verification message
        await asyncio.sleep(10)
        try:
            await notify.delete()
        except TelegramError:
            pass
    else:
        # Wrong answer — kick user
        try:
            await context.bot.ban_chat_member(chat.id, user.id)
            await context.bot.unban_chat_member(chat.id, user.id)
        except TelegramError:
            pass
        await context.bot.send_message(
            chat.id,
            f"❌ {user_mention(user)} failed verification and was removed.",
            parse_mode=ParseMode.MARKDOWN,
        )


async def _send_welcome_direct(context, user, chat, settings: dict) -> None:
    """Send welcome message directly via bot context."""
    text = build_welcome_message(user, chat, settings)
    await context.bot.send_message(chat.id, text, parse_mode=ParseMode.MARKDOWN)


# ═══════════════════════════════════════════════════════════════════════════════
#  MESSAGE FILTER — ANTI-SPAM / ANTI-LINK / KEYWORDS / BANNED WORDS
# ═══════════════════════════════════════════════════════════════════════════════

async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Main message filter handler. Runs on every group message.
    Order: banned words → anti-link → anti-spam → AI toxicity → keyword reply
    """
    chat    = update.effective_chat
    user    = update.effective_user
    message = update.message

    if not message or not user or chat.type == ChatType.PRIVATE:
        return

    text = message.text or message.caption or ""

    # Skip admins
    try:
        member = await chat.get_member(user.id)
        if member.status in ("administrator", "creator"):
            # Still check keywords for admins
            await _check_keywords(update, context, text, chat.id)
            return
    except TelegramError:
        return

    # Update activity
    await db.users.update_one(
        {"user_id": user.id},
        {"$inc": {"message_count": 1}, "$set": {"last_seen": datetime.now(timezone.utc)}},
    )

    group = await db.get_group(chat.id)
    if not group:
        return

    settings = group.get("settings", {})

    # ── Banned Words ──────────────────────────────────────────────────────────
    banned_words = await db.get_banned_words(chat.id)
    text_lower   = text.lower()
    if any(bw in text_lower for bw in banned_words):
        try:
            await message.delete()
            await _warn_user(update, context, user, chat, "banned word usage")
        except TelegramError:
            pass
        return

    # ── Anti-Link ─────────────────────────────────────────────────────────────
    if settings.get("anti_link", True) and contains_link(text):
        # Check if user is VIP (VIP can post links)
        user_doc = await db.get_user(user.id)
        user_role = user_doc.get("role", "member") if user_doc else "member"
        if user_role not in ("vip", "admin", "owner", "moderator"):
            try:
                await message.delete()
                notice = await context.bot.send_message(
                    chat.id,
                    f"🔗 {user_mention(user)}, links are not allowed here!",
                    parse_mode=ParseMode.MARKDOWN,
                )
                await _warn_user(update, context, user, chat, "posting a link")
                await asyncio.sleep(5)
                try:
                    await notice.delete()
                except TelegramError:
                    pass
            except TelegramError:
                pass
            return

    # ── Anti-Spam ─────────────────────────────────────────────────────────────
    if settings.get("anti_spam", True):
        rate_prob = spam_tracker.record(user.id)
        spam_prob = estimate_spam_probability(text, rate_prob)

        is_spam, reason = analyze_spam(text, spam_prob)
        if is_spam:
            strikes = spam_tracker.add_strike(user.id)
            try:
                await message.delete()
            except TelegramError:
                pass

            if strikes >= 3:
                # Mute after 3 strikes
                spam_tracker.reset(user.id)
                mute_until = datetime.now(timezone.utc) + timedelta(minutes=10)
                try:
                    await context.bot.restrict_chat_member(
                        chat.id, user.id,
                        permissions=ChatPermissions(can_send_messages=False),
                        until_date=mute_until,
                    )
                    await context.bot.send_message(
                        chat.id,
                        f"🚫 {user_mention(user)} auto-muted for 10m (spam detected).",
                        parse_mode=ParseMode.MARKDOWN,
                    )
                    await db.log_action("auto_mute", user.id, chat.id, details={"reason": "spam"})
                except TelegramError:
                    pass
            else:
                try:
                    warning = await context.bot.send_message(
                        chat.id,
                        f"⚠️ {user_mention(user)}, slow down! (Strike {strikes}/3)",
                        parse_mode=ParseMode.MARKDOWN,
                    )
                    await asyncio.sleep(5)
                    await warning.delete()
                except TelegramError:
                    pass
            return

    # ── AI Toxicity Check ─────────────────────────────────────────────────────
    if config.ENABLE_AI_MODERATION and text:
        is_toxic, confidence = analyze_toxicity(text)
        if is_toxic and confidence > 0.7:
            try:
                await message.delete()
                warn_msg = await context.bot.send_message(
                    chat.id,
                    f"⚠️ {user_mention(user)}, toxic content detected and removed.",
                    parse_mode=ParseMode.MARKDOWN,
                )
                await db.log_action("auto_delete_toxic", user.id, chat.id,
                                    details={"confidence": confidence})
                await asyncio.sleep(8)
                await warn_msg.delete()
            except TelegramError:
                pass
            return

    # ── Keyword Auto-Reply ────────────────────────────────────────────────────
    await _check_keywords(update, context, text, chat.id)


async def _check_keywords(update, context, text: str, group_id: int) -> None:
    """Check message text for keyword triggers and auto-reply."""
    if not text:
        return
    response = await db.find_keyword_response(group_id, text)
    if response:
        await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)


async def _warn_user(update, context, user, chat, reason: str) -> None:
    """Issue a warning and take action if limit reached."""
    warn_limit = await db.get_group_setting(chat.id, "warn_limit", config.WARN_LIMIT)
    mute_first = await db.get_group_setting(chat.id, "mute_first", True)
    warns      = await db.add_warn(user.id, chat.id, reason)

    if warns >= warn_limit:
        if mute_first:
            until = datetime.now(timezone.utc) + timedelta(hours=24)
            try:
                await context.bot.restrict_chat_member(
                    chat.id, user.id,
                    permissions=ChatPermissions(can_send_messages=False),
                    until_date=until,
                )
                await context.bot.send_message(
                    chat.id,
                    f"🚨 {user_mention(user)} auto-muted 24h (warn limit reached).",
                    parse_mode=ParseMode.MARKDOWN,
                )
            except TelegramError:
                pass
        else:
            try:
                await context.bot.ban_chat_member(chat.id, user.id)
                await context.bot.send_message(
                    chat.id,
                    f"🔨 {user_mention(user)} auto-banned (warn limit reached).",
                    parse_mode=ParseMode.MARKDOWN,
                )
            except TelegramError:
                pass


# ═══════════════════════════════════════════════════════════════════════════════
#  SCHEDULED JOBS
# ═══════════════════════════════════════════════════════════════════════════════

async def _captcha_timeout_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Kick user who didn't complete captcha in time."""
    data    = context.job.data
    user_id = data["user_id"]
    chat_id = data["chat_id"]

    # Check if still pending
    pending = await db.captcha.find_one({"user_id": user_id, "group_id": chat_id})
    if pending:
        await db.remove_captcha_pending(user_id, chat_id)
        try:
            await context.bot.ban_chat_member(chat_id, user_id)
            await context.bot.unban_chat_member(chat_id, user_id)
            await context.bot.send_message(
                chat_id,
                f"⏰ User `{user_id}` removed (captcha timeout).",
                parse_mode=ParseMode.MARKDOWN,
            )
        except TelegramError:
            pass


async def _unlock_group_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Re-open group after anti-raid lock expires."""
    chat_id = context.job.data["chat_id"]
    try:
        await context.bot.set_chat_permissions(
            chat_id,
            ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
            ),
        )
        await context.bot.send_message(
            chat_id,
            "✅ *Anti-Raid lock lifted.* Group is open again.",
            parse_mode=ParseMode.MARKDOWN,
        )
        await db.clear_raid_mode(chat_id)
    except TelegramError as e:
        logger.warning(f"Group unlock failed: {e}")


async def send_scheduled_announcements(context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    APScheduler job: deliver active announcements.
    Runs every hour and filters by daily/weekly schedule.
    """
    now  = datetime.now(timezone.utc)
    anns = await db.get_active_announcements()

    for ann in anns:
        last_sent = ann.get("last_sent")
        schedule  = ann.get("schedule", "daily")

        should_send = False
        if schedule == "daily" and (not last_sent or (now - last_sent).total_seconds() >= 86400):
            should_send = True
        elif schedule == "weekly" and (not last_sent or (now - last_sent).total_seconds() >= 604800):
            should_send = True

        if should_send:
            try:
                await context.bot.send_message(
                    ann["group_id"],
                    f"📢 *Announcement*\n\n{ann['message']}",
                    parse_mode=ParseMode.MARKDOWN,
                )
                await db.mark_announcement_sent(str(ann["_id"]))
            except TelegramError as e:
                logger.warning(f"Announcement send failed for group {ann['group_id']}: {e}")
