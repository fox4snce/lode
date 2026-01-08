"""
Find tools for discovering specific content in conversations.

Tools:
- Find all code blocks
- Find all links/URLs
- Find all file paths
- Find all TODOs
- Find questions
- Find dates mentioned
- Find decisions
- Find prompts
"""
import sqlite3
import re
from typing import List, Dict, Optional
from collections import Counter
from urllib.parse import urlparse


DB_PATH = 'conversations.db'

# Regex patterns
CODE_BLOCK_PATTERN = re.compile(r'```([\w]*)\n?([\s\S]*?)```', re.MULTILINE)
URL_PATTERN = re.compile(r'https?://[^\s<>"{}|\\^`\[\]]+', re.IGNORECASE)
FILE_PATH_PATTERN = re.compile(r'(?:[A-Z]:\\|/)(?:[^/\s<>:"|?*]+[/\\])*[^/\s<>:"|?*]+', re.IGNORECASE)
TODO_PATTERN = re.compile(r'\b(TODO|FIXME|XXX|HACK|NOTE|BUG|OPTIMIZE|REFACTOR|CLEANUP|REVIEW|CHANGELOG|WIP|TBD|FIX|FIXME|HACK|XXX|OPTIMIZE|REFACTOR|CLEANUP|REVIEW|CHANGELOG|WIP|TBD|next:|I should|we need to|need to|should|must|gotta|have to)\b', re.IGNORECASE)
QUESTION_PATTERN = re.compile(r'[^.!?]*\?[^.!?]*')
DATE_PATTERN = re.compile(r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}\b|\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}/\d{1,2}/\d{2,4}\b', re.IGNORECASE)
DECISION_PATTERN = re.compile(r'\b(I decided|we\'ll do|we will do|final|going with|ship|shipping|approved|decided on|chose|choosing|selected|selecting|picked|picking)\b', re.IGNORECASE)
PROMPT_PATTERN = re.compile(r'^\s*(Write|Generate|Create|Make|Build|Design|Develop|Implement|Code|Draft|Compose|Produce|Construct|Formulate|Prepare|Assemble|Craft|Author|Script|Program|Develop|Build|Make|Create|Generate|Write|Design|Implement|Code|Draft|Compose|Produce|Construct|Formulate|Prepare|Assemble|Craft|Author|Script|Program)', re.IGNORECASE | re.MULTILINE)


def find_code_blocks(db_path: str = DB_PATH, limit: int = 100) -> List[Dict]:
    """Find all fenced code blocks."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    cursor = conn.execute('''
        SELECT conversation_id, message_id, role, content, create_time
        FROM messages
        WHERE content IS NOT NULL
        ORDER BY create_time DESC
    ''')
    
    results = []
    for row in cursor:
        matches = CODE_BLOCK_PATTERN.findall(row['content'])
        if matches:
            for lang, code in matches:
                results.append({
                    'conversation_id': row['conversation_id'],
                    'message_id': row['message_id'],
                    'role': row['role'],
                    'language': lang or 'plain',
                    'code': code[:500],  # First 500 chars
                    'create_time': row['create_time']
                })
                if len(results) >= limit:
                    break
    
    conn.close()
    return results


def find_links(db_path: str = DB_PATH, limit: int = 100) -> List[Dict]:
    """Find all URLs/links."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    cursor = conn.execute('''
        SELECT conversation_id, message_id, role, content, create_time
        FROM messages
        WHERE content IS NOT NULL
        ORDER BY create_time DESC
    ''')
    
    results = []
    domains = Counter()
    
    for row in cursor:
        matches = URL_PATTERN.findall(row['content'])
        if matches:
            for url in matches:
                try:
                    parsed = urlparse(url)
                    domain = parsed.netloc or parsed.path.split('/')[0]
                    domains[domain] += 1
                except:
                    pass
                
                # Get context around the URL
                idx = row['content'].find(url)
                start = max(0, idx - 80)
                end = min(len(row['content']), idx + len(url) + 80)
                context = row['content'][start:end]
                
                results.append({
                    'conversation_id': row['conversation_id'],
                    'message_id': row['message_id'],
                    'role': row['role'],
                    'url': url,
                    'link': url,  # Alias for consistency
                    'domain': domain if 'domain' in locals() else '',
                    'context': context,
                    'create_time': row['create_time']
                })
                if len(results) >= limit:
                    break
    
    conn.close()
    
    # Add domain stats
    top_domains = domains.most_common(10)
    
    return {
        'links': results,
        'total_unique_domains': len(domains),
        'top_domains': top_domains
    }


def find_file_paths(db_path: str = DB_PATH, limit: int = 100) -> List[Dict]:
    """Find all file paths."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    cursor = conn.execute('''
        SELECT conversation_id, message_id, role, content, create_time
        FROM messages
        WHERE content IS NOT NULL
        ORDER BY create_time DESC
    ''')
    
    results = []
    seen_paths = set()
    
    for row in cursor:
        matches = FILE_PATH_PATTERN.findall(row['content'])
        if matches:
            for path in matches:
                if path not in seen_paths:
                    seen_paths.add(path)
                    results.append({
                        'conversation_id': row['conversation_id'],
                        'message_id': row['message_id'],
                        'role': row['role'],
                        'path': path,
                        'create_time': row['create_time']
                    })
                    if len(results) >= limit:
                        break
    
    conn.close()
    return results


def find_todos(db_path: str = DB_PATH, limit: int = 100) -> List[Dict]:
    """Find all TODOs and similar markers."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    cursor = conn.execute('''
        SELECT conversation_id, message_id, role, content, create_time
        FROM messages
        WHERE content IS NOT NULL
        ORDER BY create_time DESC
    ''')
    
    results = []
    
    for row in cursor:
        matches = TODO_PATTERN.findall(row['content'])
        if matches:
            # Get context around match
            for match in matches[:3]:  # Limit matches per message
                idx = row['content'].find(match)
                start = max(0, idx - 50)
                end = min(len(row['content']), idx + len(match) + 50)
                context = row['content'][start:end]
                
                results.append({
                    'conversation_id': row['conversation_id'],
                    'message_id': row['message_id'],
                    'role': row['role'],
                    'marker': match,
                    'context': context,
                    'create_time': row['create_time']
                })
                if len(results) >= limit:
                    break
            if len(results) >= limit:
                break
    
    conn.close()
    return results


def find_questions(db_path: str = DB_PATH, limit: int = 100) -> List[Dict]:
    """Find all questions (messages ending with ?)."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    cursor = conn.execute('''
        SELECT conversation_id, message_id, role, content, create_time
        FROM messages
        WHERE content LIKE '%?%'
        ORDER BY create_time DESC
        LIMIT ?
    ''', (limit,))
    
    results = []
    for row in cursor:
        # Extract question sentences
        questions = QUESTION_PATTERN.findall(row['content'])
        if questions:
            results.append({
                'conversation_id': row['conversation_id'],
                'message_id': row['message_id'],
                'role': row['role'],
                'question': questions[0][:200],  # First question, truncated
                'create_time': row['create_time']
            })
    
    conn.close()
    return results


def find_dates(db_path: str = DB_PATH, limit: int = 100) -> List[Dict]:
    """Find all dates mentioned."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    cursor = conn.execute('''
        SELECT conversation_id, message_id, role, content, create_time
        FROM messages
        WHERE content IS NOT NULL
        ORDER BY create_time DESC
    ''')
    
    results = []
    seen_dates = set()
    
    for row in cursor:
        matches = DATE_PATTERN.findall(row['content'])
        if matches:
            for date_str in matches:
                if date_str not in seen_dates:
                    seen_dates.add(date_str)
                    # Get context around the date
                    idx = row['content'].find(date_str)
                    start = max(0, idx - 80)
                    end = min(len(row['content']), idx + len(date_str) + 80)
                    context = row['content'][start:end]
                    
                    results.append({
                        'conversation_id': row['conversation_id'],
                        'message_id': row['message_id'],
                        'role': row['role'],
                        'date': date_str,
                        'context': context,
                        'create_time': row['create_time']
                    })
                    if len(results) >= limit:
                        break
            if len(results) >= limit:
                break
    
    conn.close()
    return results


def find_decisions(db_path: str = DB_PATH, limit: int = 100) -> List[Dict]:
    """Find decision statements."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    cursor = conn.execute('''
        SELECT conversation_id, message_id, role, content, create_time
        FROM messages
        WHERE content IS NOT NULL
        ORDER BY create_time DESC
    ''')
    
    results = []
    
    for row in cursor:
        matches = DECISION_PATTERN.findall(row['content'])
        if matches:
            # Get sentence containing decision
            for match in matches[:2]:  # Limit per message
                idx = row['content'].find(match)
                start = max(0, idx - 100)
                end = min(len(row['content']), idx + 200)
                context = row['content'][start:end]
                
                results.append({
                    'conversation_id': row['conversation_id'],
                    'message_id': row['message_id'],
                    'role': row['role'],
                    'decision_marker': match,
                    'context': context,
                    'create_time': row['create_time']
                })
                if len(results) >= limit:
                    break
            if len(results) >= limit:
                break
    
    conn.close()
    return results


def find_prompts(db_path: str = DB_PATH, limit: int = 100) -> List[Dict]:
    """Find prompt-like messages (starting with action verbs)."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    cursor = conn.execute('''
        SELECT conversation_id, message_id, role, content, create_time
        FROM messages
        WHERE content IS NOT NULL AND role = 'user'
        ORDER BY create_time DESC
    ''')
    
    results = []
    
    for row in cursor:
        matches = PROMPT_PATTERN.findall(row['content'])
        if matches:
            # Get first line or first 200 chars
            first_line = row['content'].split('\n')[0][:200]
            
            results.append({
                'conversation_id': row['conversation_id'],
                'message_id': row['message_id'],
                'role': row['role'],
                'prompt': first_line,
                'create_time': row['create_time']
            })
            if len(results) >= limit:
                break
    
    conn.close()
    return results


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python find_tools.py <tool> [--limit N]")
        print("Tools: code, links, files, todos, questions, dates, decisions, prompts")
        sys.exit(1)
    
    tool = sys.argv[1].lower()
    limit = 20
    
    if '--limit' in sys.argv:
        idx = sys.argv.index('--limit')
        if idx + 1 < len(sys.argv):
            limit = int(sys.argv[idx + 1])
    
    print(f"Finding: {tool} (limit: {limit})")
    print("-"*70)
    
    if tool == 'code':
        results = find_code_blocks(limit=limit)
        print(f"Found {len(results)} code blocks:\n")
        for r in results:
            print(f"  [{r['language']}] {r['code'][:80]}...")
    
    elif tool == 'links':
        result = find_links(limit=limit)
        print(f"Found {len(result['links'])} links")
        print(f"Unique domains: {result['total_unique_domains']}")
        print(f"\nTop domains:")
        for domain, count in result['top_domains']:
            print(f"  {domain}: {count}")
        print(f"\nSample links:")
        for r in result['links'][:10]:
            print(f"  {r['url']}")
    
    elif tool == 'files':
        results = find_file_paths(limit=limit)
        print(f"Found {len(results)} file paths:\n")
        for r in results:
            print(f"  {r['path']}")
    
    elif tool == 'todos':
        results = find_todos(limit=limit)
        print(f"Found {len(results)} TODOs:\n")
        for r in results:
            print(f"  [{r['marker']}] {r['context'][:80]}...")
    
    elif tool == 'questions':
        results = find_questions(limit=limit)
        print(f"Found {len(results)} questions:\n")
        for r in results:
            print(f"  {r['question']}")
    
    elif tool == 'dates':
        results = find_dates(limit=limit)
        print(f"Found {len(results)} dates:\n")
        for r in results:
            print(f"  {r['date']}")
    
    elif tool == 'decisions':
        results = find_decisions(limit=limit)
        print(f"Found {len(results)} decisions:\n")
        for r in results:
            print(f"  [{r['decision_marker']}] {r['context'][:80]}...")
    
    elif tool == 'prompts':
        results = find_prompts(limit=limit)
        print(f"Found {len(results)} prompts:\n")
        for r in results:
            print(f"  {r['prompt']}")
    
    else:
        print(f"Unknown tool: {tool}")
        print("Available: code, links, files, todos, questions, dates, decisions, prompts")

