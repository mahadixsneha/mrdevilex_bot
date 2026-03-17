"""
╔══════════════════════════════════════════╗
║     ⚡ CHALLENGE BY MRDEVILEX ⚡          ║
║     Telegram Group Management Bot        ║
║     Configuration Module                 ║
╚══════════════════════════════════════════╝
"""

import os
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


# ─── PERMISSION LEVELS ────────────────────────────────────────────────────────
class Roles:
    OWNER     = "owner"
    ADMIN     = "admin"
    MODERATOR = "moderator"
    VIP       = "vip"
    MEMBER    = "member"

    HIERARCHY = {
        "owner":     5,
        "admin":     4,
        "moderator": 3,
        "vip":       2,
        "member":    1,
    }

    @staticmethod
    def has_permission(user_role: str, required_role: str) -> bool:
        return Roles.HIERARCHY.get(user_role, 0) >= Roles.HIERARCHY.get(required_role, 0)


# ─── ROLE PERMISSIONS ─────────────────────────────────────────────────────────
ROLE_PERMISSIONS = {
    Roles.OWNER: {
        "can_ban", "can_kick", "can_mute", "can_warn", "can_purge",
        "can_set_rules", "can_pin", "can_promote", "can_demote",
        "can_broadcast", "can_backup", "can_restore", "can_export",
        "can_set_welcome", "can_set_keywords", "can_manage_premium",
        "can_manage_codes", "can_view_logs", "can_set_antispam",
        "can_set_antilink", "can_set_antiraid",
    },
    Roles.ADMIN: {
        "can_ban", "can_kick", "can_mute", "can_warn", "can_purge",
        "can_set_rules", "can_pin", "can_promote",
        "can_set_welcome", "can_set_keywords",
        "can_view_logs", "can_set_antispam", "can_set_antilink",
    },
    Roles.MODERATOR: {
        "can_kick", "can_mute", "can_warn", "can_purge",
        "can_view_logs",
    },
    Roles.VIP: set(),
    Roles.MEMBER: set(),
}


# ─── BOT CONFIGURATION ────────────────────────────────────────────────────────
@dataclass
class BotConfig:
    # Core
    TOKEN: str                 = field(default_factory=lambda: os.getenv("BOT_TOKEN", ""))
    USERNAME: str              = field(default_factory=lambda: os.getenv("BOT_USERNAME", ""))
    OWNER_ID: int              = field(default_factory=lambda: int(os.getenv("OWNER_ID", "0")))

    # MongoDB
    MONGO_URI: str             = field(default_factory=lambda: os.getenv("MONGO_URI", ""))
    MONGO_DB_NAME: str         = field(default_factory=lambda: os.getenv("MONGO_DB_NAME", "telegram_bot"))

    # Logging
    LOG_CHANNEL_ID: Optional[int] = field(default_factory=lambda: int(os.getenv("LOG_CHANNEL_ID", "0")) or None)
    SUPPORT_GROUP_ID: Optional[int] = field(default_factory=lambda: int(os.getenv("SUPPORT_GROUP_ID", "0")) or None)

    # Dashboard API
    API_HOST: str              = field(default_factory=lambda: os.getenv("API_HOST", "0.0.0.0"))
    API_PORT: int              = field(default_factory=lambda: int(os.getenv("API_PORT", "10000")))
    WEBHOOK_URL: str           = field(default_factory=lambda: os.getenv("WEBHOOK_URL", ""))
    SECRET_KEY: str            = field(default_factory=lambda: os.getenv("SECRET_KEY", "changeme"))
    API_ADMIN_USERNAME: str    = field(default_factory=lambda: os.getenv("API_ADMIN_USERNAME", "admin"))
    API_ADMIN_PASSWORD: str    = field(default_factory=lambda: os.getenv("API_ADMIN_PASSWORD", "admin"))

    # AI Moderation
    ENABLE_AI_MODERATION: bool = field(default_factory=lambda: os.getenv("ENABLE_AI_MODERATION", "true").lower() == "true")
    SPAM_THRESHOLD: float      = field(default_factory=lambda: float(os.getenv("SPAM_THRESHOLD", "0.75")))

    # Premium
    PREMIUM_DURATION_DAYS: int = field(default_factory=lambda: int(os.getenv("PREMIUM_DURATION_DAYS", "30")))
    ENABLE_PREMIUM: bool       = field(default_factory=lambda: os.getenv("ENABLE_PREMIUM", "true").lower() == "true")

    # Anti-Raid
    ANTI_RAID_THRESHOLD: int   = field(default_factory=lambda: int(os.getenv("ANTI_RAID_THRESHOLD", "10")))
    ANTI_RAID_DURATION: int    = field(default_factory=lambda: int(os.getenv("ANTI_RAID_DURATION", "300")))

    # Rate Limiting
    RATE_LIMIT_MESSAGES: int   = field(default_factory=lambda: int(os.getenv("RATE_LIMIT_MESSAGES", "5")))
    RATE_LIMIT_WINDOW: int     = field(default_factory=lambda: int(os.getenv("RATE_LIMIT_WINDOW", "10")))

    # Captcha
    CAPTCHA_TIMEOUT: int       = field(default_factory=lambda: int(os.getenv("CAPTCHA_TIMEOUT", "120")))
    ENABLE_CAPTCHA: bool       = field(default_factory=lambda: os.getenv("ENABLE_CAPTCHA", "true").lower() == "true")

    # Localization
    DEFAULT_LANGUAGE: str      = field(default_factory=lambda: os.getenv("DEFAULT_LANGUAGE", "en"))

    # Backup
    BACKUP_INTERVAL_HOURS: int = field(default_factory=lambda: int(os.getenv("BACKUP_INTERVAL_HOURS", "24")))
    BACKUP_STORAGE_PATH: str   = field(default_factory=lambda: os.getenv("BACKUP_STORAGE_PATH", "./backups"))

    # Warn limits
    WARN_LIMIT: int = 3          # Auto-ban after N warnings
    MUTE_DURATION_DEFAULT: int = 3600  # 1 hour in seconds

    def validate(self):
        errors = []
        if not self.TOKEN:
            errors.append("BOT_TOKEN is required")
        if not self.OWNER_ID:
            errors.append("OWNER_ID is required")
        if not self.MONGO_URI:
            errors.append("MONGO_URI is required")
        if errors:
            raise ValueError("Config errors:\n" + "\n".join(f"  ✗ {e}" for e in errors))
        return True


# ─── SINGLETON INSTANCE ───────────────────────────────────────────────────────
config = BotConfig()


# ─── ASCII BANNER ─────────────────────────────────────────────────────────────
BANNER = r"""
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║        ⚡  C H A L L E N G E   B Y   M R D E V I L E X  ⚡    ║
║                                                               ║
║          Advanced Telegram Group Management Bot               ║
║          Built with Python • MongoDB • FastAPI                ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
"""

# ─── SUPPORTED LANGUAGES ──────────────────────────────────────────────────────
SUPPORTED_LANGUAGES = {
    "en": "🇬🇧 English",
    "es": "🇪🇸 Español",
    "fr": "🇫🇷 Français",
    "de": "🇩🇪 Deutsch",
    "ar": "🇸🇦 العربية",
}

# ─── COLLECTION NAMES ─────────────────────────────────────────────────────────
class Collections:
    USERS          = "users"
    GROUPS         = "groups"
    PREMIUM_CODES  = "premium_codes"
    LOGS           = "logs"
    KEYWORDS       = "keywords"
    CAPTCHA        = "captcha_pending"
    ANNOUNCEMENTS  = "announcements"
    BANNED_WORDS   = "banned_words"
    SUBSCRIPTIONS  = "subscriptions"
    BACKUPS        = "backups"
    RAID_STATE     = "raid_state"

# ─── DEFAULT GROUP SETTINGS ───────────────────────────────────────────────────
DEFAULT_GROUP_SETTINGS = {
    "anti_link":       True,
    "anti_spam":       True,
    "anti_raid":       True,
    "captcha":         True,
    "welcome":         True,
    "goodbye":         True,
    "auto_role":       True,
    "warn_limit":      3,
    "mute_first":      True,      # mute before ban on warn limit
    "welcome_msg":     "👋 Welcome {name} to {group}! Please read the rules.",
    "goodbye_msg":     "👋 {name} has left the group.",
    "rules":           "No rules set yet. Use /setrules to add rules.",
    "language":        "en",
    "log_actions":     True,
    "delete_commands": False,
}
