"""
Import Claude conversations from JSON export.

Handles the Claude export format with 'chat_messages' array.
Uses data/claude/conversations.json by default.
"""
import json
import sqlite3
from pathlib import Path
from datetime import datetime

def parse_iso_datetime(iso_string):
    """Convert ISO datetime string to Unix timestamp."""
    try:
        dt = datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
        return dt.timestamp()
    except (ValueError, AttributeError):
        return None

def extract_messages_from_claude(chat_messages):
    """Extract messages from Claude chat_messages array."""
    messages = []
    for msg in chat_messages:
        # Extract text content - Claude has both 'text' field and 'content' array
        text_content = msg.get('text', '')
        if not text_content or not text_content.strip():
            # Try to extract from content array
            content = msg.get('content', [])
            if isinstance(content, list):
                text_parts = []
                for item in content:
                    if isinstance(item, dict) and item.get('type') == 'text':
                        text_parts.append(item.get('text', ''))
                text_content = '\n'.join(text_parts)
        
        if not text_content or not text_content.strip():
            continue
        
        # Map Claude sender to our role format
        sender = msg.get('sender', '')
        if sender == 'human':
            role = 'user'
        elif sender == 'assistant':
            role = 'assistant'
        else:
            role = sender  # fallback
        
        create_time = parse_iso_datetime(msg.get('created_at'))
        
        messages.append({
            'message_id': msg.get('uuid'),
            'parent_id': None,  # Claude doesn't have parent/child structure like OpenAI
            'role': role,
            'content': text_content,
            'create_time': create_time,
            'weight': 1.0,
            'status': 'finished_successfully'
        })
    
    return messages

def import_claude_conversations(claude_json_path='data/claude/conversations.json', db_path='conversations.db'):
    """Import Claude conversations from JSON file into SQLite database."""
    
    print(f"Loading Claude conversations from {claude_json_path}...")
    with open(claude_json_path, 'r', encoding='utf-8') as f:
        conversations = json.load(f)
    
    print(f"Found {len(conversations)} conversations")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    imported = 0
    skipped = 0
    duplicates = 0
    
    for idx, conv in enumerate(conversations):
        if (idx + 1) % 100 == 0:
            print(f"Processing conversation {idx + 1}/{len(conversations)}...")
        
        conversation_id = conv.get('uuid')
        if not conversation_id:
            skipped += 1
            continue
        
        # Check if conversation already exists (duplicate detection)
        cursor.execute('SELECT conversation_id FROM conversations WHERE conversation_id = ?', (conversation_id,))
        if cursor.fetchone():
            duplicates += 1
            continue
        
        # Parse timestamps
        create_time = parse_iso_datetime(conv.get('created_at'))
        update_time = parse_iso_datetime(conv.get('updated_at'))
        
        # Get conversation title
        title = conv.get('name') or conv.get('summary', '')[:100]  # Use name, or first 100 chars of summary
        
        # Extract and insert messages
        chat_messages = conv.get('chat_messages', [])
        messages = extract_messages_from_claude(chat_messages)
        
        # Skip conversations with no messages
        if not messages:
            skipped += 1
            continue
        
        # Insert conversation metadata
        try:
            cursor.execute('''
                INSERT INTO conversations 
                (conversation_id, title, create_time, update_time, is_archived, is_starred, 
                 default_model_slug, conversation_origin, ai_source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                conversation_id,
                title,
                create_time,
                update_time,
                0,  # is_archived
                0,  # is_starred
                'claude',  # default_model_slug
                'claude',  # conversation_origin
                'claude'   # ai_source
            ))
            
            # Insert messages
            for msg in messages:
                cursor.execute('''
                    INSERT INTO messages 
                    (conversation_id, message_id, parent_id, role, content, create_time, weight, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    conversation_id,
                    msg['message_id'],
                    msg['parent_id'],
                    msg['role'],
                    msg['content'],
                    msg['create_time'],
                    msg['weight'],
                    msg['status']
                ))
            
            imported += 1
            
        except sqlite3.IntegrityError as e:
            print(f"Error importing conversation {conversation_id}: {e}")
            skipped += 1
            continue
    
    conn.commit()
    
    # Print statistics
    cursor.execute('SELECT COUNT(*) FROM conversations WHERE ai_source = ?', ('claude',))
    total_claude = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM conversations')
    total_conv = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM messages WHERE conversation_id IN (SELECT conversation_id FROM conversations WHERE ai_source = ?)', ('claude',))
    total_msgs = cursor.fetchone()[0]
    
    print(f"\nImport complete!")
    print(f"  Imported: {imported} Claude conversations")
    print(f"  Duplicates skipped: {duplicates} conversations")
    print(f"  Skipped (no ID or no messages): {skipped} conversations")
    print(f"  Total Claude conversations in DB: {total_claude}")
    print(f"  Total conversations in DB: {total_conv}")
    print(f"  Total Claude messages in DB: {total_msgs}")
    
    conn.close()

if __name__ == '__main__':
    import sys
    claude_path = sys.argv[1] if len(sys.argv) > 1 else 'data/claude/conversations.json'
    import_claude_conversations(claude_path)

