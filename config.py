import os
# Bot Config
API_ID = 36972503
API_HASH = "00f224a50c765561cefe10bbacaffa2f"
BOT_TOKEN = "7813830750:AAEGBMmhwSZRN7ZWihphHmq1P6hdQofJGs8"

# Device Configuration
DEVICE = 'cuda' if os.system('nvidia-smi') == 0 else 'cpu'

# Auto-Ban Settings
STRIKE_LIMIT = 3
STRIKE_RESET_HOURS = 24

# ML Model Settings
ML_SENSITIVITY = 0.5
MODEL_INPUT_SIZE = 150

# File Paths
MODEL_PATH = 'spam_model.pth'
VECTORIZER_PATH = 'vectorizer.pkl'
BAN_DATA_PATH = 'ban_data.pkl'
LEARNING_DATA_PATH = 'learning_data.pkl'
DELETION_LOG_PATH = 'deletion_log.txt'

# Feature Toggles (Defaults)
DEFAULT_SETTINGS = {
    'welcome_enabled': True,
    'url_blocking': True,
    'mention_blocking': True,
    'tag_blocking': False,
    'sticker_blocking': True,
    'threshold': ML_SENSITIVITY
}

# Training Settings
TRAINING_EPOCHS = 300
LEARNING_RATE = 0.001