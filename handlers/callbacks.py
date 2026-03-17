"""
╔══════════════════════════════════════════╗
║  Inline Keyboard Callback Dispatcher     ║
╚══════════════════════════════════════════╝
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from database.db import db
from config import config
from handlers.premium import premium_callback
from handlers.group_setup import settings_callback


FEATURES_TEXT = """
🛡️ *Advanced Features*

━━━━━━━━━━━━━━━━━━━
🤖 *AI Moderation*
• Toxic message detection
• Spam probability scoring
• Auto-remove offensive content

🛡️ *Auto Protection*
• Anti-link filtering
• Anti-spam rate limiting
• Anti-raid join flood guard
• Math captcha verification

⚙️ *Smart Automation*
• Custom welcome messages
• Auto-reply keywords
• Scheduled announcements
• Banned word filter

💎 *Premium System*
• VIP role & perks
• Code-based activation
• Premium expiry tracking

📊 *Logging & Analytics*
• Full action logs
• Per-group statistics
• Admin log channel
"""


async def main_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Route all callback_query events to the appropriate handler."""
    query = update.callback_query
    data  = query.data

    # Route to sub-handlers
    if data.startswith("stg_"):
        return await settings_callback(update, context)

    if data.startswith("premium_"):
        return await premium_callback(update, context)

    if data.startswith("lang_"):
        return await _handle_language(update, context)

    if data.startswith("help_"):
        return await _handle_help_section(update, context)

    if data == "menu_help":
        await query.answer()
        from handlers.basic import HELP_TEXT
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="menu_main")],
        ])
        await query.edit_message_text(HELP_TEXT, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)

    elif data == "menu_features":
        await query.answer()
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="menu_main")],
        ])
        await query.edit_message_text(FEATURES_TEXT, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)

    elif data == "menu_premium":
        await query.answer()
        user = update.effective_user
        is_prem = await db.is_premium(user.id)
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎟️ Redeem Code", callback_data="premium_redeem")],
            [InlineKeyboardButton("💎 View Perks", callback_data="premium_perks")],
            [InlineKeyboardButton("🔙 Back", callback_data="menu_main")],
        ])
        await query.edit_message_text(
            f"💎 *Premium System*\n\nStatus: {'✅ Active' if is_prem else '❌ Inactive'}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard,
        )

    elif data == "menu_stats":
        await query.answer()
        stats = await db.get_stats()
        text = (
            f"📊 *Live Bot Statistics*\n\n"
            f"👥 Users: `{stats['total_users']:,}`\n"
            f"🏘️ Groups: `{stats['total_groups']:,}`\n"
            f"💎 Premium: `{stats['premium_users']:,}`\n"
            f"⚡ Today: `{stats['actions_today']:,}`\n"
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="menu_main")],
        ])
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)

    elif data == "menu_language":
        await query.answer()
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
                InlineKeyboardButton("🔙 Back",       callback_data="menu_main"),
            ],
        ])
        await query.edit_message_text(
            "🌐 *Select your language:*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard,
        )

    elif data == "menu_main":
        await query.answer()
        from locales.strings import get_string
        user = update.effective_user
        user_doc = await db.get_user(user.id)
        lang = user_doc.get("language", config.DEFAULT_LANGUAGE) if user_doc else config.DEFAULT_LANGUAGE
        text = get_string("welcome_pm", lang)
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📚 Help",       callback_data="menu_help"),
                InlineKeyboardButton("🛡️ Features",   callback_data="menu_features"),
            ],
            [
                InlineKeyboardButton("💎 Premium",    callback_data="menu_premium"),
                InlineKeyboardButton("🌐 Language",   callback_data="menu_language"),
            ],
            [
                InlineKeyboardButton("📊 Stats",      callback_data="menu_stats"),
                InlineKeyboardButton("➕ Add to Group", url=f"https://t.me/{config.USERNAME}?startgroup=true"),
            ],
        ])
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)

    elif data == "show_rules":
        await query.answer()
        chat = update.effective_chat
        group = await db.get_group(chat.id)
        rules = group.get("rules", "No rules set.") if group else "No rules set."
        await query.answer(rules[:200], show_alert=True)

    else:
        await query.answer("🔄 Processing...", show_alert=False)


async def _handle_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Set user language preference."""
    query = update.callback_query
    lang  = query.data.split("_")[1]  # lang_en → en

    lang_names = {
        "en": "🇬🇧 English",
        "es": "🇪🇸 Español",
        "fr": "🇫🇷 Français",
        "de": "🇩🇪 Deutsch",
        "ar": "🇸🇦 Arabic",
    }

    await db.users.update_one(
        {"user_id": update.effective_user.id},
        {"$set": {"language": lang}},
    )

    await query.answer(f"Language set to {lang_names.get(lang, lang)}", show_alert=False)
    await query.edit_message_text(
        f"✅ Language set to *{lang_names.get(lang, lang)}*",
        parse_mode=ParseMode.MARKDOWN,
    )


async def _handle_help_section(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show a specific help section."""
    query   = update.callback_query
    section = query.data  # e.g., help_mod

    sections = {
        "help_mod": (
            "🛡️ *Moderation Commands*\n\n"
            "/ban — Ban a user\n"
            "/unban — Unban a user\n"
            "/kick — Kick a user\n"
            "/mute [time] — Mute a user\n"
            "/unmute — Unmute a user\n"
            "/warn [reason] — Warn a user\n"
            "/clearwarn — Clear warnings\n"
            "/purge [count] — Delete messages"
        ),
        "help_roles": (
            "👑 *Role Management*\n\n"
            "Roles (high → low):\n"
            "👑 Owner → 🔱 Admin → 🛡️ Moderator → 💎 VIP → 👤 Member\n\n"
            "/promote — Grant Admin\n"
            "/demote — Remove Admin\n"
            "/addmod — Grant Moderator\n"
            "/myrole — Check your role"
        ),
        "help_premium": (
            "💎 *Premium System*\n\n"
            "/premium — Check status\n"
            "/redeem <code> — Activate code\n"
            "/gencode [days] — Generate code (Owner)\n\n"
            "VIP Perks:\n"
            "✅ Post links freely\n"
            "✅ Bypass rate limits\n"
            "✅ VIP badge"
        ),
        "help_auto": (
            "🤖 *Auto Features*\n\n"
            "/setwelcome — Custom welcome\n"
            "/setgoodbye — Goodbye message\n"
            "/addkeyword — Auto-reply trigger\n"
            "/addbword — Banned word\n"
            "/announce — Scheduled post\n\n"
            "Auto Systems:\n"
            "🔗 Anti-link\n"
            "🛑 Anti-spam\n"
            "🚨 Anti-raid\n"
            "🔐 Captcha"
        ),
        "help_stats": (
            "📊 *Stats & Logging*\n\n"
            "/stats — Global statistics\n"
            "/backup — Export group data\n"
            "/export — JSON data export\n"
            "/broadcast — Message all groups\n\n"
            "📝 All actions are logged to MongoDB"
        ),
    }

    text = sections.get(section, "Section not found.")
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back to Help", callback_data="menu_help")],
    ])
    await query.answer()
    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
