"""
Spam keywords database - Multi-language support
"""

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
    ]
}    
  """  ,
    'patterns': [
        r'\d+\s*(₹|rs|rupees)',
        r'(₹|rs)\s*\d+',
        r'(.)\1{4,}',
        r'(dm|msg|message|call)\s*(me|karo|here)',
    ]
}
"""
SEVERE_KEYWORDS = [
    'child', 'minor', 'underage', 'kid', 'cp', 'child porn',
    'school girl', 'college girl', 'hostel girl', 'young girl',
    'बच्चा', 'नाबालिग', 'குழந்தை'
]