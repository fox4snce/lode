"""
Analytics features for conversation data.

Features:
- Usage over time: messages per day/week/month
- Longest streak: consecutive days with chats
- Top conversations by volume
- Top words / phrases (stopword filtered)
- Vocabulary size trend
- Response ratio: user vs assistant volume
- Time-of-day heatmap
"""
import sqlite3
import re
from typing import List, Dict, Optional
from collections import Counter, defaultdict
from datetime import datetime, timedelta


DB_PATH = 'conversations.db'

# Basic stopwords (can be expanded)
STOPWORDS = {
    'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
    'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been', 'be', 'have', 'has', 'had',
    'do', 'does', 'did', 'will', 'would', 'should', 'could', 'may', 'might', 'must',
    'can', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they',
    'me', 'him', 'her', 'us', 'them', 'my', 'your', 'his', 'her', 'its', 'our', 'their',
    'what', 'which', 'who', 'whom', 'whose', 'where', 'when', 'why', 'how', 'all', 'each',
    'every', 'both', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not',
    'only', 'own', 'same', 'so', 'than', 'too', 'very', 'just', 'now'
}


def extract_words(text: str) -> List[str]:
    """Extract words from text, lowercased."""
    words = re.findall(r'\b[a-z]+\b', text.lower())
    return [w for w in words if len(w) > 2]  # Filter very short words


def usage_over_time(
    db_path: str = DB_PATH,
    period: str = 'day',
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> List[Dict]:
    """
    Get usage statistics over time.
    
    Args:
        period: 'day', 'week', or 'month'
        start_date: Optional start date
        end_date: Optional end date
    
    Returns:
        List of dicts with period, message_count, conversation_count
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    # Get all messages with timestamps
    query = '''
        SELECT create_time, conversation_id
        FROM messages
        WHERE create_time IS NOT NULL
    '''
    params = []
    
    if start_date:
        query += ' AND create_time >= ?'
        params.append(start_date.timestamp())
    
    if end_date:
        query += ' AND create_time <= ?'
        params.append(end_date.timestamp())
    
    query += ' ORDER BY create_time'
    
    cursor = conn.execute(query, params)
    messages = cursor.fetchall()
    
    # Group by period
    period_counts = defaultdict(lambda: {'messages': 0, 'conversations': set()})
    
    for row in messages:
        try:
            dt = datetime.fromtimestamp(row['create_time'])
            conv_id = row['conversation_id']
            
            if period == 'day':
                key = dt.date().isoformat()
            elif period == 'week':
                # Get Monday of the week
                monday = dt - timedelta(days=dt.weekday())
                key = monday.date().isoformat()
            elif period == 'month':
                key = dt.strftime('%Y-%m')
            else:
                key = dt.date().isoformat()
            
            period_counts[key]['messages'] += 1
            period_counts[key]['conversations'].add(conv_id)
        except (ValueError, OSError):
            continue
    
    # Convert to list
    results = []
    for key in sorted(period_counts.keys()):
        results.append({
            'period': key,
            'message_count': period_counts[key]['messages'],
            'conversation_count': len(period_counts[key]['conversations'])
        })
    
    conn.close()
    return results


def longest_streak(db_path: str = DB_PATH) -> Dict:
    """Calculate longest streak of consecutive days with chats."""
    conn = sqlite3.connect(db_path)
    cursor = conn.execute('''
        SELECT DISTINCT DATE(datetime(create_time, 'unixepoch')) as chat_date
        FROM messages
        WHERE create_time IS NOT NULL
        ORDER BY chat_date
    ''')
    
    dates = [datetime.strptime(row[0], '%Y-%m-%d').date() for row in cursor.fetchall()]
    conn.close()
    
    if not dates:
        return {'longest_streak': 0, 'start_date': None, 'end_date': None}
    
    # Find longest streak
    longest = 1
    current = 1
    streak_start = dates[0]
    best_start = dates[0]
    best_end = dates[0]
    
    for i in range(1, len(dates)):
        days_diff = (dates[i] - dates[i-1]).days
        if days_diff == 1:
            current += 1
            if current > longest:
                longest = current
                best_start = streak_start
                best_end = dates[i]
        else:
            current = 1
            streak_start = dates[i]
    
    return {
        'longest_streak': longest,
        'start_date': best_start.isoformat(),
        'end_date': best_end.isoformat()
    }


def top_conversations_by_volume(db_path: str = DB_PATH, limit: int = 10) -> List[Dict]:
    """Get top conversations by message/word count."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    cursor = conn.execute('''
        SELECT 
            c.conversation_id,
            c.title,
            s.message_count_total,
            s.word_count_total,
            s.duration_seconds
        FROM conversations c
        JOIN conversation_stats s ON s.conversation_id = c.conversation_id
        ORDER BY s.message_count_total DESC, s.word_count_total DESC
        LIMIT ?
    ''', (limit,))
    
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results


def top_words(db_path: str = DB_PATH, limit: int = 50, min_length: int = 3) -> List[Dict]:
    """Get top words across all conversations (stopword filtered)."""
    conn = sqlite3.connect(db_path)
    cursor = conn.execute('''
        SELECT content FROM messages
        WHERE content IS NOT NULL
    ''')
    
    word_counts = Counter()
    
    for row in cursor.fetchall():
        words = extract_words(row[0])
        # Filter stopwords and short words
        words = [w for w in words if w not in STOPWORDS and len(w) >= min_length]
        word_counts.update(words)
    
    conn.close()
    
    # Return top N
    results = []
    for word, count in word_counts.most_common(limit):
        results.append({'word': word, 'count': count})
    
    return results


def top_phrases(db_path: str = DB_PATH, limit: int = 30, phrase_length: int = 2) -> List[Dict]:
    """Get top phrases (n-grams) across conversations."""
    conn = sqlite3.connect(db_path)
    cursor = conn.execute('''
        SELECT content FROM messages
        WHERE content IS NOT NULL
    ''')
    
    phrase_counts = Counter()
    
    for row in cursor.fetchall():
        words = extract_words(row[0])
        words = [w for w in words if w not in STOPWORDS and len(w) >= 3]
        
        # Generate n-grams
        for i in range(len(words) - phrase_length + 1):
            phrase = ' '.join(words[i:i+phrase_length])
            if len(phrase) > phrase_length * 2:  # Filter very short phrases
                phrase_counts[phrase] += 1
    
    conn.close()
    
    results = []
    for phrase, count in phrase_counts.most_common(limit):
        results.append({'phrase': phrase, 'count': count})
    
    return results


def vocabulary_size_trend(db_path: str = DB_PATH, period: str = 'month') -> List[Dict]:
    """Track vocabulary size (unique words) over time."""
    conn = sqlite3.connect(db_path)
    cursor = conn.execute('''
        SELECT content, create_time
        FROM messages
        WHERE content IS NOT NULL AND create_time IS NOT NULL
        ORDER BY create_time
    ''')
    
    # Group by period and track unique words
    period_vocab = defaultdict(set)
    
    for row in cursor.fetchall():
        try:
            dt = datetime.fromtimestamp(row[1])
            
            if period == 'month':
                key = dt.strftime('%Y-%m')
            elif period == 'week':
                monday = dt - timedelta(days=dt.weekday())
                key = monday.date().isoformat()
            else:
                key = dt.date().isoformat()
            
            words = extract_words(row[0])
            words = [w for w in words if w not in STOPWORDS and len(w) >= 3]
            period_vocab[key].update(words)
        except (ValueError, OSError):
            continue
    
    conn.close()
    
    results = []
    for key in sorted(period_vocab.keys()):
        results.append({
            'period': key,
            'unique_words': len(period_vocab[key])
        })
    
    return results


def response_ratio(db_path: str = DB_PATH) -> Dict:
    """Calculate user vs assistant message/word ratio."""
    conn = sqlite3.connect(db_path)
    cursor = conn.execute('''
        SELECT 
            SUM(CASE WHEN role = 'user' THEN 1 ELSE 0 END) as user_messages,
            SUM(CASE WHEN role = 'assistant' THEN 1 ELSE 0 END) as assistant_messages,
            SUM(CASE WHEN role = 'user' THEN LENGTH(content) ELSE 0 END) as user_chars,
            SUM(CASE WHEN role = 'assistant' THEN LENGTH(content) ELSE 0 END) as assistant_chars
        FROM messages
        WHERE content IS NOT NULL
    ''')
    
    row = cursor.fetchone()
    conn.close()
    
    user_msgs = row[0] or 0
    assistant_msgs = row[1] or 0
    user_chars = row[2] or 0
    assistant_chars = row[3] or 0
    
    total_msgs = user_msgs + assistant_msgs
    total_chars = user_chars + assistant_chars
    
    return {
        'user_messages': user_msgs,
        'assistant_messages': assistant_msgs,
        'user_characters': user_chars,
        'assistant_characters': assistant_chars,
        'message_ratio': assistant_msgs / user_msgs if user_msgs > 0 else 0,
        'character_ratio': assistant_chars / user_chars if user_chars > 0 else 0,
        'user_message_percent': (user_msgs / total_msgs * 100) if total_msgs > 0 else 0,
        'assistant_message_percent': (assistant_msgs / total_msgs * 100) if total_msgs > 0 else 0
    }


def time_of_day_heatmap(db_path: str = DB_PATH) -> List[Dict]:
    """Count messages by hour of day."""
    conn = sqlite3.connect(db_path)
    cursor = conn.execute('''
        SELECT create_time
        FROM messages
        WHERE create_time IS NOT NULL
    ''')
    
    hour_counts = Counter()
    
    for row in cursor.fetchall():
        try:
            dt = datetime.fromtimestamp(row[0])
            hour_counts[dt.hour] += 1
        except (ValueError, OSError):
            continue
    
    conn.close()
    
    results = []
    for hour in range(24):
        results.append({
            'hour': hour,
            'count': hour_counts[hour],
            'hour_label': f"{hour:02d}:00"
        })
    
    return results


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python analytics.py <command> [args...]")
        print("\nCommands:")
        print("  usage [day|week|month]")
        print("  streak")
        print("  top-conversations [limit]")
        print("  top-words [limit]")
        print("  top-phrases [limit]")
        print("  vocabulary [month|week|day]")
        print("  response-ratio")
        print("  heatmap")
        sys.exit(1)
    
    command = sys.argv[1]
    args = sys.argv[2:]
    
    try:
        if command == 'usage':
            period = args[0] if args else 'day'
            results = usage_over_time(period=period)
            print(f"Usage over time ({period}):")
            print(f"{'Period':<15} {'Messages':<12} {'Conversations':<15}")
            print("-" * 45)
            for r in results:
                print(f"{r['period']:<15} {r['message_count']:<12} {r['conversation_count']:<15}")
        
        elif command == 'streak':
            result = longest_streak()
            print(f"Longest streak: {result['longest_streak']} days")
            if result['start_date']:
                print(f"  From: {result['start_date']} to {result['end_date']}")
        
        elif command == 'top-conversations':
            limit = int(args[0]) if args else 10
            results = top_conversations_by_volume(limit=limit)
            print(f"Top {limit} conversations by volume:")
            print(f"{'Title':<40} {'Messages':<10} {'Words':<10}")
            print("-" * 65)
            for r in results:
                title = (r['title'] or '(no title)')[:38]
                print(f"{title:<40} {r['message_count_total']:<10} {r['word_count_total']:<10}")
        
        elif command == 'top-words':
            limit = int(args[0]) if args else 50
            results = top_words(limit=limit)
            print(f"Top {limit} words:")
            for r in results:
                print(f"  {r['word']}: {r['count']}")
        
        elif command == 'top-phrases':
            limit = int(args[0]) if args else 30
            results = top_phrases(limit=limit)
            print(f"Top {limit} phrases:")
            for r in results:
                print(f"  {r['phrase']}: {r['count']}")
        
        elif command == 'vocabulary':
            period = args[0] if args else 'month'
            results = vocabulary_size_trend(period=period)
            print(f"Vocabulary size trend ({period}):")
            print(f"{'Period':<15} {'Unique Words':<15}")
            print("-" * 35)
            for r in results:
                print(f"{r['period']:<15} {r['unique_words']:<15}")
        
        elif command == 'response-ratio':
            result = response_ratio()
            print("Response Ratio:")
            print(f"  User messages: {result['user_messages']} ({result['user_message_percent']:.1f}%)")
            print(f"  Assistant messages: {result['assistant_messages']} ({result['assistant_message_percent']:.1f}%)")
            print(f"  Message ratio (assistant/user): {result['message_ratio']:.2f}")
            print(f"  Character ratio (assistant/user): {result['character_ratio']:.2f}")
        
        elif command == 'heatmap':
            results = time_of_day_heatmap()
            print("Time of day heatmap:")
            print(f"{'Hour':<10} {'Count':<10}")
            print("-" * 20)
            for r in results:
                print(f"{r['hour_label']:<10} {r['count']:<10}")
        
        else:
            print(f"Unknown command: {command}")
    
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

