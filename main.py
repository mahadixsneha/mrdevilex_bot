"""
╔═══════════════════════════════════════════════════════════════╗
║        ⚡  C H A L L E N G E   B Y   M R D E V I L E X  ⚡    ║
║          Advanced Telegram Group Management Bot               ║
║          v2.0 | Render Web Service | Webhook Mode             ║
╚═══════════════════════════════════════════════════════════════╝
"""

import asyncio, sys, os, threading
from loguru import logger
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from contextlib import asynccontextmanager

from telegram import Update
from telegram.ext import (
    Application, ApplicationBuilder,
    CommandHandler, MessageHandler,
    CallbackQueryHandler, filters,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import config
from database.db import db
from handlers.basic import cmd_start, cmd_help, cmd_ping, cmd_id, cmd_stats, cmd_rules, cmd_myrole, cmd_language
from handlers.moderation import cmd_ban, cmd_unban, cmd_kick, cmd_mute, cmd_unmute, cmd_warn, cmd_clearwarn, cmd_purge, cmd_promote, cmd_demote, cmd_addmod
from handlers.group_setup import cmd_setgroup, cmd_settings, cmd_setrules, cmd_setwelcome, cmd_setgoodbye, cmd_addkeyword, cmd_delkeyword, cmd_keywords, cmd_addbword, cmd_delbword, cmd_bwords, cmd_announce, cmd_backup, cmd_broadcast
from handlers.premium import cmd_premium, cmd_redeem, cmd_gencode, cmd_listcodes
from handlers.auto_events import on_member_join, on_member_leave, on_message, on_captcha_answer, send_scheduled_announcements
from handlers.callbacks import main_callback_handler

console = Console()
ptb_app: Application = None
scheduler: AsyncIOScheduler = None


def setup_logging():
    logger.remove()
    logger.add(sys.stdout, colorize=True,
        format="<green>{time:HH:mm:ss}</green> | <level>{level:<8}</level> | <cyan>{name}</cyan> — <white>{message}</white>",
        level="INFO")


def print_banner():
    text = Text()
    text.append("\n  ⚡  CHALLENGE BY MRDEVILEX  ⚡\n", style="bold yellow")
    text.append("  Advanced Telegram Group Manager\n", style="bold cyan")
    text.append("  v2.0 | Render Web Service | Webhook Mode\n", style="dim")
    console.print(Panel(text, border_style="bright_yellow", padding=(0, 2)))


def build_ptb_application() -> Application:
    app = ApplicationBuilder().token(config.TOKEN).updater(None).concurrent_updates(True).build()
    for name, handler in [
        ("start", cmd_start), ("help", cmd_help), ("ping", cmd_ping), ("id", cmd_id),
        ("stats", cmd_stats), ("rules", cmd_rules), ("myrole", cmd_myrole), ("language", cmd_language),
        ("setgroup", cmd_setgroup), ("settings", cmd_settings), ("setrules", cmd_setrules),
        ("setwelcome", cmd_setwelcome), ("setgoodbye", cmd_setgoodbye),
        ("addkeyword", cmd_addkeyword), ("delkeyword", cmd_delkeyword), ("keywords", cmd_keywords),
        ("addbword", cmd_addbword), ("delbword", cmd_delbword), ("bwords", cmd_bwords),
        ("announce", cmd_announce), ("backup", cmd_backup), ("broadcast", cmd_broadcast),
        ("ban", cmd_ban), ("unban", cmd_unban), ("kick", cmd_kick),
        ("mute", cmd_mute), ("unmute", cmd_unmute), ("warn", cmd_warn),
        ("clearwarn", cmd_clearwarn), ("purge", cmd_purge),
        ("promote", cmd_promote), ("demote", cmd_demote), ("addmod", cmd_addmod),
        ("premium", cmd_premium), ("redeem", cmd_redeem),
        ("gencode", cmd_gencode), ("listcodes", cmd_listcodes),
    ]:
        app.add_handler(CommandHandler(name, handler))

    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, on_member_join))
    app.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, on_member_leave))
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & ~filters.UpdateType.EDITED_MESSAGE,
        _message_router,
    ))
    app.add_handler(CallbackQueryHandler(main_callback_handler))
    app.add_error_handler(error_handler)
    return app


async def _message_router(update: Update, context):
    user = update.effective_user
    chat = update.effective_chat
    if not user or not chat:
        return
    from telegram.constants import ChatType
    if chat.type != ChatType.PRIVATE:
        pending = await db.captcha.find_one({"user_id": user.id, "group_id": chat.id})
        if pending:
            await on_captcha_answer(update, context)
            return
    await on_message(update, context)


async def error_handler(update: object, context):
    logger.error(f"Exception: {context.error}", exc_info=context.error)
    try:
        if config.OWNER_ID:
            await context.bot.send_message(int(config.OWNER_ID),
                f"⚠️ *Bot Error*\n\n`{str(context.error)[:500]}`", parse_mode="Markdown")
    except Exception:
        pass


def setup_scheduler(application: Application) -> AsyncIOScheduler:
    sched = AsyncIOScheduler(timezone="UTC")
    sched.add_job(send_scheduled_announcements, "interval", hours=1,
        kwargs={"context": application}, id="announcements", replace_existing=True)
    sched.add_job(_expire_premium_users, "interval", hours=6,
        id="premium_expiry", replace_existing=True)
    return sched


async def _expire_premium_users():
    from datetime import datetime, timezone
    from config import Roles
    now = datetime.now(timezone.utc)
    expired = await db.users.find({
        "premium_expiry": {"$lt": now, "$ne": None}, "role": Roles.VIP,
    }).to_list(length=None)
    for user in expired:
        await db.users.update_one({"user_id": user["user_id"]}, {"$set": {"role": Roles.MEMBER}})
    if expired:
        logger.info(f"Expired premium for {len(expired)} users")


# ── Flask dashboard thread ─────────────────────────────────────────────────────
def start_flask_dashboard():
    try:
        from api.dashboard import app as flask_app
        import logging
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)
        flask_app.run(host="0.0.0.0", port=8080, debug=False, use_reloader=False)
    except Exception as e:
        logger.warning(f"Dashboard not started: {e}")


# ── Main FastAPI app (for webhook) ─────────────────────────────────────────────
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

@asynccontextmanager
async def lifespan(app: FastAPI):
    global ptb_app, scheduler

    print_banner()
    setup_logging()

    try:
        config.validate()
        logger.success("✅ Config validated")
    except ValueError as e:
        logger.error(f"❌ Config error: {e}")
        sys.exit(1)

    await db.connect()
    logger.success("✅ MongoDB connected")

    ptb_app = build_ptb_application()
    await ptb_app.initialize()
    await ptb_app.start()
    logger.success("✅ PTB started")

    webhook_url = f"{config.WEBHOOK_URL.rstrip('/')}/webhook/{config.TOKEN}"
    await ptb_app.bot.set_webhook(url=webhook_url, allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
    logger.success(f"✅ Webhook: {webhook_url}")

    try:
        await ptb_app.bot.send_message(int(config.OWNER_ID),
            f"⚡ *Bot Online!*\n\n🌐 Mode: `Webhook`\n🔗 URL: `{config.WEBHOOK_URL}`",
            parse_mode="Markdown")
    except Exception:
        pass

    scheduler = setup_scheduler(ptb_app)
    scheduler.start()
    logger.success("✅ Scheduler started")

    # Start Flask dashboard in background
    t = threading.Thread(target=start_flask_dashboard, daemon=True)
    t.start()
    logger.success("✅ Dashboard thread started")

    yield

    logger.info("🛑 Shutting down...")
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=False)
    await ptb_app.bot.delete_webhook()
    await ptb_app.stop()
    await ptb_app.shutdown()
    await db.disconnect()
    logger.info("👋 Done")


main_app = FastAPI(lifespan=lifespan, title="MrDevilEx Bot")


@main_app.get("/")
async def root():
    return JSONResponse({"status": "online", "bot": "MrDevilEx", "version": "2.0"})


@main_app.get("/health")
async def health():
    return JSONResponse({"status": "ok"})


@main_app.post("/webhook/{token}")
async def telegram_webhook(token: str, request: Request):
    if token != config.TOKEN:
        return Response(status_code=403)
    try:
        data = await request.json()
        update = Update.de_json(data, ptb_app.bot)
        await ptb_app.process_update(update)
    except Exception as e:
        logger.error(f"Webhook error: {e}")
    return Response(status_code=200)


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "10000"))
    uvicorn.run("main:main_app", host="0.0.0.0", port=port, log_level="warning")
