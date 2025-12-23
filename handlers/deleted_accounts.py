import logging
import asyncio
import os
import pickle
import config
from telegram import Update
from telegram.ext import ContextTypes, ApplicationHandlerStop

# Telethon imports
try:
    from telethon import TelegramClient
    from telethon.errors import (
        SessionPasswordNeededError,
        PhoneCodeExpiredError,
        PhoneCodeInvalidError
    )
    TELETHON_AVAILABLE = True
except ImportError:
    TELETHON_AVAILABLE = False

logger = logging.getLogger(__name__)

# Config
SESSION_DIR = "sessions"
DATA_DIR = "data"
SESSION_FILE = os.path.join(DATA_DIR, "deleted_accounts_sessions.pkl")

os.makedirs(SESSION_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

# ============================================
# Session Management (Compact)
# ============================================

class DeletedAccountsSession:
    """Simple session management for deleted accounts feature"""
    
    @staticmethod
    def load_sessions():
        if os.path.exists(SESSION_FILE):
            try:
                with open(SESSION_FILE, 'rb') as f:
                    return pickle.load(f)
            except:
                return {}
        return {}
    
    @staticmethod
    def save_sessions(sessions):
        with open(SESSION_FILE, 'wb') as f:
            pickle.dump(sessions, f)
    
    @staticmethod
    def get_session_path(user_id, chat_id):
        return os.path.join(SESSION_DIR, f"deleted_acc_{user_id}_{chat_id}.session")
    
    @staticmethod
    def get_session_key(user_id, chat_id):
        return f"{user_id}_{chat_id}"
    
    @staticmethod
    def add_session(user_id, chat_id, phone):
        sessions = DeletedAccountsSession.load_sessions()
        key = DeletedAccountsSession.get_session_key(user_id, chat_id)
        sessions[key] = {
            'phone': phone,
            'created_at': asyncio.get_event_loop().time()
        }
        DeletedAccountsSession.save_sessions(sessions)
        return True
    
    @staticmethod
    def remove_session(user_id, chat_id):
        sessions = DeletedAccountsSession.load_sessions()
        key = DeletedAccountsSession.get_session_key(user_id, chat_id)
        
        if key in sessions:
            # Remove session file
            session_path = DeletedAccountsSession.get_session_path(user_id, chat_id)
            if os.path.exists(session_path):
                try:
                    os.remove(session_path)
                except:
                    pass
            
            # Remove from sessions data
            del sessions[key]
            DeletedAccountsSession.save_sessions(sessions)
            return True
        return False

# ============================================
# Core Scanner (Compact)
# ============================================

async def telethon_scan_deleted_accounts(api_id, api_hash, session_path, chat_id, progress_callback=None):
    """Compact scanner function"""
    if not TELETHON_AVAILABLE:
        return {'total': 0, 'deleted': 0, 'removed': 0, 'errors': 1}
    
    results = {'total': 0, 'deleted': 0, 'removed': 0, 'errors': 0}
    
    try:
        client = TelegramClient(
            session=session_path,
            api_id=api_id,
            api_hash=api_hash,
            device_model="Android 14",
            system_version="4.16.30-vh+",
            app_version="10.5.0"
        )
        
        await client.connect()
        
        if not await client.is_user_authorized():
            return {'total': 0, 'deleted': 0, 'removed': 0, 'errors': 1}
        
        # Scan participants
        async for user in client.iter_participants(chat_id, limit=10000):
            results['total'] += 1
            
            if getattr(user, 'deleted', False):
                results['deleted'] += 1
                
                try:
                    await client.edit_permissions(chat_id, user.id, view_messages=False)
                    results['removed'] += 1
                except Exception as e:
                    logger.error(f"Remove error: {e}")
                    results['errors'] += 1
            
            # Progress update every 50 users
            if results['total'] % 50 == 0 and progress_callback:
                try:
                    await progress_callback(
                        f"Scanned: {results['total']} | "
                        f"Deleted: {results['deleted']} | "
                        f"Removed: {results['removed']}"
                    )
                except:
                    pass
            
            await asyncio.sleep(0.1)  # Rate limiting
        
        await client.disconnect()
        return results
        
    except Exception as e:
        logger.error(f"Scan error: {e}")
        return {'total': results['total'], 'deleted': results['deleted'], 
                'removed': results['removed'], 'errors': results['errors'] + 1}

# ============================================
# Command Handlers (Compact)
# ============================================

class DeletedAccountsHandler:
    """Compact handler for deleted accounts feature"""
    
    def __init__(self, api_id, api_hash):
        self.api_id = api_id
        self.api_hash = api_hash
        self.setup_data = {}  # {user_id: {stage, chat_id, client, phone, phone_hash}}
    
    def _get_setup_key(self, user_id):
        return f"setup_{user_id}"
    
    async def scandeleted_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /scandeleted command"""
        user = update.effective_user
        chat = update.effective_chat
        
        # Only work in private chat
        if chat.type != "private":
            await update.message.reply_text(
                "⚠️ Please use this command in private chat with me.\n"
                "I'll message you privately to continue."
            )
            
            # Try to send private message
            try:
                await context.bot.send_message(
                    user.id,
                    f"Let's setup scanning for **{chat.title}**."
                )
            except:
                pass
            return
        
        session_path = DeletedAccountsSession.get_session_path(user.id, chat.id)
        
        # Check if session exists and is valid
        if os.path.exists(session_path):
            await self._start_scan(update, context, session_path, chat)
        else:
            # Start setup
            await update.message.reply_text(
                f"📱 **Setup for {chat.title}**\n\n"
                f"Send your phone number (with country code):\n"
                f"Example: `+919876543210`"
            )
            
            # Store setup data
            setup_key = self._get_setup_key(user.id)
            self.setup_data[setup_key] = {
                'stage': 'phone',
                'chat_id': chat.id,
                'chat_title': chat.title
            }
    
    async def _start_scan(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                         session_path: str, chat):
        """Start scanning process"""
        status_msg = await update.message.reply_text("🔍 Starting scan...")
        
        async def progress_update(text):
            try:
                await status_msg.edit_text(f"🔍 {text}")
            except:
                pass
        
        # Run scan
        results = await telethon_scan_deleted_accounts(
            self.api_id,
            self.api_hash,
            session_path,
            chat.id,
            progress_callback=progress_update
        )
        
        # Send results
        result_text = (
            f"✅ **Scan Complete**\n\n"
            f"• Total: {results['total']}\n"
            f"• Deleted: {results['deleted']}\n"
            f"• Removed: {results['removed']}\n"
            f"• Errors: {results['errors']}"
        )
        
        await status_msg.edit_text(result_text, parse_mode='Markdown')
    
    async def handle_private_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle private messages for setup"""
        if update.effective_chat.type != "private":
            return
        
        user = update.effective_user
        text = update.message.text.strip()
        setup_key = self._get_setup_key(user.id)
        
        if setup_key not in self.setup_data:
            return  # Not in setup mode
        
        setup_info = self.setup_data[setup_key]
        stage = setup_info.get('stage')
        
        if stage == 'phone':
            await self._handle_phone(update, setup_info, text)
            
        elif stage == 'otp':
            await self._handle_otp(update, setup_info, text)
            
        elif stage == 'password':
            await self._handle_password(update, setup_info, text)
    
    async def _handle_phone(self, update, setup_info, phone):
        """Handle phone number input"""
        user = update.effective_user
        setup_key = self._get_setup_key(user.id)
        
        if not phone.startswith('+'):
            await update.message.reply_text("❌ Include country code (e.g., +91)")
            return
        
        session_path = DeletedAccountsSession.get_session_path(
            user.id, setup_info['chat_id']
        )
        
        try:
            client = TelegramClient(
                session_path,
                self.api_id,
                self.api_hash
            )
            await client.connect()
            
            sent = await client.send_code_request(phone)
            
            # Update setup info
            setup_info.update({
                'stage': 'otp',
                'client': client,
                'phone': phone,
                'phone_hash': sent.phone_code_hash
            })
            
            await update.message.reply_text("📨 OTP sent! Send the code:")
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")
            if 'client' in locals():
                await client.disconnect()
            self.setup_data.pop(setup_key, None)
    
    async def _handle_otp(self, update, setup_info, otp):
        """Handle OTP input"""
        user = update.effective_user
        setup_key = self._get_setup_key(user.id)
        client = setup_info.get('client')
        
        if not client:
            await update.message.reply_text("❌ Session expired. Start again.")
            self.setup_data.pop(setup_key, None)
            return
        
        try:
            await client.sign_in(
                setup_info['phone'],
                otp,
                phone_code_hash=setup_info['phone_hash']
            )
            
            # Save session
            DeletedAccountsSession.add_session(
                user.id,
                setup_info['chat_id'],
                setup_info['phone']
            )
            
            await update.message.reply_text(
                f"✅ Setup complete!\n"
                f"You can now scan **{setup_info['chat_title']}**"
            )
            
            await client.disconnect()
            self.setup_data.pop(setup_key, None)
            
        except SessionPasswordNeededError:
            setup_info['stage'] = 'password'
            await update.message.reply_text("🔐 2FA enabled. Send password:")
            
        except (PhoneCodeExpiredError, PhoneCodeInvalidError):
            await update.message.reply_text("❌ Invalid/Expired OTP. Start again.")
            await client.disconnect()
            self.setup_data.pop(setup_key, None)
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")
            await client.disconnect()
            self.setup_data.pop(setup_key, None)
    
    async def _handle_password(self, update, setup_info, password):
        """Handle 2FA password"""
        user = update.effective_user
        setup_key = self._get_setup_key(user.id)
        client = setup_info.get('client')
        
        try:
            await client.sign_in(password=password)
            
            # Save session
            DeletedAccountsSession.add_session(
                user.id,
                setup_info['chat_id'],
                setup_info['phone']
            )
            
            await update.message.reply_text(
                f"✅ Setup complete!\n"
                f"You can now scan **{setup_info['chat_title']}**"
            )
            
            await client.disconnect()
            self.setup_data.pop(setup_key, None)
            
        except Exception as e:
            await update.message.reply_text(f"❌ Wrong password: {e}")
            self.setup_data.pop(setup_key, None)
            if client:
                await client.disconnect()

# ============================================
# Utility Commands (Shared with other features)
# ============================================

async def mysessions_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /mysessions command (shared)"""
    user = update.effective_user
    
    sessions = DeletedAccountsSession.load_sessions()
    user_sessions = []
    
    for key, data in sessions.items():
        if key.startswith(f"{user.id}_"):
            user_sessions.append((key, data))
    
    if not user_sessions:
        await update.message.reply_text("No sessions found.")
        return
    
    message = "📋 **Your Sessions:**\n\n"
    
    for key, data in user_sessions.items():
        user_id, chat_id = key.split('_')
        phone = data.get('phone', 'Unknown')
        message += f"• Chat ID: {chat_id}\n  Phone: {phone}\n\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def clearsession_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /clearsession command (shared)"""
    user = update.effective_user
    chat = update.effective_chat
    
    if chat.type != "private":
        await update.message.reply_text("Use in private chat.")
        return
    
    success = DeletedAccountsSession.remove_session(user.id, chat.id)
    
    if success:
        await update.message.reply_text("✅ Session cleared.")
    else:
        await update.message.reply_text("ℹ️ No session found.")

# ============================================
# Registration Function
# ============================================

def register_deleted_accounts_handlers(app, api_id, api_hash):
    """Register all handlers for this feature"""
    
    # Initialize handler
    handler = DeletedAccountsHandler(api_id, api_hash)
    
    # Register commands
    app.add_handler(CommandHandler("scandeleted", handler.scandeleted_command))
    
    # Register message handler for setup (high priority)
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE,
            handler.handle_private_message
        ),
        group=1  # Higher priority group
    )
    
    logger.info("Deleted accounts feature registered")