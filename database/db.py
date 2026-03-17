"""
╔══════════════════════════════════════════╗
║  Database Layer — Async MongoDB (Motor)  ║
╚══════════════════════════════════════════╝
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import motor.motor_asyncio
from loguru import logger
from pymongo import ASCENDING, DESCENDING, IndexModel

from config import Collections, config, DEFAULT_GROUP_SETTINGS, Roles


# ─── DATABASE CLIENT ─────────────────────────────────────────────────────────
class Database:
    """Async MongoDB database manager using Motor driver."""

    def __init__(self):
        self.client: Optional[motor.motor_asyncio.AsyncIOMotorClient] = None
        self.db: Optional[motor.motor_asyncio.AsyncIOMotorDatabase] = None
        self._connected = False

    async def connect(self):
        """Establish MongoDB Atlas connection and create indexes."""
        try:
            self.client = motor.motor_asyncio.AsyncIOMotorClient(
                config.MONGO_URI,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=10000,
            )
            self.db = self.client[config.MONGO_DB_NAME]

            # Verify connection
            await self.client.admin.command("ping")
            self._connected = True
            logger.success("✅ MongoDB Atlas connected successfully")

            # Setup indexes
            await self._create_indexes()
        except Exception as e:
            logger.error(f"❌ MongoDB connection failed: {e}")
            raise

    async def disconnect(self):
        """Close MongoDB connection."""
        if self.client:
            self.client.close()
            self._connected = False
            logger.info("🔌 MongoDB connection closed")

    async def _create_indexes(self):
        """Create database indexes for performance."""
        try:
            # Users indexes
            await self.db[Collections.USERS].create_indexes([
                IndexModel([("user_id", ASCENDING)], unique=True),
                IndexModel([("username", ASCENDING)]),
                IndexModel([("role", ASCENDING)]),
                IndexModel([("premium_expiry", ASCENDING)]),
            ])

            # Groups indexes
            await self.db[Collections.GROUPS].create_indexes([
                IndexModel([("group_id", ASCENDING)], unique=True),
                IndexModel([("owner_id", ASCENDING)]),
            ])

            # Logs indexes (TTL: auto-delete after 90 days)
            await self.db[Collections.LOGS].create_indexes([
                IndexModel([("timestamp", DESCENDING)]),
                IndexModel([("user_id", ASCENDING)]),
                IndexModel([("group_id", ASCENDING)]),
                IndexModel([("timestamp", ASCENDING)], expireAfterSeconds=7776000),
            ])

            # Premium codes indexes
            await self.db[Collections.PREMIUM_CODES].create_indexes([
                IndexModel([("code", ASCENDING)], unique=True),
            ])

            # Keywords indexes
            await self.db[Collections.KEYWORDS].create_indexes([
                IndexModel([("group_id", ASCENDING), ("trigger", ASCENDING)], unique=True),
            ])

            # Captcha pending indexes (TTL: auto-delete after 10 minutes)
            await self.db[Collections.CAPTCHA].create_indexes([
                IndexModel([("created_at", ASCENDING)], expireAfterSeconds=600),
                IndexModel([("user_id", ASCENDING), ("group_id", ASCENDING)]),
            ])

            # Raid state TTL
            await self.db[Collections.RAID_STATE].create_indexes([
                IndexModel([("created_at", ASCENDING)], expireAfterSeconds=3600),
                IndexModel([("group_id", ASCENDING)], unique=True),
            ])

            logger.success("✅ Database indexes created")
        except Exception as e:
            logger.warning(f"⚠️ Index creation warning: {e}")

    # ─── PROPERTY SHORTCUTS ───────────────────────────────────────────────────
    @property
    def users(self):
        return self.db[Collections.USERS]

    @property
    def groups(self):
        return self.db[Collections.GROUPS]

    @property
    def logs(self):
        return self.db[Collections.LOGS]

    @property
    def premium_codes(self):
        return self.db[Collections.PREMIUM_CODES]

    @property
    def keywords(self):
        return self.db[Collections.KEYWORDS]

    @property
    def captcha(self):
        return self.db[Collections.CAPTCHA]

    @property
    def banned_words(self):
        return self.db[Collections.BANNED_WORDS]

    @property
    def announcements(self):
        return self.db[Collections.ANNOUNCEMENTS]

    @property
    def raid_state(self):
        return self.db[Collections.RAID_STATE]

    # ═══════════════════════════════════════════════════════════════════════════
    #  USER OPERATIONS
    # ═══════════════════════════════════════════════════════════════════════════

    async def get_user(self, user_id: int) -> Optional[Dict]:
        """Fetch user document by Telegram user_id."""
        return await self.users.find_one({"user_id": user_id})

    async def upsert_user(self, user_id: int, data: Dict) -> None:
        """Insert or update user document."""
        await self.users.update_one(
            {"user_id": user_id},
            {"$set": data, "$setOnInsert": {"joined_at": datetime.now(timezone.utc), "warns": 0, "role": Roles.MEMBER}},
            upsert=True,
        )

    async def get_or_create_user(self, user_id: int, username: str = "", full_name: str = "") -> Dict:
        """Fetch user or create a new record."""
        user = await self.get_user(user_id)
        if not user:
            doc = {
                "user_id":        user_id,
                "username":       username,
                "full_name":      full_name,
                "role":           Roles.MEMBER,
                "warns":          0,
                "premium_expiry": None,
                "is_banned":      False,
                "is_muted":       False,
                "mute_until":     None,
                "language":       config.DEFAULT_LANGUAGE,
                "joined_at":      datetime.now(timezone.utc),
                "last_seen":      datetime.now(timezone.utc),
                "message_count":  0,
            }
            await self.users.insert_one(doc)
            return doc
        return user

    async def add_warn(self, user_id: int, group_id: int, reason: str = "") -> int:
        """Add warning to a user. Returns current warn count."""
        result = await self.users.find_one_and_update(
            {"user_id": user_id},
            {"$inc": {"warns": 1}},
            return_document=True,
        )
        warns = result["warns"] if result else 1
        await self.log_action("warn", user_id, group_id, details={"reason": reason, "warns": warns})
        return warns

    async def clear_warns(self, user_id: int, group_id: int) -> None:
        """Reset user warn count."""
        await self.users.update_one({"user_id": user_id}, {"$set": {"warns": 0}})
        await self.log_action("clearwarn", user_id, group_id)

    async def set_user_role(self, user_id: int, role: str, group_id: int) -> None:
        """Update user role."""
        await self.users.update_one({"user_id": user_id}, {"$set": {"role": role}})
        await self.log_action("role_change", user_id, group_id, details={"new_role": role})

    async def ban_user(self, user_id: int, group_id: int, reason: str = "", banned_by: int = 0) -> None:
        await self.users.update_one({"user_id": user_id}, {"$set": {"is_banned": True}})
        await self.log_action("ban", user_id, group_id, actor_id=banned_by, details={"reason": reason})

    async def unban_user(self, user_id: int, group_id: int, unbanned_by: int = 0) -> None:
        await self.users.update_one({"user_id": user_id}, {"$set": {"is_banned": False}})
        await self.log_action("unban", user_id, group_id, actor_id=unbanned_by)

    async def mute_user(self, user_id: int, group_id: int, until: Optional[datetime] = None, muted_by: int = 0) -> None:
        await self.users.update_one(
            {"user_id": user_id},
            {"$set": {"is_muted": True, "mute_until": until}},
        )
        await self.log_action("mute", user_id, group_id, actor_id=muted_by, details={"until": str(until)})

    async def unmute_user(self, user_id: int, group_id: int, unmuted_by: int = 0) -> None:
        await self.users.update_one(
            {"user_id": user_id},
            {"$set": {"is_muted": False, "mute_until": None}},
        )
        await self.log_action("unmute", user_id, group_id, actor_id=unmuted_by)

    async def set_premium(self, user_id: int, days: int = None) -> datetime:
        """Grant premium to user. Returns expiry datetime."""
        days = days or config.PREMIUM_DURATION_DAYS
        expiry = datetime.now(timezone.utc) + timedelta(days=days)
        await self.users.update_one(
            {"user_id": user_id},
            {"$set": {"premium_expiry": expiry, "role": Roles.VIP}},
        )
        return expiry

    async def is_premium(self, user_id: int) -> bool:
        """Check if user has active premium."""
        user = await self.get_user(user_id)
        if not user or not user.get("premium_expiry"):
            return False
        return user["premium_expiry"] > datetime.now(timezone.utc)

    async def get_all_users(self) -> List[Dict]:
        return await self.users.find({}).to_list(length=None)

    async def count_users(self) -> int:
        return await self.users.count_documents({})

    async def count_premium_users(self) -> int:
        now = datetime.now(timezone.utc)
        return await self.users.count_documents({"premium_expiry": {"$gt": now}})

    # ═══════════════════════════════════════════════════════════════════════════
    #  GROUP OPERATIONS
    # ═══════════════════════════════════════════════════════════════════════════

    async def get_group(self, group_id: int) -> Optional[Dict]:
        return await self.groups.find_one({"group_id": group_id})

    async def setup_group(self, group_id: int, title: str, owner_id: int) -> Dict:
        """Initialize or update a group configuration."""
        doc = {
            "group_id":   group_id,
            "title":      title,
            "owner_id":   owner_id,
            "admins":     [owner_id],
            "moderators": [],
            "settings":   DEFAULT_GROUP_SETTINGS.copy(),
            "rules":      "No rules set yet.",
            "created_at": datetime.now(timezone.utc),
            "member_count": 0,
        }
        await self.groups.update_one(
            {"group_id": group_id},
            {"$setOnInsert": doc, "$set": {"title": title, "owner_id": owner_id}},
            upsert=True,
        )
        return await self.get_group(group_id)

    async def update_group_setting(self, group_id: int, key: str, value: Any) -> None:
        await self.groups.update_one(
            {"group_id": group_id},
            {"$set": {f"settings.{key}": value}},
        )

    async def get_group_setting(self, group_id: int, key: str, default: Any = None) -> Any:
        group = await self.get_group(group_id)
        if not group:
            return default
        return group.get("settings", {}).get(key, DEFAULT_GROUP_SETTINGS.get(key, default))

    async def add_group_admin(self, group_id: int, user_id: int) -> None:
        await self.groups.update_one({"group_id": group_id}, {"$addToSet": {"admins": user_id}})

    async def remove_group_admin(self, group_id: int, user_id: int) -> None:
        await self.groups.update_one({"group_id": group_id}, {"$pull": {"admins": user_id}})

    async def add_group_moderator(self, group_id: int, user_id: int) -> None:
        await self.groups.update_one({"group_id": group_id}, {"$addToSet": {"moderators": user_id}})

    async def remove_group_moderator(self, group_id: int, user_id: int) -> None:
        await self.groups.update_one({"group_id": group_id}, {"$pull": {"moderators": user_id}})

    async def count_groups(self) -> int:
        return await self.groups.count_documents({})

    async def get_all_group_ids(self) -> List[int]:
        groups = await self.groups.find({}, {"group_id": 1}).to_list(length=None)
        return [g["group_id"] for g in groups]

    # ═══════════════════════════════════════════════════════════════════════════
    #  PREMIUM CODE OPERATIONS
    # ═══════════════════════════════════════════════════════════════════════════

    async def create_premium_code(self, code: str, days: int, created_by: int) -> Dict:
        doc = {
            "code":       code,
            "days":       days,
            "used_by":    None,
            "used_at":    None,
            "is_used":    False,
            "created_by": created_by,
            "created_at": datetime.now(timezone.utc),
        }
        await self.premium_codes.insert_one(doc)
        return doc

    async def redeem_code(self, code: str, user_id: int) -> Optional[Dict]:
        """Attempt to redeem a premium code. Returns code doc if valid."""
        code_doc = await self.premium_codes.find_one({"code": code, "is_used": False})
        if not code_doc:
            return None

        # Mark as used
        await self.premium_codes.update_one(
            {"code": code},
            {"$set": {"is_used": True, "used_by": user_id, "used_at": datetime.now(timezone.utc)}},
        )

        # Grant premium
        await self.set_premium(user_id, code_doc["days"])
        return code_doc

    async def get_active_codes(self) -> List[Dict]:
        return await self.premium_codes.find({"is_used": False}).to_list(length=100)

    # ═══════════════════════════════════════════════════════════════════════════
    #  LOGGING OPERATIONS
    # ═══════════════════════════════════════════════════════════════════════════

    async def log_action(
        self,
        action: str,
        user_id: int,
        group_id: int,
        actor_id: int = 0,
        details: Dict = None,
    ) -> None:
        """Write action to logs collection."""
        doc = {
            "action":    action,
            "user_id":   user_id,
            "group_id":  group_id,
            "actor_id":  actor_id,
            "details":   details or {},
            "timestamp": datetime.now(timezone.utc),
        }
        await self.logs.insert_one(doc)

    async def get_logs(self, group_id: int, limit: int = 50) -> List[Dict]:
        return await self.logs.find(
            {"group_id": group_id},
            sort=[("timestamp", DESCENDING)],
        ).limit(limit).to_list(length=limit)

    async def get_user_logs(self, user_id: int, limit: int = 20) -> List[Dict]:
        return await self.logs.find(
            {"user_id": user_id},
            sort=[("timestamp", DESCENDING)],
        ).limit(limit).to_list(length=limit)

    # ═══════════════════════════════════════════════════════════════════════════
    #  KEYWORD OPERATIONS
    # ═══════════════════════════════════════════════════════════════════════════

    async def add_keyword(self, group_id: int, trigger: str, response: str) -> None:
        await self.keywords.update_one(
            {"group_id": group_id, "trigger": trigger.lower()},
            {"$set": {"response": response, "updated_at": datetime.now(timezone.utc)}},
            upsert=True,
        )

    async def remove_keyword(self, group_id: int, trigger: str) -> bool:
        result = await self.keywords.delete_one({"group_id": group_id, "trigger": trigger.lower()})
        return result.deleted_count > 0

    async def get_keywords(self, group_id: int) -> List[Dict]:
        return await self.keywords.find({"group_id": group_id}).to_list(length=200)

    async def find_keyword_response(self, group_id: int, text: str) -> Optional[str]:
        text_lower = text.lower()
        keywords = await self.get_keywords(group_id)
        for kw in keywords:
            if kw["trigger"] in text_lower:
                return kw["response"]
        return None

    # ═══════════════════════════════════════════════════════════════════════════
    #  BANNED WORDS
    # ═══════════════════════════════════════════════════════════════════════════

    async def add_banned_word(self, group_id: int, word: str) -> None:
        await self.banned_words.update_one(
            {"group_id": group_id},
            {"$addToSet": {"words": word.lower()}},
            upsert=True,
        )

    async def remove_banned_word(self, group_id: int, word: str) -> None:
        await self.banned_words.update_one(
            {"group_id": group_id},
            {"$pull": {"words": word.lower()}},
        )

    async def get_banned_words(self, group_id: int) -> List[str]:
        doc = await self.banned_words.find_one({"group_id": group_id})
        return doc.get("words", []) if doc else []

    # ═══════════════════════════════════════════════════════════════════════════
    #  ANTI-RAID STATE
    # ═══════════════════════════════════════════════════════════════════════════

    async def is_raid_active(self, group_id: int) -> bool:
        doc = await self.raid_state.find_one({"group_id": group_id})
        if not doc:
            return False
        expiry = doc.get("expires_at")
        return expiry and expiry > datetime.now(timezone.utc)

    async def set_raid_mode(self, group_id: int, duration_seconds: int) -> None:
        expiry = datetime.now(timezone.utc) + timedelta(seconds=duration_seconds)
        await self.raid_state.update_one(
            {"group_id": group_id},
            {"$set": {"expires_at": expiry, "created_at": datetime.now(timezone.utc)}},
            upsert=True,
        )

    async def clear_raid_mode(self, group_id: int) -> None:
        await self.raid_state.delete_one({"group_id": group_id})

    # ═══════════════════════════════════════════════════════════════════════════
    #  CAPTCHA OPERATIONS
    # ═══════════════════════════════════════════════════════════════════════════

    async def set_captcha_pending(self, user_id: int, group_id: int, answer: str) -> None:
        doc = {
            "user_id":    user_id,
            "group_id":   group_id,
            "answer":     answer,
            "created_at": datetime.now(timezone.utc),
        }
        await self.captcha.update_one(
            {"user_id": user_id, "group_id": group_id},
            {"$set": doc},
            upsert=True,
        )

    async def verify_captcha(self, user_id: int, group_id: int, answer: str) -> bool:
        doc = await self.captcha.find_one({"user_id": user_id, "group_id": group_id})
        if not doc:
            return False
        correct = doc["answer"].strip().lower() == answer.strip().lower()
        if correct:
            await self.captcha.delete_one({"user_id": user_id, "group_id": group_id})
        return correct

    async def remove_captcha_pending(self, user_id: int, group_id: int) -> None:
        await self.captcha.delete_one({"user_id": user_id, "group_id": group_id})

    # ═══════════════════════════════════════════════════════════════════════════
    #  ANNOUNCEMENTS
    # ═══════════════════════════════════════════════════════════════════════════

    async def create_announcement(self, group_id: int, message: str, schedule: str, created_by: int) -> str:
        """Create a scheduled announcement. schedule: 'daily' | 'weekly'"""
        doc = {
            "group_id":   group_id,
            "message":    message,
            "schedule":   schedule,
            "created_by": created_by,
            "is_active":  True,
            "created_at": datetime.now(timezone.utc),
            "last_sent":  None,
        }
        result = await self.announcements.insert_one(doc)
        return str(result.inserted_id)

    async def get_active_announcements(self) -> List[Dict]:
        return await self.announcements.find({"is_active": True}).to_list(length=None)

    async def mark_announcement_sent(self, ann_id: str) -> None:
        from bson import ObjectId
        await self.announcements.update_one(
            {"_id": ObjectId(ann_id)},
            {"$set": {"last_sent": datetime.now(timezone.utc)}},
        )

    # ═══════════════════════════════════════════════════════════════════════════
    #  STATISTICS
    # ═══════════════════════════════════════════════════════════════════════════

    async def get_stats(self) -> Dict:
        """Get global bot statistics."""
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        return {
            "total_users":     await self.count_users(),
            "total_groups":    await self.count_groups(),
            "premium_users":   await self.count_premium_users(),
            "actions_today":   await self.logs.count_documents({"timestamp": {"$gte": today_start}}),
            "total_bans":      await self.logs.count_documents({"action": "ban"}),
            "total_warns":     await self.logs.count_documents({"action": "warn"}),
            "total_mutes":     await self.logs.count_documents({"action": "mute"}),
        }

    async def get_group_stats(self, group_id: int) -> Dict:
        """Get per-group statistics."""
        return {
            "total_bans":  await self.logs.count_documents({"group_id": group_id, "action": "ban"}),
            "total_warns": await self.logs.count_documents({"group_id": group_id, "action": "warn"}),
            "total_mutes": await self.logs.count_documents({"group_id": group_id, "action": "mute"}),
            "total_kicks": await self.logs.count_documents({"group_id": group_id, "action": "kick"}),
        }

    # ═══════════════════════════════════════════════════════════════════════════
    #  BACKUP & EXPORT
    # ═══════════════════════════════════════════════════════════════════════════

    async def export_group_data(self, group_id: int) -> Dict:
        """Export all group data as dictionary."""
        group  = await self.get_group(group_id)
        logs   = await self.get_logs(group_id, limit=500)
        kws    = await self.get_keywords(group_id)
        bwords = await self.get_banned_words(group_id)

        return {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "group":       group,
            "logs":        logs,
            "keywords":    kws,
            "banned_words": bwords,
        }


# ─── SINGLETON ────────────────────────────────────────────────────────────────
db = Database()
