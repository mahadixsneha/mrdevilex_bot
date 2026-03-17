"""
╔══════════════════════════════════════════╗
║  Dashboard API — Flask (no pydantic)     ║
╚══════════════════════════════════════════╝
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
from flask import Flask, request, jsonify, render_template_string
import jwt
import bcrypt
from loguru import logger

from config import config
from database.db import db

# ─── Flask App ────────────────────────────────────────────────────────────────
app = Flask(__name__)

ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 24


# ─── Auth helpers ─────────────────────────────────────────────────────────────

def create_token(username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS)
    return jwt.encode({"sub": username, "exp": expire}, config.SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, config.SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except Exception:
        return None


def get_auth_user():
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    return verify_token(auth[7:])


def require_auth(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not get_auth_user():
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template_string(DASHBOARD_HTML)


@app.route("/api/auth/token", methods=["POST"])
def login():
    data = request.get_json() or {}
    username = data.get("username") or request.form.get("username", "")
    password = data.get("password") or request.form.get("password", "")

    if username != config.API_ADMIN_USERNAME or password != config.API_ADMIN_PASSWORD:
        return jsonify({"error": "Invalid credentials"}), 401

    token = create_token(username)
    return jsonify({"access_token": token, "token_type": "bearer"})


@app.route("/api/stats")
@require_auth
def get_stats():
    import asyncio
    loop = asyncio.new_event_loop()
    try:
        stats = loop.run_until_complete(db.get_stats())
        return jsonify(stats)
    finally:
        loop.close()


@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "bot": "MrDevilEx", "version": "2.0"})


# ─── Dashboard HTML ───────────────────────────────────────────────────────────

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>⚡ MrDevilEx Bot Dashboard</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { background: #0a0a0a; color: #e0e0e0; font-family: 'Courier New', monospace; }
  .header { background: linear-gradient(135deg, #1a1a2e, #16213e); padding: 20px; text-align: center; border-bottom: 2px solid #ff0040; }
  .header h1 { color: #ff0040; font-size: 28px; letter-spacing: 4px; }
  .header p { color: #888; margin-top: 5px; }
  .container { max-width: 1000px; margin: 30px auto; padding: 0 20px; }
  .card { background: #111; border: 1px solid #222; border-radius: 8px; padding: 20px; margin-bottom: 20px; }
  .card h2 { color: #ff0040; margin-bottom: 15px; font-size: 16px; letter-spacing: 2px; }
  .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; }
  .stat { background: #1a1a1a; border: 1px solid #333; border-radius: 6px; padding: 15px; text-align: center; }
  .stat .num { font-size: 32px; color: #ff0040; font-weight: bold; }
  .stat .label { color: #888; font-size: 12px; margin-top: 5px; }
  .login-form { max-width: 400px; margin: 50px auto; }
  input { width: 100%; background: #1a1a1a; border: 1px solid #333; color: #e0e0e0; padding: 12px; border-radius: 6px; margin-bottom: 15px; font-family: monospace; font-size: 14px; }
  button { width: 100%; background: #ff0040; border: none; color: white; padding: 12px; border-radius: 6px; cursor: pointer; font-size: 16px; letter-spacing: 2px; }
  button:hover { background: #cc0033; }
  .online { color: #00ff88; }
  .hidden { display: none; }
</style>
</head>
<body>
<div class="header">
  <h1>⚡ MRDEVILEX BOT</h1>
  <p>Telegram Group Management Dashboard</p>
</div>
<div class="container">

  <!-- Login -->
  <div id="loginSection" class="card login-form">
    <h2>🔐 LOGIN</h2>
    <input type="text" id="username" placeholder="Username" value="admin">
    <input type="password" id="password" placeholder="Password">
    <button onclick="login()">LOGIN</button>
    <p id="loginError" style="color:#ff0040;margin-top:10px;"></p>
  </div>

  <!-- Dashboard -->
  <div id="dashSection" class="hidden">
    <div class="card">
      <h2>📊 LIVE STATS</h2>
      <div class="stats" id="statsGrid">
        <div class="stat"><div class="num" id="totalUsers">-</div><div class="label">Total Users</div></div>
        <div class="stat"><div class="num" id="totalGroups">-</div><div class="label">Groups</div></div>
        <div class="stat"><div class="num" id="premiumUsers">-</div><div class="label">Premium</div></div>
        <div class="stat"><div class="num online">●</div><div class="label">Bot Status</div></div>
      </div>
    </div>
    <div class="card">
      <h2>ℹ️ BOT INFO</h2>
      <p>🌐 URL: <a href="https://mrdevilex-bot.onrender.com" style="color:#ff0040">mrdevilex-bot.onrender.com</a></p>
      <p style="margin-top:10px">⚡ Mode: Webhook | v2.0 | MrDevilEx</p>
    </div>
  </div>

</div>
<script>
const TOKEN_KEY = 'mrdevilex_token';
let token = localStorage.getItem(TOKEN_KEY);
if (token) showDash();

async function login() {
  const u = document.getElementById('username').value;
  const p = document.getElementById('password').value;
  const r = await fetch('/api/auth/token', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({username: u, password: p})
  });
  const d = await r.json();
  if (d.access_token) {
    token = d.access_token;
    localStorage.setItem(TOKEN_KEY, token);
    showDash();
  } else {
    document.getElementById('loginError').textContent = '❌ Wrong credentials!';
  }
}

function showDash() {
  document.getElementById('loginSection').classList.add('hidden');
  document.getElementById('dashSection').classList.remove('hidden');
  loadStats();
}

async function loadStats() {
  try {
    const r = await fetch('/api/stats', {headers: {'Authorization': 'Bearer ' + token}});
    if (r.status === 401) { localStorage.removeItem(TOKEN_KEY); location.reload(); return; }
    const d = await r.json();
    document.getElementById('totalUsers').textContent = d.total_users || 0;
    document.getElementById('totalGroups').textContent = d.total_groups || 0;
    document.getElementById('premiumUsers').textContent = d.premium_users || 0;
  } catch(e) {}
}

setInterval(loadStats, 30000);
</script>
</body>
</html>
"""
