import logging
import asyncio
import os
import pickle
from typing import Optional
import config
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters

# Pyrogram imports
try:
    from pyrogram import Client
    from pyrogram.errors import FloodWait
    PYROGRAM_AVAILABLE = True
except ImportError:
    PYROGRAM_AVAILABLE = False

logger = logging.getLogger(__name__)
SESSION_FILE = "data/user_sessions.pkl"

# --- Utils ---
def load_sessions():
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, 'rb') as f: return pickle.load(f)
        except: return {}
    return {}

def save_sessions(sessions):
    os.makedirs(os.path.dirname(SESSION_FILE), exist_ok=True)
    with open(SESSION_FILE, 'wb') as f: pickle.dump(sessions, f)

def get_session_name(user_id: int, chat_id: int) -> str:
    return f"sessions/user_{user_id}_chat_{chat_id}"

# --- Message Router (with Privacy Fix) ---
async def deleted_account_message_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Check if this is a Private Chat
    if update.effective_chat.type != "private":
        # Agar user group mein phone/OTP bhej raha hai
        if context.user_data.get('awaiting_phone') or context.user_data.get('awaiting_otp'):
            try:
                await update.message.delete() # Privacy ke liye message delete karein
                await context.bot.send_message(
                    chat_id=update.effective_user.id,
                    text="⚠️ Security Reason: Apna phone number/OTP sirf yahan (Private mein) bhejein!"
                )
            except: pass
        return

    # Private chat logic
    if context.user_data.get('awaiting_phone'):
        await handle_phone_number(update, context)
    elif context.user_data.get('awaiting_otp'):
        await handle_otp_code(update, context)

# --- Handlers ---
async def scan_deleted_accounts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat, user = update.effective_chat, update.effective_user
    
    # Credentials check
    api_id = config.PYROGRAM_API_ID
    api_hash = config.PYROGRAM_API_HASH
    
    if not api_id or not api_hash:
        return await update.message.reply_text("❌ API credentials missing in config.py!")

    # Admin check
    member = await chat.get_member(user.id)
    if member.status not in ['creator', 'administrator']:
        return await update.message.reply_text("❌ Sirf Admins use kar sakte hain!")

    sessions = load_sessions()
    session_key = f"{user.id}_{chat.id}"

    if session_key not in sessions:
        await update.message.reply_text("📱 Setup start karne ke liye mujhe **Private Message** (PM) karein.")
        # User ke PM mein instruction bhejein
        try:
            await context.bot.send_message(
                chat_id=user.id,
                text=f"Group: **{chat.title}** ke liye setup.\n\nAb yahan apna phone number bhejein (+countrycode ke saath):"
            )
            context.user_data['awaiting_phone'] = True
            context.user_data['scan_chat_id'] = chat.id
        except:
            await update.message.reply_text("❌ Pehle mujhe Start (Private mein) karke message karein!")
        return

    await start_scan(update, context, get_session_name(user.id, chat.id), sessions[session_key])

async def handle_phone_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.text.strip()
    if not phone.startswith('+'):
        return await update.message.reply_text("❌ Sahi format use karein: +91876xxxxxxx")

    session_name = get_session_name(update.effective_user.id, context.user_data['scan_chat_id'])
    try:
        app = Client(session_name, config.PYROGRAM_API_ID, config.PYROGRAM_API_HASH, phone_number=phone, workdir="sessions")
        await app.connect()
        sent_code = await app.send_code(phone)
        context.user_data.update({
            'phone': phone, 
            'pyrogram_app': app, 
            'phone_code_hash': sent_code.phone_code_hash, 
            'awaiting_phone': False, 
            'awaiting_otp': True
        })
        await update.message.reply_text("📨 Telegram par ek code aaya hoga, wo yahan bhejein:")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def handle_otp_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    otp = update.message.text.strip()
    app = context.user_data.get('pyrogram_app')
    phone = context.user_data.get('phone')
    
    try:
        await app.sign_in(phone, context.user_data['phone_code_hash'], otp)
        await app.disconnect()
        
        sessions = load_sessions()
        sessions[f"{update.effective_user.id}_{context.user_data['scan_chat_id']}"] = phone
        save_sessions(sessions)
        
        context.user_data['awaiting_otp'] = False
        await update.message.reply_text("✅ Setup successful! Ab group mein wapas jaakar `/scandeleted` likhein.")
    except Exception as e:
        await update.message.reply_text(f"❌ OTP Galat hai: {e}")

async def start_scan(update: Update, context: ContextTypes.DEFAULT_TYPE, session_name, phone):
    # (Pehle wala start_scan logic yahan rahega...)
    msg = await update.message.reply_text("🔍 Scanning started...")
    # ... rest of pyrogram_scan_deleted_accounts call ...

def register_deleted_account_handlers(app):
    app.add_handler(CommandHandler("scandeleted", scan_deleted_accounts))
    # 'group=-1' lagana zaroori hai taaki spam-check se pehle ye chale
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, deleted_account_message_router), group=-1)
