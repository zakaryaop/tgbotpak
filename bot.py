import requests
import json
import sqlite3
import random
import string
import time
from datetime import datetime, timedelta
from flask import Flask, request, jsonify

# ============================================
# CONFIGURATION
# ============================================
BOT_TOKEN = "8921411956:AAFJihWjWC1SNDJBiQZj36LmHaRIP8XQ7Ls"  # Get from @BotFather
ADMIN_IDS = [5130475597]  # Your Telegram ID
PRICE = 5
KEY_EXPIRY_DAYS = 30

# ============================================
# TELEGRAM API FUNCTIONS (No telebot library)
# ============================================
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

def send_message(chat_id, text, parse_mode=None, reply_markup=None):
    """Send message using Telegram API"""
    url = f"{TELEGRAM_API}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode or "HTML"
    }
    if reply_markup:
        data["reply_markup"] = reply_markup
    response = requests.post(url, json=data)
    return response.json()

def send_inline_keyboard(chat_id, text, buttons):
    """Send message with inline keyboard"""
    reply_markup = {
        "inline_keyboard": buttons
    }
    return send_message(chat_id, text, "HTML", json.dumps(reply_markup))

def get_updates(offset=None):
    """Get new messages"""
    url = f"{TELEGRAM_API}/getUpdates"
    data = {}
    if offset:
        data["offset"] = offset
    response = requests.get(url, params=data)
    return response.json()

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
# KEY FUNCTIONS
# ============================================
def generate_key():
    """Generate unique key"""
    parts = []
    for i in range(4):
        part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        parts.append(part)
    return '-'.join(parts)

def generate_order_id():
    return 'ORD-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

def save_key_to_db(key, user_id, days_valid=KEY_EXPIRY_DAYS):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    buy_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    expiry_date = (datetime.now() + timedelta(days=days_valid)).strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO keys (key, user_id, buy_date, expiry_date, status, device_id) VALUES (?, ?, ?, ?, ?, ?)",
              (key, user_id, buy_date, expiry_date, 'active', ''))
    conn.commit()
    conn.close()

def get_user_keys(user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT key, buy_date, expiry_date, status FROM keys WHERE user_id = ? ORDER BY buy_date DESC", (user_id,))
    keys = c.fetchall()
    conn.close()
    return keys

def check_key_validity(key):
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
    
    expiry = datetime.strptime(expiry_date, "%Y-%m-%d %H:%M:%S")
    if datetime.now() > expiry:
        return False, "Key has expired"
    
    return True, "Key is valid"

def activate_device(key, device_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE keys SET device_id = ? WHERE key = ?", (device_id, key))
    conn.commit()
    conn.close()

def get_key_info(key):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT user_id, buy_date, expiry_date, status, device_id FROM keys WHERE key = ?", (key,))
    result = c.fetchone()
    conn.close()
    return result

def save_user(user_id, username, first_name, last_name):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    registered_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT OR IGNORE INTO users (user_id, username, first_name, last_name, registered_date) VALUES (?, ?, ?, ?, ?)",
              (user_id, username or "", first_name or "", last_name or "", registered_date))
    conn.commit()
    conn.close()

# ============================================
# COMMAND HANDLERS
# ============================================
def handle_start(message):
    user_id = message['from']['id']
    username = message['from'].get('username', '')
    first_name = message['from'].get('first_name', '')
    last_name = message['from'].get('last_name', '')
    
    save_user(user_id, username, first_name, last_name)
    
    text = f"""
🔐 <b>VIP MOD KEY SHOP</b>

Welcome {first_name}! 🎉

━━━━━━━━━━━━━━━━━━━━━━━
💎 <b>What is this?</b>
Premium VIP Mod for PUBG Mobile
Unlock all features: ESP, Aimbot, Skins

━━━━━━━━━━━━━━━━━━━━━━━
💰 <b>Price: ${PRICE}</b>
⏰ <b>Validity: {KEY_EXPIRY_DAYS} days</b>
━━━━━━━━━━━━━━━━━━━━━━━

📌 <b>Commands:</b>
/buy - Purchase a new key
/mykeys - View your keys
/check KEY - Check key validity
/status - Account status
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

def handle_buy(message):
    user_id = message['from']['id']
    
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
    
    text = f"""
✅ <b>KEY GENERATED SUCCESSFULLY!</b>

━━━━━━━━━━━━━━━━━━━━━━━
🔑 <b>Your Key:</b>
<code>{key}</code>

⏰ <b>Valid for: {KEY_EXPIRY_DAYS} days</b>
📅 <b>Expires: {(datetime.now() + timedelta(days=KEY_EXPIRY_DAYS)).strftime('%Y-%m-%d')}</b>
━━━━━━━━━━━━━━━━━━━━━━━

📌 <b>How to use:</b>
1. Open PUBG Mobile
2. Go to Settings → Mod Menu
3. Enter key: <code>{key}</code>
4. Enjoy VIP features! 🎮

━━━━━━━━━━━━━━━━━━━━━━━
⚠️ <b>Note:</b> Key is one-time use
Keep your key safe!

📱 @zakarya_op
💬 +92 319 2530306
"""
    
    send_message(user_id, text, "HTML")

def handle_mykeys(message):
    user_id = message['from']['id']
    keys = get_user_keys(user_id)
    
    if not keys:
        send_message(user_id, "❌ You don't have any keys yet!\nUse /buy to purchase one.")
        return
    
    text = "🔐 <b>Your Keys:</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n"
    for key, buy_date, expiry_date, status in keys:
        status_emoji = "✅" if status == "active" else "❌"
        text += f"{status_emoji} <code>{key}</code>\n"
        text += f"   Expires: {expiry_date}\n\n"
    
    text += "━━━━━━━━━━━━━━━━━━━━━━━\n"
    text += "Use /buy to get more keys!"
    
    send_message(user_id, text, "HTML")

def handle_check(message):
    parts = message.get('text', '').split()
    if len(parts) < 2:
        send_message(message['from']['id'], "❌ Usage: /check YOUR_KEY")
        return
    
    key = parts[1]
    valid, msg = check_key_validity(key)
    
    if valid:
        info = get_key_info(key)
        if info:
            user_id, buy_date, expiry_date, status, device_id = info
            text = f"""
✅ <b>Key is VALID!</b>

━━━━━━━━━━━━━━━━━━━━━━━
🔑 <b>Key:</b> <code>{key}</code>
📅 <b>Bought:</b> {buy_date}
⏰ <b>Expires:</b> {expiry_date}
📱 <b>Device:</b> {device_id if device_id else 'Not activated'}
━━━━━━━━━━━━━━━━━━━━━━━
"""
            send_message(message['from']['id'], text, "HTML")
        else:
            send_message(message['from']['id'], "✅ Key is valid!")
    else:
        send_message(message['from']['id'], f"❌ {msg}")

def handle_status(message):
    user_id = message['from']['id']
    keys = get_user_keys(user_id)
    active_keys = [k for k in keys if k[3] == 'active']
    
    text = f"""
📊 <b>Account Status</b>

━━━━━━━━━━━━━━━━━━━━━━━
👤 <b>User ID:</b> <code>{user_id}</code>
🔑 <b>Total Keys:</b> {len(keys)}
✅ <b>Active Keys:</b> {len(active_keys)}
💰 <b>Total Spent:</b> ${len(keys) * PRICE}
━━━━━━━━━━━━━━━━━━━━━━━
"""
    send_message(message['from']['id'], text, "HTML")

def handle_help(message):
    text = """
📖 <b>Help & Support</b>

━━━━━━━━━━━━━━━━━━━━━━━
<b>Commands:</b>

/buy - Purchase VIP key
/mykeys - View your keys
/check KEY - Check key validity
/status - Account status
/help - This help menu

━━━━━━━━━━━━━━━━━━━━━━━
<b>How to use key:</b>

1. Copy your key from /buy
2. Open PUBG Mobile
3. Settings → Mod Menu
4. Paste and verify

━━━━━━━━━━━━━━━━━━━━━━━
<b>Support:</b>

📱 Telegram: @zakarya_op
💬 WhatsApp: +92 319 2530306
━━━━━━━━━━━━━━━━━━━━━━━
"""
    send_message(message['from']['id'], text, "HTML")

# ============================================
# WEBHOOK / POLLING
# ============================================
def process_updates():
    """Process incoming updates"""
    last_update_id = 0
    
    while True:
        try:
            updates = get_updates(last_update_id + 1)
            
            if 'result' in updates:
                for update in updates['result']:
                    last_update_id = update['update_id']
                    
                    # Handle messages
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
                        elif text.startswith('/help'):
                            handle_help(msg)
                        else:
                            send_message(chat_id, "❌ Unknown command. Use /help for available commands.")
                    
                    # Handle callback queries
                    elif 'callback_query' in update:
                        callback = update['callback_query']
                        data = callback['data']
                        chat_id = callback['message']['chat']['id']
                        
                        if data == 'buy':
                            # Simulate /buy command
                            handle_buy({'from': {'id': chat_id}})
                        elif data == 'mykeys':
                            handle_mykeys({'from': {'id': chat_id}})
            
            time.sleep(1)
            
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)

# ============================================
# FLASK API SERVER (For Lua Verification)
# ============================================
app = Flask(__name__)

@app.route('/api/verify', methods=['POST'])
def verify_key():
    try:
        data = request.json
        key = data.get('key', '')
        device_id = data.get('device_id', '')
        
        valid, msg = check_key_validity(key)
        
        if valid:
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
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'valid': False,
            'message': str(e)
        })

@app.route('/api/generate', methods=['POST'])
def generate_key_api():
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

@app.route('/')
def home():
    return "🔐 VIP Key System is running!"

# ============================================
# START BOT
# ============================================
if __name__ == "__main__":
    import threading
    
    # Start bot polling in background
    bot_thread = threading.Thread(target=process_updates)
    bot_thread.daemon = True
    bot_thread.start()
    
    print("🤖 Bot is running with polling...")
    print("🌐 API server running on http://0.0.0.0:5000")
    print("📱 Bot: @YOUR_BOT_USERNAME")
    
    # Start Flask server
    app.run(host='0.0.0.0', port=5000, debug=False)
