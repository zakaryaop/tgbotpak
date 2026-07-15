import time
import logging
import os
import json
import random
import sys
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

# ==========================================
# CONFIGURATION - YAHAN APNA TOKEN DAALO
# ==========================================
TOKEN = "8603563956:AAG6O02ZTMVNqDM9u-Mrc3EkwYqgR-_rHNw"  # BOTFATHER SE TOKEN DAALO
ADMIN_IDS = [5130475597, 5130475597]  # APNE ADMIN IDS DAALO

# Database file
DB_FILE = "licenses.json"

# SECRET KEY - Must match Lua code
SECRET_KEY = "ZakPubgSkin_VIP_2026_Ultimate!"

# Channel info
CHANNEL_USERNAME = "zakpubgskin"
OWNER_USERNAME = "zakarya_op"

# Pricing
PRICES = {
    "1": 1,    # 1 day - $1
    "30": 8,   # 30 days - $8
    "60": 12   # 60 days - $12
}

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==========================================
# DATABASE MANAGEMENT
# ==========================================
def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {"licenses": {}, "users": {}, "pending_payments": {}, "referrals": {}}
    return {"licenses": {}, "users": {}, "pending_payments": {}, "referrals": {}}

def save_db(db):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(db, f, indent=2, ensure_ascii=False)

# ==========================================
# LICENSE GENERATION
# ==========================================
def custom_hash(text):
    hash_val = 5381
    for char in text:
        hash_val = (hash_val * 33 + ord(char)) % 4294967296
    return f"{hash_val:08X}"

def generate_license_key(hwid, days, user_id):
    expiry_timestamp = int(time.time()) + (days * 24 * 60 * 60)
    raw_data = f"{hwid}{expiry_timestamp}{SECRET_KEY}{user_id}"
    signature = custom_hash(raw_data)
    return f"{signature}|{expiry_timestamp}|{days}"

def parse_license_key(license_key):
    try:
        parts = license_key.split('|')
        if len(parts) >= 2:
            signature = parts[0]
            expiry = int(parts[1])
            days = int(parts[2]) if len(parts) > 2 else 30
            return signature, expiry, days
        return None, None, None
    except:
        return None, None, None

def get_license_info(hwid, db):
    if hwid in db["licenses"]:
        license_key = db["licenses"][hwid]["key"]
        signature, expiry, days = parse_license_key(license_key)
        if expiry:
            days_left = int((expiry - time.time()) / (24 * 60 * 60))
            return {
                "key": license_key,
                "expires": expiry,
                "days_left": days_left,
                "is_valid": time.time() < expiry,
                "days": days,
                "user_id": db["licenses"][hwid].get("user_id", 0)
            }
    return None

# ==========================================
# START COMMAND
# ==========================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        username = update.effective_user.username or "User"
        
        db = load_db()
        if str(user_id) not in db["users"]:
            db["users"][str(user_id)] = {
                "username": username,
                "first_seen": time.time(),
                "is_admin": user_id in ADMIN_IDS,
                "referral_count": 0,
                "referral_code": f"REF{random.randint(100000, 999999)}",
                "referred_by": None
            }
            save_db(db)
        
        is_admin = user_id in ADMIN_IDS
        user_data = db["users"].get(str(user_id), {})
        ref_count = user_data.get("referral_count", 0)
        
        keyboard = [
            [InlineKeyboardButton("🛒 BUY KEY", callback_data="buy_key")],
            [InlineKeyboardButton("📦 PAK FILES", callback_data="pak_files")],
            [InlineKeyboardButton("👥 REFERRAL (3 = FREE KEY)", callback_data="referral")]
        ]
        
        if is_admin:
            keyboard.append([InlineKeyboardButton("━━━ ADMIN PANEL ━━━", callback_data="admin_sep")])
            keyboard.append([InlineKeyboardButton("👑 Admin Dashboard", callback_data="admin_dashboard")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        welcome_text = f"""
🔥 ZAK PUBG SKIN VIP

Welcome {username}!

⚡ 3 Simple Steps:
1️⃣ Buy Key
2️⃣ Download PAK Files
3️⃣ Install and Play!

💎 Prices:
🟢 1 Day  - $1
🔵 30 Days - $8
🔴 60 Days - $12

👥 Referral Bonus:
3 Referrals = 1 DAY FREE!
You have: {ref_count}/3 referrals

📢 Channel: @{CHANNEL_USERNAME}
        """
        
        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Start error: {e}")

# ==========================================
# BUTTON CALLBACK HANDLER
# ==========================================
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        data = query.data
        
        # BUY KEY
        if data == "buy_key":
            keyboard = [
                [InlineKeyboardButton("🟢 1 Day - $1", callback_data="buy_1")],
                [InlineKeyboardButton("🔵 30 Days - $8", callback_data="buy_30")],
                [InlineKeyboardButton("🔴 60 Days - $12", callback_data="buy_60")],
                [InlineKeyboardButton("🔙 Back", callback_data="back_main")]
            ]
            await query.edit_message_text(
                "💎 SELECT YOUR PLAN\n\nChoose your VIP duration:\n\n🟢 1 Day - $1\n🔵 30 Days - $8\n🔴 60 Days - $12",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        elif data.startswith("buy_"):
            days = data.split("_")[1]
            price = PRICES.get(days, 0)
            day_names = {"1": "1 Day", "30": "30 Days", "60": "60 Days"}
            
            random.seed(user_id)
            part1 = f"{random.randint(1000, 9999):04X}"
            part2 = f"{random.randint(1000, 9999):04X}"
            part3 = f"{random.randint(1000, 9999):04X}"
            hwid = f"RDZ-{part1}-{part2}-{part3}"
            
            db = load_db()
            if "pending_payments" not in db:
                db["pending_payments"] = {}
            
            payment_id = f"PAY_{int(time.time())}_{user_id}"
            db["pending_payments"][payment_id] = {
                "user_id": user_id,
                "hwid": hwid,
                "days": int(days),
                "price": price,
                "timestamp": time.time(),
                "status": "pending"
            }
            save_db(db)
            
            await query.edit_message_text(
                f"💳 COMPLETE PAYMENT\n\nOrder Details:\nHWID: {hwid}\nPlan: {day_names.get(days, days)}\nPrice: ${price}\nOrder ID: {payment_id}\n\nPayment Methods:\n1️⃣ USDT (TRC20)\n2️⃣ Binance Pay\n3️⃣ Telegram Stars\n4️⃣ EasyPaisa\n5️⃣ JazzCash\n\nAfter payment, click 'Send Screenshot' below.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📸 Send Screenshot", callback_data="send_screenshot")],
                    [InlineKeyboardButton("🔙 Back", callback_data="buy_key")]
                ])
            )
            
        elif data == "send_screenshot":
            await query.edit_message_text(
                "📸 SEND PAYMENT SCREENSHOT\n\nSend a screenshot of your payment as a photo to this bot.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back", callback_data="buy_key")]
                ])
            )
            context.user_data['waiting_for'] = 'screenshot'
            
        # PAK FILES
        elif data == "pak_files":
            features_text = "🔥 ESP: Skeleton, Box, Distance, Health, Radar, Antenna, Outline\n🔥 Aimbot: Auto Headshot, Magic Bullet, No Recoil\n🔥 Visual: 165 FPS, IPAD View, Remove Grass/Fog, White Body, Black Sky, Wallhack\n🔥 Other: God Mode, Wall Climb, Fast Car"
            
            await query.edit_message_text(
                f"📦 ZAK PUBG SKIN PAK FILES\n\n{features_text}\n\nDownload: @{CHANNEL_USERNAME}\n\nInstall: Extract to Android/data/com.tencent.ig/files/\nCreate zakpubgskin.txt with your license key.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🛒 Buy Key", callback_data="buy_key")],
                    [InlineKeyboardButton("🔙 Back", callback_data="back_main")]
                ])
            )
            
        # REFERRAL
        elif data == "referral":
            db = load_db()
            user_data = db["users"].get(str(user_id), {})
            ref_code = user_data.get("referral_code", "")
            ref_count = user_data.get("referral_count", 0)
            remaining = 3 - ref_count
            
            await query.edit_message_text(
                f"👥 REFERRAL PROGRAM\n\n3 Referrals = 1 DAY FREE!\n\nYour Code: {ref_code}\n\nYour referrals: {ref_count}/3\nProgress: {'█' * ref_count}{'░' * remaining}\nNeed {remaining} more referrals.\n\nShare: t.me/{CHANNEL_USERNAME}?start={ref_code}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back", callback_data="back_main")]
                ])
            )
            
        # ADMIN PANEL
        elif data == "admin_dashboard":
            if user_id not in ADMIN_IDS:
                await query.edit_message_text("⛔ Not authorized!")
                return
            
            db = load_db()
            total_licenses = len(db.get("licenses", {}))
            total_users = len(db.get("users", {}))
            pending_payments = len([p for p in db.get("pending_payments", {}).values() if p.get("status") == "pending"])
            
            keyboard = [
                [InlineKeyboardButton("🆕 Generate License", callback_data="admin_gen")],
                [InlineKeyboardButton("💰 Pending Payments", callback_data="admin_pending")],
                [InlineKeyboardButton("📋 All Licenses", callback_data="admin_list")],
                [InlineKeyboardButton("❌ Revoke License", callback_data="admin_revoke")],
                [InlineKeyboardButton("📊 Stats", callback_data="admin_stats")],
                [InlineKeyboardButton("🔙 Back", callback_data="back_main")]
            ]
            
            await query.edit_message_text(
                f"👑 ADMIN DASHBOARD\n\nUsers: {total_users}\nLicenses: {total_licenses}\nPending: {pending_payments}",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        elif data == "admin_gen":
            if user_id not in ADMIN_IDS:
                await query.edit_message_text("⛔ Not authorized!")
                return
            
            await query.edit_message_text(
                "🆕 GENERATE LICENSE\n\nFormat: HWID|DAYS\nExample: RDZ-1234-5678-9ABC|30\nDays: 1, 30, 60",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back", callback_data="admin_dashboard")]
                ])
            )
            context.user_data['waiting_for'] = 'admin_gen_license'
            
        elif data == "admin_pending":
            if user_id not in ADMIN_IDS:
                await query.edit_message_text("⛔ Not authorized!")
                return
            
            db = load_db()
            pending = db.get("pending_payments", {})
            
            pending_list = [p for p in pending.values() if p.get("status") == "pending"]
            
            if not pending_list:
                await query.edit_message_text("No pending payments.")
                return
            
            text = "💰 PENDING PAYMENTS\n\n"
            for pid, data in pending.items():
                if data.get("status") == "pending":
                    text += f"ID: {pid}\nUser: {data.get('user_id', 0)}\nHWID: {data.get('hwid', '')}\nDays: {data.get('days', 0)}\nPrice: ${data.get('price', 0)}\n\n"
            
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back", callback_data="admin_dashboard")]
                ])
            )
            
        elif data == "admin_list":
            if user_id not in ADMIN_IDS:
                await query.edit_message_text("⛔ Not authorized!")
                return
            
            db = load_db()
            licenses = db["licenses"]
            
            if not licenses:
                await query.edit_message_text("No licenses found.")
                return
            
            text = "📋 ALL LICENSES\n\n"
            count = 0
            for hwid, data in list(licenses.items()):
                if count >= 20:
                    break
                info = get_license_info(hwid, db)
                if info:
                    status = "✅ Active" if info["is_valid"] else "❌ Expired"
                    text += f"HWID: {hwid}\nStatus: {status}\nDays Left: {info['days_left']}\nPlan: {info.get('days', 0)} days\n\n"
                count += 1
            
            if len(licenses) > 20:
                text += f"\n... and {len(licenses) - 20} more."
            
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back", callback_data="admin_dashboard")]
                ])
            )
            
        elif data == "admin_revoke":
            if user_id not in ADMIN_IDS:
                await query.edit_message_text("⛔ Not authorized!")
                return
            
            await query.edit_message_text(
                "❌ REVOKE LICENSE\n\nSend HWID to revoke.\nExample: RDZ-1234-5678-9ABC",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back", callback_data="admin_dashboard")]
                ])
            )
            context.user_data['waiting_for'] = 'admin_revoke_license'
            
        elif data == "admin_stats":
            if user_id not in ADMIN_IDS:
                await query.edit_message_text("⛔ Not authorized!")
                return
            
            db = load_db()
            licenses = db.get("licenses", {})
            users = db.get("users", {})
            pending = db.get("pending_payments", {})
            
            active = sum(1 for hwid, data in licenses.items() if get_license_info(hwid, db) and get_license_info(hwid, db)["is_valid"])
            expired = len(licenses) - active
            
            await query.edit_message_text(
                f"📊 STATS\n\nUsers: {len(users)}\nLicenses: {len(licenses)}\nActive: {active}\nExpired: {expired}\nPending: {len([p for p in pending.values() if p.get('status') == 'pending'])}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back", callback_data="admin_dashboard")]
                ])
            )
            
        # APPROVE/REJECT
        elif data.startswith("approve_payment_"):
            if user_id not in ADMIN_IDS:
                await query.edit_message_text("⛔ Not authorized!")
                return
            
            payment_id = data.replace("approve_payment_", "")
            db = load_db()
            
            if "pending_payments" not in db or payment_id not in db["pending_payments"]:
                await query.edit_message_text(f"❌ Payment not found!")
                return
            
            payment = db["pending_payments"][payment_id]
            hwid = payment["hwid"]
            days = payment["days"]
            user_id_pay = payment["user_id"]
            
            license_key = generate_license_key(hwid, days, user_id_pay)
            
            if "licenses" not in db:
                db["licenses"] = {}
            
            db["licenses"][hwid] = {
                "key": license_key,
                "user_id": user_id_pay,
                "purchased_at": time.time(),
                "days": days,
                "expiry": int(time.time()) + (days * 24 * 60 * 60)
            }
            
            payment["status"] = "completed"
            db["pending_payments"][payment_id] = payment
            save_db(db)
            
            expiry_timestamp = int(time.time()) + (days * 24 * 60 * 60)
            expiry_date = time.strftime("%d.%m.%Y %H:%M", time.localtime(expiry_timestamp))
            
            await query.edit_message_text(f"✅ PAYMENT APPROVED!\nHWID: {hwid}\nDays: {days}\nExpires: {expiry_date}\n\nLicense Key:\n{license_key}")
            
            try:
                await context.bot.send_message(
                    chat_id=user_id_pay,
                    text=f"✅ PAYMENT APPROVED!\n\nHWID: {hwid}\nPlan: {days} Days\nExpires: {expiry_date}\n\nYour License Key:\n{license_key}\n\nCreate zakpubgskin.txt and paste this key.\nPath: Android/data/com.tencent.ig/files/",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📦 Download PAK", callback_data="pak_files")],
                        [InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{CHANNEL_USERNAME}")]
                    ])
                )
            except:
                pass
            
        elif data.startswith("reject_payment_"):
            if user_id not in ADMIN_IDS:
                await query.edit_message_text("⛔ Not authorized!")
                return
            
            payment_id = data.replace("reject_payment_", "")
            db = load_db()
            
            if "pending_payments" not in db or payment_id not in db["pending_payments"]:
                await query.edit_message_text(f"❌ Payment not found!")
                return
            
            payment = db["pending_payments"][payment_id]
            user_id_pay = payment["user_id"]
            
            payment["status"] = "rejected"
            db["pending_payments"][payment_id] = payment
            save_db(db)
            
            await query.edit_message_text(f"❌ PAYMENT REJECTED!\nOrder: {payment_id}")
            
            try:
                await context.bot.send_message(
                    chat_id=user_id_pay,
                    text=f"❌ Payment Rejected!\n\nPlease check your payment and try again.\nContact @{OWNER_USERNAME} for support.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🛒 Try Again", callback_data="buy_key")]
                    ])
                )
            except:
                pass
            
        elif data == "back_main":
            await start(update, context)
            
    except Exception as e:
        logger.error(f"Button callback error: {e}")

# ==========================================
# MESSAGE HANDLER
# ==========================================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        db = load_db()
        
        # Screenshot
        if context.user_data.get('waiting_for') == 'screenshot':
            if update.message.photo:
                photo = update.message.photo[-1]
                file_id = photo.file_id
                
                db = load_db()
                payment_id = None
                for pid, data in db.get("pending_payments", {}).items():
                    if data.get("user_id") == user_id and data.get("status") == "pending":
                        payment_id = pid
                        break
                
                if not payment_id:
                    random.seed(user_id)
                    part1 = f"{random.randint(1000, 9999):04X}"
                    part2 = f"{random.randint(1000, 9999):04X}"
                    part3 = f"{random.randint(1000, 9999):04X}"
                    hwid = f"RDZ-{part1}-{part2}-{part3}"
                    
                    payment_id = f"PAY_{int(time.time())}_{user_id}"
                    db["pending_payments"][payment_id] = {
                        "user_id": user_id,
                        "hwid": hwid,
                        "days": 30,
                        "price": 8,
                        "timestamp": time.time(),
                        "status": "pending"
                    }
                    save_db(db)
                
                for admin_id in ADMIN_IDS:
                    try:
                        keyboard = [
                            [
                                InlineKeyboardButton("✅ APPROVE", callback_data=f"approve_payment_{payment_id}"),
                                InlineKeyboardButton("❌ REJECT", callback_data=f"reject_payment_{payment_id}")
                            ]
                        ]
                        
                        await context.bot.send_photo(
                            chat_id=admin_id,
                            photo=file_id,
                            caption=f"📸 Payment Screenshot!\n\nUser: @{update.effective_user.username or 'N/A'}\nID: {user_id}\nOrder: {payment_id}\nHWID: {db['pending_payments'][payment_id]['hwid']}\nDays: {db['pending_payments'][payment_id]['days']}\nPrice: ${db['pending_payments'][payment_id]['price']}",
                            reply_markup=InlineKeyboardMarkup(keyboard)
                        )
                    except:
                        pass
                
                await update.message.reply_text(
                    "✅ Screenshot Sent!\n\nAdmin will confirm shortly.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 Back", callback_data="back_main")]
                    ])
                )
                
                context.user_data['waiting_for'] = None
                return
            else:
                await update.message.reply_text("❌ Send a photo/screenshot!")
                return
        
        # Referral
        message_text = update.message.text or ""
        if message_text.startswith("REF") or message_text.startswith("ref"):
            ref_code = message_text.upper()
            db = load_db()
            
            for uid, data in db["users"].items():
                if data.get("referral_code") == ref_code:
                    referrer_id = int(uid)
                    if referrer_id != user_id:
                        if "referrals" not in db:
                            db["referrals"] = {}
                        
                        if str(user_id) not in db.get("referrals", {}):
                            db["referrals"][str(user_id)] = {"referred_by": referrer_id}
                            
                            db["users"][str(referrer_id)]["referral_count"] = db["users"][str(referrer_id)].get("referral_count", 0) + 1
                            new_count = db["users"][str(referrer_id)]["referral_count"]
                            
                            if new_count >= 3:
                                db["users"][str(referrer_id)]["referral_count"] = 0
                                
                                random.seed(referrer_id)
                                part1 = f"{random.randint(1000, 9999):04X}"
                                part2 = f"{random.randint(1000, 9999):04X}"
                                part3 = f"{random.randint(1000, 9999):04X}"
                                hwid = f"RDZ-{part1}-{part2}-{part3}"
                                
                                license_key = generate_license_key(hwid, 1, referrer_id)
                                
                                if "licenses" not in db:
                                    db["licenses"] = {}
                                
                                db["licenses"][hwid] = {
                                    "key": license_key,
                                    "user_id": referrer_id,
                                    "purchased_at": time.time(),
                                    "days": 1,
                                    "from_referral": True
                                }
                                
                                try:
                                    await context.bot.send_message(
                                        chat_id=referrer_id,
                                        text=f"🎉 CONGRATULATIONS! You got 1 DAY FREE LICENSE!\n\nHWID: {hwid}\nKey: {license_key}\n\nCreate zakpubgskin.txt and paste this key."
                                    )
                                except:
                                    pass
                            
                            save_db(db)
                            
                            await update.message.reply_text(f"✅ Referral Added!\nYou have {new_count}/3 referrals.")
                            break
            
            return
        
        # Admin commands
        waiting_for = context.user_data.get('waiting_for', '')
        
        if waiting_for == 'admin_gen_license':
            if user_id not in ADMIN_IDS:
                await update.message.reply_text("⛔ Not authorized!")
                return
            
            try:
                parts = message_text.split('|')
                if len(parts) != 2:
                    raise ValueError
                hwid = parts[0].strip().upper()
                days = int(parts[1].strip())
            except:
                await update.message.reply_text("❌ Invalid Format! Use: HWID|DAYS")
                return
            
            if days not in [1, 30, 60]:
                await update.message.reply_text("❌ Days must be 1, 30, or 60!")
                return
            
            hwid_clean = hwid.replace("-", "")
            if not hwid_clean.startswith("RDZ") or len(hwid_clean) < 15:
                await update.message.reply_text("❌ Invalid HWID!")
                return
            
            if len(hwid_clean) >= 15:
                hwid = f"RDZ-{hwid_clean[4:8]}-{hwid_clean[8:12]}-{hwid_clean[12:16]}"
            
            license_key = generate_license_key(hwid, days, user_id)
            
            if "licenses" not in db:
                db["licenses"] = {}
            
            db["licenses"][hwid] = {
                "key": license_key,
                "user_id": user_id,
                "purchased_at": time.time(),
                "days": days,
                "expiry": int(time.time()) + (days * 24 * 60 * 60)
            }
            save_db(db)
            
            expiry_timestamp = int(time.time()) + (days * 24 * 60 * 60)
            expiry_date = time.strftime("%d.%m.%Y %H:%M", time.localtime(expiry_timestamp))
            
            await update.message.reply_text(
                f"✅ LICENSE GENERATED!\n\nHWID: {hwid}\nDays: {days}\nExpires: {expiry_date}\n\nLicense Key:\n{license_key}"
            )
            
            context.user_data['waiting_for'] = None
            return
        
        if waiting_for == 'admin_revoke_license':
            if user_id not in ADMIN_IDS:
                await update.message.reply_text("⛔ Not authorized!")
                return
            
            hwid = message_text.strip().upper()
            hwid_clean = hwid.replace("-", "")
            
            if len(hwid_clean) >= 15:
                hwid = f"RDZ-{hwid_clean[4:8]}-{hwid_clean[8:12]}-{hwid_clean[12:16]}"
            
            db = load_db()
            if hwid in db["licenses"]:
                del db["licenses"][hwid]
                save_db(db)
                await update.message.reply_text(f"✅ LICENSE REVOKED!\nHWID: {hwid}")
            else:
                await update.message.reply_text(f"❌ License Not Found!\nHWID: {hwid}")
            
            context.user_data['waiting_for'] = None
            return
        
        await update.message.reply_text("❓ Unknown command. Type /start")
        
    except Exception as e:
        logger.error(f"Message handler error: {e}")

async def hwid_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        
        random.seed(user_id)
        hwid = f"RDZ-{random.randint(1000, 9999):04X}-{random.randint(1000, 9999):04X}-{random.randint(1000, 9999):04X}"
        
        await update.message.reply_text(
            f"🔑 YOUR HWID:\n\n{hwid}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🛒 Buy Key", callback_data="buy_key")]
            ])
        )
    except:
        pass

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if 'waiting_for' in context.user_data:
            context.user_data['waiting_for'] = None
            await update.message.reply_text("✅ Cancelled.")
        else:
            await update.message.reply_text("❌ No active operation.")
    except:
        pass

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        logger.error(f"Error: {context.error}")
        if update and update.effective_message:
            await update.effective_message.reply_text("❌ Error! Please try again.")
    except:
        pass

# ==========================================
# MAIN
# ==========================================
def main():
    global application
    
    print("\n" + "="*50)
    print("    ZAK PUBG SKIN - DEPLOYED BOT")
    print("="*50)
    print(f"📌 Token: {TOKEN[:20]}...")
    print(f"👤 Admins: {ADMIN_IDS}")
    print(f"💰 Prices: $1, $8, $12")
    print("="*50 + "\n")
    
    if TOKEN == "8921411956:AAFisybXC...":
        print("⚠️ WARNING: Update your bot token!")
        return
    
    try:
        application = Application.builder().token(TOKEN).connect_timeout(30.0).read_timeout(30.0).build()
        
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("hwid", hwid_command))
        application.add_handler(CommandHandler("cancel", cancel_command))
        application.add_handler(CallbackQueryHandler(button_callback))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        application.add_handler(MessageHandler(filters.PHOTO, handle_message))
        application.add_error_handler(error_handler)
        
        print("🤖 Bot is running...")
        print("📱 Type /start in Telegram")
        print("🛑 Press CTRL+C to stop")
        print("="*50 + "\n")
        
        application.run_polling(timeout=60)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()    conn.commit()
    conn.close()

init_db()

# ========== HASH FUNCTION (Same as Lua) ==========
def custom_hash(text):
    """DJB2 Hash - Lua script se match karna chahiye"""
    hash_val = 5381
    for char in text:
        hash_val = (hash_val * 33 + ord(char)) % 4294967296
    return f"{hash_val:08X}"

def generate_key(hwid, days=30):
    """Generate key for given HWID"""
    expiry = int(time.time()) + (days * 86400)
    raw = f"{hwid}{expiry}{SECRET}"
    signature = custom_hash(raw)
    return f"{signature}|{expiry}"

def verify_key(key, hwid):
    """Verify if key is valid for given HWID"""
    try:
        signature, expiry = key.split('|')
        expiry = int(expiry)
        
        # Check expiry
        if time.time() > expiry:
            return False, "Key expired!"
        
        # Recalculate hash
        raw = f"{hwid}{expiry}{SECRET}"
        expected = custom_hash(raw)
        
        if signature == expected:
            return True, "Key valid!"
        else:
            return False, "Invalid key for this HWID!"
    except:
        return False, "Invalid key format!"

# ========== BOT COMMANDS ==========

# ---- /start ----
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # Register user
    conn = sqlite3.connect('redzone_keys.db')
    c = conn.cursor()
    c.execute('''INSERT OR IGNORE INTO users (id, username, first_name, last_name, registered_at)
                 VALUES (?, ?, ?, ?, ?)''',
              (user.id, user.username, user.first_name, user.last_name, int(time.time())))
    conn.commit()
    conn.close()
    
    keyboard = [
        [InlineKeyboardButton("📋 My HWID", callback_data='my_hwid')],
        [InlineKeyboardButton("🔑 Activate Key", callback_data='activate')],
        [InlineKeyboardButton("📊 Check Key Status", callback_data='check')],
    ]
    
    if user.id in ADMIN_IDS:
        keyboard.append([InlineKeyboardButton("⚙️ Admin Panel", callback_data='admin')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"👋 Welcome {user.first_name}!\n\n"
        f"🔹 **RedZone License System**\n"
        f"🔹 Your ID: `{user.id}`\n\n"
        f"Use the buttons below to manage your license.",
        reply_markup=reply_markup
    )

# ---- /hwid - Get HWID ----
async def get_hwid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    hwid = f"RDZ-{user.id:04X}-{int(time.time()):04X}-{user.id:04X}"
    
    # Save HWID
    conn = sqlite3.connect('redzone_keys.db')
    c = conn.cursor()
    c.execute('UPDATE users SET hwid = ? WHERE id = ?', (hwid, user.id))
    conn.commit()
    conn.close()
    
    keyboard = [[InlineKeyboardButton("🔑 Generate Key", callback_data='genkey')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"🆔 **Your HWID:**\n"
        f"`{hwid}`\n\n"
        f"⚠️ Send this HWID to admin to get your key!",
        reply_markup=reply_markup
    )

# ---- /genkey (Admin only) ----
async def genkey(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ You are not authorized!")
        return
    
    try:
        # Usage: /genkey HWID days
        args = context.args
        if len(args) < 1:
            await update.message.reply_text(
                "❌ Usage: `/genkey HWID [days]`\n"
                "Example: `/genkey RDZ-1234-5678-9ABC 30`"
            )
            return
        
        hwid = args[0]
        days = int(args[1]) if len(args) > 1 else 30
        
        # Generate key
        key = generate_key(hwid, days)
        expiry = int(key.split('|')[1])
        
        # Save to database
        conn = sqlite3.connect('redzone_keys.db')
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO keys (hwid, key, expiry, created_by, created_at)
                     VALUES (?, ?, ?, ?, ?)''',
                  (hwid, key, expiry, user.id, int(time.time())))
        conn.commit()
        conn.close()
        
        # Show key
        await update.message.reply_text(
            f"✅ **Key Generated Successfully!**\n\n"
            f"🔑 `{key}`\n\n"
            f"📅 Valid for: {days} days\n"
            f"📅 Expires: {datetime.fromtimestamp(expiry).strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"🆔 HWID: `{hwid}`\n\n"
            f"Send this key to the user!"
        )
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

# ---- /activate (User) ----
async def activate_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # Check if user has HWID
    conn = sqlite3.connect('redzone_keys.db')
    c = conn.cursor()
    c.execute('SELECT hwid FROM users WHERE id = ?', (user.id,))
    result = c.fetchone()
    
    if not result or not result[0]:
        await update.message.reply_text(
            "❌ You don't have HWID yet!\n"
            "Use /hwid first."
        )
        conn.close()
        return
    
    hwid = result[0]
    conn.close()
    
    # Ask for key
    context.user_data['awaiting_key'] = True
    await update.message.reply_text(
        f"🔑 **Enter your license key:**\n\n"
        f"Format: `XXXXXXXX|1234567890`\n"
        f"HWID: `{hwid}`\n\n"
        f"Type your key here or paste it."
    )

# ---- Handle key input ----
async def handle_key_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('awaiting_key'):
        return
    
    user = update.effective_user
    key = update.message.text.strip()
    context.user_data['awaiting_key'] = False
    
    # Get user HWID
    conn = sqlite3.connect('redzone_keys.db')
    c = conn.cursor()
    c.execute('SELECT hwid FROM users WHERE id = ?', (user.id,))
    result = c.fetchone()
    
    if not result or not result[0]:
        await update.message.reply_text("❌ HWID not found! Use /hwid")
        conn.close()
        return
    
    hwid = result[0]
    
    # Verify key
    valid, msg = verify_key(key, hwid)
    
    if valid:
        # Check if key exists in database
        c.execute('SELECT * FROM keys WHERE key = ?', (key,))
        db_result = c.fetchone()
        
        if not db_result:
            await update.message.reply_text("❌ Key not found in database!")
            conn.close()
            return
        
        # Mark as used
        c.execute('UPDATE keys SET used = 1, user_id = ? WHERE key = ?', (user.id, key))
        conn.commit()
        
        await update.message.reply_text(
            f"✅ **Key Activated Successfully!**\n\n"
            f"🔑 `{key}`\n\n"
            f"🎮 You can now use RedZone VIP!\n"
            f"📅 Valid until: {datetime.fromtimestamp(int(key.split('|')[1])).strftime('%Y-%m-%d %H:%M:%S')}"
        )
    else:
        await update.message.reply_text(f"❌ {msg}")
    
    conn.close()

# ---- Admin Panel ----
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ You are not authorized!")
        return
    
    keyboard = [
        [InlineKeyboardButton("📊 Stats", callback_data='admin_stats')],
        [InlineKeyboardButton("🔑 Generate Key", callback_data='admin_genkey')],
        [InlineKeyboardButton("📋 List Keys", callback_data='admin_list')],
        [InlineKeyboardButton("👥 Users", callback_data='admin_users')],
        [InlineKeyboardButton("🔙 Back", callback_data='back')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "⚙️ **Admin Panel**\n\n"
        "Select an option:",
        reply_markup=reply_markup
    )

# ---- Button Callbacks ----
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    data = query.data
    
    if data == 'my_hwid':
        conn = sqlite3.connect('redzone_keys.db')
        c = conn.cursor()
        c.execute('SELECT hwid FROM users WHERE id = ?', (user.id,))
        result = c.fetchone()
        conn.close()
        
        if result and result[0]:
            await query.edit_message_text(
                f"🆔 **Your HWID:**\n"
                f"`{result[0]}`\n\n"
                f"Send this to admin to get your key."
            )
        else:
            await query.edit_message_text(
                "❌ You don't have HWID yet!\n"
                "Use /hwid command to generate."
            )
    
    elif data == 'activate':
        await activate_key(update, context)
        await query.delete_message()
    
    elif data == 'check':
        conn = sqlite3.connect('redzone_keys.db')
        c = conn.cursor()
        c.execute('''SELECT key, expiry, used FROM keys 
                     WHERE user_id = ? ORDER BY created_at DESC LIMIT 1''', (user.id,))
        result = c.fetchone()
        conn.close()
        
        if result:
            key, expiry, used = result
            status = "✅ Active" if used and time.time() < expiry else "❌ Expired/Inactive"
            
            await query.edit_message_text(
                f"📊 **Key Status**\n\n"
                f"🔑 Key: `{key}`\n"
                f"📅 Expiry: {datetime.fromtimestamp(expiry).strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"📌 Status: {status}"
            )
        else:
            await query.edit_message_text(
                "❌ No key found for your account!"
            )
    
    elif data == 'admin':
        await admin_panel(update, context)
        await query.delete_message()
    
    elif data == 'back':
        await start(update, context)
        await query.delete_message()
    
    elif data == 'admin_stats':
        conn = sqlite3.connect('redzone_keys.db')
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM keys')
        total_keys = c.fetchone()[0]
        c.execute('SELECT COUNT(*) FROM keys WHERE used = 1')
        used_keys = c.fetchone()[0]
        c.execute('SELECT COUNT(*) FROM users')
        total_users = c.fetchone()[0]
        conn.close()
        
        await query.edit_message_text(
            f"📊 **Statistics**\n\n"
            f"👥 Total Users: {total_users}\n"
            f"🔑 Total Keys: {total_keys}\n"
            f"✅ Used Keys: {used_keys}\n"
            f"🔄 Available: {total_keys - used_keys}\n\n"
            f"📅 Last update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
    
    elif data == 'admin_genkey':
        await query.edit_message_text(
            "🔑 **Generate Key**\n\n"
            "Use command:\n"
            "`/genkey HWID days`\n\n"
            "Example: `/genkey RDZ-1234-5678-9ABC 30`"
        )
    
    elif data == 'admin_list':
        conn = sqlite3.connect('redzone_keys.db')
        c = conn.cursor()
        c.execute('SELECT hwid, key, expiry, used FROM keys ORDER BY created_at DESC LIMIT 10')
        results = c.fetchall()
        conn.close()
        
        if results:
            msg = "📋 **Recent Keys:**\n\n"
            for hwid, key, expiry, used in results:
                status = "✅" if used else "⏳"
                msg += f"{status} HWID: `{hwid[:15]}...`\n"
                msg += f"   Key: `{key}`\n"
                msg += f"   Expiry: {datetime.fromtimestamp(expiry).strftime('%Y-%m-%d')}\n\n"
            
            await query.edit_message_text(msg)
        else:
            await query.edit_message_text("No keys found!")

# ========== MAIN ==========
def main():
    # Create application
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("hwid", get_hwid))
    app.add_handler(CommandHandler("genkey", genkey))
    app.add_handler(CommandHandler("activate", activate_key))
    app.add_handler(CommandHandler("admin", admin_panel))
    
    # Message handler for key input
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_key_input))
    
    # Callback query handler
    app.add_handler(CallbackQueryHandler(button_callback))
    
    # Start bot
    print("🤖 Bot started! Press Ctrl+C to stop.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()KEY_EXPIRY_DAYS = int(os.environ.get('KEY_EXPIRY_DAYS', '1'))
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
