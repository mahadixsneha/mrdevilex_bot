# ⚡ Render Deploy Guide — MrDevilEx Bot

## 🚀 Step-by-Step

### ১. MongoDB Atlas সেটআপ
1. https://mongodb.com/atlas → Free cluster বানান
2. **Database Access** → User তৈরি করুন (username + password)
3. **Network Access** → `0.0.0.0/0` add করুন (Render-এর জন্য)
4. **Connect** → "Connect your application" → URI কপি করুন

---

### ২. GitHub-এ Code Push করুন
```bash
# github_uploader.py দিয়ে অথবা manually
git init && git add . && git commit -m "🚀 Deploy"
git remote add origin https://github.com/USERNAME/REPO.git
git push -u origin main
```

---

### ৩. Render-এ Deploy করুন

1. **https://render.com** → Sign up (GitHub দিয়ে)
2. **New** → **Web Service**
3. GitHub repo connect করুন
4. Settings:
   - **Name**: `mrdevilex-bot`
   - **Runtime**: `Python`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python main.py`
   - **Plan**: Free

---

### ৪. Environment Variables সেট করুন

Render Dashboard → আপনার Service → **Environment** tab:

| Variable | Value |
|----------|-------|
| `BOT_TOKEN` | BotFather থেকে নেওয়া token |
| `OWNER_ID` | আপনার Telegram user ID |
| `MONGO_URI` | MongoDB Atlas URI |
| `MONGO_DB_NAME` | `telegram_bot` |
| `WEBHOOK_URL` | `https://your-app.onrender.com` *(Deploy হওয়ার পর পাবেন)* |
| `SECRET_KEY` | যেকোনো random string |
| `API_ADMIN_PASSWORD` | Dashboard password |
| `RENDER` | `true` |

> ⚠️ **WEBHOOK_URL** প্রথম deploy-এর পর Render আপনাকে URL দেবে — সেটা দিয়ে আবার set করুন।

---

### ৫. Deploy করুন
- **Manual Deploy** → Deploy Latest Commit
- Log দেখুন — `✅ Webhook set` দেখলেই বুঝবেন সফল হয়েছে

---

## 📊 Dashboard Access
```
https://your-app.onrender.com/dashboard
```

## 🔗 Endpoints
| URL | কী করে |
|-----|--------|
| `/` | Health check |
| `/health` | Status check |
| `/webhook/{token}` | Telegram updates (auto) |
| `/dashboard` | Web dashboard |
| `/dashboard/api/docs` | API docs |

---

## ⚠️ Free Plan সীমাবদ্ধতা
- **750 hours/month** — একটা bot সারামাস চালাতে পারবেন
- **Sleep after 15 min idle** — কিন্তু webhook আসলে জেগে উঠবে
- **No persistent disk** — backup files সেভ হবে না (MongoDB তে সব থাকে)

## 💡 Pro Tip
Free plan-এ bot slow হতে পারে প্রথম request-এ (cold start ~30sec)।
Paid plan ($7/month) নিলে always-on থাকবে।
