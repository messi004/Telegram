"""
Message handlers for spam detection
"""
import asyncio
from telegram import Update
from telegram.ext import ContextTypes
from utils.text_processing import contains_url, contains_mentions, has_user_tags
from utils.validators import is_whitelisted, is_user_admin
from utils.logger import log_deletion
from systems.spam_detection import is_spam
import config

async def check_message(update: Update, context: ContextTypes.DEFAULT_TYPE, model, vectorizer, smart_learning, auto_ban):
    """Main message handler with spam detection"""
    if not update.message or not update.message.text:
        return

    message_text = update.message.text
    chat_id = update.message.chat_id
    message_id = update.message.message_id
    user = update.message.from_user
    entities = update.message.entities

    # Initialize stats
    if 'stats' not in context.bot_data:
        context.bot_data['stats'] = {
            'messages_scanned': 0, 'spam_detected': 0, 'messages_deleted': 0,
            'ml_detections': 0, 'keyword_detections': 0, 'severe_detections': 0,
            'url_blocked': 0, 'mention_blocked': 0, 'tag_blocked': 0,
            'sticker_blocked': 0, 'image_blocked': 0
        }

    if 'settings' not in context.bot_data:
        context.bot_data['settings'] = config.DEFAULT_SETTINGS.copy()

    if 'whitelist' not in context.bot_data:
        context.bot_data['whitelist'] = set()

    context.bot_data['stats']['messages_scanned'] += 1

    # Check if user is banned
    if auto_ban.is_banned(user.id):
        return

    # Check if user is whitelisted
    if is_whitelisted(user.id, context):
        return

    # Check if user is admin (auto-whitelist)
    if await is_user_admin(chat_id, user.id, context):
        context.bot_data['whitelist'].add(user.id)
        return

    settings = context.bot_data['settings']
    delete_reason = None

    # Check URLs
    if settings.get('url_blocking', True):
        has_url, url_type = contains_url(message_text)
        if has_url:
            delete_reason = f"URL_blocked ({url_type})"
            context.bot_data['stats']['url_blocked'] += 1

    # Check @mentions
    if not delete_reason and settings.get('mention_blocking', True):
        has_mention, mentions = contains_mentions(message_text)
        if has_mention:
            delete_reason = f"@mention_blocked ({len(mentions)} mentions)"
            context.bot_data['stats']['mention_blocked'] += 1

    # Check user tags
    if not delete_reason and settings.get('tag_blocking', True):
        if has_user_tags(entities):
            delete_reason = "user_tag_blocked"
            context.bot_data['stats']['tag_blocked'] += 1

    # Check spam
    if not delete_reason:
        threshold = settings.get('threshold', 0.5)
        spam, confidence, method, keywords = is_spam(message_text, model, vectorizer, smart_learning, threshold)

        if spam:
            delete_reason = f"spam ({method})"
            context.bot_data['stats']['spam_detected'] += 1

            if 'severe' in method:
                context.bot_data['stats']['severe_detections'] += 1
            elif 'keyword' in method or 'explicit' in method:
                context.bot_data['stats']['keyword_detections'] += 1
            elif 'ml' in method:
                context.bot_data['stats']['ml_detections'] += 1

    # Delete if violation found
    if delete_reason:
        await handle_violation(update, context, delete_reason, auto_ban, message_text)

async def handle_violation(update, context, delete_reason, auto_ban, message_text):
    """Handle message violation - delete and apply strikes"""
    chat_id = update.message.chat_id
    message_id = update.message.message_id
    user = update.message.from_user

    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        context.bot_data['stats']['messages_deleted'] += 1

        # Add strike
        strikes, should_ban = auto_ban.add_strike(user.id, user.first_name, delete_reason, message_text)

        if should_ban and not auto_ban.is_banned(user.id):
            await ban_user(update, context, user, strikes, auto_ban)
        else:
            await send_warning(context, chat_id, user, delete_reason, strikes, auto_ban)

        auto_ban.save_ban_data()
        log_deletion(user, message_text, delete_reason)

    except Exception as e:
        error_msg = str(e).lower()
        if "not found" not in error_msg:
            print(f"Error: {e}")

async def ban_user(update, context, user, strikes, auto_ban):
    """Ban user from group"""
    try:
        await context.bot.ban_chat_member(chat_id=update.message.chat_id, user_id=user.id)
        auto_ban.ban_user(user.id)

        ban_msg = f"🚫 *USER BANNED*\n\n"
        ban_msg += f"User: {user.first_name} (ID: {user.id})\n"
        ban_msg += f"Reason: {auto_ban.strike_limit} strikes reached\n"
        ban_msg += f"Total Violations: {strikes}\n\n"
        ban_msg += f"⛔ User has been permanently banned from the group"

        await context.bot.send_message(chat_id=update.message.chat_id, text=ban_msg, parse_mode='Markdown')
    except Exception as e:
        print(f"Ban error: {e}")

async def send_warning(context, chat_id, user, delete_reason, strikes, auto_ban):
    """Send strike warning to user"""
    warning_text = f"⚠️ WARNING - STRIKE {strikes}/{auto_ban.strike_limit}\n\n"
    warning_text += f"User: {user.first_name}\n"
    warning_text += f"Reason: {delete_reason}\n"
    warning_text += f"\n✓ Message deleted\n"
    warning_text += f"⚠️ {auto_ban.strike_limit - strikes} strike(s) remaining before BAN"

    warning_msg = await context.bot.send_message(chat_id=chat_id, text=warning_text)

    await asyncio.sleep(7)
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=warning_msg.message_id)
    except:
        pass

async def check_media(update: Update, context: ContextTypes.DEFAULT_TYPE, model, vectorizer, smart_learning, auto_ban):
    """Handle image and sticker spam"""
    if not update.message:
        return

    user = update.message.from_user
    chat_id = update.message.chat_id
    message_id = update.message.message_id

    if 'stats' not in context.bot_data:
        context.bot_data['stats'] = {'sticker_blocked': 0, 'image_blocked': 0}

    if 'settings' not in context.bot_data:
        context.bot_data['settings'] = config.DEFAULT_SETTINGS.copy()

    # Check whitelist/admin
    if is_whitelisted(user.id, context) or await is_user_admin(chat_id, user.id, context):
        return

    settings = context.bot_data['settings']
    delete_reason = None

    # Check stickers (3+ is spam)
    if update.message.sticker and settings.get('sticker_blocking', True):
        user_key = f'sticker_count_{user.id}'
        sticker_count = context.bot_data.get(user_key, 0) + 1
        context.bot_data[user_key] = sticker_count

        if sticker_count >= 3:
            delete_reason = "sticker_spam"
            context.bot_data['stats']['sticker_blocked'] += 1
            context.bot_data[user_key] = 0

    # Check image captions
    if update.message.photo and update.message.caption:
        caption = update.message.caption
        spam, confidence, method, keywords = is_spam(caption, model, vectorizer, smart_learning, 0.4)
        if spam:
            delete_reason = f"image_spam ({method})"
            context.bot_data['stats']['image_blocked'] += 1

    if delete_reason:
        await handle_media_violation(update, context, delete_reason, auto_ban)

async def handle_media_violation(update, context, delete_reason, auto_ban):
    """Handle media violation"""
    chat_id = update.message.chat_id
    message_id = update.message.message_id
    user = update.message.from_user

    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        context.bot_data['stats']['messages_deleted'] += 1

        strikes, should_ban = auto_ban.add_strike(user.id, user.first_name, delete_reason, "[Media]")

        if should_ban and not auto_ban.is_banned(user.id):
            await ban_user(update, context, user, strikes, auto_ban)
        else:
            await send_warning(context, chat_id, user, delete_reason, strikes, auto_ban)

        auto_ban.save_ban_data()
    except Exception as e:
        if "not found" not in str(e).lower():
            print(f"Media error: {e}")

async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcome new members"""
    from data.templates import DEFAULT_WELCOME
    
    settings = context.bot_data.get('settings', {})
    if not settings.get('welcome_enabled', True):
        return

    for member in update.message.new_chat_members:
        if member.is_bot:
            continue

        custom_welcome = context.bot_data.get('custom_welcome', DEFAULT_WELCOME)
        welcome_msg = custom_welcome.replace('{name}', member.first_name)
        welcome_msg = welcome_msg.replace('{group}', update.effective_chat.title or 'the group')
        welcome_msg = welcome_msg.replace('{mention}', f'@{member.username}' if member.username else member.first_name)

        try:
            await update.message.reply_text(welcome_msg)
        except Exception as e:
            print(f"Welcome error: {e}")