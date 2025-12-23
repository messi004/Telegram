"""
Data Models and Structures
Define data classes and models used across the bot
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional

@dataclass
class UserStrike:
    """User strike information"""
    user_id: int
    user_name: str
    count: int
    last_strike_time: datetime
    reasons: List[Dict[str, str]] = field(default_factory=list)
    
    def add_violation(self, reason: str, message: str):
        """Add a violation to user's record"""
        self.reasons.append({
            'time': datetime.now().isoformat(),
            'reason': reason,
            'message': message[:100]  # Store first 100 chars
        })
    
    def should_reset(self, reset_hours: int) -> bool:
        """Check if strikes should be reset"""
        time_diff = (datetime.now() - self.last_strike_time).total_seconds() / 3600
        return time_diff >= reset_hours
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {
            'user_id': self.user_id,
            'user_name': self.user_name,
            'count': self.count,
            'last_strike_time': self.last_strike_time.isoformat(),
            'reasons': self.reasons
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        """Create from dictionary"""
        return cls(
            user_id=data['user_id'],
            user_name=data['user_name'],
            count=data['count'],
            last_strike_time=datetime.fromisoformat(data['last_strike_time']),
            reasons=data.get('reasons', [])
        )

@dataclass
class SpamDetectionResult:
    """Result of spam detection"""
    is_spam: bool
    confidence: float
    method: str  # ml_model, keywords, severe, etc.
    matched_keywords: List[str] = field(default_factory=list)
    
    def __str__(self):
        return f"Spam: {self.is_spam}, Confidence: {self.confidence:.2%}, Method: {self.method}"

@dataclass
class MessageStats:
    """Bot statistics"""
    messages_scanned: int = 0
    spam_detected: int = 0
    messages_deleted: int = 0
    ml_detections: int = 0
    keyword_detections: int = 0
    severe_detections: int = 0
    url_blocked: int = 0
    mention_blocked: int = 0
    tag_blocked: int = 0
    sticker_blocked: int = 0
    image_blocked: int = 0
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'messages_scanned': self.messages_scanned,
            'spam_detected': self.spam_detected,
            'messages_deleted': self.messages_deleted,
            'ml_detections': self.ml_detections,
            'keyword_detections': self.keyword_detections,
            'severe_detections': self.severe_detections,
            'url_blocked': self.url_blocked,
            'mention_blocked': self.mention_blocked,
            'tag_blocked': self.tag_blocked,
            'sticker_blocked': self.sticker_blocked,
            'image_blocked': self.image_blocked
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        """Create from dictionary"""
        return cls(**data)
    
    def get_detection_rate(self) -> float:
        """Calculate detection rate percentage"""
        if self.messages_scanned == 0:
            return 0.0
        return (self.spam_detected / self.messages_scanned) * 100

@dataclass
class BotSettings:
    """Bot configuration settings"""
    welcome_enabled: bool = True
    url_blocking: bool = True
    mention_blocking: bool = True
    tag_blocking: bool = False
    sticker_blocking: bool = True
    threshold: float = 0.5
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'welcome_enabled': self.welcome_enabled,
            'url_blocking': self.url_blocking,
            'mention_blocking': self.mention_blocking,
            'tag_blocking': self.tag_blocking,
            'sticker_blocking': self.sticker_blocking,
            'threshold': self.threshold
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        """Create from dictionary"""
        return cls(
            welcome_enabled=data.get('welcome_enabled', True),
            url_blocking=data.get('url_blocking', True),
            mention_blocking=data.get('mention_blocking', True),
            tag_blocking=data.get('tag_blocking', True),
            sticker_blocking=data.get('sticker_blocking', True),
            threshold=data.get('threshold', 0.5)
        )

@dataclass
class LearningData:
    """Smart learning data"""
    false_positives: List[Dict[str, str]] = field(default_factory=list)
    false_negatives: List[Dict[str, str]] = field(default_factory=list)
    learned_spam_patterns: List[str] = field(default_factory=list)
    learned_safe_patterns: List[str] = field(default_factory=list)
    
    def add_false_positive(self, message: str):
        """Record a false positive"""
        self.false_positives.append({
            'message': message,
            'timestamp': datetime.now().isoformat()
        })
    
    def add_false_negative(self, message: str):
        """Record a false negative"""
        self.false_negatives.append({
            'message': message,
            'timestamp': datetime.now().isoformat()
        })
    
    def get_stats(self) -> dict:
        """Get learning statistics"""
        return {
            'false_positives': len(self.false_positives),
            'false_negatives': len(self.false_negatives),
            'spam_patterns': len(self.learned_spam_patterns),
            'safe_patterns': len(self.learned_safe_patterns),
            'total_feedback': len(self.false_positives) + len(self.false_negatives)
        }
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'false_positives': self.false_positives,
            'false_negatives': self.false_negatives,
            'learned_spam_patterns': self.learned_spam_patterns,
            'learned_safe_patterns': self.learned_safe_patterns
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        """Create from dictionary"""
        return cls(
            false_positives=data.get('false_positives', []),
            false_negatives=data.get('false_negatives', []),
            learned_spam_patterns=data.get('learned_spam_patterns', []),
            learned_safe_patterns=data.get('learned_safe_patterns', [])
        )

@dataclass
class BanRecord:
    """Ban record for a user"""
    user_id: int
    user_name: str
    ban_time: datetime
    reason: str
    total_violations: int
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'user_id': self.user_id,
            'user_name': self.user_name,
            'ban_time': self.ban_time.isoformat(),
            'reason': self.reason,
            'total_violations': self.total_violations
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        """Create from dictionary"""
        return cls(
            user_id=data['user_id'],
            user_name=data['user_name'],
            ban_time=datetime.fromisoformat(data['ban_time']),
            reason=data['reason'],
            total_violations=data['total_violations']
        )

@dataclass
class WhitelistEntry:
    """Whitelist entry"""
    user_id: int
    user_name: str
    added_by: int
    added_time: datetime
    reason: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'user_id': self.user_id,
            'user_name': self.user_name,
            'added_by': self.added_by,
            'added_time': self.added_time.isoformat(),
            'reason': self.reason
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        """Create from dictionary"""
        return cls(
            user_id=data['user_id'],
            user_name=data['user_name'],
            added_by=data['added_by'],
            added_time=datetime.fromisoformat(data['added_time']),
            reason=data.get('reason')
        )

@dataclass
class ViolationLog:
    """Log entry for a violation"""
    user_id: int
    user_name: str
    message: str
    reason: str
    timestamp: datetime
    action_taken: str  # deleted, warned, banned
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'user_id': self.user_id,
            'user_name': self.user_name,
            'message': self.message,
            'reason': self.reason,
            'timestamp': self.timestamp.isoformat(),
            'action_taken': self.action_taken
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        """Create from dictionary"""
        return cls(
            user_id=data['user_id'],
            user_name=data['user_name'],
            message=data['message'],
            reason=data['reason'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            action_taken=data['action_taken']
        )
    
    def to_log_string(self) -> str:
        """Convert to log string format"""
        return (
            f"[{self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}]\n"
            f"User: {self.user_name} (ID: {self.user_id})\n"
            f"Reason: {self.reason}\n"
            f"Action: {self.action_taken}\n"
            f"Message: {self.message}\n"
            f"{'-' * 60}\n"
        )

class BotState:
    """Global bot state management"""
    
    def __init__(self):
        self.stats = MessageStats()
        self.settings = BotSettings()
        self.whitelist: set = set()
        self.custom_welcome: Optional[str] = None
    
    def get_state_dict(self) -> dict:
        """Get complete bot state"""
        return {
            'stats': self.stats.to_dict(),
            'settings': self.settings.to_dict(),
            'whitelist': list(self.whitelist),
            'custom_welcome': self.custom_welcome
        }
    
    def load_state_dict(self, data: dict):
        """Load bot state from dictionary"""
        if 'stats' in data:
            self.stats = MessageStats.from_dict(data['stats'])
        if 'settings' in data:
            self.settings = BotSettings.from_dict(data['settings'])
        if 'whitelist' in data:
            self.whitelist = set(data['whitelist'])
        if 'custom_welcome' in data:
            self.custom_welcome = data['custom_welcome']

# Enums for better type safety
class DetectionMethod:
    """Detection method constants"""
    ML_MODEL = "ml_model"
    KEYWORDS = "explicit_keywords"
    SEVERE = "severe_keywords"
    COMBINED = "combined"
    LEARNED_SAFE = "learned_safe"
    URL = "url_blocked"
    MENTION = "mention_blocked"
    TAG = "tag_blocked"
    STICKER = "sticker_spam"
    IMAGE = "image_spam"

class ActionType:
    """Action type constants"""
    DELETED = "deleted"
    WARNED = "warned"
    BANNED = "banned"
    STRIKE_ADDED = "strike_added"

# Helper functions for data models
def create_spam_result(is_spam: bool, confidence: float, method: str, keywords: List[str] = None) -> SpamDetectionResult:
    """Factory function to create SpamDetectionResult"""
    return SpamDetectionResult(
        is_spam=is_spam,
        confidence=confidence,
        method=method,
        matched_keywords=keywords or []
    )

def create_violation_log(user_id: int, user_name: str, message: str, reason: str, action: str) -> ViolationLog:
    """Factory function to create ViolationLog"""
    return ViolationLog(
        user_id=user_id,
        user_name=user_name,
        message=message,
        reason=reason,
        timestamp=datetime.now(),
        action_taken=action
    )