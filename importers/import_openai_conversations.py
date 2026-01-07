"""
Import OpenAI ChatGPT conversations from JSON export.

Handles the OpenAI export format with 'mapping' structure.
"""
import json
import sqlite3
from pathlib import Path
from datetime import datetime

def extract_messages_from_mapping(mapping):
    """Extract all messages from the mapping structure."""
    messages = []
    for node_id, node in mapping.items():
        if node.get('message') is not None:
            msg = node['message']
            content = msg.get('content', {})
            
            # Extract text content from parts
            parts = []
            if isinstance(content, dict):
                parts = content.get('parts', [])
            elif isinstance(content, list):
                parts = content
            
            # Join parts into single text (filter out empty strings)
            text_content = '\n'.join(str(p) for p in parts if p and str(p).strip())
            
            # Only include messages with actual content
            if text_content.strip():
                messages.append({
                    'message_id': node_id,
                    'parent_id': node.get('parent'),
                    'role': msg.get('author', {}).get('role'),
                    'content': text_content,
                    'create_time': msg.get('create_time'),
                    'weight': msg.get('weight', 0.0),
                    'status': msg.get('status')
                })
    
    return messages

def import_openai_conversations(json_path='data/conversations.json', db_path='conversations.db'):
    """Import OpenAI conversations from JSON file into SQLite database."""
    
    print(f"Loading OpenAI conversations from {json_path}...")
    with open(json_path, 'r', encoding='utf-8') as f:
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
        
        # Handle both 'conversation_id' and 'id' fields
        conversation_id = conv.get('conversation_id') or conv.get('id')
        if not conversation_id:
            skipped += 1
            continue
        
        # Check if conversation already exists (duplicate detection)
        cursor.execute('SELECT conversation_id FROM conversations WHERE conversation_id = ?', (conversation_id,))
        if cursor.fetchone():
            duplicates += 1
            continue
        
        # Insert conversation metadata
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO conversations 
                (conversation_id, title, create_time, update_time, is_archived, is_starred, 
                 default_model_slug, conversation_origin, ai_source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                conversation_id,
                conv.get('title'),
                conv.get('create_time'),
                conv.get('update_time'),
                int(conv.get('is_archived') or False),
                int(conv.get('is_starred') or False),
                conv.get('default_model_slug'),
                conv.get('conversation_origin'),
                'gpt'  # Label OpenAI conversations as gpt
            ))
            
            # Extract and insert messages
            mapping = conv.get('mapping', {})
            messages = extract_messages_from_mapping(mapping)
            
            # Delete existing messages for this conversation (in case of re-import)
            cursor.execute('DELETE FROM messages WHERE conversation_id = ?', (conversation_id,))
            
            # Insert messages
            for msg in messages:
                cursor.execute('''
                    INSERT OR REPLACE INTO messages 
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
    cursor.execute('SELECT COUNT(*) FROM conversations WHERE ai_source = ?', ('gpt',))
    total_openai = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM conversations')
    total_conv = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM messages WHERE conversation_id IN (SELECT conversation_id FROM conversations WHERE ai_source = ?)', ('gpt',))
    total_msgs = cursor.fetchone()[0]
    
    print(f"\nImport complete!")
    print(f"  Imported: {imported} OpenAI conversations")
    print(f"  Duplicates skipped: {duplicates} conversations")
    print(f"  Skipped (no ID): {skipped} conversations")
    print(f"  Total OpenAI conversations in DB: {total_openai}")
    print(f"  Total conversations in DB: {total_conv}")
    print(f"  Total OpenAI messages in DB: {total_msgs}")
    
    conn.close()

if __name__ == '__main__':
    import sys
    json_path = sys.argv[1] if len(sys.argv) > 1 else 'data/conversations.json'
    import_openai_conversations(json_path)

