"""
╔══════════════════════════════════════════╗
║  Group Setup & Configuration Handlers    ║
╚══════════════════════════════════════════╝
"""

import json
import os
from datetime import datetime, timezone

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ChatType, ParseMode, ChatMemberStatus
from telegram.ext import ContextTypes
from telegram.error import TelegramError
from loguru import logger

from config import config
from database.db import db
from utils.helpers import get_user_role
from config import Roles


# ─── /setgroup ───────────────────────────────────────────────────────────────

async def cmd_setgroup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /setgroup
    Initialize or reinitialize this group in the database.
    Must be run by the group owner or bot owner.
    """
    chat = update.effective_chat
    user = update.effective_user

    if chat.type == ChatType.PRIVATE:
        await update.message.reply_text("ℹ️ This command must be used in a group.")
        return

    # Allow: bot owner, group creator, or any group admin
    member = await chat.get_member(user.id)
    is_creator   = member.status == ChatMemberStatus.OWNER
    is_admin     = member.status == ChatMemberStatus.ADMINISTRATOR
    is_bot_owner = int(user.id) == int(config.OWNER_ID)

    if not (is_creator or is_admin or is_bot_owner):
        await update.message.reply_text("🚫 Only group admins can initialize the group.")
        return

    await update.message.reply_text("⏳ Setting up group...")

    # Setup group in DB
    group_doc = await db.setup_group(chat.id, chat.title, user.id)

    # Sync current admins from Telegram
    admins = await chat.get_administrators()
    admin_ids = [a.user.id for a in admins if not a.user.is_bot]
    for admin_id in admin_ids:
        await db.add_group_admin(chat.id, admin_id)

    await update.message.reply_text(
        f"✅ *Group Initialized!*\n\n"
        f"🏘️ *Title:* {chat.title}\n"
        f"🆔 *ID:* `{chat.id}`\n"
        f"👑 *Owner:* [{update.effective_user.full_name}](tg://user?id={user.id})\n"
        f"👮 *Admins synced:* `{len(admin_ids)}`\n\n"
        f"Use /settings to configure the group.",
        parse_mode=ParseMode.MARKDOWN,
    )


# ─── /settings ───────────────────────────────────────────────────────────────

async def cmd_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display an inline settings control panel for the group."""
    chat = update.effective_chat
    user = update.effective_user

    if chat.type == ChatType.PRIVATE:
        await update.message.reply_text("ℹ️ Use this command in a group.")
        return

    role = await get_user_role(update, user.id, db)
    if role not in (Roles.OWNER, Roles.ADMIN):
        await update.message.reply_text("🚫 Only admins can access settings.")
        return

    group = await db.get_group(chat.id)
    if not group:
        await update.message.reply_text("⚠️ Group not set up. Use /setgroup first.")
        return

    settings = group.get("settings", {})

    def toggle_icon(key: str) -> str:
        return "✅" if settings.get(key, True) else "❌"

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(f"{toggle_icon('anti_link')} Anti-Link",  callback_data="stg_anti_link"),
            InlineKeyboardButton(f"{toggle_icon('anti_spam')} Anti-Spam",  callback_data="stg_anti_spam"),
        ],
        [
            InlineKeyboardButton(f"{toggle_icon('anti_raid')} Anti-Raid",  callback_data="stg_anti_raid"),
            InlineKeyboardButton(f"{toggle_icon('captcha')} Captcha",      callback_data="stg_captcha"),
        ],
        [
            InlineKeyboardButton(f"{toggle_icon('welcome')} Welcome Msg",  callback_data="stg_welcome"),
            InlineKeyboardButton(f"{toggle_icon('goodbye')} Goodbye Msg",  callback_data="stg_goodbye"),
        ],
        [
            InlineKeyboardButton(f"{toggle_icon('log_actions')} Action Logs", callback_data="stg_log_actions"),
            InlineKeyboardButton(f"⚠️ Warn Limit: {settings.get('warn_limit',3)}", callback_data="stg_warn_limit"),
        ],
        [
            InlineKeyboardButton("📋 Rules", callback_data="stg_rules"),
            InlineKeyboardButton("🔙 Close",  callback_data="stg_close"),
        ],
    ])

    await update.message.reply_text(
        f"⚙️ *Settings Panel — {chat.title}*\n\n"
        f"Tap a button to toggle a feature ON/OFF.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard,
    )


# ─── /setrules ───────────────────────────────────────────────────────────────

async def cmd_setrules(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /setrules <rules text>
    Set the group rules.
    """
    chat = update.effective_chat
    user = update.effective_user

    role = await get_user_role(update, user.id, db)
    if role not in (Roles.OWNER, Roles.ADMIN):
        await update.message.reply_text("🚫 Only admins can set rules.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /setrules <rules text>")
        return

    rules = " ".join(context.args)
    await db.groups.update_one({"group_id": chat.id}, {"$set": {"rules": rules}})
    await update.message.reply_text("📋 *Rules updated successfully!*", parse_mode=ParseMode.MARKDOWN)


# ─── /setwelcome ─────────────────────────────────────────────────────────────

async def cmd_setwelcome(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /setwelcome <message>
    Set a custom welcome message.
    Placeholders: {name}, {full_name}, {username}, {group}, {id}
    """
    chat = update.effective_chat
    user = update.effective_user

    role = await get_user_role(update, user.id, db)
    if role not in (Roles.OWNER, Roles.ADMIN):
        await update.message.reply_text("🚫 Admins only.")
        return

    if not context.args:
        await update.message.reply_text(
            "Usage: `/setwelcome <message>`\n\n"
            "Placeholders:\n"
            "`{name}` — First name\n"
            "`{full_name}` — Full name\n"
            "`{username}` — @Username\n"
            "`{group}` — Group name\n"
            "`{id}` — User ID",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    welcome = " ".join(context.args)
    await db.update_group_setting(chat.id, "welcome_msg", welcome)
    await update.message.reply_text(
        f"✅ *Welcome message updated!*\n\nPreview:\n_{welcome}_",
        parse_mode=ParseMode.MARKDOWN,
    )


# ─── /setgoodbye ─────────────────────────────────────────────────────────────

async def cmd_setgoodbye(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /setgoodbye <message>
    Set a custom goodbye message.
    """
    chat = update.effective_chat
    user = update.effective_user

    role = await get_user_role(update, user.id, db)
    if role not in (Roles.OWNER, Roles.ADMIN):
        await update.message.reply_text("🚫 Admins only.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /setgoodbye <message>")
        return

    goodbye = " ".join(context.args)
    await db.update_group_setting(chat.id, "goodbye_msg", goodbye)
    await update.message.reply_text("✅ *Goodbye message updated!*", parse_mode=ParseMode.MARKDOWN)


# ─── TOGGLE HANDLERS (inline button callbacks) ────────────────────────────────

async def settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle settings panel button presses."""
    query = update.callback_query
    await query.answer()

    data  = query.data
    chat  = update.effective_chat
    user  = update.effective_user

    role = await get_user_role(update, user.id, db)
    if role not in (Roles.OWNER, Roles.ADMIN):
        await query.answer("🚫 Admins only!", show_alert=True)
        return

    setting_map = {
        "stg_anti_link":   "anti_link",
        "stg_anti_spam":   "anti_spam",
        "stg_anti_raid":   "anti_raid",
        "stg_captcha":     "captcha",
        "stg_welcome":     "welcome",
        "stg_goodbye":     "goodbye",
        "stg_log_actions": "log_actions",
    }

    if data == "stg_close":
        await query.message.delete()
        return

    if data == "stg_warn_limit":
        # Cycle warn limit: 2 → 3 → 4 → 5 → 2
        current = await db.get_group_setting(chat.id, "warn_limit", 3)
        new_limit = (current % 5) + 2
        await db.update_group_setting(chat.id, "warn_limit", new_limit)
        await query.answer(f"Warn limit set to {new_limit}", show_alert=False)

    elif data in setting_map:
        key     = setting_map[data]
        current = await db.get_group_setting(chat.id, key, True)
        new_val = not current
        await db.update_group_setting(chat.id, key, new_val)
        status  = "✅ Enabled" if new_val else "❌ Disabled"
        await query.answer(f"{key.replace('_', ' ').title()}: {status}", show_alert=False)

    elif data == "stg_rules":
        group = await db.get_group(chat.id)
        rules = group.get("rules", "Not set.") if group else "Not set."
        await query.answer(f"Rules: {rules[:100]}", show_alert=True)
        return

    # Refresh the settings panel
    group    = await db.get_group(chat.id)
    settings = group.get("settings", {}) if group else {}

    def toggle_icon(key: str) -> str:
        return "✅" if settings.get(key, True) else "❌"

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(f"{toggle_icon('anti_link')} Anti-Link",  callback_data="stg_anti_link"),
            InlineKeyboardButton(f"{toggle_icon('anti_spam')} Anti-Spam",  callback_data="stg_anti_spam"),
        ],
        [
            InlineKeyboardButton(f"{toggle_icon('anti_raid')} Anti-Raid",  callback_data="stg_anti_raid"),
            InlineKeyboardButton(f"{toggle_icon('captcha')} Captcha",      callback_data="stg_captcha"),
        ],
        [
            InlineKeyboardButton(f"{toggle_icon('welcome')} Welcome Msg",  callback_data="stg_welcome"),
            InlineKeyboardButton(f"{toggle_icon('goodbye')} Goodbye Msg",  callback_data="stg_goodbye"),
        ],
        [
            InlineKeyboardButton(f"{toggle_icon('log_actions')} Action Logs", callback_data="stg_log_actions"),
            InlineKeyboardButton(f"⚠️ Warn Limit: {settings.get('warn_limit',3)}", callback_data="stg_warn_limit"),
        ],
        [
            InlineKeyboardButton("📋 Rules", callback_data="stg_rules"),
            InlineKeyboardButton("🔙 Close",  callback_data="stg_close"),
        ],
    ])

    try:
        await query.edit_message_reply_markup(reply_markup=keyboard)
    except TelegramError:
        pass


# ─── KEYWORD MANAGEMENT ───────────────────────────────────────────────────────

async def cmd_addkeyword(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /addkeyword <trigger> | <response>
    Add an auto-reply keyword.
    """
    chat = update.effective_chat
    user = update.effective_user

    role = await get_user_role(update, user.id, db)
    if role not in (Roles.OWNER, Roles.ADMIN, Roles.MODERATOR):
        await update.message.reply_text("🚫 Moderators and above only.")
        return

    full_text = " ".join(context.args) if context.args else ""
    if "|" not in full_text:
        await update.message.reply_text("Usage: /addkeyword <trigger> | <response>")
        return

    parts    = full_text.split("|", 1)
    trigger  = parts[0].strip()
    response = parts[1].strip()

    await db.add_keyword(chat.id, trigger, response)
    await update.message.reply_text(
        f"✅ Keyword added!\n🔑 Trigger: `{trigger}`\n💬 Response: _{response}_",
        parse_mode=ParseMode.MARKDOWN,
    )


async def cmd_delkeyword(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /delkeyword <trigger>
    Remove an auto-reply keyword.
    """
    chat = update.effective_chat
    user = update.effective_user

    role = await get_user_role(update, user.id, db)
    if role not in (Roles.OWNER, Roles.ADMIN):
        await update.message.reply_text("🚫 Admins only.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /delkeyword <trigger>")
        return

    trigger = " ".join(context.args)
    deleted = await db.remove_keyword(chat.id, trigger)

    if deleted:
        await update.message.reply_text(f"✅ Keyword `{trigger}` removed.", parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(f"❌ Keyword `{trigger}` not found.", parse_mode=ParseMode.MARKDOWN)


async def cmd_keywords(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /keywords
    List all auto-reply keywords.
    """
    chat = update.effective_chat
    keywords = await db.get_keywords(chat.id)

    if not keywords:
        await update.message.reply_text("📭 No keywords configured.")
        return

    lines = [f"🔑 *Keywords — {chat.title}*\n"]
    for kw in keywords:
        lines.append(f"• `{kw['trigger']}` → _{kw['response']}_")

    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)


# ─── BANNED WORDS ─────────────────────────────────────────────────────────────

async def cmd_addbword(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /addbword <word>
    Add a word to the banned word list.
    """
    chat = update.effective_chat
    user = update.effective_user

    role = await get_user_role(update, user.id, db)
    if role not in (Roles.OWNER, Roles.ADMIN):
        await update.message.reply_text("🚫 Admins only.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /addbword <word>")
        return

    word = " ".join(context.args).lower()
    await db.add_banned_word(chat.id, word)
    await update.message.reply_text(f"✅ `{word}` added to banned words.", parse_mode=ParseMode.MARKDOWN)


async def cmd_delbword(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /delbword <word>
    Remove a banned word.
    """
    chat = update.effective_chat
    user = update.effective_user

    role = await get_user_role(update, user.id, db)
    if role not in (Roles.OWNER, Roles.ADMIN):
        await update.message.reply_text("🚫 Admins only.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /delbword <word>")
        return

    word = " ".join(context.args)
    await db.remove_banned_word(chat.id, word)
    await update.message.reply_text(f"✅ `{word}` removed from banned words.", parse_mode=ParseMode.MARKDOWN)


async def cmd_bwords(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /bwords
    Show all banned words.
    """
    chat = update.effective_chat
    words = await db.get_banned_words(chat.id)

    if not words:
        await update.message.reply_text("📭 No banned words configured.")
        return

    text = "🚫 *Banned Words:*\n\n" + "\n".join(f"• `{w}`" for w in words)
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


# ─── ANNOUNCEMENTS ────────────────────────────────────────────────────────────

async def cmd_announce(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /announce [daily|weekly] <message>
    Create a scheduled announcement.
    """
    chat = update.effective_chat
    user = update.effective_user

    role = await get_user_role(update, user.id, db)
    if role not in (Roles.OWNER, Roles.ADMIN):
        await update.message.reply_text("🚫 Admins only.")
        return

    if not context.args or len(context.args) < 2:
        await update.message.reply_text("Usage: /announce [daily|weekly] <message>")
        return

    schedule = context.args[0].lower()
    if schedule not in ("daily", "weekly"):
        await update.message.reply_text("❌ Schedule must be `daily` or `weekly`.", parse_mode=ParseMode.MARKDOWN)
        return

    message = " ".join(context.args[1:])
    ann_id  = await db.create_announcement(chat.id, message, schedule, user.id)

    await update.message.reply_text(
        f"✅ *Announcement scheduled ({schedule})!*\n\n_{message}_",
        parse_mode=ParseMode.MARKDOWN,
    )


# ─── BACKUP / EXPORT ──────────────────────────────────────────────────────────

async def cmd_backup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /backup
    Create a JSON backup of group data.
    """
    chat = update.effective_chat
    user = update.effective_user

    if int(user.id) != int(config.OWNER_ID):
        role = await get_user_role(update, user.id, db)
        if role != Roles.OWNER:
            await update.message.reply_text("🚫 Owner only.")
            return

    data = await db.export_group_data(chat.id)
    os.makedirs(config.BACKUP_STORAGE_PATH, exist_ok=True)

    filename = f"backup_{chat.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    filepath = os.path.join(config.BACKUP_STORAGE_PATH, filename)

    with open(filepath, "w") as f:
        json.dump(data, f, default=str, indent=2)

    with open(filepath, "rb") as f:
        await context.bot.send_document(
            chat_id=user.id,
            document=f,
            filename=filename,
            caption=f"📦 *Backup — {chat.title}*\n🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            parse_mode=ParseMode.MARKDOWN,
        )

    await update.message.reply_text("✅ Backup sent to your DM!")


async def cmd_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /broadcast <message>
    Send a message to ALL groups (Owner only).
    """
    if int(update.effective_user.id) != int(config.OWNER_ID):
        await update.message.reply_text("🚫 Bot owner only.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /broadcast <message>")
        return

    message = " ".join(context.args)
    group_ids = await db.get_all_group_ids()
    sent = 0
    failed = 0

    for gid in group_ids:
        try:
            await context.bot.send_message(gid, f"📢 *Broadcast*\n\n{message}", parse_mode=ParseMode.MARKDOWN)
            sent += 1
        except TelegramError:
            failed += 1

    await update.message.reply_text(
        f"📢 *Broadcast Complete!*\n✅ Sent: `{sent}` | ❌ Failed: `{failed}`",
        parse_mode=ParseMode.MARKDOWN,
    )
