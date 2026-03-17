"""
╔══════════════════════════════════════════╗
║  Localization — Multi-Language Strings   ║
╚══════════════════════════════════════════╝
"""

from typing import Dict

STRINGS: Dict[str, Dict[str, str]] = {
    # ── ENGLISH ──────────────────────────────────────────────────────────────
    "en": {
        "welcome_pm": (
            "⚡ *Welcome to the Group Manager Bot!*\n\n"
            "I'm a powerful group management bot with advanced moderation, "
            "AI filtering, premium features, and much more.\n\n"
            "📌 Add me to your group and use /setgroup to get started."
        ),
        "help_title":       "📚 *Command Help Center*",
        "ping_reply":       "🏓 Pong! Latency: `{latency}ms`",
        "id_reply":         "🆔 *Your ID:* `{user_id}`\n🏘️ *Chat ID:* `{chat_id}`",
        "ban_success":      "✅ {user} has been *banned*.",
        "unban_success":    "✅ {user} has been *unbanned*.",
        "kick_success":     "✅ {user} has been *kicked*.",
        "mute_success":     "🔇 {user} has been *muted* for `{duration}`.",
        "unmute_success":   "🔊 {user} has been *unmuted*.",
        "warn_success":     "⚠️ {user} has been *warned* (`{warns}/{limit}`).",
        "warn_banned":      "🚨 {user} reached warn limit and has been *banned*!",
        "warn_muted":       "🚨 {user} reached warn limit and has been *muted*!",
        "clearwarn_success":"✅ Warnings cleared for {user}.",
        "purge_success":    "🗑️ Deleted `{count}` messages.",
        "group_setup_ok":   "✅ Group *{title}* has been configured!\nUse /help to see all commands.",
        "no_permission":    "🚫 You don't have permission for this action.",
        "premium_active":   "💎 *Premium Active!*\nExpires: `{expiry}`",
        "premium_expired":  "⚠️ Your premium has expired. Use /redeem to reactivate.",
        "code_redeemed":    "🎉 *Code redeemed!* Premium activated for `{days}` days.\nExpires: `{expiry}`",
        "code_invalid":     "❌ Invalid or already used code.",
        "stats_title":      "📊 *Bot Statistics*",
        "not_in_group":     "ℹ️ This command works in groups only.",
        "captcha_prompt":   "🔐 *Verification Required*\n\nSolve this to join: `{question}`\n\nYou have `{timeout}s` to answer.",
        "captcha_pass":     "✅ Verification passed! Welcome to the group.",
        "captcha_fail":     "❌ Wrong answer. You have been removed.",
        "captcha_timeout":  "⏰ Verification timed out. You have been removed.",
        "anti_link":        "🔗 Links are not allowed here.",
        "anti_spam":        "🛑 Stop spamming!",
        "backup_done":      "✅ Backup created successfully.",
        "export_done":      "📦 Group data exported.",
        "broadcast_sent":   "📢 Broadcast sent to `{count}` groups.",
        "set_language":     "🌐 Language set to *{lang}*.",
        "rules_set":        "📋 Rules updated.",
        "keyword_added":    "✅ Keyword `{trigger}` added.",
        "keyword_removed":  "✅ Keyword `{trigger}` removed.",
    },

    # ── SPANISH ──────────────────────────────────────────────────────────────
    "es": {
        "welcome_pm":       "⚡ *¡Bienvenido al Bot de Gestión de Grupos!*\n\nSoy un poderoso bot con moderación avanzada.",
        "ping_reply":       "🏓 ¡Pong! Latencia: `{latency}ms`",
        "id_reply":         "🆔 *Tu ID:* `{user_id}`\n🏘️ *ID del Chat:* `{chat_id}`",
        "ban_success":      "✅ {user} ha sido *baneado*.",
        "unban_success":    "✅ {user} ha sido *desbaneado*.",
        "kick_success":     "✅ {user} fue *expulsado*.",
        "mute_success":     "🔇 {user} fue *silenciado* por `{duration}`.",
        "unmute_success":   "🔊 {user} fue *habilitado*.",
        "no_permission":    "🚫 No tienes permiso para esta acción.",
        "code_redeemed":    "🎉 *¡Código canjeado!* Premium activado por `{days}` días.",
        "code_invalid":     "❌ Código inválido o ya utilizado.",
        "not_in_group":     "ℹ️ Este comando solo funciona en grupos.",
    },

    # ── FRENCH ───────────────────────────────────────────────────────────────
    "fr": {
        "welcome_pm":       "⚡ *Bienvenue sur le Bot de Gestion de Groupe!*\n\nJe suis un bot puissant avec modération avancée.",
        "ping_reply":       "🏓 Pong! Latence: `{latency}ms`",
        "id_reply":         "🆔 *Votre ID:* `{user_id}`\n🏘️ *ID du Chat:* `{chat_id}`",
        "ban_success":      "✅ {user} a été *banni*.",
        "no_permission":    "🚫 Vous n'avez pas la permission.",
        "code_redeemed":    "🎉 *Code échangé!* Premium activé pour `{days}` jours.",
        "code_invalid":     "❌ Code invalide ou déjà utilisé.",
        "not_in_group":     "ℹ️ Cette commande fonctionne uniquement dans les groupes.",
    },

    # ── GERMAN ───────────────────────────────────────────────────────────────
    "de": {
        "welcome_pm":       "⚡ *Willkommen beim Gruppenmanagement-Bot!*\n\nIch bin ein leistungsstarker Bot.",
        "ping_reply":       "🏓 Pong! Latenz: `{latency}ms`",
        "ban_success":      "✅ {user} wurde *gebannt*.",
        "no_permission":    "🚫 Du hast keine Berechtigung.",
        "code_invalid":     "❌ Ungültiger oder bereits verwendeter Code.",
        "not_in_group":     "ℹ️ Dieser Befehl funktioniert nur in Gruppen.",
    },

    # ── ARABIC ───────────────────────────────────────────────────────────────
    "ar": {
        "welcome_pm":       "⚡ *مرحباً بك في بوت إدارة المجموعات!*\n\nأنا بوت قوي بمعالجة متقدمة.",
        "ping_reply":       "🏓 Pong! زمن الاستجابة: `{latency}ms`",
        "ban_success":      "✅ {user} تم *حظره*.",
        "no_permission":    "🚫 ليس لديك صلاحية لهذا الإجراء.",
        "code_invalid":     "❌ رمز غير صالح أو مستخدم بالفعل.",
        "not_in_group":     "ℹ️ هذا الأمر يعمل في المجموعات فقط.",
    },
}


def get_string(key: str, lang: str = "en", **kwargs) -> str:
    """
    Retrieve localized string by key, falling back to English.
    Format placeholders using kwargs.
    """
    lang_strings = STRINGS.get(lang, STRINGS["en"])
    text = lang_strings.get(key) or STRINGS["en"].get(key, f"[{key}]")
    if kwargs:
        try:
            return text.format(**kwargs)
        except KeyError:
            return text
    return text
