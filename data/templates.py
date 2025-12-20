"""
Message templates for bot responses
"""

DEFAULT_WELCOME = """
👋 Welcome {name}!

🎉 Welcome to {group}!

📌 Group Rules:
✅ Be respectful
✅ No spam
✅ No adult content
✅ No external links
✅ No @mentions spam

🤖 I keep the group clean!

Enjoy! 😊
"""

START_MESSAGE = """
🤖 *Ultra Advanced Spam Detector Bot*

*🆕 Auto-Ban System (3-Strike):*
✅ 3 strikes → Permanent ban
✅ Strike tracking per user
✅ Auto-reset after 24 hours
✅ Admin unban control

*Smart Learning:*
✅ Learns from mistakes
✅ User feedback integration
✅ Auto-updating keywords

*Core Features:*
✅ Whitelist System
✅ Custom Welcome
✅ Image/Sticker Detection
✅ Multi-Language (EN/HI/TA)
✅ URL/Link Blocking

*Ban Commands:*
/strikes - Check your strikes
/banlist - View banned users
/unban <id> - Unban user (admin)

*All Commands:*
/help - Full command list

Made with ❤️ using PyTorch + Smart AI
"""

HELP_MESSAGE = """
📚 *All Commands*

*🚨 Auto-Ban System:*
/strikes [user_id] - Check strikes
/resetstrikes <user_id> - Reset strikes (admin)
/banlist - View banned users
/unban <user_id> - Unban user (admin)
/strikelimit <number> - Set strike limit (admin)

*🧠 Smart Learning:*
/notspam <message> - Report false positive
/reportspam - Report missed spam (reply)
/learningstats - View learning data
/resetlearning - Reset learning (admin)

*Settings:*
/settings - View all settings
/setwelcome on/off - Toggle welcome
/seturl on/off - Toggle URL blocking
/setmention on/off - Toggle @mention
/settags on/off - Toggle user tags
/setsticker on/off - Toggle sticker spam
/setsensitivity <0.1-0.9> - ML threshold

*Whitelist:*
/whitelist - View whitelisted users
/addwhitelist <user_id> - Add user
/removewhitelist <user_id> - Remove user

*Custom Welcome:*
/customwelcome <message> - Set custom
/resetwelcome - Reset to default

*Info:*
/stats - Bot statistics
"""