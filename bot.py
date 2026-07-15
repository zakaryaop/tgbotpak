import telebot
import json
import sqlite3
import random
import string
import time
from datetime import datetime, timedelta
import threading
import os

# ============================================
# CONFIGURATION
# ============================================
BOT_TOKEN = "8921411956:AAFJihWjWC1SNDJBiQZj36LmHaRIP8XQ7Ls"  # Change this
ADMIN_IDS = [5130475597, 5130475597]  # Your Telegram IDs
PRICE = 5  # Price in USD or your currency
KEY_EXPIRY_DAYS = 7  # Days key is valid

# ============================================
# DATABASE SETUP
# ============================================
DB_FILE = "keys.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS keys
                 (key TEXT PRIMARY KEY,
                  user_id INTEGER,
                  buy_date TEXT,
                  expiry_date TEXT,
                  status TEXT,
                  device_id TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY,
                  username TEXT,
                  first_name TEXT,
                  last_name TEXT,
                  registered_date TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS orders
                 (order_id TEXT PRIMARY KEY,
                  user_id INTEGER,
                  key TEXT,
                  amount REAL,
                  payment_status TEXT,
                  order_date TEXT)''')
    conn.commit()
    conn.close()

init_db()

# ============================================
# KEY GENERATION FUNCTIONS
# ============================================
def generate_key():
    """Generate unique key format: XXXX-XXXX-XXXX-XXXX"""
    parts = []
    for i in range(4):
        part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        parts.append(part)
    return '-'.join(parts)

def generate_order_id():
    """Generate order ID"""
    return 'ORD-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

def save_key_to_db(key, user_id, days_valid=KEY_EXPIRY_DAYS):
    """Save key to database"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    buy_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    expiry_date = (datetime.now() + timedelta(days=days_valid)).strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO keys (key, user_id, buy_date, expiry_date, status, device_id) VALUES (?, ?, ?, ?, ?, ?)",
              (key, user_id, buy_date, expiry_date, 'active', ''))
    conn.commit()
    conn.close()

def save_user_to_db(user_id, username, first_name, last_name):
    """Save user to database"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    registered_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT OR IGNORE INTO users (user_id, username, first_name, last_name, registered_date) VALUES (?, ?, ?, ?, ?)",
              (user_id, username, first_name, last_name, registered_date))
    conn.commit()
    conn.close()

def get_user_keys(user_id):
    """Get all keys for a user"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT key, buy_date, expiry_date, status FROM keys WHERE user_id = ? ORDER BY buy_date DESC", (user_id,))
    keys = c.fetchall()
    conn.close()
    return keys

def check_key_validity(key):
    """Check if key is valid and not expired"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT status, expiry_date FROM keys WHERE key = ?", (key,))
    result = c.fetchone()
    conn.close()
    
    if not result:
        return False, "Key not found"
    
    status, expiry_date = result
    
    if status != 'active':
        return False, "Key is inactive or revoked"
    
    # Check expiry
    expiry = datetime.strptime(expiry_date, "%Y-%m-%d %H:%M:%S")
    if datetime.now() > expiry:
        return False, "Key has expired"
    
    return True, "Key is valid"

def activate_device(key, device_id):
    """Activate key for a device"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE keys SET device_id = ? WHERE key = ?", (device_id, key))
    conn.commit()
    conn.close()

def get_key_info(key):
    """Get key information"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT user_id, buy_date, expiry_date, status, device_id FROM keys WHERE key = ?", (key,))
    result = c.fetchone()
    conn.close()
    return result

# ============================================
# BOT COMMANDS
# ============================================
bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    username = message.from_user.username or "NoUsername"
    first_name = message.from_user.first_name or "NoName"
    last_name = message.from_user.last_name or ""
    
    # Save user
    save_user_to_db(user_id, username, first_name, last_name)
    
    welcome_text = f"""
🔐 *VIP MOD KEY SHOP*

Welcome {first_name}! 🎉

━━━━━━━━━━━━━━━━━━━━━━━
💎 *What is this?*
Premium VIP Mod for PUBG Mobile
Unlock all features: ESP, Aimbot, Skins

━━━━━━━━━━━━━━━━━━━━━━━
💰 *Price: ${PRICE}*
⏰ *Validity: {KEY_EXPIRY_DAYS} days*
━━━━━━━━━━━━━━━━━━━━━━━

📌 *Commands:*
/buy - Purchase a new key
/mykeys - View your keys
/check KEY - Check key validity
/status - Account status
/help - Help & support

━━━━━━━━━━━━━━━━━━━━━━━
📱 *Contact:* @zakarya_op
💬 *WhatsApp:* +92 319 2530306
"""
    bot.reply_to(message, welcome_text, parse_mode='Markdown')

@bot.message_handler(commands=['buy'])
def buy_key(message):
    user_id = message.from_user.id
    username = message.from_user.username or "NoUsername"
    first_name = message.from_user.first_name or "NoName"
    last_name = message.from_user.last_name or ""
    
    save_user_to_db(user_id, username, first_name, last_name)
    
    # Generate key
    key = generate_key()
    save_key_to_db(key, user_id)
    
    # Generate order
    order_id = generate_order_id()
    order_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO orders (order_id, user_id, key, amount, payment_status, order_date) VALUES (?, ?, ?, ?, ?, ?)",
              (order_id, user_id, key, PRICE, 'completed', order_date))
    conn.commit()
    conn.close()
    
    buy_text = f"""
✅ *KEY GENERATED SUCCESSFULLY!*

━━━━━━━━━━━━━━━━━━━━━━━
🔑 *Your Key:*
`{key}`

⏰ *Valid for: {KEY_EXPIRY_DAYS} days*
📅 *Expires: {(datetime.now() + timedelta(days=KEY_EXPIRY_DAYS)).strftime('%Y-%m-%d')}*
━━━━━━━━━━━━━━━━━━━━━━━

📌 *How to use:*
1. Open PUBG Mobile
2. Go to Settings → Mod Menu
3. Enter key: `{key}`
4. Enjoy VIP features! 🎮

━━━━━━━━━━━━━━━━━━━━━━━
⚠️ *Note:* Key is one-time use
Keep your key safe!

📱 @zakarya_op
💬 +92 319 2530306
"""
    bot.reply_to(message, buy_text, parse_mode='Markdown')
    
    # Send private key to user (optional)
    try:
        bot.send_message(user_id, f"🔑 Your key: `{key}`", parse_mode='Markdown')
    except:
        pass

@bot.message_handler(commands=['mykeys'])
def my_keys(message):
    user_id = message.from_user.id
    keys = get_user_keys(user_id)
    
    if not keys:
        bot.reply_to(message, "❌ You don't have any keys yet!\nUse /buy to purchase one.")
        return
    
    response = "🔐 *Your Keys:*\n━━━━━━━━━━━━━━━━━━━━━━━\n"
    for key, buy_date, expiry_date, status in keys:
        status_emoji = "✅" if status == "active" else "❌"
        response += f"{status_emoji} `{key}`\n"
        response += f"   Expires: {expiry_date}\n\n"
    
    response += "━━━━━━━━━━━━━━━━━━━━━━━\n"
    response += "Use /buy to get more keys!"
    
    bot.reply_to(message, response, parse_mode='Markdown')

@bot.message_handler(commands=['check'])
def check_key(message):
    try:
        key = message.text.split()[1]
    except:
        bot.reply_to(message, "❌ Usage: /check YOUR_KEY")
        return
    
    valid, msg = check_key_validity(key)
    
    if valid:
        info = get_key_info(key)
        if info:
            user_id, buy_date, expiry_date, status, device_id = info
            check_text = f"""
✅ *Key is VALID!*

━━━━━━━━━━━━━━━━━━━━━━━
🔑 *Key:* `{key}`
📅 *Bought:* {buy_date}
⏰ *Expires:* {expiry_date}
📱 *Device:* {device_id if device_id else 'Not activated'}
━━━━━━━━━━━━━━━━━━━━━━━
"""
            bot.reply_to(message, check_text, parse_mode='Markdown')
        else:
            bot.reply_to(message, "✅ Key is valid!")
    else:
        bot.reply_to(message, f"❌ {msg}")

@bot.message_handler(commands=['status'])
def status(message):
    user_id = message.from_user.id
    keys = get_user_keys(user_id)
    active_keys = [k for k in keys if k[3] == 'active']
    
    status_text = f"""
📊 *Account Status*

━━━━━━━━━━━━━━━━━━━━━━━
👤 *User ID:* `{user_id}`
🔑 *Total Keys:* {len(keys)}
✅ *Active Keys:* {len(active_keys)}
💰 *Total Spent:* ${len(keys) * PRICE}
━━━━━━━━━━━━━━━━━━━━━━━
"""
    bot.reply_to(message, status_text, parse_mode='Markdown')

@bot.message_handler(commands=['help'])
def help_command(message):
    help_text = """
📖 *Help & Support*

━━━━━━━━━━━━━━━━━━━━━━━
*Commands:*

/buy - Purchase VIP key
/mykeys - View your keys
/check KEY - Check key validity
/status - Account status
/help - This help menu

━━━━━━━━━━━━━━━━━━━━━━━
*How to use key:*

1. Copy your key from /buy
2. Open PUBG Mobile
3. Settings → Mod Menu
4. Paste and verify

━━━━━━━━━━━━━━━━━━━━━━━
*Support:*

📱 Telegram: @zakarya_op
💬 WhatsApp: +92 319 2530306
━━━━━━━━━━━━━━━━━━━━━━━
"""
    bot.reply_to(message, help_text, parse_mode='Markdown')

# ============================================
# ADMIN COMMANDS
# ============================================
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ Unauthorized!")
        return
    
    admin_text = """
🔐 *Admin Panel*

━━━━━━━━━━━━━━━━━━━━━━━
*Commands:*

/admin_revoke KEY - Revoke a key
/admin_extend KEY DAYS - Extend key validity
/admin_stats - View stats
/admin_users - List all users
/admin_broadcast MSG - Send broadcast

━━━━━━━━━━━━━━━━━━━━━━━
"""
    bot.reply_to(message, admin_text, parse_mode='Markdown')

@bot.message_handler(commands=['admin_stats'])
def admin_stats(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ Unauthorized!")
        return
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) FROM keys")
    total_keys = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM keys WHERE status = 'active'")
    active_keys = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM orders")
    total_orders = c.fetchone()[0]
    
    c.execute("SELECT SUM(amount) FROM orders WHERE payment_status = 'completed'")
    total_revenue = c.fetchone()[0] or 0
    
    conn.close()
    
    stats_text = f"""
📊 *Server Statistics*

━━━━━━━━━━━━━━━━━━━━━━━
👥 *Total Users:* {total_users}
🔑 *Total Keys:* {total_keys}
✅ *Active Keys:* {active_keys}
📦 *Total Orders:* {total_orders}
💰 *Revenue:* ${total_revenue:.2f}
━━━━━━━━━━━━━━━━━━━━━━━
"""
    bot.reply_to(message, stats_text, parse_mode='Markdown')

@bot.message_handler(commands=['admin_revoke'])
def admin_revoke(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ Unauthorized!")
        return
    
    try:
        key = message.text.split()[1]
    except:
        bot.reply_to(message, "❌ Usage: /admin_revoke KEY")
        return
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE keys SET status = 'revoked' WHERE key = ?", (key,))
    conn.commit()
    conn.close()
    
    bot.reply_to(message, f"✅ Key `{key}` has been revoked!", parse_mode='Markdown')

@bot.message_handler(commands=['admin_extend'])
def admin_extend(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ Unauthorized!")
        return
    
    try:
        parts = message.text.split()
        key = parts[1]
        days = int(parts[2])
    except:
        bot.reply_to(message, "❌ Usage: /admin_extend KEY DAYS")
        return
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    new_expiry = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    c.execute("UPDATE keys SET expiry_date = ? WHERE key = ?", (new_expiry, key))
    conn.commit()
    conn.close()
    
    bot.reply_to(message, f"✅ Key `{key}` extended by {days} days!", parse_mode='Markdown')

@bot.message_handler(commands=['admin_broadcast'])
def admin_broadcast(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ Unauthorized!")
        return
    
    try:
        msg = message.text.split(' ', 1)[1]
    except:
        bot.reply_to(message, "❌ Usage: /admin_broadcast MESSAGE")
        return
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    users = c.fetchall()
    conn.close()
    
    sent = 0
    for user in users:
        try:
            bot.send_message(user[0], f"📢 *Broadcast from Admin:*\n\n{msg}", parse_mode='Markdown')
            sent += 1
        except:
            pass
    
    bot.reply_to(message, f"✅ Broadcast sent to {sent} users!")

# ============================================
# API ENDPOINT FOR LUA (HTTP Server)
# ============================================
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/api/verify', methods=['POST'])
def verify_key():
    data = request.json
    key = data.get('key', '')
    device_id = data.get('device_id', '')
    
    valid, msg = check_key_validity(key)
    
    if valid:
        # Activate device if not already
        info = get_key_info(key)
        if info:
            user_id, buy_date, expiry_date, status, device = info
            if device == '':
                activate_device(key, device_id)
            return jsonify({
                'status': 'success',
                'valid': True,
                'message': 'Key is valid',
                'expiry': expiry_date,
                'user_id': user_id
            })
    
    return jsonify({
        'status': 'error',
        'valid': False,
        'message': msg
    })

@app.route('/api/generate', methods=['POST'])
def generate_key_api():
    # For admin use only
    auth = request.headers.get('Authorization')
    if auth != 'ADMIN_SECRET':
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    user_id = data.get('user_id', 1)
    days = data.get('days', KEY_EXPIRY_DAYS)
    
    key = generate_key()
    save_key_to_db(key, user_id, days)
    
    return jsonify({
        'status': 'success',
        'key': key,
        'expiry': (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    })

# ============================================
# START BOT AND API SERVER
# ============================================
def run_bot():
    print("🤖 Bot is running...")
    bot.infinity_polling()

def run_api():
    print("🌐 API server running on http://0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)

# Run both in separate threads
if __name__ == "__main__":
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.start()
    
    api_thread = threading.Thread(target=run_api)
    api_thread.start()
    
    print("✅ System is ready!")
    print("📱 Bot: @YOUR_BOT_USERNAME")
    print("🌐 API: http://YOUR_IP:5000/api/verify")