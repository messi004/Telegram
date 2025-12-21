"""
Telegram Spam Detector Bot - Main Entry Point
Professional Industry Standard Architecture
"""
import nest_asyncio
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ChatMemberHandler

# Import configuration
import config

# Import models
from models.spam_classifier import load_spam_model

# Import systems
from systems.smart_learning import SmartLearning
from systems.auto_ban import AutoBan

# Import bot commands setup
from utils.bot_commands import setup_bot_commands, setup_categorized_commands

# Import handlers
from handlers.commands import (
    start_command, help_command, stats_command, settings_command,
    set_welcome_command, set_url_command, set_mention_command,
    set_tags_command, set_sticker_command, set_sensitivity_command
)
from handlers.admin import (
    whitelist_command, addwhitelist_command, removewhitelist_command, clearwhitelist_command,
    strikes_command, resetstrikes_command, banlist_command, unban_command, strikelimit_command,
    notspam_command, reportspam_command, learningstats_command, resetlearning_command,
    customwelcome_command, resetwelcome_command
)
from handlers.messages import check_message, check_media, welcome_new_member

# Apply nest_asyncio for compatibility
nest_asyncio.apply()

# Initialize systems
smart_learning = SmartLearning()
auto_ban = AutoBan()
model = None
vectorizer = None

def print_startup_banner():
    """Print bot startup information"""
    print("\n" + "="*60)
    print("✓ Ultra Advanced Spam Detector Bot Running!")
    print("="*60)
    print("\n🆕 AUTO-BAN SYSTEM:")
    print(f"  🚨 {auto_ban.strike_limit}-Strike Rule Active")
    print(f"  ⏰ Strikes reset after {auto_ban.reset_interval_hours} hours")
    print("  ⛔ Automatic permanent ban")
    print(f"  📊 {len(auto_ban.banned_users)} users currently banned")
    print(f"  📊 {len(auto_ban.user_strikes)} users with active strikes")
    print("\n🧠 SMART LEARNING SYSTEM:")
    print("  🔄 Auto-updates spam patterns")
    print("  📈 Improves detection over time")
    print(f"  📊 {len(smart_learning.learned_spam_patterns)} spam patterns")
    print(f"  📊 {len(smart_learning.learned_safe_patterns)} safe patterns")
    print("\n📋 ALL FEATURES:")
    print("  ✅ Auto-Ban System (3-Strike)")
    print("  ✅ Smart Learning System")
    print("  ✅ Whitelist (Admins auto)")
    print("  ✅ Custom Welcome Messages")
    print("  ✅ Image/Sticker Detection")
    print("  ✅ Multi-Language (EN/HI/TA)")
    print("  ✅ AI/ML Spam Detection")
    print("  ✅ URL/Link Blocking")
    print("  ✅ @Mention Blocking")
    print("\n🎮 Commands Menu:")
    print("  ✅ Telegram commands menu configured")
    print("  💡 Type / in Telegram to see all commands")
    print("\nPress Ctrl+C to stop")
    print("="*60 + "\n")

def setup_handlers(app):
    """Setup all command and message handlers"""
    
    # Basic commands
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("stats", lambda u, c: stats_command(u, c, smart_learning)))
    app.add_handler(CommandHandler("settings", settings_command))
    
    # Setting commands
    app.add_handler(CommandHandler("setwelcome", set_welcome_command))
    app.add_handler(CommandHandler("seturl", set_url_command))
    app.add_handler(CommandHandler("setmention", set_mention_command))
    app.add_handler(CommandHandler("settags", set_tags_command))
    app.add_handler(CommandHandler("setsticker", set_sticker_command))
    app.add_handler(CommandHandler("setsensitivity", set_sensitivity_command))
    
    # Whitelist commands
    app.add_handler(CommandHandler("whitelist", whitelist_command))
    app.add_handler(CommandHandler("addwhitelist", addwhitelist_command))
    app.add_handler(CommandHandler("removewhitelist", removewhitelist_command))
    app.add_handler(CommandHandler("clearwhitelist", clearwhitelist_command))
    
    # Ban commands
    app.add_handler(CommandHandler("strikes", lambda u, c: strikes_command(u, c, auto_ban)))
    app.add_handler(CommandHandler("resetstrikes", lambda u, c: resetstrikes_command(u, c, auto_ban)))
    app.add_handler(CommandHandler("banlist", lambda u, c: banlist_command(u, c, auto_ban)))
    app.add_handler(CommandHandler("unban", lambda u, c: unban_command(u, c, auto_ban)))
    app.add_handler(CommandHandler("strikelimit", lambda u, c: strikelimit_command(u, c, auto_ban)))
    
    # Learning commands
    app.add_handler(CommandHandler("notspam", lambda u, c: notspam_command(u, c, smart_learning)))
    app.add_handler(CommandHandler("reportspam", lambda u, c: reportspam_command(u, c, smart_learning)))
    app.add_handler(CommandHandler("learningstats", lambda u, c: learningstats_command(u, c, smart_learning)))
    app.add_handler(CommandHandler("resetlearning", lambda u, c: resetlearning_command(u, c, smart_learning)))
    
    # Custom welcome commands
    app.add_handler(CommandHandler("customwelcome", customwelcome_command))
    app.add_handler(CommandHandler("resetwelcome", resetwelcome_command))
    
    # Message handlers
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))
    app.add_handler(MessageHandler(
        (filters.PHOTO | filters.Sticker.ALL) & ~filters.COMMAND,
        lambda u, c: check_media(u, c, model, vectorizer, smart_learning, auto_ban)
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        lambda u, c: check_message(u, c, model, vectorizer, smart_learning, auto_ban)
    ))

def main():
    """Main function - Entry point"""
    global model, vectorizer
    
    print("🚀 Bot starting...")
    
    # Load smart learning data
    smart_learning.load_learning_data()
    
    # Load auto-ban data
    auto_ban.load_ban_data()
    
    # Load ML model
    model, vectorizer = load_spam_model()
    print("✓ Model loaded!")
    
    # Validate bot token
    if config.BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("\n⚠️ ERROR: Please set your bot token in config.py!")
        print("Get token from @BotFather on Telegram")
        return
    
    # Create application
    app = Application.builder().token(config.BOT_TOKEN).build()
    
    # Setup all handlers
    setup_handlers(app)
    
    # Setup bot commands menu
    import asyncio
    loop = asyncio.get_event_loop()
    
    # Choose setup method:
    # Option 1: All commands (simple)
    loop.run_until_complete(setup_bot_commands(app.bot, mode='all'))
    
    # Option 2: Categorized (groups vs private) - Uncomment to use
    # loop.run_until_complete(setup_categorized_commands(app.bot))
    
    # Print startup banner
    print_startup_banner()
    
    # Start bot
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n✓ Bot stopped gracefully!")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")