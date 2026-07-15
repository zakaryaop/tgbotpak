# ============================================
# 🔐 REDZONE ULTIMATE BOT v4.0
# Complete Telegram Bot + Key System Integration
# ============================================

import os
import json
import sqlite3
import random
import string
import time
import hashlib
import threading
from datetime import datetime, timedelta

# Try to import, fallback if not available
try:
    import requests
except ImportError:
    import subprocess
    subprocess.check_call(['pip', 'install', 'requests'])
    import requests

try:
    from flask import Flask, request, jsonify
except ImportError:
    import subprocess
    subprocess.check_call(['pip', 'install', 'flask'])
    from flask import Flask, request, jsonify

# ============================================
# CONFIGURATION
# ============================================
BOT_TOKEN = os.environ.get('BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
ADMIN_IDS = [int(id) for id in os.environ.get('ADMIN_IDS', '123456789').split(',')]
PRICE = int(os.environ.get('PRICE', '5'))
KEY_EXPIRY_DAYS = int(os.environ.get('KEY_EXPIRY_DAYS', '30'))
API_PORT = int(os.environ.get('PORT', '5000'))
SECRET_KEY = os.environ.get('SECRET_KEY', 'RedZone_Ultra_Secure_2026_@ZAKPUBGSKIN')

print(f"🤖 Bot Token: {BOT_TOKEN[:10]}...")
print(f"👑 Admin IDs: {ADMIN_IDS}")
print(f"💰 Price: ${PRICE}")
print(f"⏰ Key Expiry: {KEY_EXPIRY_DAYS} days")
print(f"🔐 Secret Key: {SECRET_KEY[:10]}...")

# ============================================
# TELEGRAM API FUNCTIONS
# ============================================
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

def send_message(chat_id, text, parse_mode=None, reply_markup=None):
    """Send message using Telegram API"""
    try:
        url = f"{TELEGRAM_API}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode or "HTML"
        }
        if reply_markup:
            data["reply_markup"] = reply_markup
        response = requests.post(url, json=data, timeout=30)
        return response.json()
    except Exception as e:
        print(f"Error sending message: {e}")
        return None

def send_inline_keyboard(chat_id, text, buttons):
    """Send message with inline keyboard"""
    reply_markup = {
        "inline_keyboard": buttons
    }
    return send_message(chat_id, text, "HTML", json.dumps(reply_markup))

def get_updates(offset=None):
    """Get new messages"""
    try:
        url = f"{TELEGRAM_API}/getUpdates"
        data = {}
        if offset:
            data["offset"] = offset
        response = requests.get(url, params=data, timeout=30)
        return response.json()
    except Exception as e:
        print(f"Error getting updates: {e}")
        return {"result": []}

def set_webhook(webhook_url):
    """Set webhook for bot"""
    try:
        url = f"{TELEGRAM_API}/setWebhook"
        data = {"url": webhook_url}
        response = requests.post(url, json=data, timeout=30)
        return response.json()
    except Exception as e:
        print(f"Error setting webhook: {e}")
        return None

# ============================================
# DATABASE SETUP
# ============================================
DB_FILE = "redzone_keys.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Main keys table
    c.execute('''CREATE TABLE IF NOT EXISTS keys
                 (key TEXT PRIMARY KEY,
                  user_id INTEGER,
                  buy_date TEXT,
                  expiry_date TEXT,
                  status TEXT,
                  device_id TEXT,
                  hwid TEXT,
                  last_used TEXT,
                  notes TEXT)''')
    
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY,
                  username TEXT,
                  first_name TEXT,
                  last_name TEXT,
                  registered_date TEXT,
                  total_keys INTEGER DEFAULT 0,
                  total_spent REAL DEFAULT 0)''')
    
    # Orders table
    c.execute('''CREATE TABLE IF NOT EXISTS orders
                 (order_id TEXT PRIMARY KEY,
                  user_id INTEGER,
                  key TEXT,
                  amount REAL,
                  payment_status TEXT,
                  order_date TEXT,
                  payment_method TEXT)''')
    
    # Blacklisted HWIDs
    c.execute('''CREATE TABLE IF NOT EXISTS blacklist
                 (hwid TEXT PRIMARY KEY,
                  user_id INTEGER,
                  reason TEXT,
                  banned_date TEXT)''')
    
    # Device history
    c.execute('''CREATE TABLE IF NOT EXISTS device_history
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  key TEXT,
                  device_id TEXT,
                  hwid TEXT,
                  first_used TEXT,
                  last_used TEXT)''')
    
    conn.commit()
    conn.close()
    print("✅ Database initialized")

init_db()

# ============================================
# HASH FUNCTIONS (Same as Lua)
# ============================================
def custom_hash(data):
    """Custom hash function (matches Lua)"""
    hash_val = 5381
    for char in data:
        hash_val = (hash_val * 33 + ord(char)) % 4294967296
    return format(hash_val, '08X')

def generate_license_signature(hwid, expiry, user_id, device_id):
    """Generate license signature (matches Lua)"""
    data = f"{hwid}|{expiry}|{user_id}|{device_id}|{SECRET_KEY}"
    return custom_hash(data)

# ============================================
# KEY FUNCTIONS
# ============================================
def generate_key():
    """Generate unique key: XXXX-XXXX-XXXX-XXXX"""
    parts = []
    for i in range(4):
        part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        parts.append(part)
    return '-'.join(parts)

def generate_order_id():
    return 'ORD-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

def generate_hwid():
    """Generate HWID for license file"""
    import uuid
    return f"RZ-{str(uuid.uuid4())[:8].upper()}-{str(uuid.uuid4())[:8].upper()}"

def save_key_to_db(key, user_id, days_valid=KEY_EXPIRY_DAYS, device_id='', hwid=''):
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        buy_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        expiry_date = (datetime.now() + timedelta(days=days_valid)).strftime("%Y-%m-%d %H:%M:%S")
        
        if not hwid:
            hwid = generate_hwid()
        
        c.execute("INSERT INTO keys (key, user_id, buy_date, expiry_date, status, device_id, hwid, last_used, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                  (key, user_id, buy_date, expiry_date, 'active', device_id, hwid, '', ''))
        conn.commit()
        conn.close()
        return True, hwid
    except Exception as e:
        print(f"Error saving key: {e}")
        return False, None

def get_user_keys(user_id):
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT key, buy_date, expiry_date, status, device_id, hwid FROM keys WHERE user_id = ? ORDER BY buy_date DESC", (user_id,))
        keys = c.fetchall()
        conn.close()
        return keys
    except Exception as e:
        print(f"Error getting keys: {e}")
        return []

def get_user_by_hwid(hwid):
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT user_id FROM keys WHERE hwid = ? AND status = 'active'", (hwid,))
        result = c.fetchone()
        conn.close()
        return result[0] if result else None
    except Exception as e:
        print(f"Error getting user by hwid: {e}")
        return None

def check_key_validity(key):
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT status, expiry_date, user_id, device_id, hwid FROM keys WHERE key = ?", (key,))
        result = c.fetchone()
        conn.close()
        
        if not result:
            return False, "Key not found", None, None, None
        
        status, expiry_date, user_id, device_id, hwid = result
        
        if status != 'active':
            return False, "Key is inactive or revoked", None, None, None
        
        expiry = datetime.strptime(expiry_date, "%Y-%m-%d %H:%M:%S")
        if datetime.now() > expiry:
            return False, "Key has expired", None, None, None
        
        return True, "Key is valid", user_id, device_id, hwid
    except Exception as e:
        print(f"Error checking key: {e}")
        return False, "Error checking key", None, None, None

def activate_device(key, device_id, hwid):
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        last_used = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Update key with device info
        c.execute("UPDATE keys SET device_id = ?, hwid = ?, last_used = ? WHERE key = ?", 
                 (device_id, hwid, last_used, key))
        
        # Add to device history
        c.execute("INSERT INTO device_history (key, device_id, hwid, first_used, last_used) VALUES (?, ?, ?, ?, ?)",
                 (key, device_id, hwid, last_used, last_used))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error activating device: {e}")
        return False

def get_key_info(key):
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT user_id, buy_date, expiry_date, status, device_id, hwid FROM keys WHERE key = ?", (key,))
        result = c.fetchone()
        conn.close()
        return result
    except Exception as e:
        print(f"Error getting key info: {e}")
        return None

def save_user(user_id, username, first_name, last_name):
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        registered_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("INSERT OR IGNORE INTO users (user_id, username, first_name, last_name, registered_date) VALUES (?, ?, ?, ?, ?)",
                  (user_id, username or "", first_name or "", last_name or "", registered_date))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error saving user: {e}")
        return False

def is_hwid_blacklisted(hwid):
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT reason FROM blacklist WHERE hwid = ?", (hwid,))
        result = c.fetchone()
        conn.close()
        return result[0] if result else None
    except Exception as e:
        print(f"Error checking blacklist: {e}")
        return None

# ============================================
# LICENSE FILE GENERATION
# ============================================
def generate_license_file(key, device_id=None):
    """Generate license file content for user"""
    info = get_key_info(key)
    if not info:
        return None, None
    
    user_id, buy_date, expiry_date, status, existing_device, hwid = info
    
    if status != 'active':
        return None, None
    
    if not hwid:
        hwid = generate_hwid()
    
    # Generate signature
    signature = generate_license_signature(hwid, expiry_date, user_id, device_id or '')
    
    # Format: HWID|SIGNATURE|EXPIRY|USER_ID|DEVICE_ID
    license_content = f"{hwid}|{signature}|{expiry_date}|{user_id}|{device_id or ''}"
    
    return license_content, hwid

# ============================================
# COMMAND HANDLERS
# ============================================
def handle_start(message):
    try:
        user_id = message['from']['id']
        username = message['from'].get('username', '')
        first_name = message['from'].get('first_name', '')
        last_name = message['from'].get('last_name', '')
        
        save_user(user_id, username, first_name, last_name)
        
        text = f"""
🔐 <b>REDZONE VIP MOD SHOP</b>

Welcome {first_name}! 🎉

━━━━━━━━━━━━━━━━━━━━━━━
💎 <b>Premium VIP Mod for PUBG Mobile</b>
✅ ESP, Aimbot, Skins, Wallhack
✅ 100% Safe & Undetected
✅ Lifetime Updates

━━━━━━━━━━━━━━━━━━━━━━━
💰 <b>Price: ${PRICE}</b>
⏰ <b>Validity: {KEY_EXPIRY_DAYS} days</b>
📱 <b>Device Lock:</b> HWID based
━━━━━━━━━━━━━━━━━━━━━━━

📌 <b>Commands:</b>
/buy - Purchase a new key
/mykeys - View your keys
/check KEY - Check key validity
/status - Account status
/license KEY - Get license file
/help - Help & support

━━━━━━━━━━━━━━━━━━━━━━━
📱 <b>Contact:</b> @zakarya_op
💬 <b>WhatsApp:</b> +92 319 2530306
"""
        
        buttons = [
            [{"text": "💰 Buy Key", "callback_data": "buy"}],
            [{"text": "🔑 My Keys", "callback_data": "mykeys"}],
            [{"text": "📱 Contact Support", "url": "https://t.me/zakarya_op"}]
        ]
        
        send_inline_keyboard(user_id, text, buttons)
    except Exception as e:
        print(f"Error in start: {e}")

def handle_buy(message):
    try:
        user_id = message['from']['id']
        
        # Check if user has active keys
        keys = get_user_keys(user_id)
        active_keys = [k for k in keys if k[3] == 'active']
        
        if len(active_keys) >= 5:
            send_message(user_id, "❌ You already have 5 active keys. Please use or revoke some first.")
            return
        
        # Generate key
        key = generate_key()
        success, hwid = save_key_to_db(key, user_id)
        
        if not success:
            send_message(user_id, "❌ Error generating key. Please try again later.")
            return
        
        # Generate order
        order_id = generate_order_id()
        order_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("INSERT INTO orders (order_id, user_id, key, amount, payment_status, order_date) VALUES (?, ?, ?, ?, ?, ?)",
                  (order_id, user_id, key, PRICE, 'pending', order_date))
        conn.commit()
        conn.close()
        
        text = f"""
✅ <b>KEY GENERATED SUCCESSFULLY!</b>

━━━━━━━━━━━━━━━━━━━━━━━
🔑 <b>Your Key:</b>
<code>{key}</code>

📅 <b>Expires:</b> {(datetime.now() + timedelta(days=KEY_EXPIRY_DAYS)).strftime('%Y-%m-%d')}
🔐 <b>HWID:</b> <code>{hwid}</code>
━━━━━━━━━━━━━━━━━━━━━━━

📌 <b>How to use:</b>
1. Create file: <code>redzone_license.dat</code>
2. In PUBG Mobile, open Mod Menu
3. Use: <code>/license {key}</code>
4. Or paste license content manually

━━━━━━━━━━━━━━━━━━━━━━━
📁 <b>License File Content:</b>
<code>{hwid}|SIGNATURE|EXPIRY|{user_id}|DEVICE_ID</code>

━━━━━━━━━━━━━━━━━━━━━━━
⚠️ <b>Note:</b> Key is one-time use
Keep your key and HWID safe!

📱 @zakarya_op
💬 +92 319 2530306
"""
        
        send_message(user_id, text, "HTML")
        send_message(user_id, f"🔑 <b>Your Key:</b> <code>{key}</code>\n📱 <b>HWID:</b> <code>{hwid}</code>", "HTML")
        
    except Exception as e:
        print(f"Error in buy: {e}")
        send_message(message['from']['id'], "❌ Error generating key. Please try again later.")

def handle_mykeys(message):
    try:
        user_id = message['from']['id']
        keys = get_user_keys(user_id)
        
        if not keys:
            send_message(user_id, "❌ You don't have any keys yet!\nUse /buy to purchase one.")
            return
        
        text = "🔐 <b>Your Keys:</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n"
        for key, buy_date, expiry_date, status, device_id, hwid in keys:
            status_emoji = "✅" if status == "active" else "❌"
            device_info = f"📱 Device: {device_id[:10] if device_id else 'Not activated'}"
            text += f"{status_emoji} <code>{key}</code>\n"
            text += f"   Expires: {expiry_date}\n"
            text += f"   {device_info}\n"
            text += f"   🔐 HWID: <code>{hwid[:16]}...</code>\n\n"
        
        text += "━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += "Use /buy to get more keys!"
        
        send_message(user_id, text, "HTML")
    except Exception as e:
        print(f"Error in mykeys: {e}")

def handle_check(message):
    try:
        parts = message.get('text', '').split()
        if len(parts) < 2:
            send_message(message['from']['id'], "❌ Usage: /check YOUR_KEY")
            return
        
        key = parts[1]
        valid, msg, user_id, device_id, hwid = check_key_validity(key)
        
        if valid:
            info = get_key_info(key)
            if info:
                user_id, buy_date, expiry_date, status, device_id, hwid = info
                text = f"""
✅ <b>Key is VALID!</b>

━━━━━━━━━━━━━━━━━━━━━━━
🔑 <b>Key:</b> <code>{key}</code>
📅 <b>Bought:</b> {buy_date}
⏰ <b>Expires:</b> {expiry_date}
📱 <b>Device:</b> {device_id if device_id else 'Not activated'}
🔐 <b>HWID:</b> <code>{hwid}</code>
━━━━━━━━━━━━━━━━━━━━━━━
"""
                send_message(message['from']['id'], text, "HTML")
            else:
                send_message(message['from']['id'], "✅ Key is valid!")
        else:
            send_message(message['from']['id'], f"❌ {msg}")
    except Exception as e:
        print(f"Error in check: {e}")

def handle_status(message):
    try:
        user_id = message['from']['id']
        keys = get_user_keys(user_id)
        active_keys = [k for k in keys if k[3] == 'active']
        
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT total_spent FROM users WHERE user_id = ?", (user_id,))
        result = c.fetchone()
        total_spent = result[0] if result else 0
        conn.close()
        
        text = f"""
📊 <b>Account Status</b>

━━━━━━━━━━━━━━━━━━━━━━━
👤 <b>User ID:</b> <code>{user_id}</code>
🔑 <b>Total Keys:</b> {len(keys)}
✅ <b>Active Keys:</b> {len(active_keys)}
💰 <b>Total Spent:</b> ${total_spent:.2f}
━━━━━━━━━━━━━━━━━━━━━━━
"""
        send_message(message['from']['id'], text, "HTML")
    except Exception as e:
        print(f"Error in status: {e}")

def handle_license(message):
    try:
        parts = message.get('text', '').split()
        if len(parts) < 2:
            send_message(message['from']['id'], "❌ Usage: /license YOUR_KEY")
            return
        
        key = parts[1]
        valid, msg, user_id, device_id, hwid = check_key_validity(key)
        
        if not valid:
            send_message(message['from']['id'], f"❌ {msg}")
            return
        
        # Generate license file content
        license_content, hwid = generate_license_file(key, message['from']['id'])
        
        if not license_content:
            send_message(message['from']['id'], "❌ Failed to generate license file")
            return
        
        text = f"""
📁 <b>License File Generated!</b>

━━━━━━━━━━━━━━━━━━━━━━━
🔑 <b>Key:</b> <code>{key}</code>
🔐 <b>HWID:</b> <code>{hwid}</code>
━━━━━━━━━━━━━━━━━━━━━━━

<b>📄 License Content:</b>
<code>{license_content}</code>

━━━━━━━━━━━━━━━━━━━━━━━
📌 <b>How to use:</b>
1. Create file: <code>redzone_license.dat</code>
2. Paste the license content
3. Place in: <code>.../ShadowTrackerExtra/Saved/Paks/</code>
4. Restart PUBG Mobile

━━━━━━━━━━━━━━━━━━━━━━━
⚠️ <b>Keep this file safe!</b>
Do not share with others.
"""
        
        send_message(message['from']['id'], text, "HTML")
        
        # Send as file download
        send_message(message['from']['id'], 
                    f"📄 <b>Download License File:</b>\n<code>{license_content}</code>", "HTML")
        
    except Exception as e:
        print(f"Error in license: {e}")
        send_message(message['from']['id'], "❌ Error generating license file")

def handle_revoke(message):
    """Admin command to revoke a key"""
    try:
        user_id = message['from']['id']
        if user_id not in ADMIN_IDS:
            send_message(user_id, "❌ Unauthorized!")
            return
        
        parts = message.get('text', '').split()
        if len(parts) < 2:
            send_message(user_id, "❌ Usage: /revoke KEY")
            return
        
        key = parts[1]
        
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("UPDATE keys SET status = 'revoked' WHERE key = ?", (key,))
        c.execute("SELECT user_id FROM keys WHERE key = ?", (key,))
        result = c.fetchone()
        conn.commit()
        conn.close()
        
        if result:
            send_message(user_id, f"✅ Key <code>{key}</code> revoked!", "HTML")
            send_message(result[0], f"❌ Your key <code>{key}</code> has been revoked!", "HTML")
        else:
            send_message(user_id, f"❌ Key <code>{key}</code> not found", "HTML")
            
    except Exception as e:
        print(f"Error in revoke: {e}")

def handle_ban_hwid(message):
    """Admin command to ban an HWID"""
    try:
        user_id = message['from']['id']
        if user_id not in ADMIN_IDS:
            send_message(user_id, "❌ Unauthorized!")
            return
        
        parts = message.get('text', '').split()
        if len(parts) < 2:
            send_message(user_id, "❌ Usage: /ban_hwid HWID REASON")
            return
        
        hwid = parts[1]
        reason = ' '.join(parts[2:]) if len(parts) > 2 else 'No reason provided'
        
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        banned_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("INSERT OR REPLACE INTO blacklist (hwid, user_id, reason, banned_date) VALUES (?, ?, ?, ?)",
                 (hwid, user_id, reason, banned_date))
        
        # Deactivate all keys with this HWID
        c.execute("UPDATE keys SET status = 'banned' WHERE hwid = ?", (hwid,))
        c.execute("SELECT user_id FROM keys WHERE hwid = ?", (hwid,))
        users = c.fetchall()
        
        conn.commit()
        conn.close()
        
        send_message(user_id, f"✅ HWID <code>{hwid}</code> banned!\nReason: {reason}", "HTML")
        
        # Notify affected users
        for user in users:
            send_message(user[0], f"❌ Your device has been banned!\nReason: {reason}", "HTML")
            
    except Exception as e:
        print(f"Error in ban_hwid: {e}")

def handle_stats(message):
    """Admin command to view stats"""
    try:
        user_id = message['from']['id']
        if user_id not in ADMIN_IDS:
            send_message(user_id, "❌ Unauthorized!")
            return
        
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        
        c.execute("SELECT COUNT(*) FROM keys")
        total_keys = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM keys WHERE status = 'active'")
        active_keys = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM keys WHERE status = 'revoked'")
        revoked_keys = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM keys WHERE status = 'banned'")
        banned_keys = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM users")
        total_users = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM orders WHERE payment_status = 'pending'")
        pending_orders = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM orders WHERE payment_status = 'completed'")
        completed_orders = c.fetchone()[0]
        
        c.execute("SELECT SUM(amount) FROM orders WHERE payment_status = 'completed'")
        total_revenue = c.fetchone()[0] or 0
        
        c.execute("SELECT COUNT(*) FROM blacklist")
        banned_hwids = c.fetchone()[0]
        
        conn.close()
        
        text = f"""
📊 <b>REDZONE STATISTICS</b>

━━━━━━━━━━━━━━━━━━━━━━━
👥 <b>Total Users:</b> {total_users}
🔑 <b>Total Keys:</b> {total_keys}
✅ <b>Active Keys:</b> {active_keys}
❌ <b>Revoked Keys:</b> {revoked_keys}
🚫 <b>Banned Keys:</b> {banned_keys}
🔐 <b>Banned HWIDs:</b> {banned_hwids}

━━━━━━━━━━━━━━━━━━━━━━━
📦 <b>Orders:</b>
   Pending: {pending_orders}
   Completed: {completed_orders}
💰 <b>Total Revenue:</b> ${total_revenue:.2f}
━━━━━━━━━━━━━━━━━━━━━━━
"""
        send_message(user_id, text, "HTML")
        
    except Exception as e:
        print(f"Error in stats: {e}")

def handle_help(message):
    text = """
📖 <b>REDZONE VIP - Help & Support</b>

━━━━━━━━━━━━━━━━━━━━━━━
<b>User Commands:</b>

/buy - Purchase VIP key
/mykeys - View your keys
/check KEY - Check key validity
/status - Account status
/license KEY - Get license file
/help - This help menu

━━━━━━━━━━━━━━━━━━━━━━━
<b>Admin Commands:</b>

/revoke KEY - Revoke a key
/ban_hwid HWID REASON - Ban HWID
/stats - View statistics
/broadcast MSG - Send broadcast

━━━━━━━━━━━━━━━━━━━━━━━
<b>How to use key:</b>

1. Copy your key from /buy
2. Use /license YOUR_KEY to get license file
3. Create redzone_license.dat in Paks folder
4. Restart PUBG Mobile

━━━━━━━━━━━━━━━━━━━━━━━
<b>Support:</b>

📱 Telegram: @zakarya_op
💬 WhatsApp: +92 319 2530306
━━━━━━━━━━━━━━━━━━━━━━━
"""
    send_message(message['from']['id'], text, "HTML")

def handle_broadcast(message):
    """Admin command to broadcast message"""
    try:
        user_id = message['from']['id']
        if user_id not in ADMIN_IDS:
            send_message(user_id, "❌ Unauthorized!")
            return
        
        parts = message.get('text', '').split(' ', 1)
        if len(parts) < 2:
            send_message(user_id, "❌ Usage: /broadcast MESSAGE")
            return
        
        broadcast_msg = parts[1]
        
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT user_id FROM users")
        users = c.fetchall()
        conn.close()
        
        sent = 0
        for user in users:
            try:
                send_message(user[0], f"📢 <b>Broadcast from Admin:</b>\n\n{broadcast_msg}", "HTML")
                sent += 1
                time.sleep(0.1)  # Rate limit
            except Exception as e:
                print(f"Error sending broadcast to {user[0]}: {e}")
        
        send_message(user_id, f"✅ Broadcast sent to {sent} users!")
        
    except Exception as e:
        print(f"Error in broadcast: {e}")

# ============================================
# WEBHOOK HANDLER
# ============================================
app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle incoming webhook from Telegram"""
    try:
        update = request.json
        
        if 'message' in update:
            msg = update['message']
            text = msg.get('text', '')
            chat_id = msg['chat']['id']
            
            if text.startswith('/start'):
                handle_start(msg)
            elif text.startswith('/buy'):
                handle_buy(msg)
            elif text.startswith('/mykeys'):
                handle_mykeys(msg)
            elif text.startswith('/check'):
                handle_check(msg)
            elif text.startswith('/status'):
                handle_status(msg)
            elif text.startswith('/license'):
                handle_license(msg)
            elif text.startswith('/help'):
                handle_help(msg)
            elif text.startswith('/revoke') and chat_id in ADMIN_IDS:
                handle_revoke(msg)
            elif text.startswith('/ban_hwid') and chat_id in ADMIN_IDS:
                handle_ban_hwid(msg)
            elif text.startswith('/stats') and chat_id in ADMIN_IDS:
                handle_stats(msg)
            elif text.startswith('/broadcast') and chat_id in ADMIN_IDS:
                handle_broadcast(msg)
            else:
                send_message(chat_id, "❌ Unknown command. Use /help for available commands.")
        
        elif 'callback_query' in update:
            callback = update['callback_query']
            data = callback['data']
            chat_id = callback['message']['chat']['id']
            
            if data == 'buy':
                handle_buy({'from': {'id': chat_id}})
            elif data == 'mykeys':
                handle_mykeys({'from': {'id': chat_id}})
        
        return jsonify({'status': 'ok'})
        
    except Exception as e:
        print(f"Webhook error: {e}")
        return jsonify({'status': 'error'}), 500

@app.route('/api/verify', methods=['POST'])
def verify_key():
    """API endpoint for Lua verification"""
    try:
        data = request.json
        key = data.get('key', '')
        device_id = data.get('device_id', '')
        hwid = data.get('hwid', '')
        
        # Check if HWID is blacklisted
        blacklist_reason = is_hwid_blacklisted(hwid)
        if blacklist_reason:
            return jsonify({
                'status': 'error',
                'valid': False,
                'message': f'Device is blacklisted: {blacklist_reason}'
            })
        
        valid, msg, user_id, existing_device, existing_hwid = check_key_validity(key)
        
        if valid:
            info = get_key_info(key)
            if info:
                user_id, buy_date, expiry_date, status, device, hwid_db = info
                
                # Check if HWID matches (if already activated)
                if hwid_db and hwid_db != hwid and hwid_db != '':
                    return jsonify({
                        'status': 'error',
                        'valid': False,
                        'message': 'Key already activated on another device',
                        'hwid': hwid_db
                    })
                
                # Activate device
                if device == '' or hwid_db == '':
                    activate_device(key, device_id or 'UNKNOWN', hwid)
                
                # Generate license signature for verification
                signature = generate_license_signature(hwid, expiry_date, user_id, device_id or '')
                
                # Generate license content
                license_content = f"{hwid}|{signature}|{expiry_date}|{user_id}|{device_id or ''}"
                
                return jsonify({
                    'status': 'success',
                    'valid': True,
                    'message': 'Key is valid',
                    'expiry': expiry_date,
                    'user_id': user_id,
                    'device_id': device_id or '',
                    'hwid': hwid,
                    'license': license_content
                })
        
        return jsonify({
            'status': 'error',
            'valid': False,
            'message': msg
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'valid': False,
            'message': str(e)
        })

@app.route('/api/license', methods=['POST'])
def generate_license_api():
    """Generate license file via API"""
    try:
        data = request.json
        key = data.get('key', '')
        device_id = data.get('device_id', '')
        
        valid, msg, user_id, existing_device, existing_hwid = check_key_validity(key)
        
        if not valid:
            return jsonify({
                'status': 'error',
                'valid': False,
                'message': msg
            })
        
        license_content, hwid = generate_license_file(key, device_id)
        
        if not license_content:
            return jsonify({
                'status': 'error',
                'valid': False,
                'message': 'Failed to generate license'
            })
        
        return jsonify({
            'status': 'success',
            'valid': True,
            'license': license_content,
            'hwid': hwid,
            'key': key
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'valid': False,
            'message': str(e)
        })

@app.route('/')
def home():
    return """
    🔐 <b>REDZONE VIP KEY SYSTEM v4.0</b>
    <br><br>
    <b>Endpoints:</b>
    <br>
    📍 <b>Webhook:</b> /webhook
    <br>
    📍 <b>Verify API:</b> /api/verify
    <br>
    📍 <b>License API:</b> /api/license
    <br>
    📍 <b>Health Check:</b> /health
    <br><br>
    <b>Status:</b> ✅ Running
    """

@app.route('/health')
def health():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM keys")
    keys_count = c.fetchone()[0]
    conn.close()
    
    return jsonify({
        'status': 'healthy',
        'time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'keys_count': keys_count,
        'version': '4.0'
    })

# ============================================
# SETUP WEBHOOK
# ============================================
def setup_webhook():
    """Set webhook on bot start"""
    try:
        public_url = os.environ.get('PUBLIC_URL', '')
        if not public_url:
            print("⚠️ PUBLIC_URL not set, using polling mode")
            return False
        
        webhook_url = f"{public_url}/webhook"
        result = set_webhook(webhook_url)
        if result and result.get('ok'):
            print(f"✅ Webhook set: {webhook_url}")
            return True
        else:
            print(f"❌ Webhook failed: {result}")
            return False
    except Exception as e:
        print(f"Webhook setup error: {e}")
        return False

# ============================================
# POLLING MODE
# ============================================
def polling_mode():
    """Fallback to polling if webhook not available"""
    print("🔄 Starting polling mode...")
    last_update_id = 0
    
    while True:
        try:
            updates = get_updates(last_update_id + 1)
            
            if 'result' in updates:
                for update in updates['result']:
                    last_update_id = update['update_id']
                    
                    if 'message' in update:
                        msg = update['message']
                        text = msg.get('text', '')
                        chat_id = msg['chat']['id']
                        
                        if text.startswith('/start'):
                            handle_start(msg)
                        elif text.startswith('/buy'):
                            handle_buy(msg)
                        elif text.startswith('/mykeys'):
                            handle_mykeys(msg)
                        elif text.startswith('/check'):
                            handle_check(msg)
                        elif text.startswith('/status'):
                            handle_status(msg)
                        elif text.startswith('/license'):
                            handle_license(msg)
                        elif text.startswith('/help'):
                            handle_help(msg)
                        elif text.startswith('/revoke') and chat_id in ADMIN_IDS:
                            handle_revoke(msg)
                        elif text.startswith('/ban_hwid') and chat_id in ADMIN_IDS:
                            handle_ban_hwid(msg)
                        elif text.startswith('/stats') and chat_id in ADMIN_IDS:
                            handle_stats(msg)
                        elif text.startswith('/broadcast') and chat_id in ADMIN_IDS:
                            handle_broadcast(msg)
                        else:
                            send_message(chat_id, "❌ Unknown command. Use /help for available commands.")
                    
                    elif 'callback_query' in update:
                        callback = update['callback_query']
                        data = callback['data']
                        chat_id = callback['message']['chat']['id']
                        
                        if data == 'buy':
                            handle_buy({'from': {'id': chat_id}})
                        elif data == 'mykeys':
                            handle_mykeys({'from': {'id': chat_id}})
            
            time.sleep(1)
            
        except Exception as e:
            print(f"Polling error: {e}")
            time.sleep(5)

# ============================================
# START APPLICATION
# ============================================
if __name__ == "__main__":
    print("🚀 Starting REDZONE VIP Key System v4.0...")
    print(f"📱 Bot: @{os.environ.get('BOT_USERNAME', 'YOUR_BOT')}")
    print(f"🌐 Public URL: {os.environ.get('PUBLIC_URL', 'Not set')}")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    # Try webhook, fallback to polling
    webhook_set = setup_webhook()
    
    if not webhook_set:
        print("🔄 Using polling mode...")
        poll_thread = threading.Thread(target=polling_mode)
        poll_thread.daemon = True
        poll_thread.start()
    
    # Start Flask server
    port = int(os.environ.get('PORT', 5000))
    print(f"🌐 API Server running on port {port}")
    print("✅ System is ready!")
    app.run(host='0.0.0.0', port=port)
