"""
Smart Learning System - Learns from user feedback
"""
import pickle
import os
from datetime import datetime
import config

class SmartLearning:
    """Adaptive learning system for spam detection"""
    
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
        return list(self.learned_spam_patterns)[:20]

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
            with open(config.LEARNING_DATA_PATH, 'wb') as f:
                pickle.dump(data, f)
        except Exception as e:
            print(f"Save learning error: {e}")

    def load_learning_data(self):
        """Load learning data from file"""
        try:
            if os.path.exists(config.LEARNING_DATA_PATH):
                with open(config.LEARNING_DATA_PATH, 'rb') as f:
                    data = pickle.load(f)
                self.false_positives = data.get('false_positives', [])
                self.false_negatives = data.get('false_negatives', [])
                self.learned_spam_patterns = set(data.get('learned_spam_patterns', []))
                self.learned_safe_patterns = set(data.get('learned_safe_patterns', []))
                print(f"✓ Loaded {len(self.learned_spam_patterns)} spam patterns")
                print(f"✓ Loaded {len(self.learned_safe_patterns)} safe patterns")
        except Exception as e:
            print(f"Load learning error: {e}")

    def reset(self):
        """Reset all learning data"""
        self.false_positives = []
        self.false_negatives = []
        self.user_feedback = {}
        self.learned_spam_patterns = set()
        self.learned_safe_patterns = set()
        self.save_learning_data()