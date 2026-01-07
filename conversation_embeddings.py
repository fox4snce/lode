"""
Helper module for embedding conversations and preparing them for vector DB storage.

This module provides utilities to:
- Extract messages from conversations in the database
- Generate embeddings for conversation messages
- Prepare data for insertion into the vector database
"""

import sqlite3
from typing import List, Dict, Optional
from openai_llm import get_embedding
from pathlib import Path

def extract_conversation_messages(db_path: str = 'conversations.db', conversation_id: Optional[str] = None) -> List[Dict]:
    """
    Extract messages from conversations in the database.
    
    Args:
        db_path: Path to the conversations database
        conversation_id: Optional specific conversation ID to extract.
                        If None, extracts all conversations.
    
    Returns:
        List of dictionaries with message data including:
        - conversation_id: The conversation ID
        - message_id: The message ID
        - role: user, assistant, or system
        - content: The message content
        - create_time: Timestamp
        - ai_source: gpt or claude
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    if conversation_id:
        cursor.execute('''
            SELECT 
                m.conversation_id,
                m.message_id,
                m.role,
                m.content,
                m.create_time,
                c.ai_source,
                c.title as conversation_title
            FROM messages m
            JOIN conversations c ON m.conversation_id = c.conversation_id
            WHERE m.conversation_id = ?
            ORDER BY m.create_time ASC, m.id ASC
        ''', (conversation_id,))
    else:
        cursor.execute('''
            SELECT 
                m.conversation_id,
                m.message_id,
                m.role,
                m.content,
                m.create_time,
                c.ai_source,
                c.title as conversation_title
            FROM messages m
            JOIN conversations c ON m.conversation_id = c.conversation_id
            ORDER BY m.conversation_id, m.create_time ASC, m.id ASC
        ''')
    
    messages = []
    for row in cursor.fetchall():
        messages.append({
            'conversation_id': row['conversation_id'],
            'message_id': row['message_id'],
            'role': row['role'],
            'content': row['content'],
            'create_time': row['create_time'],
            'ai_source': row['ai_source'],
            'conversation_title': row['conversation_title']
        })
    
    conn.close()
    return messages


def prepare_messages_for_vectordb(
    messages: List[Dict],
    embedding_model: str = "text-embedding-3-small",
    dimensions: Optional[int] = None,
    include_metadata: bool = True
) -> List[Dict]:
    """
    Prepare messages for vector DB insertion by generating embeddings.
    
    Args:
        messages: List of message dictionaries from extract_conversation_messages
        embedding_model: Embedding model to use (default: "text-embedding-3-small")
        dimensions: Optional dimensions for embedding (default: model's native size)
        include_metadata: Whether to include conversation metadata
    
    Returns:
        List of dictionaries ready for vector DB insertion with:
        - content: The message content
        - vector: The embedding vector
        - metadata: Optional metadata dict
        - file_id: The conversation_id (used as file_id in vector DB)
    """
    items = []
    
    # Generate embeddings for all messages
    texts = [msg['content'] for msg in messages]
    embeddings = get_embedding(texts, model=embedding_model, dimensions=dimensions)
    
    for i, msg in enumerate(messages):
        item = {
            'content': msg['content'],
            'vector': embeddings[i],
            'file_id': msg['conversation_id']
        }
        
        if include_metadata:
            item['metadata'] = {
                'message_id': msg['message_id'],
                'role': msg['role'],
                'create_time': msg['create_time'],
                'ai_source': msg['ai_source'],
                'conversation_title': msg.get('conversation_title'),
                'conversation_id': msg['conversation_id']
            }
        
        items.append(item)
    
    return items


def embed_conversations_batch(
    db_path: str = 'conversations.db',
    vectordb_path: str = 'conversations_vectordb.db',
    embedding_model: str = "text-embedding-3-small",
    dimensions: Optional[int] = None,
    batch_size: int = 100,
    conversation_id: Optional[str] = None
) -> Dict:
    """
    Embed conversations and insert them into the vector database.
    
    Args:
        db_path: Path to conversations database
        vectordb_path: Path to vector database file
        embedding_model: Embedding model to use
        dimensions: Optional embedding dimensions
        batch_size: Number of messages to process in each batch
        conversation_id: Optional specific conversation to embed (None = all)
    
    Returns:
        Dictionary with statistics about the embedding process
    """
    # Import the vector DB
    import sys
    sys.path.insert(0, str(Path('storyvectordb/src').absolute()))
    from sqlite_vectordb import SQLiteVectorDB
    
    # Initialize vector DB
    vectordb = SQLiteVectorDB(vectordb_path)
    
    # Extract messages
    print(f"Extracting messages from {db_path}...")
    messages = extract_conversation_messages(db_path, conversation_id)
    print(f"Found {len(messages)} messages")
    
    if not messages:
        return {'total_messages': 0, 'inserted': 0}
    
    # Process in batches
    total_inserted = 0
    for i in range(0, len(messages), batch_size):
        batch = messages[i:i + batch_size]
        print(f"Processing batch {i//batch_size + 1}/{(len(messages)-1)//batch_size + 1} ({len(batch)} messages)...")
        
        # Prepare batch for vector DB
        items = prepare_messages_for_vectordb(
            batch,
            embedding_model=embedding_model,
            dimensions=dimensions,
            include_metadata=True
        )
        
        # Insert into vector DB
        ids = vectordb.insert_batch(items)
        total_inserted += len(ids)
        print(f"Inserted {len(ids)} vectors")
    
    stats = vectordb.get_stats()
    
    return {
        'total_messages': len(messages),
        'inserted': total_inserted,
        'vectordb_stats': stats
    }


if __name__ == "__main__":
    # Example usage
    print("Conversation Embeddings Helper")
    print("=" * 50)
    
    # Example: Extract messages from a conversation
    messages = extract_conversation_messages(conversation_id=None)
    print(f"\nTotal messages in database: {len(messages)}")
    
    if messages:
        print(f"\nSample message:")
        print(f"  Conversation: {messages[0].get('conversation_title', 'N/A')}")
        print(f"  Role: {messages[0]['role']}")
        print(f"  Content preview: {messages[0]['content'][:100]}...")
        print(f"  AI Source: {messages[0]['ai_source']}")

