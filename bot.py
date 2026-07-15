import time
import logging
import os
import json
import random
import sys
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

# ==========================================
# CONFIGURATION - ENVIRONMENT VARIABLES
# ==========================================
TOKEN = os.environ.get("8603563956:AAG6O02ZTMVNqDM9u-Mrc3EkwYqgR-_rHNw", "")
ADMIN_IDS = [int(id.strip()) for id in os.environ.get("ADMIN_IDS", "5130475597,5130475597").split(",") if id.strip()]

# Database file
DB_FILE = "licenses.json"

# SECRET KEY
SECRET_KEY = os.environ.get("SECRET_KEY", "ZakPubgSkin_VIP_2026_Ultimate!")
CHANNEL_USERNAME = os.environ.get("CHANNEL", "zakpubgskin")
OWNER_USERNAME = os.environ.get("OWNER", "zakarya_op")

# Pricing
PRICES = {
    "1": int(os.environ.get("PRICE_1", "1")),
    "30": int(os.environ.get("PRICE_30", "8")),
    "60": int(os.environ.get("PRICE_60", "12"))
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
🟢 1 Day  - ${PRICES['1']}
🔵 30 Days - ${PRICES['30']}
🔴 60 Days - ${PRICES['60']}

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
                [InlineKeyboardButton(f"🟢 1 Day - ${PRICES['1']}", callback_data="buy_1")],
                [InlineKeyboardButton(f"🔵 30 Days - ${PRICES['30']}", callback_data="buy_30")],
                [InlineKeyboardButton(f"🔴 60 Days - ${PRICES['60']}", callback_data="buy_60")],
                [InlineKeyboardButton("🔙 Back", callback_data="back_main")]
            ]
            await query.edit_message_text(
                "💎 SELECT YOUR PLAN\n\nChoose your VIP duration:",
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
            
            active = 0
            for hwid, data in licenses.items():
                info = get_license_info(hwid, db)
                if info and info["is_valid"]:
                    active += 1
            expired = len(licenses) - active
            
            await query.edit_message_text(
                f"📊 STATS\n\nUsers: {len(users)}\nLicenses: {len(licenses)}\nActive: {active}\nExpired: {expired}\nPending: {len([p for p in pending.values() if p.get('status') == 'pending'])}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back", callback_data="admin_dashboard")]
                ])
            )
            
        # APPROVE/REJECT PAYMENTS
        elif data.startswith("approve_payment_"):
            if user_id not in ADMIN_IDS:
                await query.edit_message_text("⛔ Not authorized!")
                return
            
            payment_id = data.replace("approve_payment_", "")
            db = load_db()
            
            if "pending_payments" not in db or payment_id not in db["pending_payments"]:
                await query.edit_message_text("❌ Payment not found!")
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
                await query.edit_message_text("❌ Payment not found!")
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
            
        elif data == "admin_sep":
            pass
            
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
    print("\n" + "="*50)
    print("    ZAK PUBG SKIN - DEPLOYED ON RAILWAY")
    print("="*50)
    print(f"📌 Bot Token: {TOKEN[:20] if TOKEN else 'NOT SET'}...")
    print(f"👤 Admins: {ADMIN_IDS}")
    print("="*50 + "\n")
    
    if not TOKEN:
        print("⚠️ ERROR: BOT_TOKEN environment variable not set!")
        print("Please set BOT_TOKEN in Railway environment variables.")
        sys.exit(1)
    
    try:
        application = Application.builder().token(TOKEN).connect_timeout(30.0).read_timeout(30.0).build()
        
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("hwid", hwid_command))
        application.add_handler(CommandHandler("cancel", cancel_command))
        application.add_handler(CallbackQueryHandler(button_callback))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        application.add_handler(MessageHandler(filters.PHOTO, handle_message))
        application.add_error_handler(error_handler)
        
        print("🤖 Bot is running on Railway...")
        print("📱 Type /start in Telegram")
        print("="*50 + "\n")
        
        application.run_polling(timeout=60)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
