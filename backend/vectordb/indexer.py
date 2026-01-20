"""
VectorDB indexing: chunk conversations and embed them.

Chunking strategy:
- Prefer boundaries at user-query/assistant-response pairs (as many pairs as fit in 300-800 words)
- If a chunk is inside a single query/response, just chunk it normally
- Store conversation-level embedding (average of chunk embeddings)
"""

from __future__ import annotations

import sqlite3
from typing import Dict, List, Optional, Tuple
import numpy as np

from backend.vectordb.sqlite_vectordb import SQLiteVectorDB
from backend.vectordb.service import get_embedder, get_vectordb_path


def chunk_conversation_messages(
    messages: List[Dict],
    min_words: int = 300,
    max_words: int = 800,
) -> List[Dict]:
    """
    Chunk messages with preference for user-query/assistant-response boundaries.
    
    Args:
        messages: List of dicts with keys: message_id, role, content, create_time
        min_words: Minimum chunk size in words
        max_words: Maximum chunk size in words
    
    Returns:
        List of chunk dicts with keys:
        - content: chunk text
        - message_ids: list of message IDs in this chunk
        - chunk_index: index of this chunk (0-based)
        - total_chunks: total number of chunks for this conversation
    """
    if not messages:
        return []
    
    chunks: List[Dict] = []
    current_chunk: List[Dict] = []
    current_words = 0
    chunk_index = 0
    
    i = 0
    while i < len(messages):
        msg = messages[i]
        content = msg.get('content', '') or ''
        words = len(content.split())
        
        # If single message exceeds max_words, split it
        if words > max_words:
            # Save current chunk if any
            if current_chunk:
                chunks.append({
                    'content': _format_chunk(current_chunk),
                    'message_ids': [m['message_id'] for m in current_chunk],
                    'chunk_index': chunk_index,
                    'total_chunks': 0,  # Will be set later
                })
                chunk_index += 1
                current_chunk = []
                current_words = 0
            
            # Split large message into word-based chunks
            word_list = content.split()
            for j in range(0, len(word_list), max_words):
                chunk_words = word_list[j:j + max_words]
                chunks.append({
                    'content': ' '.join(chunk_words),
                    'message_ids': [msg['message_id']],
                    'chunk_index': chunk_index,
                    'total_chunks': 0,  # Will be set later
                })
                chunk_index += 1
            i += 1
            continue
        
        # Try to add complete user-query/assistant-response pairs
        if i + 1 < len(messages):
            next_msg = messages[i + 1]
            # Check if we have a user/assistant pair
            if (msg.get('role') == 'user' and next_msg.get('role') == 'assistant') or \
               (msg.get('role') == 'user' and next_msg.get('role') == 'system'):
                pair_words = words + len((next_msg.get('content', '') or '').split())
                
                # If adding the pair would exceed max, finalize current chunk
                if current_words + pair_words > max_words and current_chunk:
                    chunks.append({
                        'content': _format_chunk(current_chunk),
                        'message_ids': [m['message_id'] for m in current_chunk],
                        'chunk_index': chunk_index,
                        'total_chunks': 0,  # Will be set later
                    })
                    chunk_index += 1
                    current_chunk = []
                    current_words = 0
                
                # Add both messages as a pair
                current_chunk.append(msg)
                current_chunk.append(next_msg)
                current_words += pair_words
                i += 2
                
                # If we've reached a good size, finalize
                if current_words >= min_words:
                    chunks.append({
                        'content': _format_chunk(current_chunk),
                        'message_ids': [m['message_id'] for m in current_chunk],
                        'chunk_index': chunk_index,
                        'total_chunks': 0,  # Will be set later
                    })
                    chunk_index += 1
                    current_chunk = []
                    current_words = 0
                continue
        
        # Single message (or not a pair)
        # If adding would exceed max, finalize current chunk
        if current_words + words > max_words and current_chunk:
            chunks.append({
                'content': _format_chunk(current_chunk),
                'message_ids': [m['message_id'] for m in current_chunk],
                'chunk_index': chunk_index,
                'total_chunks': 0,  # Will be set later
            })
            chunk_index += 1
            current_chunk = []
            current_words = 0
        
        # Add message to current chunk
        current_chunk.append(msg)
        current_words += words
        
        # If we've reached a good size, finalize
        if current_words >= min_words:
            chunks.append({
                'content': _format_chunk(current_chunk),
                'message_ids': [m['message_id'] for m in current_chunk],
                'chunk_index': chunk_index,
                'total_chunks': 0,  # Will be set later
            })
            chunk_index += 1
            current_chunk = []
            current_words = 0
        
        i += 1
    
    # Add remaining chunk
    if current_chunk:
        chunks.append({
            'content': _format_chunk(current_chunk),
            'message_ids': [m['message_id'] for m in current_chunk],
            'chunk_index': chunk_index,
            'total_chunks': 0,  # Will be set later
        })
        chunk_index += 1
    
    # Set total_chunks for all chunks
    total_chunks = len(chunks)
    for chunk in chunks:
        chunk['total_chunks'] = total_chunks
    
    return chunks


def _format_chunk(messages: List[Dict]) -> str:
    """Format a list of messages into chunk text."""
    parts = []
    for msg in messages:
        role = msg.get('role', 'unknown')
        content = msg.get('content', '') or ''
        parts.append(f"{role}: {content}")
    return "\n\n".join(parts)


def index_conversations(
    db_path: str,
    vectordb_path: str,
    conversation_ids: Optional[List[str]] = None,
    progress_callback: Optional[callable] = None,
) -> Dict:
    """
    Index conversations into the vectordb.
    
    Args:
        db_path: Path to conversations.db
        vectordb_path: Path to conversations_vectordb.db
        conversation_ids: Optional list of specific conversation IDs to index (None = all)
        progress_callback: Optional function(progress: int, message: str) for progress updates
    
    Returns:
        Dict with stats: total_conversations, total_chunks, total_vectors
    """
    embedder = get_embedder()
    vectordb = SQLiteVectorDB(vectordb_path)
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    # Get conversations to index
    if conversation_ids:
        placeholders = ','.join(['?'] * len(conversation_ids))
        query = f"""
            SELECT conversation_id, title, ai_source
            FROM conversations
            WHERE conversation_id IN ({placeholders})
            ORDER BY create_time
        """
        cursor = conn.execute(query, conversation_ids)
    else:
        query = """
            SELECT conversation_id, title, ai_source
            FROM conversations
            ORDER BY create_time
        """
        cursor = conn.execute(query)
    
    conversations = cursor.fetchall()
    total_conversations = len(conversations)
    total_chunks = 0
    total_vectors = 0
    
    if progress_callback:
        progress_callback(0, f"Starting indexing of {total_conversations} conversations...")
    
    for idx, conv_row in enumerate(conversations):
        conv_id = conv_row['conversation_id']
        title = conv_row.get('title') or ''
        ai_source = conv_row.get('ai_source') or 'gpt'
        
        try:
            # Get messages for this conversation
            msg_cursor = conn.execute("""
                SELECT message_id, role, content, create_time
                FROM messages
                WHERE conversation_id = ?
                ORDER BY create_time ASC, id ASC
            """, (conv_id,))
            
            messages = []
            for msg_row in msg_cursor.fetchall():
                messages.append({
                    'message_id': msg_row['message_id'],
                    'role': msg_row['role'],
                    'content': msg_row['content'] or '',
                    'create_time': msg_row['create_time'],
                })
            
            if not messages:
                continue
            
            # Chunk messages
            chunks = chunk_conversation_messages(messages, min_words=300, max_words=800)
            if not chunks:
                continue
            
            total_chunks += len(chunks)
            
            # Embed chunks
            chunk_texts = [chunk['content'] for chunk in chunks]
            chunk_embeddings = embedder.embed(chunk_texts, batch_size=32)
            
            # Store chunks
            chunk_vectors = []
            for chunk, embedding in zip(chunks, chunk_embeddings):
                vectordb.insert(
                    content=chunk['content'],
                    vector=embedding.tolist(),
                    metadata={
                        'conversation_id': conv_id,
                        'title': title,
                        'ai_source': ai_source,
                        'type': 'chunk',
                        'chunk_index': chunk['chunk_index'],
                        'total_chunks': chunk['total_chunks'],
                        'message_ids': chunk['message_ids'],
                    },
                    file_id=f"{conv_id}_chunk_{chunk['chunk_index']}",
                )
                chunk_vectors.append(embedding)
                total_vectors += 1
            
            # Compute conversation-level embedding (average of chunk embeddings)
            if chunk_vectors:
                conv_embedding = np.mean(chunk_vectors, axis=0)
                # L2 normalize
                norm = np.linalg.norm(conv_embedding)
                if norm > 0:
                    conv_embedding = conv_embedding / norm
                
                # Store conversation-level embedding
                conv_text = "\n\n".join([f"{m['role']}: {m['content']}" for m in messages])
                vectordb.insert(
                    content=conv_text[:1000],  # Truncate for storage (we have chunks for detail)
                    vector=conv_embedding.tolist(),
                    metadata={
                        'conversation_id': conv_id,
                        'title': title,
                        'ai_source': ai_source,
                        'type': 'conversation',
                    },
                    file_id=f"{conv_id}_conversation",
                )
                total_vectors += 1
            
            if progress_callback:
                progress = int((idx + 1) / total_conversations * 100)
                try:
                    progress_callback(
                        progress,
                        f"Indexed {idx + 1}/{total_conversations} conversations ({len(chunks)} chunks)",
                    )
                except Exception as e:
                    # Progress callback may fail (e.g., thread safety), log but continue
                    print(f"Progress callback error: {e}")
        
        except Exception as e:
            # Log error but continue
            print(f"Error indexing conversation {conv_id}: {e}")
            continue
    
    conn.close()
    
    return {
        'total_conversations': total_conversations,
        'total_chunks': total_chunks,
        'total_vectors': total_vectors,
    }
