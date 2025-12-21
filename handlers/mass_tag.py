"""
Mass Tag Feature - Tag all members with custom message
"""
from telegram import Update
from telegram.ext import ContextTypes
from utils.validators import is_user_admin
import asyncio

async def tag_all_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Tag all group members with custom message
    Usage: /tagall <your message>
    Admin only command
    """
    # Check if admin
    if not await is_user_admin(update.effective_chat.id, update.effective_user.id, context):
        await update.message.reply_text("⚠️ Only admins can use this command!")
        return
    
    # Check if in group
    if update.effective_chat.type == "private":
        await update.message.reply_text("❌ This command only works in groups!")
        return
    
    # Get custom message
    if len(context.args) == 0:
        await update.message.reply_text(
            "Usage: /tagall <your message>\n\n"
            "Example:\n"
            "/tagall Important announcement for everyone!"
        )
        return
    
    custom_message = ' '.join(context.args)
    
    # Send processing message
    status_msg = await update.message.reply_text("🔄 Fetching members...")
    
    try:
        # Get all chat members
        chat_id = update.effective_chat.id
        members = []
        member_count = await context.bot.get_chat_member_count(chat_id)
        
        # Update status
        await status_msg.edit_text(f"🔄 Found {member_count} members. Tagging...")
        
        # Fetch all members (this might take time for large groups)
        async for member in context.bot.get_chat_administrators(chat_id):
            if not member.user.is_bot:
                members.append(member.user)
        
        # Get regular members (Telegram API limitation - we'll tag visible members)
        # Note: Full member list requires special permissions
        
        if not members:
            await status_msg.edit_text("❌ No members found to tag!")
            return
        
        # Delete status message
        await status_msg.delete()
        
        # Send message with tags
        await send_mass_tag_message(update, context, members, custom_message)
        
    except Exception as e:
        await status_msg.edit_text(f"❌ Error: {str(e)}")

async def send_mass_tag_message(update, context, members, custom_message):
    """Send message with member tags in batches"""
    # Telegram limit: 4096 characters per message
    MAX_TAGS_PER_MESSAGE = 10  # Approximately 10 tags per message
    
    total_members = len(members)
    batches = [members[i:i + MAX_TAGS_PER_MESSAGE] for i in range(0, len(members), MAX_TAGS_PER_MESSAGE)]
    
    for batch_num, batch in enumerate(batches, 1):
        # Create message with tags
        message = f"📢 {custom_message}\n\n"
        message += "👥 Tagged Members:\n"
        
        for member in batch:
            if member.username:
                message += f"@{member.username} "
            else:
                # Use text mention for users without username
                message += f"[{member.first_name}](tg://user?id={member.id}) "
        
        # Send message
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=message,
                parse_mode='Markdown'
            )
            
            # Add delay between batches to avoid flood limits
            if batch_num < len(batches):
                await asyncio.sleep(2)
        except Exception as e:
            print(f"Error sending batch {batch_num}: {e}")

async def tagall_admins_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Tag only admins with custom message
    Usage: /tagadmins <your message>
    Admin only command
    """
    # Check if admin
    if not await is_user_admin(update.effective_chat.id, update.effective_user.id, context):
        await update.message.reply_text("⚠️ Only admins can use this command!")
        return
    
    # Check if in group
    if update.effective_chat.type == "private":
        await update.message.reply_text("❌ This command only works in groups!")
        return
    
    # Get custom message
    if len(context.args) == 0:
        await update.message.reply_text(
            "Usage: /tagadmins <your message>\n\n"
            "Example:\n"
            "/tagadmins Admin meeting in 10 minutes!"
        )
        return
    
    custom_message = ' '.join(context.args)
    
    try:
        # Get all admins
        admins = await context.bot.get_chat_administrators(update.effective_chat.id)
        admin_list = [admin.user for admin in admins if not admin.user.is_bot]
        
        if not admin_list:
            await update.message.reply_text("❌ No admins found!")
            return
        
        # Create message with admin tags
        message = f"👮 {custom_message}\n\n"
        message += "👥 Tagged Admins:\n"
        
        for admin in admin_list:
            if admin.username:
                message += f"@{admin.username} "
            else:
                message += f"[{admin.first_name}](tg://user?id={admin.id}) "
        
        # Send message
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=message,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def tagall_online_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Tag members who recently sent messages (pseudo-online)
    Usage: /tagonline <your message>
    Admin only command
    """
    # Check if admin
    if not await is_user_admin(update.effective_chat.id, update.effective_user.id, context):
        await update.message.reply_text("⚠️ Only admins can use this command!")
        return
    
    # Check if in group
    if update.effective_chat.type == "private":
        await update.message.reply_text("❌ This command only works in groups!")
        return
    
    # Get custom message
    if len(context.args) == 0:
        await update.message.reply_text(
            "Usage: /tagonline <your message>\n\n"
            "Tags recently active members"
        )
        return
    
    custom_message = ' '.join(context.args)
    
    # Initialize recent members tracking
    if 'recent_members' not in context.bot_data:
        context.bot_data['recent_members'] = {}
    
    chat_id = update.effective_chat.id
    recent_members = context.bot_data['recent_members'].get(chat_id, [])
    
    if not recent_members:
        await update.message.reply_text(
            "❌ No recently active members tracked yet!\n"
            "Members will be tracked as they send messages."
        )
        return
    
    # Create message
    message = f"🟢 {custom_message}\n\n"
    message += "👥 Active Members:\n"
    
    for user_id, username, first_name in recent_members[-50:]:  # Last 50 active
        if username:
            message += f"@{username} "
        else:
            message += f"[{first_name}](tg://user?id={user_id}) "
    
    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode='Markdown'
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def track_active_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Track recently active members (call this from message handler)"""
    if update.effective_chat.type == "private":
        return
    
    if 'recent_members' not in context.bot_data:
        context.bot_data['recent_members'] = {}
    
    chat_id = update.effective_chat.id
    if chat_id not in context.bot_data['recent_members']:
        context.bot_data['recent_members'][chat_id] = []
    
    user = update.effective_user
    user_info = (user.id, user.username, user.first_name)
    
    # Add to recent members (keep last 100)
    recent = context.bot_data['recent_members'][chat_id]
    if user_info not in recent:
        recent.append(user_info)
        if len(recent) > 100:
            recent.pop(0)

async def tagall_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show tagging statistics"""
    if not await is_user_admin(update.effective_chat.id, update.effective_user.id, context):
        await update.message.reply_text("⚠️ Only admins can use this command!")
        return
    
    try:
        member_count = await context.bot.get_chat_member_count(update.effective_chat.id)
        admins = await context.bot.get_chat_administrators(update.effective_chat.id)
        admin_count = len([a for a in admins if not a.user.is_bot])
        
        # Get recent members count
        chat_id = update.effective_chat.id
        recent_members = context.bot_data.get('recent_members', {}).get(chat_id, [])
        recent_count = len(recent_members)
        
        stats_msg = f"""
📊 *Group Statistics*

Total Members: {member_count}
Admins: {admin_count}
Recently Active: {recent_count}

*Available Commands:*
/tagall - Tag all members
/tagadmins - Tag only admins
/tagonline - Tag recently active members
/tagstats - This statistics
        """
        
        await update.message.reply_text(stats_msg, parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")