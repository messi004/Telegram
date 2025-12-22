"""
Deleted Account Remover Feature for Telegram Bot
Ye feature group se deleted accounts ko automatically remove karta hai
"""

from telegram import Update, ChatMember
from telegram.ext import ContextTypes, CommandHandler
from telegram.error import TelegramError
import logging

logger = logging.getLogger(__name__)

async def scan_deleted_accounts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Group ko scan karta hai aur deleted accounts ko dhoondhta hai
    Command: /scandeleted
    """
    if not update.effective_chat:
        return
    
    chat = update.effective_chat
    user = update.effective_user
    
    # Check if user is admin
    try:
        member = await chat.get_member(user.id)
        if member.status not in ['creator', 'administrator']:
            await update.message.reply_text("❌ Ye command sirf admins use kar sakte hain!")
            return
    except TelegramError as e:
        logger.error(f"Error checking admin status: {e}")
        return
    
    # Check if bot is admin
    try:
        bot_member = await chat.get_member(context.bot.id)
        if bot_member.status != 'administrator' or not bot_member.can_restrict_members:
            await update.message.reply_text(
                "❌ Mujhe admin banana zaruri hai 'Ban users' permission ke saath!"
            )
            return
    except TelegramError as e:
        logger.error(f"Error checking bot permissions: {e}")
        return
    
    await update.message.reply_text("🔍 Deleted accounts search kar raha hoon... Thoda time lagega.")
    
    deleted_count = 0
    error_count = 0
    total_members = 0
    
    try:
        # Get all chat members
        async for member in chat.iter_members():
            total_members += 1
            
            # Check if account is deleted
            # Deleted accounts have first_name as "Deleted Account"
            if member.user.first_name == "Deleted Account" or not member.user.first_name:
                try:
                    # Remove deleted account
                    await chat.ban_member(member.user.id)
                    await chat.unban_member(member.user.id)  # Unban immediately (just kick)
                    deleted_count += 1
                    logger.info(f"Removed deleted account: {member.user.id}")
                except TelegramError as e:
                    error_count += 1
                    logger.error(f"Could not remove user {member.user.id}: {e}")
        
        # Final report
        report = f"""
✅ **Scan Complete!**

📊 **Statistics:**
• Total Members: {total_members}
• Deleted Accounts Found: {deleted_count}
• Successfully Removed: {deleted_count - error_count}
• Errors: {error_count}
"""
        await update.message.reply_text(report)
        
    except TelegramError as e:
        logger.error(f"Error during scan: {e}")
        await update.message.reply_text(
            f"❌ Error: {str(e)}\n\n"
            "Note: Large groups ko scan karne mein time lagta hai."
        )


async def auto_remove_deleted(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Auto-removal ko enable/disable karta hai
    Command: /autoremovedeleted on/off
    """
    if not update.effective_chat or not update.message:
        return
    
    chat = update.effective_chat
    user = update.effective_user
    
    # Check admin
    try:
        member = await chat.get_member(user.id)
        if member.status not in ['creator', 'administrator']:
            await update.message.reply_text("❌ Ye command sirf admins use kar sakte hain!")
            return
    except TelegramError:
        return
    
    # Parse command
    args = context.args
    if not args or args[0].lower() not in ['on', 'off']:
        await update.message.reply_text(
            "Usage: /autoremovedeleted <on/off>\n"
            "Example: /autoremovedeleted on"
        )
        return
    
    status = args[0].lower() == 'on'
    
    # Store setting in bot_data
    if 'auto_remove_deleted' not in context.bot_data:
        context.bot_data['auto_remove_deleted'] = {}
    
    context.bot_data['auto_remove_deleted'][chat.id] = status
    
    if status:
        await update.message.reply_text(
            "✅ Auto-removal enabled!\n"
            "Deleted accounts automatically remove ho jayenge."
        )
    else:
        await update.message.reply_text("❌ Auto-removal disabled!")


async def check_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    New member join karne par check karta hai ki wo deleted account toh nahi
    """
    if not update.message or not update.message.new_chat_members:
        return
    
    chat = update.effective_chat
    
    # Check if auto-removal is enabled
    if 'auto_remove_deleted' not in context.bot_data:
        return
    
    if not context.bot_data['auto_remove_deleted'].get(chat.id, False):
        return
    
    for member in update.message.new_chat_members:
        # Check if deleted account
        if member.first_name == "Deleted Account" or not member.first_name:
            try:
                await chat.ban_member(member.id)
                await chat.unban_member(member.id)
                logger.info(f"Auto-removed deleted account: {member.id}")
            except TelegramError as e:
                logger.error(f"Could not auto-remove: {e}")


# Handler registration function
#def register_deleted_account_handlers(application):
    """
    Is function ko main.py mein call karo
    """
   # application.add_handler(CommandHandler("scandeleted", scan_deleted_accounts))
   # application.add_handler(CommandHandler("autoremovedeleted", auto_remove_deleted))
    
    # Note: new_chat_members handler ko message handler mein add karna hoga
    # Example:
    # from telegram.ext import MessageHandler, filters
    # application.add_handler(MessageHandler(
    #     filters.StatusUpdate.NEW_CHAT_MEMBERS, 
    #     check_new_member
    # ))


"""
=== INSTALLATION INSTRUCTIONS ===

1. Is file ko apne project mein 'handlers' folder mein save karo as 'deleted_account_handler.py'

2. main.py mein import karo:
   from handlers.deleted_account_handler import register_deleted_account_handlers

3. main.py mein handlers register karo:
   def main():
       application = Application.builder().token(BOT_TOKEN).build()
       
       # ... existing handlers ...
       
       # Add deleted account handlers
       register_deleted_account_handlers(application)
       
       application.run_polling()

4. Bot ko admin banao with 'Ban users' permission

=== USAGE ===

Commands:
• /scandeleted - Manually scan karke deleted accounts remove kare
• /autoremovedeleted on - Auto removal enable kare
• /autoremovedeleted off - Auto removal disable kare

=== FEATURES ===

✅ Manual scan with detailed report
✅ Auto-removal for new deleted accounts
✅ Admin-only access
✅ Error handling
✅ Logging support
✅ Permission checks

=== NOTES ===

• Large groups mein scan time lagta hai (Telegram API rate limits)
• Bot ko admin hona chahiye 'Ban users' permission ke saath
• Deleted accounts ko kick karta hai (permanent ban nahi)
"""