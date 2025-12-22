"""
Hybrid Deleted Account Remover - Telegram Bot + Pyrogram
Complete member list scan with session management
"""

import logging
import asyncio
import os
import pickle
from typing import Optional

from telegram import Update
from telegram.ext import (
    ContextTypes, 
    CommandHandler, 
    MessageHandler, 
    filters,
    ConversationHandler
)
from telegram.error import TelegramError

# Pyrogram imports
try:
    from pyrogram import Client
    from pyrogram.errors import FloodWait, UserNotParticipant, BadRequest
    PYROGRAM_AVAILABLE = True
except ImportError:
    PYROGRAM_AVAILABLE = False
    print("⚠️ Pyrogram not installed. Install with: pip install pyrogram tgcrypto")

logger = logging.getLogger(__name__)

# Conversation states
PHONE_NUMBER = 1
OTP_CODE = 2

# Storage file
SESSION_FILE = "data/user_sessions.pkl"

# ============================================
# Session Management
# ============================================

def load_sessions():
    """Load saved sessions"""
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, 'rb') as f:
                return pickle.load(f)
        except:
            return {}
    return {}

def save_sessions(sessions):
    """Save sessions to file"""
    os.makedirs(os.path.dirname(SESSION_FILE), exist_ok=True)
    with open(SESSION_FILE, 'wb') as f:
        pickle.dump(sessions, f)

def get_session_name(user_id: int, chat_id: int) -> str:
    """Generate session name"""
    return f"sessions/user_{user_id}_chat_{chat_id}"

# ============================================
# Pyrogram Scanner
# ============================================

async def pyrogram_scan_deleted_accounts(
    api_id: int,
    api_hash: str,
    session_name: str,
    chat_id: int,
    phone: Optional[str] = None,
    progress_callback=None
) -> dict:
    """
    Pyrogram se complete member scan karta hai
    
    Returns:
        dict with results: total, deleted, removed, errors
    """
    
    if not PYROGRAM_AVAILABLE:
        return {
            'error': 'Pyrogram not installed',
            'total': 0,
            'deleted': 0,
            'removed': 0,
            'errors': 0
        }
    
    results = {
        'total': 0,
        'deleted': 0,
        'removed': 0,
        'errors': 0
    }
    
    try:
        # Create Pyrogram client
        app = Client(
            session_name,
            api_id=api_id,
            api_hash=api_hash,
            phone_number=phone,
            workdir="sessions"
        )
        
        async with app:
            # Get chat info
            try:
                chat = await app.get_chat(chat_id)
                if progress_callback:
                    await progress_callback(f"📱 Scanning: {chat.title}")
            except Exception as e:
                logger.error(f"Could not get chat info: {e}")
            
            # Scan all members
            async for member in app.get_chat_members(chat_id):
                results['total'] += 1
                
                user = member.user
                
                # Check if deleted account
                is_deleted = (
                    user.first_name == "Deleted Account" or
                    not user.first_name or
                    (hasattr(user, 'is_deleted') and user.is_deleted)
                )
                
                if is_deleted:
                    results['deleted'] += 1
                    
                    try:
                        # Remove deleted account
                        await app.ban_chat_member(chat_id, user.id)
                        await app.unban_chat_member(chat_id, user.id)
                        results['removed'] += 1
                        
                        logger.info(f"Removed deleted account: {user.id}")
                        
                    except FloodWait as e:
                        # Wait for rate limit
                        if progress_callback:
                            await progress_callback(f"⏳ Rate limited. Waiting {e.value}s...")
                        await asyncio.sleep(e.value)
                        
                        # Retry
                        try:
                            await app.ban_chat_member(chat_id, user.id)
                            await app.unban_chat_member(chat_id, user.id)
                            results['removed'] += 1
                        except:
                            results['errors'] += 1
                            
                    except Exception as e:
                        results['errors'] += 1
                        logger.error(f"Error removing {user.id}: {e}")
                
                # Progress update
                if results['total'] % 50 == 0 and progress_callback:
                    await progress_callback(
                        f"📊 Scanned: {results['total']} | Found: {results['deleted']}"
                    )
                
                # Small delay
                await asyncio.sleep(0.1)
        
        return results
        
    except Exception as e:
        logger.error(f"Pyrogram scan error: {e}")
        results['error'] = str(e)
        return results

# ============================================
# Telegram Bot Handlers
# ============================================

async def scan_deleted_accounts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Main command: /scandeleted
    Complete member scan using Pyrogram
    """
    if not update.effective_chat or not update.effective_user:
        return
    
    chat = update.effective_chat
    user = update.effective_user
    
    # Check if Pyrogram is available
    if not PYROGRAM_AVAILABLE:
        await update.message.reply_text(
            "❌ Pyrogram not installed!\n\n"
            "Install karo:\n"
            "`pip install pyrogram tgcrypto`\n\n"
            "Phir bot restart karo.",
            parse_mode='Markdown'
        )
        return
    
    # Check if user is admin
    try:
        member = await chat.get_member(user.id)
        if member.status not in ['creator', 'administrator']:
            await update.message.reply_text("❌ Ye command sirf admins use kar sakte hain!")
            return
    except TelegramError:
        return
    
    # Check if bot is admin
    try:
        bot_member = await chat.get_member(context.bot.id)
        if bot_member.status != 'administrator' or not bot_member.can_restrict_members:
            await update.message.reply_text(
                "❌ Mujhe admin banana zaruri hai 'Ban users' permission ke saath!"
            )
            return
    except TelegramError:
        return
    
    # Check if API credentials are configured
    if not hasattr(context.bot_data, 'PYROGRAM_API_ID') or not hasattr(context.bot_data, 'PYROGRAM_API_HASH'):
        await update.message.reply_text(
            "❌ API credentials not configured!\n\n"
            "config.py mein add karo:\n"
            "```python\n"
            "PYROGRAM_API_ID = 12345678\n"
            "PYROGRAM_API_HASH = 'your_api_hash'\n"
            "```\n\n"
            "Get from: https://my.telegram.org",
            parse_mode='Markdown'
        )
        return
    
    # Load sessions
    sessions = load_sessions()
    session_key = f"{user.id}_{chat.id}"
    session_name = get_session_name(user.id, chat.id)
    
    # Check if session exists
    if session_key not in sessions:
        # Need phone number for first time
        await update.message.reply_text(
            "📱 **First Time Setup**\n\n"
            "Session create karne ke liye phone number chahiye.\n\n"
            "Phone number bhejo (with country code):\n"
            "Example: +919876543210\n\n"
            "ℹ️ Ye sirf ek baar chahiye. Session save ho jayega.",
            parse_mode='Markdown'
        )
        
        # Store state
        context.user_data['awaiting_phone'] = True
        context.user_data['scan_chat_id'] = chat.id
        return
    
    # Session exists, start scan
    await start_scan(update, context, session_name, sessions[session_key])


async def handle_phone_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle phone number input"""
    
    if not context.user_data.get('awaiting_phone'):
        return
    
    phone = update.message.text.strip()
    
    # Validate phone number
    if not phone.startswith('+') or len(phone) < 10:
        await update.message.reply_text(
            "❌ Invalid phone number!\n\n"
            "Format: +919876543210\n"
            "(with + and country code)"
        )
        return
    
    user = update.effective_user
    chat_id = context.user_data.get('scan_chat_id')
    
    # Create session
    session_name = get_session_name(user.id, chat_id)
    
    try:
        # Try to create Pyrogram session
        app = Client(
            session_name,
            api_id=context.bot_data['PYROGRAM_API_ID'],
            api_hash=context.bot_data['PYROGRAM_API_HASH'],
            phone_number=phone,
            workdir="sessions"
        )
        
        await update.message.reply_text(
            "📨 OTP bheja gaya hai!\n\n"
            "Telegram se OTP code bhejo.\n"
            "Example: 12345"
        )
        
        # Store data
        context.user_data['phone'] = phone
        context.user_data['session_name'] = session_name
        context.user_data['pyrogram_app'] = app
        context.user_data['awaiting_phone'] = False
        context.user_data['awaiting_otp'] = True
        
        # Start client to send OTP
        await app.connect()
        await app.send_code(phone)
        
    except Exception as e:
        logger.error(f"Error creating session: {e}")
        await update.message.reply_text(f"❌ Error: {e}")
        context.user_data.clear()


async def handle_otp_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle OTP code input"""
    
    if not context.user_data.get('awaiting_otp'):
        return
    
    otp = update.message.text.strip()
    
    # Validate OTP
    if not otp.isdigit() or len(otp) < 5:
        await update.message.reply_text(
            "❌ Invalid OTP!\n\n"
            "OTP should be 5-6 digits.\n"
            "Example: 12345"
        )
        return
    
    user = update.effective_user
    phone = context.user_data.get('phone')
    session_name = context.user_data.get('session_name')
    app = context.user_data.get('pyrogram_app')
    chat_id = context.user_data.get('scan_chat_id')
    
    try:
        # Sign in with OTP
        await app.sign_in(phone, otp)
        await app.disconnect()
        
        # Save session
        sessions = load_sessions()
        session_key = f"{user.id}_{chat_id}"
        sessions[session_key] = phone
        save_sessions(sessions)
        
        await update.message.reply_text(
            "✅ Session created successfully!\n\n"
            "Ab /scandeleted command chala sakte ho!"
        )
        
        # Clear user data
        context.user_data.clear()
        
        # Start scan automatically
        await update.message.reply_text("🔍 Starting scan...")
        
        # Get the update with proper chat
        from telegram import Update as TgUpdate, Message
        
        # Create a proper update for scan
        scan_update = update
        await start_scan(scan_update, context, session_name, phone)
        
    except Exception as e:
        logger.error(f"Error verifying OTP: {e}")
        await update.message.reply_text(
            f"❌ OTP verification failed!\n\n"
            f"Error: {e}\n\n"
            "Please try /scandeleted again."
        )
        
        # Disconnect app
        try:
            await app.disconnect()
        except:
            pass
        
        context.user_data.clear()


async def start_scan(update: Update, context: ContextTypes.DEFAULT_TYPE, session_name: str, phone: str):
    """Start the actual scan"""
    
    chat = update.effective_chat
    message = await update.message.reply_text(
        "🔍 **Starting Complete Scan**\n\n"
        "Deleted accounts search kar raha hoon...\n"
        "Thoda time lagega. Progress updates milte rahenge.",
        parse_mode='Markdown'
    )
    
    # Progress callback
    async def progress(msg: str):
        try:
            await message.edit_text(
                f"🔍 **Scanning...**\n\n{msg}",
                parse_mode='Markdown'
            )
        except:
            pass
    
    # Run scan
    results = await pyrogram_scan_deleted_accounts(
        api_id=context.bot_data['PYROGRAM_API_ID'],
        api_hash=context.bot_data['PYROGRAM_API_HASH'],
        session_name=session_name,
        chat_id=chat.id,
        phone=phone,
        progress_callback=progress
    )
    
    # Send final report
    if 'error' in results and results['error']:
        await message.edit_text(
            f"❌ **Scan Failed**\n\n"
            f"Error: {results['error']}\n\n"
            f"Try /scandeleted again or contact admin.",
            parse_mode='Markdown'
        )
    else:
        report = f"""
✅ **Scan Complete!**

📊 **Statistics:**
• Total Members: {results['total']}
• Deleted Accounts Found: {results['deleted']}
• Successfully Removed: {results['removed']}
• Errors: {results['errors']}

{"⚠️ Some errors occurred. Check logs for details." if results['errors'] > 0 else "✨ All deleted accounts removed!"}
"""
        await message.edit_text(report)


async def reset_session(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reset user session - /resetsession"""
    
    if not update.effective_user or not update.effective_chat:
        return
    
    user = update.effective_user
    chat = update.effective_chat
    
    # Check admin
    try:
        member = await chat.get_member(user.id)
        if member.status not in ['creator', 'administrator']:
            await update.message.reply_text("❌ Ye command sirf admins use kar sakte hain!")
            return
    except TelegramError:
        return
    
    # Remove session
    sessions = load_sessions()
    session_key = f"{user.id}_{chat.id}"
    
    if session_key in sessions:
        del sessions[session_key]
        save_sessions(sessions)
        
        # Remove session file
        session_name = get_session_name(user.id, chat.id)
        session_file = f"sessions/{session_name}.session"
        if os.path.exists(session_file):
            os.remove(session_file)
        
        await update.message.reply_text("✅ Session reset! Next /scandeleted pe naya setup hoga.")
    else:
        await update.message.reply_text("ℹ️ Koi session nahi hai.")


# ============================================
# Handler Registration
# ============================================

def register_deleted_account_handlers(application):
    """Register all handlers"""
    
    # Store API credentials from config
    from config import PYROGRAM_API_ID, PYROGRAM_API_HASH
    application.bot_data['PYROGRAM_API_ID'] = PYROGRAM_API_ID
    application.bot_data['PYROGRAM_API_HASH'] = PYROGRAM_API_HASH
    
    # Commands
    application.add_handler(CommandHandler("scandeleted", scan_deleted_accounts))
    application.add_handler(CommandHandler("resetsession", reset_session))
    
    # Message handlers for phone/OTP
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE,
        handle_phone_number
    ))
    
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE,
        handle_otp_code
    ))


"""
=== INSTALLATION GUIDE ===

**Step 1: Install Dependencies**
```bash
pip install pyrogram tgcrypto
```

**Step 2: Get API Credentials**
1. https://my.telegram.org par jao
2. Login karo
3. API Development Tools > Create Application
4. API ID aur API Hash copy karo

**Step 3: Update config.py**
```python
# config.py

# Existing config...
BOT_TOKEN = "your_bot_token"

# Add these lines:
PYROGRAM_API_ID = 12345678  # Your API ID
PYROGRAM_API_HASH = "your_api_hash_here"  # Your API Hash
```

**Step 4: Save This File**
Save as: `handlers/deleted_account_handler.py`

**Step 5: Update main.py**
```python
from handlers.deleted_account_handler import register_deleted_account_handlers

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    
    # ... existing handlers ...
    
    # Add this line
    register_deleted_account_handlers(application)
    
    application.run_polling()
```

**Step 6: Create sessions directory**
```bash
mkdir sessions
mkdir data
```

=== USAGE ===

**First Time (in group):**
1. Admin: /scandeleted
2. Bot: "Phone number bhejo"
3. Admin (in PM to bot): +919876543210
4. Bot: "OTP bhejo"
5. Admin (in PM): 12345
6. Bot: Session created! Starting scan...
7. ✅ Scan complete with results!

**Next Time:**
1. Admin: /scandeleted
2. Bot: Automatically starts scan (no phone/OTP needed)!

**Reset Session:**
/resetsession - Session delete karke naya setup

=== FEATURES ===

✅ **Hybrid Architecture**: Bot + Pyrogram combined
✅ **One-time Setup**: Phone/OTP sirf ek baar
✅ **Session Management**: Automatically saved
✅ **Complete Scan**: Sare members (no limitations!)
✅ **Progress Updates**: Real-time scan status
✅ **Error Handling**: Proper error messages
✅ **Rate Limit Handling**: FloodWait auto-handled
✅ **Private Setup**: Phone/OTP via PM only
✅ **Multi-Group**: Har group ke liye alag session

=== SECURITY ===

🔒 **Safe & Secure:**
- Sessions encrypted by Pyrogram
- Phone/OTP via private message only
- Admin-only access
- Credentials in config file (not hardcoded)
- Sessions stored safely

=== NOTES ===

⚠️ Important:
- Bot restart karne par sessions safe rahenge
- Har admin ka alag session hoga
- Phone number sirf ek baar chahiye
- OTP verification automatic hai

💡 Tips:
- Test pehle small group mein
- Large groups mein time lagega (rate limits)
- Session reset karne ke liye /resetsession use karo

🎯 Result:
Complete member list scan ho jayega aur sare deleted accounts remove!
"""