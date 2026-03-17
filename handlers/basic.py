"""
╔══════════════════════════════════════════╗
║  Basic Command Handlers                  ║
║  /start  /help  /ping  /id               ║
╚══════════════════════════════════════════╝
"""

import time
from datetime import datetime, timezone

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ChatType, ParseMode
from telegram.ext import ContextTypes
from loguru import logger

from config import config
from database.db import db
from locales.strings import get_string
from utils.helpers import user_mention


# ─── /start ──────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command in PM and groups."""
    user = update.effective_user
    chat = update.effective_chat

    # Register user in DB
    await db.get_or_create_user(user.id, user.username or "", user.full_name)

    # Determine language
    user_doc = await db.get_user(user.id)
    lang = user_doc.get("language", config.DEFAULT_LANGUAGE) if user_doc else config.DEFAULT_LANGUAGE

    if chat.type == ChatType.PRIVATE:
        text = get_string("welcome_pm", lang)
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📚 Help",      callback_data="menu_help"),
                InlineKeyboardButton("🛡️ Features",  callback_data="menu_features"),
            ],
            [
                InlineKeyboardButton("💎 Premium",   callback_data="menu_premium"),
                InlineKeyboardButton("🌐 Language",  callback_data="menu_language"),
            ],
            [
                InlineKeyboardButton("📊 Stats",     callback_data="menu_stats"),
                InlineKeyboardButton("➕ Add to Group", url=f"https://t.me/{config.USERNAME}?startgroup=true"),
            ],
        ])
        await update.message.reply_text(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(
            f"👋 Hello {user_mention(user)}! Use /help to see all commands.",
            parse_mode=ParseMode.MARKDOWN,
        )


# ─── /help ───────────────────────────────────────────────────────────────────

HELP_TEXT = """
📚 *Command Help Center*

━━━━━━━━━━━━━━━━━━━━━
🔧 *Basic Commands*
━━━━━━━━━━━━━━━━━━━━━
/start — Welcome message
/help — This menu
/ping — Check bot latency
/id — Show your / group ID
/stats — Global bot stats
/rules — Show group rules
/language — Change language

━━━━━━━━━━━━━━━━━━━━━
⚙️ *Group Setup*
━━━━━━━━━━━━━━━━━━━━━
/setgroup — Initialize group
/setrules — Set group rules
/setwelcome — Custom welcome
/setgoodbye — Goodbye message
/settings — Group settings panel
/togglecaptcha — Enable/disable captcha
/toggleantilink — Toggle anti-link
/toggleantispam — Toggle anti-spam
/toggleantiraid — Toggle anti-raid

━━━━━━━━━━━━━━━━━━━━━
🛡️ *Moderation*
━━━━━━━━━━━━━━━━━━━━━
/ban [user] [reason] — Ban user
/unban [user] — Unban user
/kick [user] — Remove user
/mute [user] [time] — Mute user
/unmute [user] — Unmute user
/warn [user] [reason] — Warn user
/clearwarn [user] — Clear warnings
/purge [count] — Delete messages

━━━━━━━━━━━━━━━━━━━━━
👑 *Role Management*
━━━━━━━━━━━━━━━━━━━━━
/promote [user] — Make admin
/demote [user] — Remove admin
/addmod [user] — Add moderator
/removemod [user] — Remove mod
/myrole — Check your role

━━━━━━━━━━━━━━━━━━━━━
💎 *Premium*
━━━━━━━━━━━━━━━━━━━━━
/redeem [code] — Activate premium
/premium — Check premium status
/gencode [days] — Generate code (Owner)

━━━━━━━━━━━━━━━━━━━━━
🤖 *Smart Features*
━━━━━━━━━━━━━━━━━━━━━
/addkeyword — Add auto-reply
/delkeyword — Delete auto-reply
/keywords — List keywords
/addbword — Add banned word
/delbword — Remove banned word
/bwords — List banned words
/announce — Schedule announcement

━━━━━━━━━━━━━━━━━━━━━
🗄️ *Data Management*
━━━━━━━━━━━━━━━━━━━━━
/backup — Backup group data
/export — Export as JSON
/broadcast — Send to all groups (Owner)
"""

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display categorized help menu."""
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🛡️ Moderation",  callback_data="help_mod"),
            InlineKeyboardButton("👑 Roles",        callback_data="help_roles"),
        ],
        [
            InlineKeyboardButton("💎 Premium",      callback_data="help_premium"),
            InlineKeyboardButton("🤖 Auto Features",callback_data="help_auto"),
        ],
        [
            InlineKeyboardButton("📊 Stats & Logs", callback_data="help_stats"),
            InlineKeyboardButton("🔙 Back",         callback_data="menu_main"),
        ],
    ])
    await update.message.reply_text(
        HELP_TEXT,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard,
    )


# ─── /ping ───────────────────────────────────────────────────────────────────

async def cmd_ping(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Measure and display bot response latency."""
    start = time.monotonic()
    msg = await update.message.reply_text("🏓 Pinging...")
    elapsed_ms = round((time.monotonic() - start) * 1000)
    await msg.edit_text(f"🏓 *Pong!*\n⚡ Latency: `{elapsed_ms}ms`", parse_mode=ParseMode.MARKDOWN)


# ─── /id ─────────────────────────────────────────────────────────────────────

async def cmd_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display user and chat IDs."""
    user = update.effective_user
    chat = update.effective_chat

    lines = [f"🆔 *Your User ID:* `{user.id}`"]

    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
        lines.append(f"👤 *Replied User ID:* `{target.id}`")
        if target.username:
            lines.append(f"📛 *Username:* @{target.username}")

    if chat.type != ChatType.PRIVATE:
        lines.append(f"🏘️ *Group ID:* `{chat.id}`")
        lines.append(f"📝 *Group Title:* {chat.title}")

    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)


# ─── /stats ──────────────────────────────────────────────────────────────────

async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show global bot statistics."""
    stats = await db.get_stats()
    text = (
        f"📊 *Bot Statistics*\n\n"
        f"👥 Total Users: `{stats['total_users']:,}`\n"
        f"🏘️ Total Groups: `{stats['total_groups']:,}`\n"
        f"💎 Premium Users: `{stats['premium_users']:,}`\n"
        f"⚡ Actions Today: `{stats['actions_today']:,}`\n\n"
        f"📋 *All Time*\n"
        f"🔨 Bans:  `{stats['total_bans']:,}`\n"
        f"⚠️ Warns: `{stats['total_warns']:,}`\n"
        f"🔇 Mutes: `{stats['total_mutes']:,}`\n"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


# ─── /rules ──────────────────────────────────────────────────────────────────

async def cmd_rules(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display group rules."""
    chat = update.effective_chat
    if chat.type == ChatType.PRIVATE:
        await update.message.reply_text("ℹ️ Use this command in a group.")
        return

    group = await db.get_group(chat.id)
    rules = group.get("rules", "No rules set.") if group else "Group not configured. Use /setgroup."
    await update.message.reply_text(
        f"📋 *Group Rules*\n\n{rules}",
        parse_mode=ParseMode.MARKDOWN,
    )


# ─── /myrole ─────────────────────────────────────────────────────────────────

async def cmd_myrole(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show the user's current role."""
    from utils.helpers import get_user_role
    user = update.effective_user
    role = await get_user_role(update, user.id, db)
    role_icons = {
        "owner":     "👑",
        "admin":     "🔱",
        "moderator": "🛡️",
        "vip":       "💎",
        "member":    "👤",
    }
    icon = role_icons.get(role, "👤")
    premium = await db.is_premium(user.id)
    user_doc = await db.get_user(user.id)
    warns = user_doc.get("warns", 0) if user_doc else 0

    text = (
        f"{icon} *Your Role Profile*\n\n"
        f"👤 Name: {user_mention(user)}\n"
        f"🎭 Role: `{role.title()}`\n"
        f"⚠️ Warns: `{warns}`\n"
        f"💎 Premium: {'✅ Active' if premium else '❌ Inactive'}\n"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


# ─── /language ───────────────────────────────────────────────────────────────

async def cmd_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Language selection menu."""
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"),
            InlineKeyboardButton("🇪🇸 Español", callback_data="lang_es"),
        ],
        [
            InlineKeyboardButton("🇫🇷 Français", callback_data="lang_fr"),
            InlineKeyboardButton("🇩🇪 Deutsch",  callback_data="lang_de"),
        ],
        [
            InlineKeyboardButton("🇸🇦 Arabic",   callback_data="lang_ar"),
        ],
    ])
    await update.message.reply_text(
        "🌐 *Select your language:*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard,
    )
