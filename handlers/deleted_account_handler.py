import logging
import asyncio
import os
import pickle
import config
from telegram import Update
from telegram.ext import (
    ContextTypes, CommandHandler, MessageHandler, filters, ApplicationHandlerStop
)

# Telethon imports
try:
    from telethon import TelegramClient
    from telethon.errors import SessionPasswordNeededError, PhoneCodeExpiredError, PhoneCodeInvalidError
    TELETHON_AVAILABLE = True
except ImportError:
    TELETHON_AVAILABLE = False
    print("⚠️ Telethon not installed. Install with: pip install telethon")

logger = logging.getLogger(__name__)

SESSION_DIR = "sessions"
DATA_DIR = "data"
SESSION_FILE = os.path.join(DATA_DIR, "user_sessions.pkl")

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

def get_session_path(user_id, chat_id):
    return os.path.join(SESSION_DIR, f"tele_user_{user_id}_{chat_id}")

async def cleanup_client(context: ContextTypes.DEFAULT_TYPE):
    client = context.user_data.get('tele_client')
    if client:
        try: await client.disconnect()
        except: pass
    context.user_data.pop('tele_client', None)

# ============================================
# Telethon Scanner Logic
# ============================================

async def telethon_scan_deleted_accounts(api_id, api_hash, session_path, chat_id, progress_callback=None):
    results = {'total': 0, 'deleted': 0, 'removed': 0, 'errors': 0}
    client = TelegramClient(session_path, api_id, api_hash)
    
    try:
        await client.connect()
        async for user in client.iter_participants(chat_id):
            results['total'] += 1
            if user.deleted:
                results['deleted'] += 1
                try:
                    # Kicking deleted accounts
                    await client.edit_permissions(chat_id, user.id, view_messages=False)
                    results['removed'] += 1
                except: results['errors'] += 1
            
            if results['total'] % 50 == 0 and progress_callback:
                await progress_callback(f"📊 Scanned: {results['total']} | Deleted: {results['deleted']}")
        return results
    finally:
        await client.disconnect()

# ============================================
# Handlers
# ============================================

async def deleted_account_message_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private": return
    
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

    if is_handled: raise ApplicationHandlerStop()

async def scan_deleted_accounts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat, user = update.effective_chat, update.effective_user
    sessions = load_sessions()
    session_key = f"{user.id}_{chat.id}"
    session_path = get_session_path(user.id, chat.id)

    if session_key not in sessions:
        await context.bot.send_message(chat_id=user.id, text=f"📌 Setup for **{chat.title}**\nSend phone number (+countrycode):")
        context.user_data.update({'awaiting_phone': True, 'scan_chat_id': chat.id})
        return

    await start_scan(update, context, session_path)

async def handle_phone_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.text.strip()
    session_path = get_session_path(update.effective_user.id, context.user_data['scan_chat_id'])
    
    await cleanup_client(context)
    client = TelegramClient(session_path, config.PYROGRAM_API_ID, config.PYROGRAM_API_HASH)
    
    try:
        await client.connect()
        # Requesting code
        sent = await client.send_code_request(phone)
        context.user_data.update({
            'tele_client': client, 'phone': phone, 
            'phone_hash': sent.phone_code_hash,
            'awaiting_phone': False, 'awaiting_otp': True
        })
        await update.message.reply_text("📨 Enter OTP code:")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def handle_otp_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    otp = update.message.text.strip().replace(" ", "")
    client = context.user_data.get('tele_client')
    
    try:
        await client.sign_in(context.user_data['phone'], otp, phone_code_hash=context.user_data['phone_hash'])
        await finalize_setup(update, context)
    except SessionPasswordNeededError:
        context.user_data.update({'awaiting_otp': False, 'awaiting_password': True})
        await update.message.reply_text("🔐 2FA Password required:")
    except PhoneCodeExpiredError:
        await update.message.reply_text("❌ OTP Expired! Send number again:")
        context.user_data['awaiting_phone'] = True
    except Exception as e:
        await update.message.reply_text(f"❌ OTP Error: {e}")

async def handle_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    password = update.message.text.strip()
    client = context.user_data.get('tele_client')
    try:
        await client.sign_in(password=password)
        await finalize_setup(update, context)
    except Exception as e:
        await update.message.reply_text(f"❌ Wrong Password: {e}")

async def finalize_setup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await cleanup_client(context)
    sessions = load_sessions()
    sessions[f"{update.effective_user.id}_{context.user_data['scan_chat_id']}"] = context.user_data['phone']
    save_sessions(sessions)
    context.user_data.update({'awaiting_otp': False, 'awaiting_password': False})
    await update.message.reply_text("✅ Setup done! Run /scandeleted in group.")

async def start_scan(update: Update, context: ContextTypes.DEFAULT_TYPE, session_path):
    msg = await update.message.reply_text("🔍 Scanning with Telethon...")
    async def prog(m): 
        try: await msg.edit_text(f"🔍 {m}")
        except: pass
    
    res = await telethon_scan_deleted_accounts(config.PYROGRAM_API_ID, config.PYROGRAM_API_HASH, session_path, update.effective_chat.id, prog)
    await msg.edit_text(f"✅ **Scan Done!**\nTotal: {res['total']}\nDeleted: {res['deleted']}\nRemoved: {res['removed']}")

def register_deleted_account_handlers(app):
    app.add_handler(CommandHandler("scandeleted", scan_deleted_accounts))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, deleted_account_message_router), group=-1)
