# 🤖 Telegram Spam Detector Bot

**Industry-Standard Professional Spam Detection System**

Advanced Telegram bot with AI/ML-powered spam detection, auto-ban system, smart learning, and multi-language support.

---

## ✨ Features

### 🚨 Auto-Ban System (3-Strike Rule)
- Automatic strike tracking per user
- Configurable strike limit (default: 3)
- Auto-reset after 24 hours
- Permanent ban on strike limit
- Admin unban control

### 🧠 Smart Learning System
- Learns from user feedback
- Adapts to new spam patterns
- False positive correction
- Continuous improvement

### 🛡️ Multi-Layer Protection
- **ML Model Detection** - PyTorch neural network
- **Keyword Detection** - Multi-language (EN/HI/TA)
- **URL Blocking** - Detects and blocks links
- **@Mention Blocking** - Prevents mention spam
- **User Tag Blocking** - Blocks user tagging
- **Image/Sticker Spam** - Media spam detection

### 👥 Whitelist System
- Admins auto-whitelisted
- Manual whitelist management
- Bypass all spam checks

### 💬 Custom Welcome Messages
- Personalized welcome for new members
- Template variables: `{name}`, `{group}`, `{mention}`
- Enable/disable toggle

---

## 📦 Installation

### 1. Clone Repository
```bash
git clone https://github.com/yourusername/telegram-spam-bot.git
cd telegram-spam-bot
2. Install Dependencies
pip install -r requirements.txt
3. Configure Bot
Edit config.py:
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"  # Get from @BotFather
4. Run Bot
python main.py
🎮 Usage
Setup in Group
Add bot to your Telegram group
Make bot admin with "Delete Messages" permission
Bot automatically starts protecting!
Commands
Basic Commands
/start - Bot information
/help - Full command list
/stats - View statistics
/settings - Current settings
Protection Settings
/setwelcome on/off - Toggle welcome messages
/seturl on/off - Toggle URL blocking
/setmention on/off - Toggle @mention blocking
/settags on/off - Toggle user tag blocking
/setsticker on/off - Toggle sticker spam
/setsensitivity 0.5 - Set ML threshold (0.1-0.9)
Ban Management
/strikes [user_id] - Check strikes
/resetstrikes <user_id> - Reset strikes (admin)
/banlist - View banned users
/unban <user_id> - Unban user (admin)
/strikelimit <number> - Set strike limit (admin)
Smart Learning
/notspam <message> - Report false positive
/reportspam - Report missed spam (reply to message)
/learningstats - View learning data
/resetlearning - Reset learning (admin)
Whitelist
/whitelist - View whitelisted users
/addwhitelist <user_id> - Add user
/removewhitelist <user_id> - Remove user
Custom Welcome
/customwelcome <message> - Set custom welcome
/resetwelcome - Reset to default
📊 Architecture
telegram-spam-bot/
├── main.py                 # Entry point
├── config.py              # Configuration
├── models/
│   └── spam_classifier.py # ML model
├── systems/
│   ├── auto_ban.py        # Auto-ban system
│   ├── smart_learning.py  # Learning system
│   └── spam_detection.py  # Spam detection
├── handlers/
│   ├── commands.py        # Command handlers
│   ├── messages.py        # Message handlers
│   └── admin.py           # Admin commands
├── utils/
│   ├── text_processing.py # Text utilities
│   ├── validators.py      # Validation
│   └── logger.py          # Logging
└── data/
    ├── keywords.py        # Spam keywords
    └── templates.py       # Message templates
⚙️ Configuration
Strike System
# config.py
STRIKE_LIMIT = 3              # Strikes before ban
STRIKE_RESET_HOURS = 24       # Reset interval
ML Model
ML_SENSITIVITY = 0.5          # Detection threshold
MODEL_INPUT_SIZE = 150        # Feature size
TRAINING_EPOCHS = 300         # Training iterations
🧪 Testing
Test Spam Detection
# Safe messages (won't be deleted)
"Hey, how are you?"
"Meeting at 3pm"
"Can you send the file?"

# Spam messages (will be deleted)
"Nude vc available"
"35rs video call"
"DM for services"
Test Strike System
User sends spam → Strike 1
User sends spam again → Strike 2
User sends spam third time → BANNED
📝 Data Files
Bot creates these files automatically:
spam_model.pth - Trained ML model
vectorizer.pkl - Text vectorizer
ban_data.pkl - Ban/strike data
learning_data.pkl - Learning data
deletion_log.txt - Deletion logs
🔒 Security
Admins automatically whitelisted
Banned users silently ignored
All data encrypted at rest
No external API calls
Privacy-focused design
🤝 Contributing
Fork the repository
Create feature branch (git checkout -b feature/amazing-feature)
Commit changes (git commit -m 'Add amazing feature')
Push to branch (git push origin feature/amazing-feature)
Open Pull Request
📄 License
MIT License - See LICENSE file
👨‍💻 Author
Created with ❤️ using PyTorch + Python-Telegram-Bot
🙏 Acknowledgments
Python Telegram Bot Library
PyTorch Team
Scikit-learn
Open Source Community
📞 Support
Report bugs: GitHub Issues
Feature requests: GitHub Discussions
Telegram: @yourusername
Made with ❤️ using PyTorch + Smart AI