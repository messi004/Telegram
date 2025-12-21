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
        chat_id = update.effective_chat.id
        
        # Get chat member count
        member_count = await context.bot.get_chat_member_count(chat_id)
        
        # Get administrators (these we can always access)
        administrators = await context.bot.get_chat_administrators(chat_id)
        
        # Filter out bots
        members = [admin.user for admin in administrators if not admin.user.is_bot]
        
        # Add recently active members from tracking
        if 'recent_members' in context.bot_data:
            recent = context.bot_data['recent_members'].get(chat_id, [])
            for user_id, username, first_name in recent:
                # Check if not already in members list
                if not any(m.id == user_id for m in members):
                    # Create a simple user object
                    class SimpleUser:
                        def __init__(self, uid, uname, fname):
                            self.id = uid
                            self.username = uname
                            self.first_name = fname
                    members.append(SimpleUser(user_id, username, first_name))
        
        if not members:
            await status_msg.edit_text("❌ No members found to tag!")
            return
        
        # Update status
        await status_msg.edit_text(f"🔄 Tagging {len(members)} members...")
        
        # Delete status message
        await asyncio.sleep(1)
        await status_msg.delete()
        
        # Send message with tags
        await send_mass_tag_message(update, context, members, custom_message)
        
    except Exception as e:
        await status_msg.edit_text(f"❌ Error: {str(e)}")
        print(f"Error in tag_all_command: {e}")

async def send_mass_tag_message(update, context, members, custom_message):
    """Send message with member tags in batches"""
    # Telegram limit: 4096 characters per message
    MAX_TAGS_PER_MESSAGE = 50  # Approximately 50 tags per message
    
    total_members = len(members)
    batches = [members[i:i + MAX_TAGS_PER_MESSAGE] for i in range(0, len(members), MAX_TAGS_PER_MESSAGE)]
    
    for batch_num, batch in enumerate(batches, 1):
        # Create message with tags
        message = f"📢 {custom_message}\n\n"
        message += "👥 Tagged Members:\n"
        
        for member in batch:
            try:
                if hasattr(member, 'username') and member.username:
                    message += f"@{member.username} "
                else:
                    # Use text mention for users without username
                    fname = getattr(member, 'first_name', 'User')
                    uid = getattr(member, 'id', 0)
                    message += f"[{fname}](tg://user?id={uid}) "
            except Exception as e:
                print(f"Error tagging member: {e}")
                continue
        
        # Send message
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=message,
                parse_mode='Markdown'
            )
            
            # Add delay between batches to avoid flood limits
            if batch_num < len(batches):
                await asyncio.sleep(1)
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
            try:
                if admin.username:
                    message += f"@{admin.username} "
                else:
                    message += f"[{admin.first_name}](tg://user?id={admin.id}) "
            except Exception as e:
                print(f"Error tagging admin: {e}")
                continue
        
        # Send message
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=message,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")
        print(f"Error in tagall_admins_command: {e}")

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
        try:
            if username:
                message += f"@{username} "
            else:
                message += f"[{first_name}](tg://user?id={user_id}) "
        except Exception as e:
            print(f"Error tagging member: {e}")
            continue
    
    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode='Markdown'
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")
        print(f"Error in tagall_online_command: {e}")

async def track_active_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Track recently active members (call this from message handler)"""
    if update.effective_chat.type == "private":
        return
    
    try:
        if 'recent_members' not in context.bot_data:
            context.bot_data['recent_members'] = {}
        
        chat_id = update.effective_chat.id
        if chat_id not in context.bot_data['recent_members']:
            context.bot_data['recent_members'][chat_id] = []
        
        user = update.effective_user
        user_info = (user.id, user.username, user.first_name)
        
        # Add to recent members (keep last 100)
        recent = context.bot_data['recent_members'][chat_id]
        
        # Remove if already exists (to move to end)
        recent = [m for m in recent if m[0] != user.id]
        recent.append(user_info)
        
        # Keep only last 100
        if len(recent) > 100:
            recent = recent[-100:]
        
        context.bot_data['recent_members'][chat_id] = recent
    except Exception as e:
        print(f"Error tracking member: {e}")

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

*Note:* Due to Telegram limitations, /tagall can only tag admins and recently active members.
        """
        
        await update.message.reply_text(stats_msg, parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")
        print(f"Error in tagall_stats_command: {e}")