# ZAK PUBG SKIN VIP BOT

Telegram bot for managing PUBG Mobile VIP licenses.

## Features

- 🔑 Generate HWID
- 🛒 Buy License (1/30/60 days)
- 📦 Download PAK Files
- 👥 Referral System (3 = Free Key)
- 💳 Payment Screenshot System
- 👑 Admin Dashboard
- ✅ Approve/Reject Payments
- 📊 Statistics

## Deploy to Railway

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template)

## Environment Variables

| Variable | Description |
|----------|-------------|
| BOT_TOKEN | Your Telegram Bot Token |
| ADMIN_IDS | Admin IDs (comma separated) |
| SECRET_KEY | License generation secret |
| CHANNEL | Channel username |
| OWNER | Owner username |
| PRICE_1 | 1 Day Price |
| PRICE_30 | 30 Day Price |
| PRICE_60 | 60 Day Price |

## Commands

- `/start` - Main menu
- `/hwid` - Generate HWID
- `/cancel` - Cancel operation
