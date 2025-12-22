import logging
import asyncio
import os
import pickle
from typing import Optional
import config
from telegram import Update
from telegram.ext import (
    ContextTypes, 
    CommandHandler, 
    MessageHandler, 
    filters
)
from telegram.error import TelegramError

# Pyrogram imports
try:
    from pyrogram import Client
    from pyrogram.errors import FloodWait
    PYROGRAM_AVAILABLE = True
except ImportError:
    PYROGRAM_AVAILABLE = False
    print("⚠️ Pyrogram not installed. Install with: pip install pyrogram tgcrypto")

logger = logging.getLogger(__name__)

SESSION_FILE = "data/user_sessions.pkl"

# ============================================
# Session Management
# ============================================

def load_sessions():
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, 'rb') as f:
                return pickle.load(f)
        except: return {}
    return {}

def save_sessions(sessions):
    os.makedirs(os.path.dirname(SESSION_FILE), exist_ok=True)
    with open(SESSION_FILE, 'wb') as f:
        pickle.dump(sessions, f)

def get_session_name(user_id: int, chat_id: int) -> str:
    return f"sessions/user_{user_id}_chat_{chat_id}"

# ============================================
# Pyrogram Scanner Logic
# ============================================

async def pyrogram_scan_deleted_accounts(api_id, api_hash, session_name, chat_id, phone, progress_callback=None):
    if not PYROGRAM_AVAILABLE: return {'error': 'Pyrogram not installed'}
    
    results = {'total': 0, 'deleted': 0, 'removed': 0, 'errors': 0}
    try:
        app = Client(session_name, api_id=api_id, api_hash=api_hash, phone_number=phone, workdir="sessions")
        async with app:
            async for member in app.get_chat_members(chat_id):
                results['total'] += 1
                user = member.user
                if user.first_name == "Deleted Account" or (hasattr(user, 'is_deleted') and user.is_deleted):
                    results['deleted'] += 1
                    try:
                        await app.ban_chat_member(chat_id, user.id)
                        await app.unban_chat_member(chat_id, user.id)
                        results['removed'] += 1
                    except FloodWait as e:
                        await asyncio.sleep(e.value)
                    except Exception: results['errors'] += 1
                
                if results['total'] % 50 == 0 and progress_callback:
                    await progress_callback(f"📊 Scanned: {results['total']} | Found: {results['deleted']}")
                await asyncio.sleep(0.1)
        return results
    except Exception as e:
        return {'error': str(e)}

# ============================================
# Message Router (Crucial Fix)
# ============================================

async def deleted_account_message_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ye decide karta hai ki input phone number hai ya OTP"""
    if context.user_data.get('awaiting_phone'):
        await handle_phone_number(update, context)
    elif context.user_data.get('awaiting_otp'):
        await handle_otp_code(update, context)

# ============================================
# Handlers
# ============================================

async def scan_deleted_accounts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat, user = update.effective_chat, update.effective_user
    
    # Credentials check
    api_id = context.bot_data.get('PYROGRAM_API_ID')
    api_hash = context.bot_data.get('PYROGRAM_API_HASH')
    
    if not api_id or not api_hash:
        await update.message.reply_text("❌ API credentials missing in config.py!")
        return

    # Admin check
    member = await chat.get_member(user.id)
    if member.status not in ['creator', 'administrator']:
        return await update.message.reply_text("❌ Admins only!")

    sessions = load_sessions()
    session_key = f"{user.id}_{chat.id}"
    session_name = get_session_name(user.id, chat.id)

    if session_key not in sessions:
        await update.message.reply_text("📱 Phone number bhejo (Example: +919876543210):")
        context.user_data['awaiting_phone'] = True
        context.user_data['scan_chat_id'] = chat.id
        return

    await start_scan(update, context, session_name, sessions[session_key])

async def handle_phone_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.text.strip()
    if not phone.startswith('+'):
        return await update.message.reply_text("❌ Invalid format! Use +countrycode")

    session_name = get_session_name(update.effective_user.id, context.user_data['scan_chat_id'])
    try:
        app = Client(session_name, config.PYROGRAM_API_ID, config.PYROGRAM_API_HASH, phone_number=phone, workdir="sessions")
        await app.connect()
        sent_code = await app.send_code(phone)
        context.user_data.update({'phone': phone, 'session_name': session_name, 'pyrogram_app': app, 'phone_code_hash': sent_code.phone_code_hash, 'awaiting_phone': False, 'awaiting_otp': True})
        await update.message.reply_text("📨 OTP bhejo (Example: 12345):")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def handle_otp_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    otp = update.message.text.strip()
    app, phone = context.user_data['pyrogram_app'], context.user_data['phone']
    try:
        await app.sign_in(phone, context.user_data['phone_code_hash'], otp)
        await app.disconnect()
        sessions = load_sessions()
        sessions[f"{update.effective_user.id}_{context.user_data['scan_chat_id']}"] = phone
        save_sessions(sessions)
        context.user_data['awaiting_otp'] = False
        await update.message.reply_text("✅ Setup Complete! Use /scandeleted again.")
    except Exception as e:
        await update.message.reply_text(f"❌ OTP Error: {e}")

async def start_scan(update: Update, context: ContextTypes.DEFAULT_TYPE, session_name, phone):
    msg = await update.message.reply_text("🔍 Scanning...")
    async def prog(m): await msg.edit_text(f"🔍 {m}")
    
    res = await pyrogram_scan_deleted_accounts(config.PYROGRAM_API_ID, config.PYROGRAM_API_HASH, session_name, update.effective_chat.id, phone, prog)
    
    if 'error' in res: await msg.edit_text(f"❌ Error: {res['error']}")
    else: await msg.edit_text(f"✅ Done!\nFound: {res['deleted']}\nRemoved: {res['removed']}")

async def reset_session(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sessions = load_sessions()
    key = f"{update.effective_user.id}_{update.effective_chat.id}"
    if key in sessions:
        del sessions[key]
        save_sessions(sessions)
        await update.message.reply_text("✅ Session Reset!")

def register_deleted_account_handlers(app):
    # API credentials setup
    app.bot_data['PYROGRAM_API_ID'] = config.PYROGRAM_API_ID
    app.bot_data['PYROGRAM_API_HASH'] = config.PYROGRAM_API_HASH
    
    app.add_handler(CommandHandler("scandeleted", scan_deleted_accounts))
    app.add_handler(CommandHandler("resetsession", reset_session))
    
    # Priority handling using 'group=-1'
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE,
        deleted_account_message_router
    ), group=-1)
