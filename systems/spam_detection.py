"""
Spam Detection System - Combines ML and keyword detection
"""
import re
import torch
from data.keywords import EXPLICIT_KEYWORDS, SEVERE_KEYWORDS
from utils.text_processing import preprocess_text

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

def contains_explicit_content(text):
    """Multi-language explicit content detection"""
    if not text:
        return False, 0, []

    text_lower = text.lower()
    text_normalized = re.sub(r'[^\w\s]', ' ', text_lower)

    matched_keywords = []
    severity_score = 0

    # Check severe keywords
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

def is_spam(text, model, vectorizer, smart_learning, threshold=0.5):
    """Enhanced spam detection with smart learning"""
    if not text or len(text.strip()) == 0:
        return False, 0.0, "empty", []

    # Check learned safe patterns
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