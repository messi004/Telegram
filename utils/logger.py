"""
Logging utility
"""
from datetime import datetime
import config

def log_deletion(user, message, reason):
    """Log deleted messages"""
    try:
        with open(config.DELETION_LOG_PATH, 'a', encoding='utf-8') as f:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            f.write(f"[{timestamp}]\n")
            f.write(f"User: {user.first_name} (ID: {user.id})\n")
            f.write(f"Reason: {reason}\n")
            f.write(f"Message: {message}\n")
            f.write("-" * 60 + "\n")
    except Exception as e:
        print(f"Logging error: {e}")