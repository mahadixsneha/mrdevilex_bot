"""
╔══════════════════════════════════════════╗
║  AI Moderation Engine                    ║
║  Spam, Toxicity, Flood Detection         ║
╚══════════════════════════════════════════╝
"""

import re
import time
from collections import defaultdict, deque
from typing import Dict, Tuple

from better_profanity import profanity
from loguru import logger

from config import config

# Initialize profanity filter
profanity.load_censor_words()


# ─── SPAM RATE TRACKER ────────────────────────────────────────────────────────

class SpamTracker:
    """
    Tracks message rates per user to detect spam flooding.
    Uses a sliding-window algorithm.
    """

    def __init__(self):
        # {user_id: deque of timestamps}
        self._windows: Dict[int, deque] = defaultdict(lambda: deque())
        self._strike_counts: Dict[int, int] = defaultdict(int)

    def record(self, user_id: int) -> float:
        """
        Record a message and return spam probability [0.0 - 1.0].
        Probability increases with message density in the window.
        """
        now = time.time()
        window = self._windows[user_id]

        # Remove old entries outside window
        cutoff = now - config.RATE_LIMIT_WINDOW
        while window and window[0] < cutoff:
            window.popleft()

        window.append(now)
        count = len(window)
        limit = config.RATE_LIMIT_MESSAGES

        if count <= 1:
            return 0.0
        elif count >= limit * 2:
            return 1.0
        else:
            # Sigmoid-like scale
            return min((count - 1) / (limit - 1), 1.0)

    def add_strike(self, user_id: int) -> int:
        self._strike_counts[user_id] += 1
        return self._strike_counts[user_id]

    def reset(self, user_id: int) -> None:
        self._windows[user_id].clear()
        self._strike_counts[user_id] = 0

    def get_strike_count(self, user_id: int) -> int:
        return self._strike_counts[user_id]


# ─── RAID TRACKER ─────────────────────────────────────────────────────────────

class RaidTracker:
    """
    Detects join floods (raids) per group.
    """

    def __init__(self):
        self._join_windows: Dict[int, deque] = defaultdict(lambda: deque())

    def record_join(self, group_id: int) -> int:
        """Record a join event. Returns number of joins in the last 60 seconds."""
        now = time.time()
        window = self._join_windows[group_id]
        cutoff = now - 60  # 1 minute window
        while window and window[0] < cutoff:
            window.popleft()
        window.append(now)
        return len(window)

    def reset(self, group_id: int) -> None:
        self._join_windows[group_id].clear()


# ─── CONTENT ANALYZERS ────────────────────────────────────────────────────────

# Common link pattern
_LINK_PATTERN = re.compile(
    r"(https?://|www\.|t\.me/|@[a-zA-Z0-9_]{5,}|telegram\.me/)",
    re.IGNORECASE,
)

# Excessive caps detection (>70% caps in 10+ char messages)
_EXCESSIVE_CAPS_THRESHOLD = 0.7
_MIN_CAPS_CHECK_LENGTH = 10

# Repeated chars: hellooooo
_REPEATED_CHARS = re.compile(r"(.)\1{4,}")

# Emoji spam
_EMOJI_PATTERN = re.compile(
    r"[\U0001F300-\U0001F9FF\U00002600-\U000027BF]{5,}",
    re.UNICODE,
)


def contains_link(text: str) -> bool:
    """Return True if message contains a URL or Telegram link."""
    return bool(_LINK_PATTERN.search(text))


def analyze_toxicity(text: str) -> Tuple[bool, float]:
    """
    Analyze message for toxic/profane content.
    Returns (is_toxic, confidence_score).
    """
    if not text:
        return False, 0.0

    # Profanity check
    if profanity.contains_profanity(text):
        return True, 0.85

    # Excessive caps
    if len(text) >= _MIN_CAPS_CHECK_LENGTH:
        cap_ratio = sum(1 for c in text if c.isupper()) / len(text)
        if cap_ratio >= _EXCESSIVE_CAPS_THRESHOLD:
            return True, 0.6

    return False, 0.0


def analyze_spam(text: str, spam_prob: float) -> Tuple[bool, str]:
    """
    Combine rate-based and content-based spam signals.
    Returns (is_spam, reason).
    """
    if spam_prob >= config.SPAM_THRESHOLD:
        return True, "message_flood"

    if _REPEATED_CHARS.search(text):
        return True, "repeated_chars"

    if _EMOJI_PATTERN.search(text):
        return True, "emoji_spam"

    return False, ""


def estimate_spam_probability(text: str, rate_prob: float) -> float:
    """
    Combine content signals with rate probability for final score.
    """
    content_signals = 0.0

    if _REPEATED_CHARS.search(text):
        content_signals += 0.3
    if _EMOJI_PATTERN.search(text):
        content_signals += 0.2
    if contains_link(text):
        content_signals += 0.1

    # Weighted combination
    return min(rate_prob * 0.7 + content_signals * 0.3, 1.0)


# ─── GLOBAL SINGLETON INSTANCES ───────────────────────────────────────────────
spam_tracker = SpamTracker()
raid_tracker  = RaidTracker()
