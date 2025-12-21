"""
Admin command handlers - Whitelist, Ban, Learning
"""
from telegram import Update
from telegram.ext import ContextTypes
from utils.validators import is_user_admin
from data.templates import DEFAULT_WELCOME

# ===== WHITELIST COMMANDS =====

async def whitelist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View whitelisted users"""
    whitelist = context.bot_data.get('whitelist', set())

    if not whitelist:
        await update.message.reply_text("No whitelisted users.\n\nUse: /addwhitelist <user_id>")
        return

    msg = "✅ *Whitelisted Users:*\n\n"
    for user_id in whitelist:
        try:
            member = await context.bot.get_chat_member(update.effective_chat.id, user_id)
            msg += f"• {member.user.first_name} (ID: {user_id})\n"
        except:
            msg += f"• User ID: {user_id}\n"

    msg += f"\nTotal: {len(whitelist)}"
    await update.message.reply_text(msg, parse_mode='Markdown')

async def addwhitelist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add user to whitelist"""
    if not await is_user_admin(update.effective_chat.id, update.effective_user.id, context):
        await update.message.reply_text("⚠️ Only admins can manage whitelist!")
        return

    if len(context.args) == 0 and not update.message.reply_to_message:
        await update.message.reply_text("Usage: /addwhitelist <user_id> or reply to user's message")
        return

    try:
        if update.message.reply_to_message:
            user_id = update.message.reply_to_message.from_user.id
            user_name = update.message.reply_to_message.from_user.first_name
        else:
            user_id = int(context.args[0])
            user_name = f"User {user_id}"

        if 'whitelist' not in context.bot_data:
            context.bot_data['whitelist'] = set()

        context.bot_data['whitelist'].add(user_id)
        await update.message.reply_text(f"✓ Added {user_name} to whitelist!\nID: {user_id}")

    except ValueError:
        await update.message.reply_text("⚠️ Invalid user ID!")

async def removewhitelist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove user from whitelist"""
    if not await is_user_admin(update.effective_chat.id, update.effective_user.id, context):
        await update.message.reply_text("⚠️ Only admins can manage whitelist!")
        return

    if len(context.args) == 0:
        await update.message.reply_text("Usage: /removewhitelist <user_id>")
        return

    try:
        user_id = int(context.args[0])
        whitelist = context.bot_data.get('whitelist', set())

        if user_id in whitelist:
            whitelist.remove(user_id)
            await update.message.reply_text(f"✓ Removed user {user_id} from whitelist")
        else:
            await update.message.reply_text("User not in whitelist")

    except ValueError:
        await update.message.reply_text("⚠️ Invalid user ID!")

async def clearwhitelist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear whitelist"""
    if not await is_user_admin(update.effective_chat.id, update.effective_user.id, context):
        await update.message.reply_text("⚠️ Only admins can manage whitelist!")
        return

    context.bot_data['whitelist'] = set()
    await update.message.reply_text("✓ Whitelist cleared!")

# ===== BAN COMMANDS =====

async def strikes_command(update: Update, context: ContextTypes.DEFAULT_TYPE, auto_ban):
    """Check user strikes"""
    target_user_id = update.effective_user.id
    user_name = update.effective_user.first_name

    if context.args:
        try:
            target_user_id = int(context.args[0])
            try:
                member = await context.bot.get_chat_member(update.effective_chat.id, target_user_id)
                user_name = member.user.first_name
            except:
                user_name = f"User {target_user_id}"
        except ValueError:
            await update.message.reply_text("⚠️ Invalid user ID!")
            return

    strikes_data = auto_ban.get_strikes(target_user_id)
    strikes_count = strikes_data['count']

    if auto_ban.is_banned(target_user_id):
        await update.message.reply_text(f"🚫 {user_name} (ID: {target_user_id}) is currently BANNED.")
    elif strikes_count == 0:
        await update.message.reply_text(f"✅ {user_name} (ID: {target_user_id}) has no active strikes.")
    else:
        msg = f"⚠️ *{user_name}* (ID: {target_user_id}) has *{strikes_count}/{auto_ban.strike_limit}* strikes.\n"
        msg += f"Remaining: {auto_ban.strike_limit - strikes_count} strike(s) before ban.\n\n"

        if strikes_data['reasons']:
            msg += "*Recent Violations:*\n"
            for i, reason in enumerate(strikes_data['reasons'][-3:]):
                msg += f"{i+1}. Reason: {reason['reason']}\n"
                message_snippet = reason['message'].replace('`', '\\`')
                msg += f"   Message: `{(message_snippet[:50] + '...') if len(message_snippet) > 50 else message_snippet}`\n"
                msg += f"   Time: {reason['time'].split('T')[0]} {reason['time'].split('T')[1].split('.')[0]}\n"

        await update.message.reply_text(msg, parse_mode='Markdown')

async def resetstrikes_command(update: Update, context: ContextTypes.DEFAULT_TYPE, auto_ban):
    """Reset user strikes"""
    if not await is_user_admin(update.effective_chat.id, update.effective_user.id, context):
        await update.message.reply_text("⚠️ Only admins can reset strikes!")
        return

    if len(context.args) == 0:
        await update.message.reply_text("Usage: /resetstrikes <user_id>")
        return

    try:
        user_id = int(context.args[0])
        if auto_ban.reset_strikes(user_id):
            auto_ban.save_ban_data()
            await update.message.reply_text(f"✓ Strikes for user {user_id} have been reset.")
        else:
            await update.message.reply_text(f"User {user_id} had no active strikes.")
    except ValueError:
        await update.message.reply_text("⚠️ Invalid user ID!")

async def banlist_command(update: Update, context: ContextTypes.DEFAULT_TYPE, auto_ban):
    """View banned users"""
    if not auto_ban.banned_users:
        await update.message.reply_text("No users are currently banned.")
        return

    msg = "🚫 *Banned Users:*\n\n"
    for user_id in auto_ban.banned_users:
        try:
            member = await context.bot.get_chat_member(update.effective_chat.id, user_id)
            msg += f"• {member.user.first_name} (ID: {user_id})\n"
        except:
            msg += f"• User ID: {user_id}\n"

    msg += f"\nTotal: {len(auto_ban.banned_users)}"
    await update.message.reply_text(msg, parse_mode='Markdown')

async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE, auto_ban):
    """Unban user"""
    if not await is_user_admin(update.effective_chat.id, update.effective_user.id, context):
        await update.message.reply_text("⚠️ Only admins can unban users!")
        return

    if len(context.args) == 0:
        await update.message.reply_text("Usage: /unban <user_id>")
        return

    try:
        user_id = int(context.args[0])
        if auto_ban.unban_user(user_id):
            auto_ban.save_ban_data()
            try:
                await context.bot.unban_chat_member(
                    chat_id=update.effective_chat.id,
                    user_id=user_id,
                    only_if_banned=True
                )
            except:
                pass
            await update.message.reply_text(f"✓ User {user_id} has been unbanned.")
        else:
            await update.message.reply_text(f"User {user_id} is not currently banned.")
    except ValueError:
        await update.message.reply_text("⚠️ Invalid user ID!")

async def strikelimit_command(update: Update, context: ContextTypes.DEFAULT_TYPE, auto_ban):
    """Set strike limit"""
    if not await is_user_admin(update.effective_chat.id, update.effective_user.id, context):
        await update.message.reply_text("⚠️ Only admins can set strike limit!")
        return

    if len(context.args) == 0:
        await update.message.reply_text(f"Current strike limit: {auto_ban.strike_limit}\nUsage: /strikelimit <number>")
        return

    try:
        new_limit = int(context.args[0])
        if new_limit > 0:
            auto_ban.strike_limit = new_limit
            auto_ban.save_ban_data()
            await update.message.reply_text(f"✓ Strike limit set to {new_limit}.")
        else:
            await update.message.reply_text("⚠️ Strike limit must be a positive number.")
    except ValueError:
        await update.message.reply_text("⚠️ Invalid number! Use: /strikelimit 3")

# ===== LEARNING COMMANDS =====

async def notspam_command(update: Update, context: ContextTypes.DEFAULT_TYPE, smart_learning):
    """Report false positive"""
    if update.message.reply_to_message and update.message.reply_to_message.text:
        message_text = update.message.reply_to_message.text
    elif context.args:
        message_text = ' '.join(context.args)
    else:
        await update.message.reply_text("Usage: Reply to a message with /notspam or use /notspam <message text>")
        return

    smart_learning.add_false_positive(message_text)
    smart_learning.add_feedback(update.effective_user.id, message_text, False)
    smart_learning.save_learning_data()

    await update.message.reply_text(
        "✅ Feedback recorded!\n\n"
        "I've learned this is NOT spam. Similar messages won't be deleted.\n\n"
        f"Learning Stats:\n"
        f"Safe Patterns: {len(smart_learning.learned_safe_patterns)}\n"
        f"Spam Patterns: {len(smart_learning.learned_spam_patterns)}"
    )

async def reportspam_command(update: Update, context: ContextTypes.DEFAULT_TYPE, smart_learning):
    """Report false negative"""
    if not update.message.reply_to_message or not update.message.reply_to_message.text:
        await update.message.reply_text("Usage: Reply to a spam message with /reportspam")
        return

    message_text = update.message.reply_to_message.text
    smart_learning.add_false_negative(message_text)
    smart_learning.add_feedback(update.effective_user.id, message_text, True)
    smart_learning.save_learning_data()

    await update.message.reply_text(
        "✅ Spam reported!\n\n"
        "I've learned this pattern. Similar messages will be blocked.\n\n"
        f"Learning Stats:\n"
        f"Safe Patterns: {len(smart_learning.learned_safe_patterns)}\n"
        f"Spam Patterns: {len(smart_learning.learned_spam_patterns)}"
    )

async def learningstats_command(update: Update, context: ContextTypes.DEFAULT_TYPE, smart_learning):
    """Show learning statistics"""
    
    # Escape special characters for Markdown
    def escape_markdown(text):
        """Escape special markdown characters"""
        special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        for char in special_chars:
            text = text.replace(char, f'\\{char}')
        return text
    
    stats_msg = "🧠 *Smart Learning Statistics*\n\n"
    stats_msg += "*Learned Patterns:*\n"
    stats_msg += f"Spam Keywords: {len(smart_learning.learned_spam_patterns)}\n"
    stats_msg += f"Safe Keywords: {len(smart_learning.learned_safe_patterns)}\n\n"
    
    stats_msg += "*User Feedback:*\n"
    stats_msg += f"False Positives: {len(smart_learning.false_positives)}\n"
    stats_msg += f"False Negatives: {len(smart_learning.false_negatives)}\n\n"
    
    stats_msg += "*Top Learned Spam Keywords:*\n"
    
    learned = smart_learning.get_learned_keywords()
    if learned:
        for i, keyword in enumerate(learned[:10], 1):
            # Escape the keyword for Markdown
            safe_keyword = escape_markdown(keyword)
            stats_msg += f"{i}\\. {safe_keyword}\n"
    else:
        stats_msg += "None yet \\- bot is still learning\\!\n"
    
    stats_msg += "\n*How It Works:*\n"
    stats_msg += "• Use /notspam for false positives\n"
    stats_msg += "• Use /reportspam for missed spam\n"
    stats_msg += "• Bot learns and improves automatically\n"
    
    await update.message.reply_text(stats_msg, parse_mode='MarkdownV2')
async def resetlearning_command(update: Update, context: ContextTypes.DEFAULT_TYPE, smart_learning):
    """Reset learning data"""
    if not await is_user_admin(update.effective_chat.id, update.effective_user.id, context):
        await update.message.reply_text("⚠️ Only admins can reset learning data!")
        return

    old_spam = len(smart_learning.learned_spam_patterns)
    old_safe = len(smart_learning.learned_safe_patterns)
    
    smart_learning.reset()
    
    await update.message.reply_text(
        f"✓ Learning data reset!\n\n"
        f"Cleared:\n"
        f"• {old_spam} spam patterns\n"
        f"• {old_safe} safe patterns\n\n"
        f"Bot will start learning fresh!"
    )

# ===== CUSTOM WELCOME COMMANDS =====

async def customwelcome_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set custom welcome message"""
    if not await is_user_admin(update.effective_chat.id, update.effective_user.id, context):
        await update.message.reply_text("⚠️ Only admins can set custom welcome!")
        return

    if len(context.args) == 0:
        await update.message.reply_text(
            "Usage: /customwelcome <your message>\n\n"
            "Placeholders:\n"
            "{name} - User's first name\n"
            "{group} - Group name\n"
            "{mention} - @username\n\n"
            "Example:\n/customwelcome Welcome {name} to {group}! Enjoy 😊"
        )
        return

    custom_msg = ' '.join(context.args)
    context.bot_data['custom_welcome'] = custom_msg

    await update.message.reply_text(f"✓ Custom welcome set!\n\nPreview:\n{custom_msg}")

async def resetwelcome_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reset welcome message to default"""
    if not await is_user_admin(update.effective_chat.id, update.effective_user.id, context):
        await update.message.reply_text("⚠️ Only admins can reset welcome!")
        return

    context.bot_data['custom_welcome'] = DEFAULT_WELCOME
    await update.message.reply_text("✓ Welcome message reset to default!")