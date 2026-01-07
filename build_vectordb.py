"""
Build vector database from conversations using ONNX embeddings.

This script:
1. Loads conversations from conversations.db
2. Embeds them using the ONNX embedder
3. Stores them in storyvectordb
4. Supports multiple strategies:
   - Summary-based (uses metadata summary if available)
   - Full conversation text
   - Chunked messages (for granular search)
"""
import sqlite3
import json
import sys
import os
from typing import List, Dict, Optional
from pathlib import Path

# Add storyvectordb to path
sys.path.insert(0, str(Path(__file__).parent / "storyvectordb" / "src"))
from sqlite_vectordb import SQLiteVectorDB

from embeddings_onnx import OfflineEmbedder

DB_PATH = 'conversations.db'
VECTORDB_PATH = 'conversations_vectordb.db'


def get_conversation_text(conn: sqlite3.Connection, conversation_id: str) -> str:
    """Get full conversation text from messages."""
    cursor = conn.execute('''
        SELECT role, content 
        FROM messages 
        WHERE conversation_id = ?
        ORDER BY create_time ASC, id ASC
    ''', (conversation_id,))
    
    parts = []
    for row in cursor.fetchall():
        role, content = row
        if content:
            parts.append(f"{role}: {content}")
    
    return "\n\n".join(parts)


def get_conversation_metadata(conn: sqlite3.Connection, conversation_id: str) -> Optional[Dict]:
    """Get conversation metadata if available."""
    cursor = conn.execute('''
        SELECT metadata_json
        FROM conversation_metadata
        WHERE conversation_id = ?
    ''', (conversation_id,))
    
    row = cursor.fetchone()
    if row and row[0]:
        try:
            metadata = json.loads(row[0])
            return metadata
        except:
            pass
    
    return None


def chunk_messages_func(messages: List[Dict], chunk_size: int = 500) -> List[str]:
    """
    Chunk messages into smaller pieces for embedding.
    
    Args:
        messages: List of message dicts with 'role' and 'content'
        chunk_size: Target chunk size in words
    
    Returns:
        List of chunked text strings
    """
    chunks = []
    current_chunk = []
    current_size = 0
    
    for msg in messages:
        content = msg.get('content', '')
        if not content:
            continue
        
        words = content.split()
        word_count = len(words)
        
        # If single message is larger than chunk_size, split it
        if word_count > chunk_size:
            # Save current chunk if any
            if current_chunk:
                chunks.append("\n\n".join(current_chunk))
                current_chunk = []
                current_size = 0
            
            # Split large message
            for i in range(0, word_count, chunk_size):
                chunk_words = words[i:i + chunk_size]
                chunks.append(" ".join(chunk_words))
        else:
            # Add to current chunk
            if current_size + word_count > chunk_size and current_chunk:
                chunks.append("\n\n".join(current_chunk))
                current_chunk = [content]
                current_size = word_count
            else:
                current_chunk.append(content)
                current_size += word_count
    
    # Add remaining chunk
    if current_chunk:
        chunks.append("\n\n".join(current_chunk))
    
    return chunks


def get_conversation_messages(conn: sqlite3.Connection, conversation_id: str) -> List[Dict]:
    """Get all messages for a conversation."""
    cursor = conn.execute('''
        SELECT role, content, create_time
        FROM messages 
        WHERE conversation_id = ?
        ORDER BY create_time ASC, id ASC
    ''', (conversation_id,))
    
    messages = []
    for row in cursor.fetchall():
        messages.append({
            'role': row[0],
            'content': row[1] or '',
            'create_time': row[2]
        })
    
    return messages


def build_vectordb(
    strategy: str = 'summary',
    chunk_messages: bool = False,
    chunk_size: int = 500,
    limit: Optional[int] = None
):
    """
    Build vector database from conversations.
    
    Args:
        strategy: 'summary' (use metadata summary), 'full' (full conversation text), or 'both'
        chunk_messages: If True, also embed individual message chunks
        chunk_size: Target chunk size in words (if chunk_messages=True)
        limit: Limit number of conversations to process
    """
    print("="*70)
    print("Building Vector Database from Conversations")
    print("="*70)
    
    # Load embedder
    print("\n[1/4] Loading ONNX embedder...")
    try:
        embedder = OfflineEmbedder.load()
        print(f"  [SUCCESS] ONNX embedder loaded")
    except Exception as e:
        print(f"  [ERROR] Failed to load embedder: {e}")
        return
    
    # Connect to databases
    print("\n[2/4] Connecting to databases...")
    conn = sqlite3.connect(DB_PATH)
    vectordb = SQLiteVectorDB(VECTORDB_PATH)
    print(f"  Conversations DB: {DB_PATH}")
    print(f"  Vector DB: {VECTORDB_PATH}")
    
    # Get conversations
    print("\n[3/4] Loading conversations...")
    query = 'SELECT conversation_id, title, ai_source FROM conversations ORDER BY create_time'
    if limit:
        query += f' LIMIT {limit}'
    
    cursor = conn.execute(query)
    conversations = cursor.fetchall()
    print(f"  Found {len(conversations)} conversations")
    
    # Process conversations
    print("\n[4/4] Embedding and storing conversations...")
    print(f"  Strategy: {strategy}")
    print(f"  Chunk messages: {chunk_messages}")
    print("-"*70)
    
    total_vectors = 0
    skipped = 0
    
    for idx, (conv_id, title, ai_source) in enumerate(conversations, 1):
        print(f"\n[{idx}/{len(conversations)}] {conv_id[:40]}...")
        print(f"  Title: {title or '(no title)'}")
        
        try:
            # Get metadata
            metadata = get_conversation_metadata(conn, conv_id)
            has_metadata = metadata is not None
            
            # Strategy: summary
            if strategy in ['summary', 'both']:
                if metadata and metadata.get('summary'):
                    summary = metadata['summary']
                    print(f"  [Summary] Embedding summary ({len(summary)} chars)...")
                    
                    embedding = embedder.embed_single(summary)
                    vectordb.insert(
                        content=summary,
                        vector=embedding.tolist(),
                        metadata={
                            'conversation_id': conv_id,
                            'title': title,
                            'ai_source': ai_source,
                            'type': 'summary',
                            'has_metadata': has_metadata
                        },
                        file_id=conv_id
                    )
                    total_vectors += 1
                    print(f"    [OK] Stored summary vector")
                else:
                    print(f"  [Summary] No metadata summary available, skipping")
            
            # Strategy: full conversation
            if strategy in ['full', 'both']:
                full_text = get_conversation_text(conn, conv_id)
                if full_text.strip():
                    print(f"  [Full] Embedding full conversation ({len(full_text)} chars)...")
                    
                    embedding = embedder.embed_single(full_text)
                    vectordb.insert(
                        content=full_text,
                        vector=embedding.tolist(),
                        metadata={
                            'conversation_id': conv_id,
                            'title': title,
                            'ai_source': ai_source,
                            'type': 'full',
                            'has_metadata': has_metadata
                        },
                        file_id=f"{conv_id}_full"
                    )
                    total_vectors += 1
                    print(f"    [OK] Stored full conversation vector")
            
            # Strategy: chunked messages
            if chunk_messages:
                messages = get_conversation_messages(conn, conv_id)
                chunks = chunk_messages_func(messages, chunk_size=chunk_size)
                
                if chunks:
                    print(f"  [Chunks] Embedding {len(chunks)} message chunks...")
                    
                    # Embed chunks in batch
                    embeddings = embedder.embed(chunks, batch_size=32)
                    
                    # Store chunks
                    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                        vectordb.insert(
                            content=chunk,
                            vector=embedding.tolist(),
                            metadata={
                                'conversation_id': conv_id,
                                'title': title,
                                'ai_source': ai_source,
                                'type': 'chunk',
                                'chunk_index': i,
                                'total_chunks': len(chunks),
                                'has_metadata': has_metadata
                            },
                            file_id=f"{conv_id}_chunk_{i}"
                        )
                        total_vectors += 1
                    
                    print(f"    [OK] Stored {len(chunks)} chunk vectors")
        
        except Exception as e:
            skipped += 1
            print(f"  [ERROR] Failed to process: {e}")
            import traceback
            traceback.print_exc()
    
    # Print summary
    stats = vectordb.get_stats()
    print("\n" + "="*70)
    print("[COMPLETE] Vector database built")
    print("="*70)
    print(f"  Total vectors stored: {total_vectors}")
    print(f"  Conversations processed: {len(conversations) - skipped}")
    print(f"  Skipped: {skipped}")
    print(f"\n  Vector DB stats:")
    print(f"    Total vectors: {stats['total_vectors']}")
    print(f"    Unique files: {stats['unique_files']}")
    
    conn.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Build vector database from conversations')
    parser.add_argument('--strategy', choices=['summary', 'full', 'both'], default='summary',
                       help='Embedding strategy: summary (use metadata), full (full text), or both')
    parser.add_argument('--chunk-messages', action='store_true',
                       help='Also embed individual message chunks')
    parser.add_argument('--chunk-size', type=int, default=500,
                       help='Chunk size in words (if chunk-messages=True)')
    parser.add_argument('--limit', type=int, default=None,
                       help='Limit number of conversations to process')
    
    args = parser.parse_args()
    
    build_vectordb(
        strategy=args.strategy,
        chunk_messages=args.chunk_messages,
        chunk_size=args.chunk_size,
        limit=args.limit
    )

