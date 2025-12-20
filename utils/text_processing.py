"""
Text processing utilities
"""
import re
import string

def preprocess_text(text):
    """Clean and normalize text"""
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    text = ' '.join(text.split())
    return text

def contains_url(text):
    """Check if text contains URLs"""
    url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    simple_url = r'www\.[a-zA-Z0-9-]+\.[a-zA-Z]{2,}'
    domain = r'[a-zA-Z0-9-]+\.(com|org|net|in|co|io|xyz|info|biz|me|tv|app|online)'
    
    if re.search(url_pattern, text) or re.search(simple_url, text, re.IGNORECASE):
        return True, "url_link"
    if re.search(domain, text, re.IGNORECASE):
        return True, "domain_name"
    return False, None

def contains_mentions(text):
    """Check if text contains @mentions"""
    mention_pattern = r'@[a-zA-Z0-9_]{5,}'
    matches = re.findall(mention_pattern, text)
    return len(matches) > 0, matches

def has_user_tags(entities):
    """Check if message has user tags"""
    if not entities:
        return False
    for entity in entities:
        if entity.type == "text_mention" or entity.type == "mention":
            return True
    return False