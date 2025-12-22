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
    filters,
    ApplicationHandlerStop
)
from telegram.error import TelegramError

# Pyrogram imports
try:
    from pyrogram import Client
    from pyrogram.errors import FloodWait, SessionPasswordNeeded
    PYROGRAM_AVAILABLE = True
except ImportError:
    PYROGRAM_AVAILABLE = False

logger = logging.getLogger(__name__)

# Folder and File Setup
SESSION_DIR = "sessions"
DATA_DIR = "data"
SESSION_FILE = os.path.join(DATA_DIR, "user_sessions.pkl")

# Auto-create folders on startup
os.makedirs(SESSION_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

# ============================================
# Session Management
# ============================================

def load_sessions():
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, 'rb') as f: return pickle.load(f)
        except: return {}
    return {}

def save_sessions(sessions):
    with open(SESSION_FILE, 'wb') as f: pickle.dump(sessions, f)

def get_session_name(user_id: int, chat_id: int) -> str:
    return f"user_{user_id}_chat_{chat_id}"

# ============================================
# Pyrogram Scanner Core
# ============================================

async def pyrogram_scan_deleted_accounts(api_id, api_hash, session_name, chat_id, phone, progress_callback=None):
    if not PYROGRAM_AVAILABLE: return {'error': 'Pyrogram not installed'}
    
    results = {'total': 0, 'deleted': 0, 'removed': 0, 'errors': 0}
    try:
        app = Client(session_name, api_id=api_id, api_hash=api_hash, phone_number=phone, workdir=SESSION_DIR)
        async with app:
            async for member in app.get_chat_members(chat_id):
                results['total'] += 1
                user = member.user
                
                # Identify Deleted Accounts
                is_deleted = False
                if not user.first_name or user.first_name == "Deleted Account" or getattr(user, 'is_deleted', False):
                    is_deleted = True
                
                if is_deleted:
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
# Logic Handlers (Phone, OTP, Password)
# ============================================

async def deleted_account_message_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sari incoming text messages ko monitor karta hai (Group Priority Fix)"""
    if update.effective_chat.type != "private":
        return

    is_handled = False
    if context.user_data.get('awaiting_phone'):
        await handle_phone_number(update, context)
        is_handled = True
    elif context.user_data.get('awaiting_otp'):
        await handle_otp_code(update, context)
        is_handled = True
    elif context.user_data.get('awaiting_password'):
        await handle_password(update, context)
        is_handled = True

    if is_handled:
        # Isse ye message Spam Model ke paas nahi jayega
        raise ApplicationHandlerStop()

async def scan_deleted_accounts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat, user = update.effective_chat, update.effective_user
    
    # Admin verification
    try:
        member = await chat.get_member(user.id)
        if member.status not in ['creator', 'administrator']:
            return await update.message.reply_text("❌ Ye command sirf admins ke liye hai!")
    except: return

    sessions = load_sessions()
    session_key = f"{user.id}_{chat.id}"
    session_name = get_session_name(user.id, chat.id)

    if session_key not in sessions:
        try:
            await context.bot.send_message(
                chat_id=user.id,
                text=f"📌 **Group: {chat.title}**\nSetup ke liye apna phone number bhejein (+countrycode ke saath):"
            )
            context.user_data['awaiting_phone'] = True
            context.user_data['scan_chat_id'] = chat.id
            await update.message.reply_text("📱 Maine aapko Private Message bheja hai setup ke liye.")
        except:
            await update.message.reply_text("❌ Pehle mujhe Private mein /start karein taaki main aapko message bhej saku!")
        return

    await start_scan(update, context, session_name, sessions[session_key])

async def handle_phone_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.text.strip()
    session_name = get_session_name(update.effective_user.id, context.user_data['scan_chat_id'])
    
    try:
        app = Client(session_name, config.PYROGRAM_API_ID, config.PYROGRAM_API_HASH, phone_number=phone, workdir=SESSION_DIR)
        await app.connect()
        sent_code = await app.send_code(phone)
        
        context.user_data.update({
            'phone': phone, 
            'pyrogram_app': app, 
            'phone_code_hash': sent_code.phone_code_hash, 
            'awaiting_phone': False, 
            'awaiting_otp': True
        })
        await update.message.reply_text("📨 Telegram se aaya hua OTP code yahan bhejein:")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def handle_otp_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    otp = update.message.text.strip()
    app = context.user_data.get('pyrogram_app')
    phone = context.user_data.get('phone')
    phone_hash = context.user_data.get('phone_code_hash')
    
    try:
        await app.sign_in(phone, phone_hash, otp)
        await finalize_setup(update, context)
    except SessionPasswordNeeded:
        context.user_data['awaiting_otp'] = False
        context.user_data['awaiting_password'] = True
        await update.message.reply_text("🔐 **2-Step Verification Password** bhejein:")
    except Exception as e:
        await update.message.reply_text(f"❌ OTP Error: {e}")

async def handle_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    password = update.message.text.strip()
    app = context.user_data.get('pyrogram_app')
    try:
        await app.check_password(password)
        await finalize_setup(update, context)
    except Exception as e:
        await update.message.reply_text(f"❌ Password Galat: {e}\nDobara koshish karein:")

async def finalize_setup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    app = context.user_data.get('pyrogram_app')
    await app.disconnect()
    
    sessions = load_sessions()
    sessions[f"{update.effective_user.id}_{context.user_data['scan_chat_id']}"] = context.user_data['phone']
    save_sessions(sessions)
    
    context.user_data.update({'awaiting_otp': False, 'awaiting_password': False})
    await update.message.reply_text("✅ Setup successful! Ab group mein `/scandeleted` likhein.")

async def start_scan(update: Update, context: ContextTypes.DEFAULT_TYPE, session_name, phone):
    msg = await update.message.reply_text("🔍 **Scan start ho raha hai...**")
    async def prog(m):
        try: await msg.edit_text(f"🔍 **Scanning...**\n{m}")
        except: pass

    res = await pyrogram_scan_deleted_accounts(config.PYROGRAM_API_ID, config.PYROGRAM_API_HASH, session_name, update.effective_chat.id, phone, prog)
    
    if 'error' in res:
        await msg.edit_text(f"❌ Scan failed: {res['error']}")
    else:
        await msg.edit_text(f"✅ **Scan Complete!**\n\n• Members: {res['total']}\n• Deleted: {res['deleted']}\n• Removed: {res['removed']}")

async def reset_session(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sessions = load_sessions()
    key = f"{update.effective_user.id}_{update.effective_chat.id}"
    if key in sessions:
        del sessions[key]
        save_sessions(sessions)
        await update.message.reply_text("✅ Session reset!")

def register_deleted_account_handlers(app):
    app.add_handler(CommandHandler("scandeleted", scan_deleted_accounts))
    app.add_handler(CommandHandler("resetsession", reset_session))
    
    # Priority group -1 ensures this blocks the ML spam model in Private chats
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, 
        deleted_account_message_router
    ), group=-1)
