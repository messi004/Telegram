import torch
import torch.nn as nn
from telegram import Update, ChatMemberUpdated
from telegram.ext import Application, MessageHandler, CommandHandler, ContextTypes, filters, ChatMemberHandler
from telegram.constants import ChatMemberStatus
import string
import pickle
import os
from datetime import datetime, timedelta
import nest_asyncio
import re

# Device configuration
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

# Spam Classifier Model
class SpamClassifier(nn.Module):
    def __init__(self, input_size):
        super(SpamClassifier, self).__init__()
        self.fc1 = nn.Linear(input_size, 64)
        self.fc2 = nn.Linear(64, 32)
        self.fc3 = nn.Linear(32, 1)
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(0.3)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        x = self.relu(self.fc1(x))
        x = self.dropout(x)
        x = self.relu(self.fc2(x))
        x = self.dropout(x)
        x = self.sigmoid(self.fc3(x))
        return x

# Multi-language spam keywords
EXPLICIT_KEYWORDS = {
    'english': [
        'nude', 'sex chat', 'video call', 'vc', 'escort', 'call girl',
        'massage', 'satisfaction', 'dating', 'hot', 'sexy', 'naughty',
        'adult', 'erotic', 'xxx', 'porn', 'nsfw', 'hookup', 'one night',
        'dm me', 'message me', 'msg me', 'earning', 'investment', 'money',
        'cash', 'paid', 'payment', 'collab', 'available for',
        'child', 'minor', 'underage', 'kid', 'teen',
        'free live', 'profile dekho', 'hard core', 'real meet',
        'available now', 'dm for', 'msg for'
    ],
    'hindi': [
        'नंबर लेना', 'आंटी', 'भाभी', 'सर्विस', 'कॉल करो',
        'मैसेज करो', 'डीएम करो', 'पैसे कमाओ', 'कमाई',
        'फ्री', 'मुफ्त', 'लड़की', 'लड़कियां', 'मिलो',
        'aunty', 'bhabhi', 'ladki', 'ladkiya', 'service',
        'kamao', 'paisa', 'free me', 'milna hai', 'number lena'
    ],
    'tamil': [
        'பெண்', 'சேவை', 'கால்', 'செய்தி', 'பணம்', 'இலவசம்',
        'pen', 'sevai', 'call', 'seythi', 'panam', 'ilavasam'
    ],
    'patterns': [
        r'\d+\s*(₹|rs|rupees)', r'(₹|rs)\s*\d+',
        r'(.)\1{4,}',
        r'(dm|msg|message|call)\s*(me|karo|here)',
    ]
}

SEVERE_KEYWORDS = [
    'child', 'minor', 'underage', 'kid', 'cp', 'child porn',
    'school girl', 'college girl', 'hostel girl', 'young girl',
    'बच्चा', 'नाबालिग', 'குழந்தை'
]

# Default welcome message
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

# Smart Learning Class
class SmartLearning:
    def __init__(self):
        self.false_positives = []
        self.false_negatives = []
        self.user_feedback = {}
        self.learned_spam_patterns = set()
        self.learned_safe_patterns = set()

    def add_false_positive(self, message):
        """Message wrongly marked as spam"""
        self.false_positives.append({
            'message': message,
            'timestamp': datetime.now().isoformat()
        })
        # Extract patterns from safe messages
        words = message.lower().split()
        for word in words:
            if len(word) > 3:
                self.learned_safe_patterns.add(word)

    def add_false_negative(self, message):
        """Spam that wasn't detected"""
        self.false_negatives.append({
            'message': message,
            'timestamp': datetime.now().isoformat()
        })
        # Extract spam patterns
        words = message.lower().split()
        for word in words:
            if len(word) > 3:
                self.learned_spam_patterns.add(word)

    def add_feedback(self, user_id, message, is_spam):
        """User feedback on detection"""
        key = f"{user_id}_{datetime.now().date()}"
        if key not in self.user_feedback:
            self.user_feedback[key] = []
        self.user_feedback[key].append({
            'message': message,
            'is_spam': is_spam,
            'timestamp': datetime.now().isoformat()
        })

    def get_learned_keywords(self):
        """Get newly learned spam keywords"""
        return list(self.learned_spam_patterns)[:20]  # Top 20

    def is_likely_safe(self, message):
        """Check if message matches safe patterns"""
        words = set(message.lower().split())
        safe_matches = words.intersection(self.learned_safe_patterns)
        return len(safe_matches) >= 2

    def save_learning_data(self):
        """Save learning data to file"""
        try:
            data = {
                'false_positives': self.false_positives,
                'false_negatives': self.false_negatives,
                'learned_spam_patterns': list(self.learned_spam_patterns),
                'learned_safe_patterns': list(self.learned_safe_patterns)
            }
            with open('learning_data.pkl', 'wb') as f:
                pickle.dump(data, f)
        except Exception as e:
            print(f"Save learning error: {e}")

    def load_learning_data(self):
        """Load learning data from file"""
        try:
            if os.path.exists('learning_data.pkl'):
                with open('learning_data.pkl', 'rb') as f:
                    data = pickle.load(f)
                self.false_positives = data.get('false_positives', [])
                self.false_negatives = data.get('false_negatives', [])
                self.learned_spam_patterns = set(data.get('learned_spam_patterns', []))
                self.learned_safe_patterns = set(data.get('learned_safe_patterns', []))
                print(f"✓ Loaded {len(self.learned_spam_patterns)} spam patterns")
                print(f"✓ Loaded {len(self.learned_safe_patterns)} safe patterns")
        except Exception as e:
            print(f"Load learning error: {e}")

# Initialize smart learning
smart_learning = SmartLearning()

# Auto-Ban System
class AutoBan:
    def __init__(self, strike_limit=3, reset_interval_hours=24):
        self.user_strikes = {}  # {user_id: {'count': int, 'last_strike_time': datetime, 'name': str, 'reasons': list}}
        self.banned_users = set() # {user_id}
        self.strike_limit = strike_limit
        self.reset_interval_hours = reset_interval_hours

    def add_strike(self, user_id, user_name, reason, message):
        current_time = datetime.now()
        if user_id not in self.user_strikes:
            self.user_strikes[user_id] = {'count': 0, 'last_strike_time': current_time, 'name': user_name, 'reasons': []}

        # Reset strikes if interval passed
        if (current_time - self.user_strikes[user_id]['last_strike_time']).total_seconds() / 3600 >= self.reset_interval_hours:
            self.user_strikes[user_id] = {'count': 0, 'last_strike_time': current_time, 'name': user_name, 'reasons': []}

        self.user_strikes[user_id]['count'] += 1
        self.user_strikes[user_id]['last_strike_time'] = current_time
        self.user_strikes[user_id]['reasons'].append({'time': current_time.isoformat(), 'reason': reason, 'message': message})

        strikes = self.user_strikes[user_id]['count']
        should_ban = strikes >= self.strike_limit
        return strikes, should_ban

    def get_strikes(self, user_id):
        return self.user_strikes.get(user_id, {'count': 0, 'name': 'Unknown', 'reasons': []})

    def ban_user(self, user_id):
        self.banned_users.add(user_id)
        if user_id in self.user_strikes:
            del self.user_strikes[user_id] # Clear strikes after ban

    def unban_user(self, user_id):
        if user_id in self.banned_users:
            self.banned_users.remove(user_id)
            return True
        return False

    def reset_strikes(self, user_id):
        if user_id in self.user_strikes:
            del self.user_strikes[user_id]
            return True
        return False

    def is_banned(self, user_id):
        return user_id in self.banned_users

    def save_ban_data(self):
        try:
            data = {
                'user_strikes': {k: {**v, 'last_strike_time': v['last_strike_time'].isoformat()} for k, v in self.user_strikes.items()},
                'banned_users': list(self.banned_users),
                'strike_limit': self.strike_limit,
                'reset_interval_hours': self.reset_interval_hours
            }
            with open('ban_data.pkl', 'wb') as f:
                pickle.dump(data, f)
        except Exception as e:
            print(f"Save ban data error: {e}")

    def load_ban_data(self):
        try:
            if os.path.exists('ban_data.pkl'):
                with open('ban_data.pkl', 'rb') as f:
                    data = pickle.load(f)
                self.user_strikes = {k: {**v, 'last_strike_time': datetime.fromisoformat(v['last_strike_time'])} for k, v in data.get('user_strikes', {}).items()}
                self.banned_users = set(data.get('banned_users', []))
                self.strike_limit = data.get('strike_limit', 3)
                self.reset_interval_hours = data.get('reset_interval_hours', 24)
                print(f"✓ Loaded {len(self.banned_users)} banned users and {len(self.user_strikes)} users with strikes.")
        except Exception as e:
            print(f"Load ban data error: {e}")

# Initialize auto_ban
auto_ban = AutoBan()

# Text preprocessing
def preprocess_text(text):
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    text = ' '.join(text.split())
    return text

# Check URLs
def contains_url(text):
    url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    simple_url = r'www\.[a-zA-Z0-9-]+\.[a-zA-Z]{2,}'
    domain = r'[a-zA-Z0-9-]+\.(com|org|net|in|co|io|xyz|info|biz|me|tv|app|online)'

    if re.search(url_pattern, text) or re.search(simple_url, text, re.IGNORECASE):
        return True, "url_link"
    if re.search(domain, text, re.IGNORECASE):
        return True, "domain_name"
    return False, None

# Check mentions
def contains_mentions(text):
    mention_pattern = r'@[a-zA-Z0-9_]{5,}'
    matches = re.findall(mention_pattern, text)
    return len(matches) > 0, matches

# Check user tags
def has_user_tags(entities):
    if not entities:
        return False
    for entity in entities:
        if entity.type == "text_mention" or entity.type == "mention":
            return True
    return False

# Multi-language explicit content detection
def contains_explicit_content(text):
    if not text:
        return False, 0, []

    text_lower = text.lower()
    text_normalized = re.sub(r'[^\w\s]', ' ', text_lower)

    matched_keywords = []
    severity_score = 0

    # Check severe keywords (all languages)
    for keyword in SEVERE_KEYWORDS:
        if keyword in text_normalized or keyword in text_lower:
            matched_keywords.append(keyword)
            severity_score += 10

    # Check English keywords
    for keyword in EXPLICIT_KEYWORDS['english']:
        if keyword in text_normalized or keyword in text_lower:
            matched_keywords.append(keyword)
            severity_score += 1

    # Check Hindi keywords
    for keyword in EXPLICIT_KEYWORDS['hindi']:
        if keyword in text or keyword in text_lower:
            matched_keywords.append(keyword)
            severity_score += 1

    # Check Tamil keywords
    for keyword in EXPLICIT_KEYWORDS['tamil']:
        if keyword in text:
            matched_keywords.append(keyword)
            severity_score += 1

    # Check patterns
    for pattern in EXPLICIT_KEYWORDS['patterns']:
        if re.search(pattern, text_lower):
            matched_keywords.append('pattern_match')
            severity_score += 2
            break

    if text.count('!') + text.count('?') > 3:
        matched_keywords.append('excessive_punctuation')
        severity_score += 1

    is_explicit = severity_score >= 2 or len(matched_keywords) >= 2

    return is_explicit, severity_score, matched_keywords

# Check if user is whitelisted
def is_whitelisted(user_id, context):
    whitelist = context.bot_data.get('whitelist', set())
    return user_id in whitelist

# Check if user is admin
async def is_user_admin(chat_id, user_id, context):
    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        return member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
    except:
        return False

# Train model (same as before)
def train_and_save_model():
    from sklearn.feature_extraction.text import TfidfVectorizer
    import torch.optim as optim

    print("Training spam detection model...")

    messages = [
        'Congratulations! You won a free iPhone. Click here to claim now',
        'URGENT! Your account will be closed. Verify now immediately',
        'Win $1000 cash prize! Call now to claim your reward',
        'FREE entry to our exclusive lottery. Limited time offer',
        'Nude video call and sex chat available',
        'Service available contact me now',
        'Available for vc boys message me',
        'DM for special services',
        'Call girls available in your area',
        'Aunty bhabhi number lena hai dm karo',
        'Paisa kamao ghar baithe',
        'Ladki chahiye to message karo',
        'Hey, are we meeting tomorrow?',
        'Can you pick up milk?',
        'Meeting at 3 PM conference room',
        'Thanks for your help yesterday',
        'What time is the movie?',
        'Good morning! Have a nice day',
        'Can I borrow your notes?',
        'See you at the meeting'
    ]

    labels = [1]*12 + [0]*8

    cleaned = [preprocess_text(msg) for msg in messages]
    vectorizer = TfidfVectorizer(max_features=150, min_df=1, ngram_range=(1, 2))
    X = vectorizer.fit_transform(cleaned).toarray()

    X_tensor = torch.FloatTensor(X).to(device)
    y_tensor = torch.FloatTensor(labels).to(device)

    input_size = X.shape[1]
    model = SpamClassifier(input_size).to(device)
    criterion = nn.BCELoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)

    for epoch in range(300):
        model.train()
        optimizer.zero_grad()
        outputs = model(X_tensor).squeeze()
        loss = criterion(outputs, y_tensor)
        loss.backward()
        optimizer.step()

        if (epoch + 1) % 50 == 0:
            print(f'Epoch [{epoch+1}/300], Loss: {loss.item():.4f}')

    model.eval()
    with torch.no_grad():
        predictions = (model(X_tensor).squeeze() > 0.5).float()
        accuracy = (predictions == y_tensor).float().mean().item() * 100
        print(f'Training Accuracy: {accuracy:.2f}%')

    torch.save({
        'model_state_dict': model.state_dict(),
        'input_size': input_size
    }, 'spam_model.pth')

    with open('vectorizer.pkl', 'wb') as f:
        pickle.dump(vectorizer, f)

    print("✓ Model saved!")
    return model, vectorizer

# Load model
def load_spam_model():
    try:
        if not os.path.exists('spam_model.pth') or not os.path.exists('vectorizer.pkl'):
            return train_and_save_model()

        with open('vectorizer.pkl', 'rb') as f:
            vectorizer = pickle.load(f)

        checkpoint = torch.load('spam_model.pth', map_location=device)
        input_size = checkpoint['input_size']

        model = SpamClassifier(input_size).to(device)
        model.load_state_dict(checkpoint['model_state_dict'])
        model.eval()

        print(f"✓ Model loaded! Input size: {input_size}")
        return model, vectorizer

    except Exception as e:
        print(f"Error loading model: {e}")
        return train_and_save_model()

# Enhanced spam detection with smart learning
def is_spam(text, model, vectorizer, threshold=0.5):
    if not text or len(text.strip()) == 0:
        return False, 0.0, "empty", []

    # Check if message matches learned safe patterns
    if smart_learning.is_likely_safe(text):
        return False, 0.0, "learned_safe", []

    is_explicit, severity_score, matched_keywords = contains_explicit_content(text)

    # Check learned spam patterns
    words = set(text.lower().split())
    learned_spam = words.intersection(smart_learning.learned_spam_patterns)
    if len(learned_spam) >= 2:
        matched_keywords.extend(list(learned_spam)[:3])
        severity_score += 3

    if severity_score >= 10:
        return True, 1.0, "severe_keywords", matched_keywords

    if is_explicit and severity_score >= 3:
        return True, 0.95, "explicit_keywords", matched_keywords

    try:
        cleaned = preprocess_text(text)
        vectorized = vectorizer.transform([cleaned]).toarray()
        input_tensor = torch.FloatTensor(vectorized).to(device)

        with torch.no_grad():
            ml_confidence = model(input_tensor).item()

        if ml_confidence > threshold:
            return True, ml_confidence, "ml_model", matched_keywords
        elif is_explicit:
            combined_confidence = max(ml_confidence, severity_score / 10)
            return True, combined_confidence, "combined", matched_keywords

        return False, ml_confidence, "safe", []

    except Exception as e:
        if is_explicit:
            return True, 0.8, "keyword_fallback", matched_keywords
        return False, 0.0, "error", []

# Welcome new members with custom message
async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    settings = context.bot_data.get('settings', {})
    if not settings.get('welcome_enabled', True):
        return

    for member in update.message.new_chat_members:
        if member.is_bot:
            continue

        # Get custom welcome message or use default
        custom_welcome = context.bot_data.get('custom_welcome', DEFAULT_WELCOME)

        # Replace placeholders
        welcome_msg = custom_welcome.replace('{name}', member.first_name)
        welcome_msg = welcome_msg.replace('{group}', update.effective_chat.title or 'the group')
        welcome_msg = welcome_msg.replace('{mention}', f'@{member.username}' if member.username else member.first_name)

        try:
            await update.message.reply_text(welcome_msg)
        except Exception as e:
            print(f"Welcome error: {e}")

# Track member status
async def track_member_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = extract_status_change(update.chat_member)
    if result is None:
        return

    was_member, is_member = result
    user = update.chat_member.new_chat_member.user

    if was_member and not is_member:
        try:
            if user.id == 0 or user.first_name == "Deleted Account":
                goodbye_msg = f"🗑️ Deleted account removed from group"
            else:
                goodbye_msg = f"👋 {user.first_name} left the group"

            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=goodbye_msg
            )
        except Exception as e:
            print(f"Member status error: {e}")

def extract_status_change(chat_member_update: ChatMemberUpdated):
    status_change = chat_member_update.difference().get("status")
    if status_change is None:
        return None

    old_status, new_status = status_change

    was_member = old_status in [
        ChatMemberStatus.MEMBER,
        ChatMemberStatus.OWNER,
        ChatMemberStatus.ADMINISTRATOR,
    ]
    is_member = new_status in [
        ChatMemberStatus.MEMBER,
        ChatMemberStatus.OWNER,
        ChatMemberStatus.ADMINISTRATOR,
    ]

    return was_member, is_member

# Bot commands
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_msg = """
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
    await update.message.reply_text(welcome_msg, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_msg = """
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
    await update.message.reply_text(help_msg, parse_mode='Markdown')

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stats = context.bot_data.get('stats', {
        'messages_scanned': 0,
        'spam_detected': 0,
        'messages_deleted': 0,
        'ml_detections': 0,
        'keyword_detections': 0,
        'severe_detections': 0,
        'url_blocked': 0,
        'mention_blocked': 0,
        'tag_blocked': 0,
        'sticker_blocked': 0,
        'image_blocked': 0
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
    settings = context.bot_data.get('settings', {
        'welcome_enabled': True,
        'url_blocking': True,
        'mention_blocking': True,
        'tag_blocking': True,
        'sticker_blocking': True,
        'threshold': 0.5
    })

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

# Whitelist commands
async def whitelist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    # Check if user is admin
    if not await is_user_admin(update.effective_chat.id, update.effective_user.id, context):
        await update.message.reply_text("⚠️ Only admins can manage whitelist!")
        return

    if len(context.args) == 0:
        await update.message.reply_text("Usage: /addwhitelist <user_id>\n\nReply to a user's message with /addwhitelist")
        return

    try:
        # Check if replying to a message
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
    if not await is_user_admin(update.effective_chat.id, update.effective_user.id, context):
        await update.message.reply_text("⚠️ Only admins can manage whitelist!")
        return

    context.bot_data['whitelist'] = set()
    await update.message.reply_text("✓ Whitelist cleared!\n\nNote: Admins are automatically whitelisted.")

# Custom welcome commands
async def customwelcome_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    if not await is_user_admin(update.effective_chat.id, update.effective_user.id, context):
        await update.message.reply_text("⚠️ Only admins can reset welcome!")
        return

    context.bot_data['custom_welcome'] = DEFAULT_WELCOME
    await update.message.reply_text("✓ Welcome message reset to default!")

# Setting toggle commands
async def set_welcome_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_user_admin(update.effective_chat.id, update.effective_user.id, context):
        await update.message.reply_text("⚠️ Only admins can change settings!")
        return
    if len(context.args) == 0:
        await update.message.reply_text("Usage: /setwelcome <on/off>")
        return

    setting = context.args[0].lower()
    if setting in ['on', 'off']:
        if 'settings' not in context.bot_data:
            context.bot_data['settings'] = {}
        context.bot_data['settings']['welcome_enabled'] = (setting == 'on')
        await update.message.reply_text(f"✓ Welcome messages: {setting.upper()}")
    else:
        await update.message.reply_text("Use: /setwelcome on or /setwelcome off")

async def set_url_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_user_admin(update.effective_chat.id, update.effective_user.id, context):
        await update.message.reply_text("⚠️ Only admins can change settings!")
        return
    if len(context.args) == 0:
        await update.message.reply_text("Usage: /seturl <on/off>")
        return

    setting = context.args[0].lower()
    if setting in ['on', 'off']:
        if 'settings' not in context.bot_data:
            context.bot_data['settings'] = {}
        context.bot_data['settings']['url_blocking'] = (setting == 'on')
        await update.message.reply_text(f"✓ URL blocking: {setting.upper()}")
    else:
        await update.message.reply_text("Use: /seturl on or /seturl off")

async def set_mention_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_user_admin(update.effective_chat.id, update.effective_user.id, context):
        await update.message.reply_text("⚠️ Only admins can change settings!")
        return
    if len(context.args) == 0:
        await update.message.reply_text("Usage: /setmention <on/off>")
        return

    setting = context.args[0].lower()
    if setting in ['on', 'off']:
        if 'settings' not in context.bot_data:
            context.bot_data['settings'] = {}
        context.bot_data['settings']['mention_blocking'] = (setting == 'on')
        await update.message.reply_text(f"✓ @Mention blocking: {setting.upper()}")
    else:
        await update.message.reply_text("Use: /setmention on or /setmention off")

async def set_tags_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_user_admin(update.effective_chat.id, update.effective_user.id, context):
        await update.message.reply_text("⚠️ Only admins can change settings!")
        return
    if len(context.args) == 0:
        await update.message.reply_text("Usage: /settags <on/off>")
        return

    setting = context.args[0].lower()
    if setting in ['on', 'off']:
        if 'settings' not in context.bot_data:
            context.bot_data['settings'] = {}
        context.bot_data['settings']['tag_blocking'] = (setting == 'on')
        await update.message.reply_text(f"✓ User tag blocking: {setting.upper()}")
    else:
        await update.message.reply_text("Use: /settags on or /settags off")

async def set_sticker_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_user_admin(update.effective_chat.id, update.effective_user.id, context):
        await update.message.reply_text("⚠️ Only admins can change settings!")
        return
    if len(context.args) == 0:
        await update.message.reply_text("Usage: /setsticker <on/off>")
        return

    setting = context.args[0].lower()
    if setting in ['on', 'off']:
        if 'settings' not in context.bot_data:
            context.bot_data['settings'] = {}
        context.bot_data['settings']['sticker_blocking'] = (setting == 'on')
        await update.message.reply_text(f"✓ Sticker spam detection: {setting.upper()}")
    else:
        await update.message.reply_text("Use: /setsticker on or /setsticker off")

async def set_sensitivity_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
                context.bot_data['settings'] = {}
            context.bot_data['settings']['threshold'] = threshold
            await update.message.reply_text(f"✓ ML sensitivity: {threshold}")
        else:
            await update.message.reply_text("⚠️ Value: 0.1 to 0.9")
    except ValueError:
        await update.message.reply_text("⚠️ Invalid! Use: /setsensitivity 0.5")

# --- Smart Learning Feedback Commands ---

async def feedback_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Allows users to report a message that was wrongly detected as spam (false positive)."""
    if update.message.reply_to_message:
        message_text = update.message.reply_to_message.text
        if message_text:
            smart_learning.add_false_positive(message_text)
            smart_learning.add_feedback(update.effective_user.id, message_text, False)
            smart_learning.save_learning_data()
            await update.message.reply_text(
                "Thank you for your feedback! This message has been noted as a false positive.\n"
                "I will try to learn from this to improve future detections."
            )
        else:
            await update.message.reply_text("Please reply to a text message that was wrongly marked as spam.")
    elif context.args:
        message_text = ' '.join(context.args)
        smart_learning.add_false_positive(message_text)
        smart_learning.add_feedback(update.effective_user.id, message_text, False)
        smart_learning.save_learning_data()
        await update.message.reply_text(
            "Thank you for your feedback! This message has been noted as a false positive.\n"
            "I will try to learn from this to improve future detections."
        )
    else:
        await update.message.reply_text(
            "Usage: Reply to a message with /notspam or use /notspam <message text> "
            "if a message was wrongly deleted as spam."
        )

async def reportspam_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Allows users to report a message that was missed by the spam filter (false negative)."""
    if update.message.reply_to_message:
        message_text = update.message.reply_to_message.text
        if message_text:
            smart_learning.add_false_negative(message_text)
            smart_learning.add_feedback(update.effective_user.id, message_text, True)
            smart_learning.save_learning_data()
            await update.message.reply_text(
                "Thank you for reporting! This message has been noted as missed spam.\n"
                "I will analyze this to improve my detection."
            )
        else:
            await update.message.reply_text("Please reply to a text message that is spam but was not detected.")
    else:
        await update.message.reply_text(
            "Usage: Reply to a spam message that was not detected with /reportspam."
        )

async def learning_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays statistics about the bot's learning data."""
    stats_msg = f"""
🧠 *Smart Learning Statistics*

False Positives Reported: {len(smart_learning.false_positives)}
False Negatives Reported: {len(smart_learning.false_negatives)}

Learned Spam Patterns: {len(smart_learning.learned_spam_patterns)}
Learned Safe Patterns: {len(smart_learning.learned_safe_patterns)}

*Top 5 Learned Spam Keywords:*
"""
    top_spam = list(smart_learning.learned_spam_patterns)[:5]
    if top_spam:
        stats_msg += "- " + "\n- ".join(top_spam)
    else:
        stats_msg += "(None yet)"

    await update.message.reply_text(stats_msg, parse_mode='Markdown')

async def reset_learning_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Resets all smart learning data (admin only)."""
    if not await is_user_admin(update.effective_chat.id, update.effective_user.id, context):
        await update.message.reply_text("⚠️ Only admins can reset learning data!")
        return

    smart_learning.false_positives = []
    smart_learning.false_negatives = []
    smart_learning.user_feedback = {}
    smart_learning.learned_spam_patterns = set()
    smart_learning.learned_safe_patterns = set()
    smart_learning.save_learning_data() # Save empty data

    await update.message.reply_text("✓ Smart learning data reset successfully!")

# --- Auto-Ban System Commands ---

async def strikes_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target_user_id = update.effective_user.id
    user_name = update.effective_user.first_name

    if context.args:
        try:
            target_user_id = int(context.args[0])
            # Try to get user info if different from effective user
            try:
                member = await context.bot.get_chat_member(update.effective_chat.id, target_user_id)
                user_name = member.user.first_name
            except Exception:
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
            for i, reason in enumerate(strikes_data['reasons'][-3:]): # Show last 3 reasons
                msg += f"{i+1}. Reason: {reason['reason']}\n"
                # Escape backticks in message content for Markdown
                message_snippet = reason['message'].replace('`', '\\`')
                msg += f"   Message: `{(message_snippet[:50] + '...') if len(message_snippet) > 50 else message_snippet}`\n"
                msg += f"   Time: {reason['time'].split('T')[0]} {reason['time'].split('T')[1].split('.')[0]}\n"

        await update.message.reply_text(msg, parse_mode='Markdown')

async def resetstrikes_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

async def banlist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            await update.message.reply_text(f"✓ User {user_id} has been unbanned.")
        else:
            await update.message.reply_text(f"User {user_id} is not currently banned.")
    except ValueError:
        await update.message.reply_text("⚠️ Invalid user ID!")

async def strikelimit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

# Image/Sticker handler
async def check_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    user = update.message.from_user
    chat_id = update.message.chat_id
    message_id = update.message.message_id

    # Initialize stats
    if 'stats' not in context.bot_data:
        context.bot_data['stats'] = {
            'messages_scanned': 0, 'spam_detected': 0, 'messages_deleted': 0,
            'sticker_blocked': 0, 'image_blocked': 0
        }

    if 'settings' not in context.bot_data:
        context.bot_data['settings'] = {'sticker_blocking': True}

    # Check if user is whitelisted or admin
    if is_whitelisted(user.id, context):
        return

    if await is_user_admin(chat_id, user.id, context):
        return

    settings = context.bot_data['settings']
    delete_reason = None

    # Check stickers
    if update.message.sticker and settings.get('sticker_blocking', True):
        # Allow up to 2 stickers, block spam (3+)
        user_key = f'sticker_count_{user.id}'
        sticker_count = context.bot_data.get(user_key, 0) + 1
        context.bot_data[user_key] = sticker_count

        if sticker_count >= 3:
            delete_reason = "sticker_spam"
            context.bot_data['stats']['sticker_blocked'] += 1
            context.bot_data[user_key] = 0  # Reset counter

    # Check images with captions (potential spam)
    if update.message.photo and update.message.caption:
        caption = update.message.caption

        # Check if caption contains spam
        spam, confidence, method, keywords = is_spam(caption, model, vectorizer, 0.4)
        if spam:
            delete_reason = f"image_spam ({method})"
            context.bot_data['stats']['image_blocked'] += 1

    # Delete if spam detected
    if delete_reason:
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
            context.bot_data['stats']['messages_deleted'] += 1

            # Add strike to user
            strikes, should_ban = auto_ban.add_strike(user.id, user.first_name, delete_reason, update.message.caption if update.message.caption else "[Media]")

            # Check if user should be banned
            if should_ban and not auto_ban.is_banned(user.id):
                try:
                    # Ban the user
                    await context.bot.ban_chat_member(chat_id=chat_id, user_id=user.id)
                    auto_ban.ban_user(user.id)
                    auto_ban.save_ban_data()

                    ban_msg = f"🚫 *USER BANNED*\n\n"
                    ban_msg += f"User: {user.first_name} (ID: {user.id})\n"
                    ban_msg += f"Reason: {auto_ban.strike_limit} strikes reached\n"
                    ban_msg += f"Total Violations: {strikes}\n\n"
                    ban_msg += f"⛔ User has been permanently banned from the group"

                    await context.bot.send_message(chat_id=chat_id, text=ban_msg, parse_mode='Markdown')

                except Exception as ban_error:
                    print(f"Ban error: {ban_error}")
            else:
                # Send warning with strike count
                warning_text = f"⚠️ WARNING - STRIKE {strikes}/{auto_ban.strike_limit}\n\n"
                warning_text += f"User: {user.first_name}\n"
                warning_text += f"Reason: {delete_reason}\n"
                warning_text += f"\n✓ Media deleted\n"
                warning_text += f"⚠️ {auto_ban.strike_limit - strikes} strike(s) remaining before BAN"

                warning_msg = await context.bot.send_message(chat_id=chat_id, text=warning_text)

                import asyncio
                await asyncio.sleep(7)
                try:
                    await context.bot.delete_message(chat_id=chat_id, message_id=warning_msg.message_id)
                except:
                    pass

            # Save strike data
            auto_ban.save_ban_data()

        except Exception as e:
            error_msg = str(e).lower()
            if "not found" not in error_msg:
                print(f"Media error: {e}")

# Main message handler
async def check_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    message_text = update.message.text
    chat_id = update.message.chat_id
    message_id = update.message.message_id
    user = update.message.from_user
    entities = update.message.entities

    # Initialize
    if 'stats' not in context.bot_data:
        context.bot_data['stats'] = {
            'messages_scanned': 0, 'spam_detected': 0, 'messages_deleted': 0,
            'ml_detections': 0, 'keyword_detections': 0, 'severe_detections': 0,
            'url_blocked': 0, 'mention_blocked': 0, 'tag_blocked': 0,
            'sticker_blocked': 0, 'image_blocked': 0
        }

    if 'settings' not in context.bot_data:
        context.bot_data['settings'] = {
            'welcome_enabled': True, 'url_blocking': True,
            'mention_blocking': True, 'tag_blocking': True,
            'sticker_blocking': True, 'threshold': 0.5
        }

    if 'whitelist' not in context.bot_data:
        context.bot_data['whitelist'] = set()

    context.bot_data['stats']['messages_scanned'] += 1

    # Check if user is banned
    if auto_ban.is_banned(user.id):
        # Silently ignore messages from banned users
        return

    # Check if user is whitelisted
    if is_whitelisted(user.id, context):
        return

    # Check if user is admin (auto-whitelist)
    if await is_user_admin(chat_id, user.id, context):
        # Auto-add admins to whitelist
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
        spam, confidence, method, keywords = is_spam(message_text, model, vectorizer, threshold)

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
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
            context.bot_data['stats']['messages_deleted'] += 1

            # Add strike to user
            strikes, should_ban = auto_ban.add_strike(user.id, user.first_name, delete_reason, message_text)

            # Check if user should be banned
            if should_ban and not auto_ban.is_banned(user.id):
                try:
                    # Ban the user
                    await context.bot.ban_chat_member(chat_id=chat_id, user_id=user.id)
                    auto_ban.ban_user(user.id)
                    auto_ban.save_ban_data()

                    ban_msg = f"🚫 *USER BANNED*\n\n"
                    ban_msg += f"User: {user.first_name} (ID: {user.id})\n"
                    ban_msg += f"Reason: {auto_ban.strike_limit} strikes reached\n"
                    ban_msg += f"Total Violations: {strikes}\n\n"
                    ban_msg += f"⛔ User has been permanently banned from the group"

                    await context.bot.send_message(chat_id=chat_id, text=ban_msg, parse_mode='Markdown')

                except Exception as ban_error:
                    print(f"Ban error: {ban_error}")
            else:
                # Send warning with strike count
                warning_text = f"⚠️ WARNING - STRIKE {strikes}/{auto_ban.strike_limit}\n\n"
                warning_text += f"User: {user.first_name}\n"
                warning_text += f"Reason: {delete_reason}\n"
                warning_text += f"\n✓ Message deleted\n"
                warning_text += f"⚠️ {auto_ban.strike_limit - strikes} strike(s) remaining before BAN"

                warning_msg = await context.bot.send_message(chat_id=chat_id, text=warning_text)

                import asyncio
                await asyncio.sleep(7)
                try:
                    await context.bot.delete_message(chat_id=chat_id, message_id=warning_msg.message_id)
                except:
                    pass

            # Save strike data
            auto_ban.save_ban_data()
            log_deletion(user, message_text, delete_reason)

        except Exception as e:
            error_msg = str(e).lower()
            if "not found" not in error_msg:
                print(f"Error: {e}")

def log_deletion(user, message, reason):
    try:
        with open('deletion_log.txt', 'a', encoding='utf-8') as f:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            f.write(f"[{timestamp}]\n")
            f.write(f"User: {user.first_name} (ID: {user.id})\n")
            f.write(f"Reason: {reason}\n")
            f.write(f"Message: {message}\n")
            f.write("-" * 60 + "\n")
    except:
        pass

# Main
def main():
    global model, vectorizer

    nest_asyncio.apply()
    print("🚀 Bot starting...")

    # Load smart learning data
    smart_learning.load_learning_data()

    # Load auto-ban data
    auto_ban.load_ban_data()

    model, vectorizer = load_spam_model()
    print("✓ Model loaded!")

    BOT_TOKEN = "7813830750:AAEGBMmhwSZRN7ZWihphHmq1P6hdQofJGs8"

    app = Application.builder().token(BOT_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("stats", stats_command))
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

    # Custom welcome commands
    app.add_handler(CommandHandler("customwelcome", customwelcome_command))
    app.add_handler(CommandHandler("resetwelcome", resetwelcome_command))

    # Smart learning commands
    app.add_handler(CommandHandler("notspam", feedback_command))
    app.add_handler(CommandHandler("reportspam", reportspam_command))
    app.add_handler(CommandHandler("learningstats", learning_stats_command))
    app.add_handler(CommandHandler("resetlearning", reset_learning_command))

    # Auto-ban commands
    app.add_handler(CommandHandler("strikes", strikes_command))
    app.add_handler(CommandHandler("resetstrikes", resetstrikes_command))
    app.add_handler(CommandHandler("banlist", banlist_command))
    app.add_handler(CommandHandler("unban", unban_command))
    app.add_handler(CommandHandler("strikelimit", strikelimit_command))

    # Message handlers
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))
    app.add_handler(ChatMemberHandler(track_member_status, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(MessageHandler((filters.PHOTO | filters.Sticker.ALL) & ~filters.COMMAND, check_media))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_message))

    print("\n" + "="*60)
    print("✓ Ultra Advanced Spam Detector Bot Running!")
    print("="*60)
    print("\n🆕 AUTO-BAN SYSTEM:")
    print("  🚨 " + str(auto_ban.strike_limit) + "-Strike Rule Active")
    print("  ⏰ Strikes reset after " + str(auto_ban.reset_interval_hours) + " hours")
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
    print("\n🚨 Ban Commands:")
    print("  /strikes - Check your strikes")
    print("  /banlist - View banned users")
    print("  /unban - Unban user (admin)")
    print("\nPress Ctrl+C to stop")
    print("="*60 + "\n")

    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()