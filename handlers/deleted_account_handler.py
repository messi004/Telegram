import logging
import asyncio
import os
import pickle
from typing import Optional
import config
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters, ApplicationHandlerStop

# Pyrogram imports
try:
    from pyrogram import Client
    from pyrogram.errors import FloodWait
    PYROGRAM_AVAILABLE = True
except ImportError:
    PYROGRAM_AVAILABLE = False

logger = logging.getLogger(__name__)

# --- Message Router with Stop Signal ---
async def deleted_account_message_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Only process in Private Chat
    if update.effective_chat.type != "private":
        return

    is_handled = False
    if context.user_data.get('awaiting_phone'):
        await handle_phone_number(update, context)
        is_handled = True
    elif context.user_data.get('awaiting_otp'):
        await handle_otp_code(update, context)
        is_handled = True

    # AGAR MESSAGE HANDLE HO GAYA HAI, TOH ISSE SPAM MODEL TAK MAT BHEJO
    if is_handled:
        raise ApplicationHandlerStop()

# --- Updated Phone Handler with Database Fix ---
async def handle_phone_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.text.strip()
    if not phone.startswith('+'):
        return await update.message.reply_text("❌ Galat format! +91... se start karein.")

    user_id = update.effective_user.id
    chat_id = context.user_data.get('scan_chat_id')
    session_name = f"user_{user_id}_chat_{chat_id}"
    
    # Ensure directory exists
    os.makedirs("sessions", exist_ok=True)

    try:
        app = Client(
            name=session_name,
            api_id=config.PYROGRAM_API_ID,
            api_hash=config.PYROGRAM_API_HASH,
            phone_number=phone,
            workdir="sessions" # Yahan sessions folder use ho raha hai
        )
        await app.connect()
        sent_code = await app.send_code(phone)
        
        context.user_data.update({
            'phone': phone, 
            'pyrogram_app': app, 
            'phone_code_hash': sent_code.phone_code_hash, 
            'awaiting_phone': False, 
            'awaiting_otp': True
        })
        await update.message.reply_text("📨 Telegram app check karein aur OTP yahan bhejein:")
    except Exception as e:
        logger.error(f"Pyrogram Error: {e}")
        await update.message.reply_text(f"❌ Error: {e}\nTip: 'sessions' folder check karein.")

# --- Registration Update ---
def register_deleted_account_handlers(app):
    app.bot_data['PYROGRAM_API_ID'] = config.PYROGRAM_API_ID
    app.bot_data['PYROGRAM_API_HASH'] = config.PYROGRAM_API_HASH
    
    app.add_handler(CommandHandler("scandeleted", scan_deleted_accounts))
    
    # Group -1 ensures it runs before the Spam Model
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, 
        deleted_account_message_router
    ), group=-1)
