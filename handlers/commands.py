"""
Command handlers for bot
"""
from telegram import Update
from telegram.ext import ContextTypes
from data.templates import START_MESSAGE, HELP_MESSAGE
from utils.validators import is_user_admin
import config

# Basic Commands
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send start message"""
    await update.message.reply_text(START_MESSAGE, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send help message"""
    await update.message.reply_text(HELP_MESSAGE, parse_mode='Markdown')

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE, smart_learning):
    """Show bot statistics"""
    stats = context.bot_data.get('stats', {
        'messages_scanned': 0, 'spam_detected': 0, 'messages_deleted': 0,
        'ml_detections': 0, 'keyword_detections': 0, 'severe_detections': 0,
        'url_blocked': 0, 'mention_blocked': 0, 'tag_blocked': 0,
        'sticker_blocked': 0, 'image_blocked': 0
    })

    whitelist_count = len(context.bot_data.get('whitelist', set()))

    stats_msg = f"""
📊 *Bot Statistics*

Messages Scanned: {stats['messages_scanned']}
Total Deleted: {stats['messages_deleted']}

*Spam Detection:*
🤖 ML Model: {stats.get('ml_detections', 0)}
🔑 Keywords: {stats.get('keyword_detections', 0)}
🚨 Severe: {stats.get('severe_detections', 0)}

*Content Blocking:*
🔗 URLs: {stats.get('url_blocked', 0)}
@ Mentions: {stats.get('mention_blocked', 0)}
👤 Tags: {stats.get('tag_blocked', 0)}
🖼️ Images: {stats.get('image_blocked', 0)}
😀 Stickers: {stats.get('sticker_blocked', 0)}

*Smart Learning:*
🧠 Learned Spam: {len(smart_learning.learned_spam_patterns)}
✅ Learned Safe: {len(smart_learning.learned_safe_patterns)}
📝 User Feedback: {len(smart_learning.false_positives) + len(smart_learning.false_negatives)}

Whitelisted Users: {whitelist_count}
Detection Rate: {(stats['spam_detected']/stats['messages_scanned']*100) if stats['messages_scanned'] > 0 else 0:.1f}%

Use /learningstats for detailed learning info
    """
    await update.message.reply_text(stats_msg, parse_mode='Markdown')

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show current settings"""
    settings = context.bot_data.get('settings', config.DEFAULT_SETTINGS.copy())

    settings_msg = f"""
⚙️ *Current Settings*

Welcome Messages: {'✅ ON' if settings.get('welcome_enabled', True) else '❌ OFF'}
URL Blocking: {'✅ ON' if settings.get('url_blocking', True) else '❌ OFF'}
@Mention Blocking: {'✅ ON' if settings.get('mention_blocking', True) else '❌ OFF'}
User Tag Blocking: {'✅ ON' if settings.get('tag_blocking', True) else '❌ OFF'}
Sticker Spam Detection: {'✅ ON' if settings.get('sticker_blocking', True) else '❌ OFF'}
ML Sensitivity: {settings.get('threshold', 0.5)}
Multi-Language: ✅ EN/HI/TA

Use /help for all commands
    """
    await update.message.reply_text(settings_msg, parse_mode='Markdown')

# Setting Commands
async def set_welcome_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggle welcome messages"""
    if not await is_user_admin(update.effective_chat.id, update.effective_user.id, context):
        await update.message.reply_text("⚠️ Only admins can change settings!")
        return

    if len(context.args) == 0:
        await update.message.reply_text("Usage: /setwelcome <on/off>")
        return

    setting = context.args[0].lower()
    if setting in ['on', 'off']:
        if 'settings' not in context.bot_data:
            context.bot_data['settings'] = config.DEFAULT_SETTINGS.copy()
        context.bot_data['settings']['welcome_enabled'] = (setting == 'on')
        await update.message.reply_text(f"✓ Welcome messages: {setting.upper()}")
    else:
        await update.message.reply_text("Use: /setwelcome on or /setwelcome off")

async def set_url_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggle URL blocking"""
    if not await is_user_admin(update.effective_chat.id, update.effective_user.id, context):
        await update.message.reply_text("⚠️ Only admins can change settings!")
        return

    if len(context.args) == 0:
        await update.message.reply_text("Usage: /seturl <on/off>")
        return

    setting = context.args[0].lower()
    if setting in ['on', 'off']:
        if 'settings' not in context.bot_data:
            context.bot_data['settings'] = config.DEFAULT_SETTINGS.copy()
        context.bot_data['settings']['url_blocking'] = (setting == 'on')
        await update.message.reply_text(f"✓ URL blocking: {setting.upper()}")
    else:
        await update.message.reply_text("Use: /seturl on or /seturl off")

async def set_mention_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggle @mention blocking"""
    if not await is_user_admin(update.effective_chat.id, update.effective_user.id, context):
        await update.message.reply_text("⚠️ Only admins can change settings!")
        return

    if len(context.args) == 0:
        await update.message.reply_text("Usage: /setmention <on/off>")
        return

    setting = context.args[0].lower()
    if setting in ['on', 'off']:
        if 'settings' not in context.bot_data:
            context.bot_data['settings'] = config.DEFAULT_SETTINGS.copy()
        context.bot_data['settings']['mention_blocking'] = (setting == 'on')
        await update.message.reply_text(f"✓ @Mention blocking: {setting.upper()}")
    else:
        await update.message.reply_text("Use: /setmention on or /setmention off")

async def set_tags_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggle user tag blocking"""
    if not await is_user_admin(update.effective_chat.id, update.effective_user.id, context):
        await update.message.reply_text("⚠️ Only admins can change settings!")
        return

    if len(context.args) == 0:
        await update.message.reply_text("Usage: /settags <on/off>")
        return

    setting = context.args[0].lower()
    if setting in ['on', 'off']:
        if 'settings' not in context.bot_data:
            context.bot_data['settings'] = config.DEFAULT_SETTINGS.copy()
        context.bot_data['settings']['tag_blocking'] = (setting == 'on')
        await update.message.reply_text(f"✓ User tag blocking: {setting.upper()}")
    else:
        await update.message.reply_text("Use: /settags on or /settags off")

async def set_sticker_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggle sticker spam detection"""
    if not await is_user_admin(update.effective_chat.id, update.effective_user.id, context):
        await update.message.reply_text("⚠️ Only admins can change settings!")
        return

    if len(context.args) == 0:
        await update.message.reply_text("Usage: /setsticker <on/off>")
        return

    setting = context.args[0].lower()
    if setting in ['on', 'off']:
        if 'settings' not in context.bot_data:
            context.bot_data['settings'] = config.DEFAULT_SETTINGS.copy()
        context.bot_data['settings']['sticker_blocking'] = (setting == 'on')
        await update.message.reply_text(f"✓ Sticker spam detection: {setting.upper()}")
    else:
        await update.message.reply_text("Use: /setsticker on or /setsticker off")

async def set_sensitivity_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set ML sensitivity threshold"""
    if not await is_user_admin(update.effective_chat.id, update.effective_user.id, context):
        await update.message.reply_text("⚠️ Only admins can change settings!")
        return

    try:
        if len(context.args) == 0:
            current = context.bot_data.get('settings', {}).get('threshold', 0.5)
            await update.message.reply_text(f"Current sensitivity: {current}\nUsage: /setsensitivity <0.1-0.9>")
            return

        threshold = float(context.args[0])
        if 0.1 <= threshold <= 0.9:
            if 'settings' not in context.bot_data:
                context.bot_data['settings'] = config.DEFAULT_SETTINGS.copy()
            context.bot_data['settings']['threshold'] = threshold
            await update.message.reply_text(f"✓ ML sensitivity: {threshold}")
        else:
            await update.message.reply_text("⚠️ Value: 0.1 to 0.9")
    except ValueError:
        await update.message.reply_text("⚠️ Invalid! Use: /setsensitivity 0.5")