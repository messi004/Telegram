"""
Bot Commands Menu Configuration
Telegram me commands menu show karne ke liye
"""
from telegram import BotCommand

# === Basic Commands (Everyone) ===
BASIC_COMMANDS = [
    BotCommand("start", "🤖 Bot information and features"),
    BotCommand("help", "📚 Complete command list"),
    BotCommand("stats", "📊 Bot statistics and analytics"),
]

# === User Commands ===
USER_COMMANDS = [
    BotCommand("strikes", "⚠️ Check your current strikes"),
    BotCommand("learningstats", "🧠 Smart learning statistics"),
    BotCommand("notspam", "✅ Report false positive"),
    BotCommand("reportspam", "🚫 Report missed spam"),
]

# === Settings Commands (Admin) ===
SETTINGS_COMMANDS = [
    BotCommand("settings", "⚙️ View current settings"),
    BotCommand("setwelcome", "👋 Toggle welcome (on/off)"),
    BotCommand("seturl", "🔗 Toggle URL blocking (on/off)"),
    BotCommand("setmention", "@ Toggle mention blocking (on/off)"),
    BotCommand("settags", "👤 Toggle tag blocking (on/off)"),
    BotCommand("setsticker", "😀 Toggle sticker spam (on/off)"),
    BotCommand("setsensitivity", "🎯 Set ML threshold (0.1-0.9)"),
]

# === Whitelist Commands (Admin) ===
WHITELIST_COMMANDS = [
    BotCommand("whitelist", "✅ View whitelisted users"),
    BotCommand("addwhitelist", "➕ Add user to whitelist"),
    BotCommand("removewhitelist", "➖ Remove from whitelist"),
    BotCommand("clearwhitelist", "🗑️ Clear whitelist"),
]

# === Ban System Commands (Admin) ===
BAN_COMMANDS = [
    BotCommand("banlist", "🚫 View all banned users"),
    BotCommand("resetstrikes", "🔄 Reset user strikes"),
    BotCommand("unban", "✅ Unban a user"),
    BotCommand("strikelimit", "⚙️ Set strike limit"),
]

# === Welcome Commands (Admin) ===
WELCOME_COMMANDS = [
    BotCommand("customwelcome", "✏️ Set custom welcome message"),
    BotCommand("resetwelcome", "🔄 Reset to default welcome"),
]

# === Mass Tag Commands (Admin) ===
MASS_TAG_COMMANDS = [
    BotCommand("tagall", "👥 Tag all members"),
    BotCommand("tagadmins", "👮 Tag only admins"),
    BotCommand("tagonline", "🟢 Tag active members"),
    BotCommand("tagstats", "📊 Group statistics"),
]

# === delete accounts Commands (Admin) ===
DELETE_ACCOUNTS_COMMANDS = [
    BotCommand("scandeleted", "deleted accounts removed"),
    BotCommand("resetsession", "Session delete"),
]    

# === All Commands Combined ===
ALL_COMMANDS = (
    BASIC_COMMANDS + 
    USER_COMMANDS + 
    SETTINGS_COMMANDS + 
    WHITELIST_COMMANDS + 
    BAN_COMMANDS + 
    WELCOME_COMMANDS +
    MASS_TAG_COMMANDS +
    DELETE_ACCOUNTS_COMMANDS
)

# === User-Only Commands (Non-Admin) ===
USER_ONLY_COMMANDS = BASIC_COMMANDS + USER_COMMANDS

# === Admin-Only Commands ===
ADMIN_ONLY_COMMANDS = (
    BASIC_COMMANDS + 
    USER_COMMANDS + 
    SETTINGS_COMMANDS + 
    WHITELIST_COMMANDS + 
    BAN_COMMANDS + 
    WELCOME_COMMANDS +
    MASS_TAG_COMMANDS +
    DELETE_ACCOUNTS_COMMANDS
    
)


async def setup_bot_commands(bot, mode='all'):
    """
    Setup bot commands menu
    
    Args:
        bot: Telegram Bot instance
        mode: 'all', 'user', 'admin'
    """
    try:
        if mode == 'all':
            await bot.set_my_commands(ALL_COMMANDS)
            print(f"✓ Bot commands menu set! ({len(ALL_COMMANDS)} commands)")
        elif mode == 'user':
            await bot.set_my_commands(USER_ONLY_COMMANDS)
            print(f"✓ User commands menu set! ({len(USER_ONLY_COMMANDS)} commands)")
        elif mode == 'admin':
            await bot.set_my_commands(ADMIN_ONLY_COMMANDS)
            print(f"✓ Admin commands menu set! ({len(ADMIN_ONLY_COMMANDS)} commands)")
        else:
            print(f"⚠️ Unknown mode: {mode}")
            return False
        
        return True
    except Exception as e:
        print(f"❌ Failed to set commands: {e}")
        return False


async def setup_categorized_commands(bot):
    """
    Setup different commands for different scopes
    (Groups vs Private chats)
    """
    from telegram import BotCommandScopeAllGroupChats, BotCommandScopeAllPrivateChats
    
    try:
        # Commands for private chats (detailed)
        await bot.set_my_commands(ALL_COMMANDS, scope=BotCommandScopeAllPrivateChats())
        print(f"✓ Private chat commands set! ({len(ALL_COMMANDS)} commands)")
        
        # Commands for groups (essential only)
        group_commands = BASIC_COMMANDS + [
            BotCommand("strikes", "⚠️ Check strikes"),
            BotCommand("settings", "⚙️ Settings"),
            BotCommand("banlist", "🚫 Banned users"),
        ]
        await bot.set_my_commands(group_commands, scope=BotCommandScopeAllGroupChats())
        print(f"✓ Group commands set! ({len(group_commands)} commands)")
        
        return True
    except Exception as e:
        print(f"❌ Failed to set categorized commands: {e}")
        return False


async def remove_bot_commands(bot):
    """Remove all bot commands"""
    try:
        await bot.delete_my_commands()
        print("✓ Bot commands removed!")
        return True
    except Exception as e:
        print(f"❌ Failed to remove commands: {e}")
        return False


def get_command_list_text():
    """Get formatted text of all commands"""
    text = "📋 *Bot Commands List*\n\n"
    
    text += "*🎯 Basic Commands:*\n"
    for cmd in BASIC_COMMANDS:
        text += f"/{cmd.command} - {cmd.description}\n"
    
    text += "\n*👤 User Commands:*\n"
    for cmd in USER_COMMANDS:
        text += f"/{cmd.command} - {cmd.description}\n"
    
    text += "\n*⚙️ Settings (Admin):*\n"
    for cmd in SETTINGS_COMMANDS:
        text += f"/{cmd.command} - {cmd.description}\n"
    
    text += "\n*✅ Whitelist (Admin):*\n"
    for cmd in WHITELIST_COMMANDS:
        text += f"/{cmd.command} - {cmd.description}\n"
    
    text += "\n*🚫 Ban System (Admin):*\n"
    for cmd in BAN_COMMANDS:
        text += f"/{cmd.command} - {cmd.description}\n"
    
    text += "\n*👋 Welcome (Admin):*\n"
    for cmd in WELCOME_COMMANDS:
        text += f"/{cmd.command} - {cmd.description}\n"
    
    return text


# Command categories for easy access
COMMAND_CATEGORIES = {
    'basic': BASIC_COMMANDS,
    'user': USER_COMMANDS,
    'settings': SETTINGS_COMMANDS,
    'whitelist': WHITELIST_COMMANDS,
    'ban': BAN_COMMANDS,
    'welcome': WELCOME_COMMANDS,
}


def get_commands_by_category(category):
    """Get commands by category name"""
    return COMMAND_CATEGORIES.get(category, [])


def get_all_command_names():
    """Get list of all command names (without /)"""
    return [cmd.command for cmd in ALL_COMMANDS]


def is_valid_command(command_name):
    """Check if command exists"""
    return command_name in get_all_command_names()