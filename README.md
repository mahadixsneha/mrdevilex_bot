# ⚡ Advanced Telegram Group Management Bot
### Challenge by MrDevilEx

```
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║        ⚡  C H A L L E N G E   B Y   M R D E V I L E X  ⚡    ║
║                                                               ║
║          Advanced Telegram Group Management Bot               ║
║          Built with Python 3 • MongoDB Atlas • FastAPI        ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
```

A production-ready, fully async Telegram group management bot with AI moderation, premium system, web dashboard, and SaaS-grade features.

---

## 📦 Project Structure

```
telegram_bot/
├── main.py                  # 🚀 Entry point
├── config.py                # ⚙️  Configuration & roles
├── requirements.txt         # 📋 Dependencies
├── .env.example             # 🔐 Environment template
│
├── database/
│   └── db.py                # 🗄️  Async MongoDB operations
│
├── handlers/
│   ├── basic.py             # /start /help /ping /id /stats
│   ├── moderation.py        # /ban /kick /mute /warn /purge
│   ├── group_setup.py       # /setgroup /settings /setwelcome
│   ├── premium.py           # /premium /redeem /gencode
│   ├── auto_events.py       # Welcome/Captcha/Anti-spam/Raid
│   └── callbacks.py         # Inline keyboard router
│
├── utils/
│   ├── helpers.py           # Shared utilities & formatters
│   └── ai_moderation.py     # Spam/toxicity detection engine
│
├── api/
│   └── dashboard.py         # FastAPI web dashboard + REST API
│
├── locales/
│   └── strings.py           # Multi-language strings
│
├── logs/                    # Auto-created log files
└── backups/                 # Auto-created backup directory
```

---

## 🚀 Quick Setup

### Prerequisites
- Python 3.11+
- MongoDB Atlas account (free tier works)
- Telegram Bot Token from [@BotFather](https://t.me/BotFather)

### Step 1 — Clone & Install

```bash
git clone <your-repo>
cd telegram_bot
python -m venv venv
source venv/bin/activate        # Linux/Mac
# venv\Scripts\activate         # Windows
pip install -r requirements.txt
```

### Step 2 — Configure Environment

```bash
cp .env.example .env
nano .env  # or use any text editor
```

Fill in the required values:

```env
BOT_TOKEN=your_bot_token_here
OWNER_ID=your_telegram_user_id
MONGO_URI=mongodb+srv://user:pass@cluster.mongodb.net/
```

### Step 3 — Get Your Telegram ID

Message [@userinfobot](https://t.me/userinfobot) on Telegram to get your user ID.

### Step 4 — Create MongoDB Atlas Database

1. Go to [mongodb.com/atlas](https://www.mongodb.com/atlas)
2. Create a free cluster
3. Create a database user
4. Whitelist your IP (or use `0.0.0.0/0` for any IP)
5. Copy the connection string to `MONGO_URI` in `.env`

### Step 5 — Run the Bot

```bash
python main.py
```

You should see:
```
  ⚡  CHALLENGE BY MRDEVILEX  ⚡
  Advanced Telegram Group Manager
  v2.0 | Python 3 | MongoDB | FastAPI

✅ MongoDB Atlas connected successfully
✅ Database indexes created
✅ Configuration validated
📅 Task scheduler started
🌐 Dashboard running at http://0.0.0.0:8080
🤖 Starting Telegram bot (polling)...
✅ Bot started successfully
```

---

## 🔧 Bot Commands Reference

### Basic
| Command | Description |
|---------|-------------|
| `/start` | Welcome message with inline menu |
| `/help` | Full command reference |
| `/ping` | Check bot latency |
| `/id` | Show your / group ID |
| `/stats` | Global bot statistics |
| `/rules` | Show group rules |
| `/myrole` | Check your role |
| `/language` | Change UI language |

### Group Setup (Admin+)
| Command | Description |
|---------|-------------|
| `/setgroup` | Initialize group (Owner only) |
| `/settings` | Toggle features panel |
| `/setrules <text>` | Set group rules |
| `/setwelcome <msg>` | Custom welcome |
| `/setgoodbye <msg>` | Custom goodbye |

### Moderation (Moderator+)
| Command | Description |
|---------|-------------|
| `/ban [@user] [reason]` | Ban a user |
| `/unban [@user]` | Unban a user |
| `/kick [@user]` | Remove without ban |
| `/mute [@user] [10m/2h/1d]` | Time-based mute |
| `/unmute [@user]` | Restore permissions |
| `/warn [@user] [reason]` | Issue warning |
| `/clearwarn [@user]` | Reset warnings |
| `/purge [count]` | Delete messages |

### Role Management (Admin+)
| Command | Description |
|---------|-------------|
| `/promote [@user]` | Grant Admin |
| `/demote [@user]` | Remove Admin |
| `/addmod [@user]` | Grant Moderator |

### Premium
| Command | Description |
|---------|-------------|
| `/premium` | Check subscription status |
| `/redeem <code>` | Activate premium code |
| `/gencode [days] [count]` | Generate codes (Owner) |
| `/listcodes` | List active codes (Owner) |

### Smart Features (Admin+)
| Command | Description |
|---------|-------------|
| `/addkeyword trigger \| response` | Add auto-reply |
| `/delkeyword <trigger>` | Remove auto-reply |
| `/keywords` | List all keywords |
| `/addbword <word>` | Add banned word |
| `/delbword <word>` | Remove banned word |
| `/bwords` | List banned words |
| `/announce [daily\|weekly] <msg>` | Schedule announcement |

### Owner Only
| Command | Description |
|---------|-------------|
| `/broadcast <msg>` | Send to all groups |
| `/backup` | Export group data |

---

## 🛡️ Auto-Moderation Features

### Anti-Link
- Automatically deletes messages containing URLs or Telegram links
- Warns user upon deletion
- VIP users are exempt

### Anti-Spam
- Sliding window rate detection per user
- Strike system (3 strikes → 10-minute mute)
- Emoji spam and repeated character detection

### Anti-Raid
- Monitors join rate per group
- Locks group when `ANTI_RAID_THRESHOLD` joins/min exceeded
- Auto-unlocks after `ANTI_RAID_DURATION` seconds

### Math Captcha
- New members are muted and presented with a math problem
- Must solve within `CAPTCHA_TIMEOUT` seconds
- Failed/timeout → automatic kick
- VIP users bypass captcha

### AI Toxicity Detection
- Uses `better-profanity` for profane content
- Caps ratio analysis for aggressive text
- Configurable confidence threshold

---

## 💎 Premium System

Generate codes as the bot owner:
```
/gencode 30 5      → 5 codes, each valid 30 days
/gencode 7         → 1 code, valid 7 days
```

Users redeem with:
```
/redeem ABC123DEFGHI
```

Premium (VIP) users get:
- ✅ Exempt from anti-link filter
- ✅ VIP role badge
- ✅ Access to future premium features

---

## 🌐 Web Dashboard

Access at: `http://your-server:8080`

Login with credentials from `.env`:
- Username: `API_ADMIN_USERNAME`
- Password: `API_ADMIN_PASSWORD`

### REST API Endpoints

```
GET  /api/health          → Health check (no auth)
POST /api/auth/token      → Login → JWT token
GET  /api/stats           → Global statistics
GET  /api/users           → List users (paginated)
GET  /api/users/{id}      → Get user
GET  /api/groups          → List groups
GET  /api/groups/{id}     → Get group config
PUT  /api/groups/{id}/settings → Update setting
GET  /api/groups/{id}/logs → Group action logs
GET  /api/logs            → Global logs
POST /api/premium/codes   → Generate codes
GET  /api/premium/codes   → List active codes
GET  /api/docs            → Swagger UI
```

---

## 🗄️ Database Schema

### users
```json
{
  "user_id":        123456,
  "username":       "john_doe",
  "full_name":      "John Doe",
  "role":           "member",
  "warns":          0,
  "premium_expiry": null,
  "is_banned":      false,
  "is_muted":       false,
  "mute_until":     null,
  "language":       "en",
  "message_count":  42,
  "joined_at":      "2025-01-01T00:00:00Z",
  "last_seen":      "2025-01-10T12:30:00Z"
}
```

### groups
```json
{
  "group_id":   -1001234567890,
  "title":      "My Group",
  "owner_id":   123456,
  "admins":     [123456, 789012],
  "moderators": [345678],
  "settings": {
    "anti_link": true,
    "anti_spam": true,
    "captcha":   true,
    "welcome":   true,
    "warn_limit": 3
  },
  "rules": "Be respectful.",
  "created_at": "2025-01-01T00:00:00Z"
}
```

### logs (auto-expire after 90 days)
```json
{
  "action":    "ban",
  "user_id":   123456,
  "group_id":  -1001234567890,
  "actor_id":  789012,
  "details":   { "reason": "spam" },
  "timestamp": "2025-01-10T12:30:00Z"
}
```

---

## 🚀 VPS Deployment

### With systemd

Create `/etc/systemd/system/tgbot.service`:
```ini
[Unit]
Description=Telegram Group Manager Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/telegram_bot
EnvironmentFile=/home/ubuntu/telegram_bot/.env
ExecStart=/home/ubuntu/telegram_bot/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable tgbot
sudo systemctl start tgbot
sudo systemctl status tgbot
```

### With Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "main.py"]
```

```bash
docker build -t tgbot .
docker run -d --env-file .env --name tgbot tgbot
```

### With PM2

```bash
pip install pm2
pm2 start main.py --interpreter python3 --name tgbot
pm2 save
pm2 startup
```

---

## 🌍 Multi-Language Support

Supported languages:
- 🇬🇧 English (`en`) — full support
- 🇪🇸 Español (`es`) — partial
- 🇫🇷 Français (`fr`) — partial
- 🇩🇪 Deutsch (`de`) — partial
- 🇸🇦 Arabic (`ar`) — partial

Add translations in `locales/strings.py`.

---

## 🔐 Security Notes

1. **Never commit `.env`** — add it to `.gitignore`
2. Change `SECRET_KEY` to a random 64-char string
3. Use a strong `API_ADMIN_PASSWORD`
4. MongoDB: use IP allowlist, not `0.0.0.0/0` in production
5. Behind a firewall, restrict port `8080` to trusted IPs only
6. Rotate premium codes regularly

---

## 📝 License

MIT License — Free to use, modify, and distribute.

---

> ⚡ **Challenge by MrDevilEx** — Built with ❤️ for the Telegram developer community.
