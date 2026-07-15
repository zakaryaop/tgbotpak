# ============================================
# VIP KEY SYSTEM - Koyeb Compatible
# ============================================

import os
import json
import sqlite3
import random
import string
import time
from datetime import datetime, timedelta
import threading

# Try to import, fallback if not available
try:
    import requests
except ImportError:
    # Install requests if not available
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
# CONFIGURATION - Get from environment variables
# ============================================
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8921411956:AAFJihWjWC1SNDJBiQZj36LmHaRIP8XQ7Ls')
ADMIN_IDS = [int(id) for id in os.environ.get('ADMIN_IDS', '5130475597').split(',')]
PRICE = int(os.environ.get('PRICE', '5'))
KEY_EXPIRY_DAYS = int(os.environ.get('KEY_EXPIRY_DAYS', '30'))
API_PORT = int(os.environ.get('PORT', '5000'))

print(f"🤖 Bot Token: {BOT_TOKEN[:10]}...")
print(f"👑 Admin IDs: {ADMIN_IDS}")
print(f"💰 Price: ${PRICE}")
print(f"⏰ Key Expiry: {KEY_EXPIRY_DAYS} days")

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
        response = requests.post(url, json=data)
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
        response = requests.post(url, json=data)
        return response.json()
    except Exception as e:
        print(f"Error setting webhook: {e}")
        return None

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
    print("✅ Database initialized")

init_db()

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

def save_key_to_db(key, user_id, days_valid=KEY_EXPIRY_DAYS):
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        buy_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        expiry_date = (datetime.now() + timedelta(days=days_valid)).strftime("%Y-%m-%d %H:%M:%S")
        c.execute("INSERT INTO keys (key, user_id, buy_date, expiry_date, status, device_id) VALUES (?, ?, ?, ?, ?, ?)",
                  (key, user_id, buy_date, expiry_date, 'active', ''))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error saving key: {e}")
        return False

def get_user_keys(user_id):
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT key, buy_date, expiry_date, status FROM keys WHERE user_id = ? ORDER BY buy_date DESC", (user_id,))
        keys = c.fetchall()
        conn.close()
        return keys
    except Exception as e:
        print(f"Error getting keys: {e}")
        return []

def check_key_validity(key):
    try:
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
    except Exception as e:
        print(f"Error checking key: {e}")
        return False, "Error checking key"

def activate_device(key, device_id):
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("UPDATE keys SET device_id = ? WHERE key = ?", (device_id, key))
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
        c.execute("SELECT user_id, buy_date, expiry_date, status, device_id FROM keys WHERE key = ?", (key,))
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
    except Exception as e:
        print(f"Error in start: {e}")

def handle_buy(message):
    try:
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
        
        # Also send key as separate message
        send_message(user_id, f"🔑 Your Key: <code>{key}</code>", "HTML")
        
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
        for key, buy_date, expiry_date, status in keys:
            status_emoji = "✅" if status == "active" else "❌"
            text += f"{status_emoji} <code>{key}</code>\n"
            text += f"   Expires: {expiry_date}\n\n"
        
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
    except Exception as e:
        print(f"Error in check: {e}")

def handle_status(message):
    try:
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
    except Exception as e:
        print(f"Error in status: {e}")

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
# WEBHOOK HANDLER (For Koyeb)
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
            elif text.startswith('/help'):
                handle_help(msg)
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
    """Generate key via API (Admin only)"""
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
    return """
    🔐 VIP Key System is running!
    <br>
    <b>Webhook URL:</b> /webhook
    <br>
    <b>API:</b> /api/verify
    """

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'keys_count': len(get_user_keys(1))  # Just to test DB
    })

# ============================================
# SETUP WEBHOOK
# ============================================
def setup_webhook():
    """Set webhook on bot start"""
    try:
        # Get the public URL from environment or use default
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
# POLLING MODE (Fallback if webhook fails)
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
                        elif text.startswith('/help'):
                            handle_help(msg)
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
    print("🚀 Starting VIP Key System...")
    print(f"📱 Bot: @{os.environ.get('BOT_USERNAME', 'YOUR_BOT')}")
    print(f"🌐 Public URL: {os.environ.get('PUBLIC_URL', 'Not set')}")
    
    # Try webhook, fallback to polling
    webhook_set = setup_webhook()
    
    if not webhook_set:
        print("🔄 Using polling mode...")
        # Start polling in background thread
        poll_thread = threading.Thread(target=polling_mode)
        poll_thread.daemon = True
        poll_thread.start()
    
    # Start Flask server
    port = int(os.environ.get('PORT', 5000))
    print(f"🌐 API Server running on port {port}")
    app.run(host='0.0.0.0', port=port)
