"""
Validation utilities
"""
from telegram.constants import ChatMemberStatus

def is_whitelisted(user_id, context):
    """Check if user is whitelisted"""
    whitelist = context.bot_data.get('whitelist', set())
    return user_id in whitelist

async def is_user_admin(chat_id, user_id, context):
    """Check if user is admin"""
    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        return member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
    except:
        return False