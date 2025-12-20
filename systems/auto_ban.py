"""
Auto-Ban System - 3-Strike Rule
"""
import pickle
import os
from datetime import datetime
import config

class AutoBan:
    """Automatic ban system with strike tracking"""
    
    def __init__(self, strike_limit=None, reset_interval_hours=None):
        self.user_strikes = {}
        self.banned_users = set()
        self.strike_limit = strike_limit or config.STRIKE_LIMIT
        self.reset_interval_hours = reset_interval_hours or config.STRIKE_RESET_HOURS

    def add_strike(self, user_id, user_name, reason, message):
        """Add a strike to user"""
        current_time = datetime.now()
        
        if user_id not in self.user_strikes:
            self.user_strikes[user_id] = {
                'count': 0,
                'last_strike_time': current_time,
                'name': user_name,
                'reasons': []
            }

        # Reset strikes if interval passed
        time_diff = (current_time - self.user_strikes[user_id]['last_strike_time']).total_seconds() / 3600
        if time_diff >= self.reset_interval_hours:
            self.user_strikes[user_id] = {
                'count': 0,
                'last_strike_time': current_time,
                'name': user_name,
                'reasons': []
            }

        self.user_strikes[user_id]['count'] += 1
        self.user_strikes[user_id]['last_strike_time'] = current_time
        self.user_strikes[user_id]['reasons'].append({
            'time': current_time.isoformat(),
            'reason': reason,
            'message': message[:100]
        })

        strikes = self.user_strikes[user_id]['count']
        should_ban = strikes >= self.strike_limit
        return strikes, should_ban

    def get_strikes(self, user_id):
        """Get user's current strikes"""
        return self.user_strikes.get(user_id, {
            'count': 0,
            'name': 'Unknown',
            'reasons': []
        })

    def ban_user(self, user_id):
        """Ban a user"""
        self.banned_users.add(user_id)
        if user_id in self.user_strikes:
            del self.user_strikes[user_id]

    def unban_user(self, user_id):
        """Unban a user"""
        if user_id in self.banned_users:
            self.banned_users.remove(user_id)
            return True
        return False

    def reset_strikes(self, user_id):
        """Reset user's strikes"""
        if user_id in self.user_strikes:
            del self.user_strikes[user_id]
            return True
        return False

    def is_banned(self, user_id):
        """Check if user is banned"""
        return user_id in self.banned_users

    def save_ban_data(self):
        """Save ban data to file"""
        try:
            data = {
                'user_strikes': {
                    k: {
                        **v,
                        'last_strike_time': v['last_strike_time'].isoformat()
                    } for k, v in self.user_strikes.items()
                },
                'banned_users': list(self.banned_users),
                'strike_limit': self.strike_limit,
                'reset_interval_hours': self.reset_interval_hours
            }
            with open(config.BAN_DATA_PATH, 'wb') as f:
                pickle.dump(data, f)
        except Exception as e:
            print(f"Save ban data error: {e}")

    def load_ban_data(self):
        """Load ban data from file"""
        try:
            if os.path.exists(config.BAN_DATA_PATH):
                with open(config.BAN_DATA_PATH, 'rb') as f:
                    data = pickle.load(f)
                
                self.user_strikes = {
                    k: {
                        **v,
                        'last_strike_time': datetime.fromisoformat(v['last_strike_time'])
                    } for k, v in data.get('user_strikes', {}).items()
                }
                
                self.banned_users = set(data.get('banned_users', []))
                self.strike_limit = data.get('strike_limit', config.STRIKE_LIMIT)
                self.reset_interval_hours = data.get('reset_interval_hours', config.STRIKE_RESET_HOURS)
                
                print(f"✓ Loaded {len(self.banned_users)} banned users")
                print(f"✓ Loaded {len(self.user_strikes)} users with strikes")
        except Exception as e:
            print(f"Load ban data error: {e}")