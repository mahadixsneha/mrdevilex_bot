"""
╔══════════════════════════════════════════╗
║  Premium & Monetization Handlers         ║
║  /premium /redeem /gencode               ║
╚══════════════════════════════════════════╝
"""

from datetime import datetime, timezone

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from loguru import logger

from config import config
from database.db import db
from utils.helpers import generate_code, expires_in


# ─── /premium ────────────────────────────────────────────────────────────────

async def cmd_premium(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /premium
    Check the user's premium subscription status.
    """
    user     = update.effective_user
    user_doc = await db.get_user(user.id)

    if not user_doc:
        await update.message.reply_text("ℹ️ Use /start first to register.")
        return

    expiry   = user_doc.get("premium_expiry")
    is_prem  = await db.is_premium(user.id)
    time_left = expires_in(expiry) if expiry else "Not active"

    status_icon = "💎" if is_prem else "⬜"
    status_text = "Active" if is_prem else "Inactive"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎟️ Redeem Code", callback_data="premium_redeem")],
        [InlineKeyboardButton("💎 Premium Perks", callback_data="premium_perks")],
    ])

    await update.message.reply_text(
        f"{status_icon} *Premium Status*\n\n"
        f"👤 User: [{user.full_name}](tg://user?id={user.id})\n"
        f"💎 Status: *{status_text}*\n"
        f"⏳ Expires: `{time_left}`\n\n"
        f"{'_Your premium features are active!_' if is_prem else '_Use /redeem <code> to activate premium._'}",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard,
    )


# ─── /redeem ─────────────────────────────────────────────────────────────────

async def cmd_redeem(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /redeem <code>
    Redeem a premium activation code.
    """
    user = update.effective_user

    if not context.args:
        await update.message.reply_text(
            "🎟️ Usage: `/redeem <your-code>`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    code     = context.args[0].strip().upper()
    code_doc = await db.redeem_code(code, user.id)

    if not code_doc:
        await update.message.reply_text(
            "❌ *Invalid or already used code!*\n\nCheck the code and try again.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    days      = code_doc["days"]
    user_doc  = await db.get_user(user.id)
    expiry    = user_doc.get("premium_expiry") if user_doc else None
    time_left = expires_in(expiry)

    await update.message.reply_text(
        f"🎉 *Premium Activated!*\n\n"
        f"✅ Code: `{code}`\n"
        f"📅 Duration: `{days} days`\n"
        f"⏳ Expires: `{time_left}`\n\n"
        f"💎 You now have VIP access!",
        parse_mode=ParseMode.MARKDOWN,
    )
    logger.info(f"User {user.id} redeemed code {code} for {days} days premium")


# ─── /gencode ────────────────────────────────────────────────────────────────

async def cmd_gencode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /gencode [days] [count]
    Generate premium activation codes. Owner only.
    """
    user = update.effective_user

    if int(user.id) != int(config.OWNER_ID):
        await update.message.reply_text("🚫 Bot owner only.")
        return

    days  = 30
    count = 1

    if context.args:
        try:
            days = int(context.args[0])
        except ValueError:
            pass
        if len(context.args) > 1:
            try:
                count = min(int(context.args[1]), 20)  # max 20 at once
            except ValueError:
                pass

    codes = []
    for _ in range(count):
        code = generate_code(12)
        await db.create_premium_code(code, days, user.id)
        codes.append(code)

    codes_text = "\n".join(f"• `{c}`" for c in codes)
    await update.message.reply_text(
        f"🎟️ *Generated {count} Premium Code(s)*\n"
        f"📅 Duration: `{days} days` each\n\n"
        f"{codes_text}\n\n"
        f"_Share these codes with your users._",
        parse_mode=ParseMode.MARKDOWN,
    )


# ─── /listcodes ──────────────────────────────────────────────────────────────

async def cmd_listcodes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /listcodes
    List all active (unused) premium codes. Owner only.
    """
    user = update.effective_user

    if int(user.id) != int(config.OWNER_ID):
        await update.message.reply_text("🚫 Bot owner only.")
        return

    codes = await db.get_active_codes()

    if not codes:
        await update.message.reply_text("📭 No active codes.")
        return

    lines = [f"🎟️ *Active Premium Codes* (`{len(codes)}`)\n"]
    for c in codes[:20]:  # show max 20
        lines.append(f"• `{c['code']}` — `{c['days']}d`")

    await update.message.reply_text(
        "\n".join(lines),
        parse_mode=ParseMode.MARKDOWN,
    )


# ─── PREMIUM CALLBACK ─────────────────────────────────────────────────────────

async def premium_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle premium menu inline buttons."""
    query = update.callback_query
    await query.answer()
    data  = query.data

    if data == "premium_redeem":
        await query.edit_message_text(
            "🎟️ *Redeem a Premium Code*\n\nSend: `/redeem <your-code>`",
            parse_mode=ParseMode.MARKDOWN,
        )

    elif data == "premium_perks":
        await query.edit_message_text(
            "💎 *Premium VIP Perks*\n\n"
            "✅ Post links freely\n"
            "✅ Bypass slow-mode\n"
            "✅ VIP badge in role\n"
            "✅ Priority support\n"
            "✅ Access to exclusive features\n\n"
            "_Redeem a code to unlock these features!_",
            parse_mode=ParseMode.MARKDOWN,
        )
