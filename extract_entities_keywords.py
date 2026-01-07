"""
Extract entities and keywords from conversations using Stanza (NER) and KeyBERT (keyphrase extraction).

This pipeline:
1. Uses Stanza to extract named entities and candidate phrases
2. Uses KeyBERT with local embeddings to extract top keyphrases
3. Stores results in the database
"""

import sqlite3
import json
import hashlib
import re
from typing import List, Dict, Optional, Tuple, Set
from pathlib import Path
from datetime import datetime
import urllib.request
import urllib.parse

import stanza
import numpy as np


DB_PATH = 'conversations.db'
EMBEDDINGS_URL = 'http://localhost:1234/v1/embeddings'
EMBEDDINGS_MODEL = 'text-embedding-nomic-embed-text-v1.5'
MAX_KEYWORDS = 25
CANDIDATE_PHRASE_MIN_WORDS = 2
CANDIDATE_PHRASE_MAX_WORDS = 5


def normalize_text(text: str) -> str:
    """Normalize text for analysis (collapse whitespace, standardize quotes)."""
    # Collapse repeated whitespace
    text = re.sub(r'\s+', ' ', text)
    # Standardize quotes (optional - keep simple for now)
    text = text.strip()
    return text


def get_conversation_messages(conn: sqlite3.Connection, conversation_id: str) -> List[Dict]:
    """Get all messages for a conversation in chronological order."""
    cursor = conn.execute('''
        SELECT 
            m.message_id,
            m.role,
            m.content,
            m.create_time,
            c.ai_source
        FROM messages m
        JOIN conversations c ON m.conversation_id = c.conversation_id
        WHERE m.conversation_id = ?
        ORDER BY m.create_time ASC, m.id ASC
    ''', (conversation_id,))
    
    messages = []
    for row in cursor.fetchall():
        messages.append({
            'message_id': row[0],
            'role': row[1],
            'content': row[2],
            'create_time': row[3],
            'ai_source': row[4] if len(row) > 4 else 'gpt'
        })
    
    return messages


def assemble_conversation_text(messages: List[Dict], include_speakers: bool = False) -> str:
    """
    Assemble conversation text from messages.
    Optionally include speaker labels (default: omit to avoid polluting entities/keywords).
    """
    parts = []
    for msg in messages:
        content = msg['content']
        if not content:
            continue
        
        if include_speakers:
            role = msg['role']
            parts.append(f"{role}: {content}")
        else:
            parts.append(content)
    
    return "\n\n".join(parts)


def get_embedding(text: str, cache_conn: Optional[sqlite3.Connection] = None) -> List[float]:
    """
    Get embedding for text using local embeddings endpoint.
    Uses cache if available.
    """
    # Generate hash for caching
    text_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()
    
    # Check cache
    if cache_conn:
        cursor = cache_conn.execute('''
            SELECT vector FROM embedding_cache
            WHERE text_hash = ? AND model = ?
        ''', (text_hash, EMBEDDINGS_MODEL))
        row = cursor.fetchone()
        if row:
            return json.loads(row[0])
    
    # Call embeddings API
    data = {
        "model": EMBEDDINGS_MODEL,
        "input": text
    }
    req = urllib.request.Request(
        EMBEDDINGS_URL,
        data=json.dumps(data).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.loads(response.read().decode('utf-8'))
            embedding = result['data'][0]['embedding']
            
            # Cache the embedding
            if cache_conn:
                cache_conn.execute('''
                    INSERT OR REPLACE INTO embedding_cache (text_hash, model, vector)
                    VALUES (?, ?, ?)
                ''', (text_hash, EMBEDDINGS_MODEL, json.dumps(embedding)))
                cache_conn.commit()
            
            return embedding
    except Exception as e:
        print(f"  [ERROR] Failed to get embedding: {e}")
        raise


def get_embeddings_batch(texts: List[str], cache_conn: Optional[sqlite3.Connection] = None) -> List[List[float]]:
    """
    Get embeddings for multiple texts in a single batch call.
    Falls back to individual calls if batch fails.
    """
    # Check cache for all texts first
    cached_embeddings = {}
    uncached_texts = []
    uncached_indices = []
    
    if cache_conn:
        for i, text in enumerate(texts):
            text_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()
            cursor = cache_conn.execute('''
                SELECT vector FROM embedding_cache
                WHERE text_hash = ? AND model = ?
            ''', (text_hash, EMBEDDINGS_MODEL))
            row = cursor.fetchone()
            if row:
                cached_embeddings[i] = json.loads(row[0])
            else:
                uncached_texts.append(text)
                uncached_indices.append(i)
    else:
        uncached_texts = texts
        uncached_indices = list(range(len(texts)))
    
    # If all cached, return cached results
    if not uncached_texts:
        return [cached_embeddings[i] for i in range(len(texts))]
    
    # Call embeddings API for uncached texts
    data = {
        "model": EMBEDDINGS_MODEL,
        "input": uncached_texts
    }
    req = urllib.request.Request(
        EMBEDDINGS_URL,
        data=json.dumps(data).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            result = json.loads(response.read().decode('utf-8'))
            embeddings = [item['embedding'] for item in result['data']]
            
            # Cache the embeddings
            if cache_conn:
                for i, text, embedding in zip(uncached_indices, uncached_texts, embeddings):
                    text_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()
                    cache_conn.execute('''
                        INSERT OR REPLACE INTO embedding_cache (text_hash, model, vector)
                        VALUES (?, ?, ?)
                    ''', (text_hash, EMBEDDINGS_MODEL, json.dumps(embedding)))
                cache_conn.commit()
            
            # Combine cached and new embeddings
            result_embeddings = []
            cached_idx = 0
            for i in range(len(texts)):
                if i in cached_embeddings:
                    result_embeddings.append(cached_embeddings[i])
                else:
                    result_embeddings.append(embeddings[cached_idx])
                    cached_idx += 1
            
            return result_embeddings
    except Exception as e:
        print(f"  [WARNING] Batch embedding failed, falling back to individual calls: {e}")
        # Fallback to individual calls
        embeddings = []
        for i in range(len(texts)):
            if i in cached_embeddings:
                embeddings.append(cached_embeddings[i])
            else:
                emb = get_embedding(uncached_texts[uncached_indices.index(i)] if i in uncached_indices else texts[i], cache_conn)
                embeddings.append(emb)
        return embeddings


def normalize_entity_text(text: str) -> str:
    """Normalize entity text for deduplication."""
    # Trim whitespace and punctuation
    text = text.strip().strip('.,;:!?"()[]{}')
    # Collapse internal whitespace
    text = re.sub(r'\s+', ' ', text)
    # Case normalize (keep original for display)
    return text.lower()


def extract_entities_stanza(text: str, nlp: stanza.Pipeline) -> List[Dict]:
    """
    Extract named entities using Stanza.
    Returns list of entity dicts with: text, label, start_char, end_char, normalized_text
    """
    doc = nlp(text)
    entities = []
    entity_texts = set()
    
    for ent in doc.entities:
        text = ent.text
        normalized = normalize_entity_text(text)
        
        # Skip if already seen (dedupe)
        if normalized in entity_texts:
            continue
        
        entity_texts.add(normalized)
        entities.append({
            'text': text,
            'label': ent.type,
            'start_char': ent.start_char,
            'end_char': ent.end_char,
            'normalized_text': normalized
        })
    
    return entities


def extract_candidate_phrases_stanza(text: str, nlp: stanza.Pipeline) -> List[str]:
    """
    Extract candidate noun phrases and meaningful phrases from Stanza parse.
    Filters for 2-5 word phrases, excludes stopword-only phrases.
    """
    doc = nlp(text)
    candidates = []
    seen = set()
    
    # Extract noun phrases using dependency parse
    for sentence in doc.sentences:
        # Build noun phrases by following dependency relations
        for word in sentence.words:
            if word.upos not in ['NOUN', 'PROPN']:
                continue
            
            # Start with this noun
            phrase_words = [word]
            phrase_text = [word.text]
            
            # Collect modifiers (adjectives, compound nouns, etc.)
            for other in sentence.words:
                if other.head == word.id:
                    if other.deprel in ['amod', 'compound', 'nmod', 'det', 'nummod']:
                        if other.upos in ['ADJ', 'NOUN', 'PROPN', 'DET', 'NUM']:
                            # Insert before the head noun
                            phrase_words.insert(0, other)
                            phrase_text.insert(0, other.text)
            
            # Check if phrase is valid length
            if CANDIDATE_PHRASE_MIN_WORDS <= len(phrase_text) <= CANDIDATE_PHRASE_MAX_WORDS:
                phrase = ' '.join(phrase_text)
                phrase_lower = phrase.lower()
                if phrase_lower not in seen and len(phrase.strip()) > 3:
                    seen.add(phrase_lower)
                    candidates.append(phrase)
    
    # Also extract simple n-grams (2-5 words) as fallback
    words = re.findall(r'\b\w+\b', text)  # Extract words only
    for n in range(CANDIDATE_PHRASE_MIN_WORDS, CANDIDATE_PHRASE_MAX_WORDS + 1):
        for i in range(len(words) - n + 1):
            phrase = ' '.join(words[i:i+n])
            phrase_lower = phrase.lower()
            if phrase_lower not in seen and len(phrase) > 3:
                seen.add(phrase_lower)
                candidates.append(phrase)
    
    return candidates[:200]  # Limit candidates


def store_entities(conn: sqlite3.Connection, conversation_id: str, entities: List[Dict]) -> None:
    """Store entities in the database with deduplication."""
    # Group entities by normalized text
    entity_groups: Dict[str, List[Dict]] = {}
    for ent in entities:
        norm = ent['normalized_text']
        if norm not in entity_groups:
            entity_groups[norm] = []
        entity_groups[norm].append(ent)
    
    # Delete existing entities for this conversation
    conn.execute('''
        DELETE FROM conversation_entities WHERE conversation_id = ?
    ''', (conversation_id,))
    
    # Upsert entities
    for normalized_text, group in entity_groups.items():
        # Find most common surface form
        surface_forms = [e['text'] for e in group]
        display_text = max(set(surface_forms), key=surface_forms.count)
        
        # Get primary entity type
        types = [e['label'] for e in group]
        primary_type = max(set(types), key=types.count) if types else None
        
        # Insert or get entity_id
        cursor = conn.execute('''
            INSERT INTO entities (canonical_text, preferred_display_text, entity_type)
            VALUES (?, ?, ?)
            ON CONFLICT(canonical_text) DO UPDATE SET
                preferred_display_text = excluded.preferred_display_text,
                entity_type = COALESCE(excluded.entity_type, entities.entity_type),
                updated_at = CURRENT_TIMESTAMP
            RETURNING entity_id
        ''', (normalized_text, display_text, primary_type))
        
        result = cursor.fetchone()
        entity_id = result[0] if result else None
        
        if not entity_id:
            # Fetch entity_id if insert didn't return it
            cursor = conn.execute('SELECT entity_id FROM entities WHERE canonical_text = ?', (normalized_text,))
            row = cursor.fetchone()
            entity_id = row[0] if row else None
        
        if entity_id:
            # Insert conversation-entity link
            conn.execute('''
                INSERT INTO conversation_entities
                (conversation_id, entity_id, count, surface_forms)
                VALUES (?, ?, ?, ?)
            ''', (conversation_id, entity_id, len(group), json.dumps(surface_forms)))
    
    conn.commit()


def store_keywords(conn: sqlite3.Connection, conversation_id: str, keywords: List[Tuple[str, float]], 
                   method_config: Optional[Dict] = None) -> None:
    """Store keywords in the database with deduplication."""
    # Delete existing keywords for this conversation
    conn.execute('''
        DELETE FROM conversation_keywords WHERE conversation_id = ?
    ''', (conversation_id,))
    
    # Upsert keywords
    for rank, (phrase, score) in enumerate(keywords, 1):
        normalized = phrase.lower().strip()
        
        # Insert or get keyword_id
        cursor = conn.execute('''
            INSERT INTO keywords (canonical_phrase, preferred_display_phrase)
            VALUES (?, ?)
            ON CONFLICT(canonical_phrase) DO UPDATE SET
                preferred_display_phrase = excluded.preferred_display_phrase,
                updated_at = CURRENT_TIMESTAMP
            RETURNING keyword_id
        ''', (normalized, phrase))
        
        result = cursor.fetchone()
        keyword_id = result[0] if result else None
        
        if not keyword_id:
            # Fetch keyword_id if insert didn't return it
            cursor = conn.execute('SELECT keyword_id FROM keywords WHERE canonical_phrase = ?', (normalized,))
            row = cursor.fetchone()
            keyword_id = row[0] if row else None
        
        if keyword_id:
            # Insert conversation-keyword link
            config_json = json.dumps(method_config) if method_config else None
            conn.execute('''
                INSERT INTO conversation_keywords
                (conversation_id, keyword_id, score, rank, source, method_config)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (conversation_id, keyword_id, score, rank, 'keybert', config_json))
    
    conn.commit()


def process_conversation(
    conn: sqlite3.Connection,
    conversation_id: str,
    nlp: stanza.Pipeline,
    force_regenerate: bool = False
) -> bool:
    """
    Process a single conversation: extract entities and keywords, store in DB.
    Returns True if successful, False if skipped.
    """
    # Check if already processed (unless force)
    if not force_regenerate:
        cursor = conn.execute('''
            SELECT 1 FROM conversation_entities WHERE conversation_id = ?
            LIMIT 1
        ''', (conversation_id,))
        if cursor.fetchone():
            return False  # Already processed
    
    # Get messages
    messages = get_conversation_messages(conn, conversation_id)
    if not messages:
        return False
    
    # Assemble conversation text
    conversation_text = assemble_conversation_text(messages, include_speakers=False)
    normalized_text = normalize_text(conversation_text)
    
    if not normalized_text.strip():
        return False
    
    print(f"\n[Processing] {conversation_id}")
    print(f"  Text length: {len(normalized_text):,} chars, {len(normalized_text.split()):,} words")
    
    # Run Stanza
    print("  [Stanza] Running NER and phrase extraction...")
    entities = extract_entities_stanza(normalized_text, nlp)
    candidate_phrases = extract_candidate_phrases_stanza(normalized_text, nlp)
    
    print(f"  [Stanza] Found {len(entities)} entities, {len(candidate_phrases)} candidate phrases")
    
    # Store entities
    if entities:
        print(f"  [Database] Storing {len(entities)} entities...")
        store_entities(conn, conversation_id, entities)
        print(f"  [Database] Entities stored")
    
    # Run KeyBERT with local embeddings
    print("  [Embeddings] Getting document embedding...")
    doc_embedding = np.array(get_embedding(normalized_text, conn))
    doc_embedding = doc_embedding / (np.linalg.norm(doc_embedding) + 1e-8)  # Normalize
    print(f"  [Embeddings] Document embedding: {len(doc_embedding)} dimensions")
    
    # Get candidate phrase embeddings (batch)
    if candidate_phrases and len(candidate_phrases) > 0:
        print(f"  [Embeddings] Getting embeddings for {len(candidate_phrases)} candidate phrases (batched)...")
        candidate_embeddings = np.array(get_embeddings_batch(candidate_phrases, conn))
        candidate_embeddings = candidate_embeddings / (np.linalg.norm(candidate_embeddings, axis=1, keepdims=True) + 1e-8)
        print(f"  [Embeddings] Candidate embeddings ready: {candidate_embeddings.shape}")
        
        # Compute cosine similarities
        print("  [KeyBERT] Computing similarities...")
        similarities = np.dot(candidate_embeddings, doc_embedding)
        
        # Use MMR (Maximal Marginal Relevance) for diversity
        print(f"  [KeyBERT] Selecting top {MAX_KEYWORDS} keywords using MMR (diversity=0.5)...")
        selected_indices = []
        selected_embeddings_list = []
        lambda_param = 0.5  # Diversity parameter
        
        # Create a list of (index, similarity) tuples for remaining candidates
        remaining = [(i, similarities[i]) for i in range(len(candidate_phrases))]
        
        for iteration in range(min(MAX_KEYWORDS, len(candidate_phrases))):
            if not remaining:
                break
            
            if len(selected_indices) == 0:
                # First selection: pick highest similarity
                best_idx, best_sim = max(remaining, key=lambda x: x[1])
            else:
                # MMR: max(sim_to_doc - lambda * max_sim_to_selected)
                best_score = -float('inf')
                best_idx = None
                selected_embeddings_array = np.array(selected_embeddings_list)
                
                for idx, sim_to_doc in remaining:
                    # Compute max similarity to already selected phrases
                    if len(selected_embeddings_list) > 0:
                        sims_to_selected = np.dot(candidate_embeddings[idx], selected_embeddings_array.T)
                        max_sim_to_selected = float(np.max(sims_to_selected))
                    else:
                        max_sim_to_selected = 0.0
                    
                    mmr_score = sim_to_doc - lambda_param * max_sim_to_selected
                    if mmr_score > best_score:
                        best_score = mmr_score
                        best_idx = idx
            
            if best_idx is not None:
                selected_indices.append(best_idx)
                selected_embeddings_list.append(candidate_embeddings[best_idx])
                remaining = [(i, s) for i, s in remaining if i != best_idx]
        
        keywords = [(candidate_phrases[i], float(similarities[i])) for i in selected_indices if similarities[i] > 0.1]
        print(f"  [KeyBERT] Selected {len(keywords)} keywords (similarity > 0.1)")
    else:
        # Fallback: generate simple n-grams as candidates and rank them
        print("  [KeyBERT] No candidate phrases from Stanza, generating n-grams...")
        words = re.findall(r'\b\w+\b', normalized_text)
        ngram_candidates = []
        for n in range(CANDIDATE_PHRASE_MIN_WORDS, CANDIDATE_PHRASE_MAX_WORDS + 1):
            for i in range(len(words) - n + 1):
                ngram_candidates.append(' '.join(words[i:i+n]))
        
        if ngram_candidates:
            print(f"  [Embeddings] Getting embeddings for {min(200, len(ngram_candidates))} n-gram candidates...")
            candidate_embeddings = np.array(get_embeddings_batch(ngram_candidates[:200], conn))
            candidate_embeddings = candidate_embeddings / (np.linalg.norm(candidate_embeddings, axis=1, keepdims=True) + 1e-8)
            similarities = np.dot(candidate_embeddings, doc_embedding)
            
            # Simple top-N selection (no MMR for fallback)
            top_indices = np.argsort(similarities)[::-1][:MAX_KEYWORDS]
            keywords = [(ngram_candidates[i], float(similarities[i])) for i in top_indices if similarities[i] > 0.1]
            print(f"  [KeyBERT] Selected {len(keywords)} keywords from n-grams")
        else:
            keywords = []
            print("  [KeyBERT] No n-grams generated")
    
    # Store keywords
    if keywords:
        print(f"  [Database] Storing {len(keywords)} keywords...")
        method_config = {
            'max_keywords': MAX_KEYWORDS,
            'model': EMBEDDINGS_MODEL,
            'candidate_phrase_min_words': CANDIDATE_PHRASE_MIN_WORDS,
            'candidate_phrase_max_words': CANDIDATE_PHRASE_MAX_WORDS
        }
        store_keywords(conn, conversation_id, keywords, method_config)
        print(f"  [Database] Keywords stored")
    
    print(f"  [DONE] Conversation {conversation_id} processed successfully")
    return True


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Extract entities and keywords from conversations')
    parser.add_argument('--db', default=DB_PATH, help='Database path')
    parser.add_argument('--test', help='Test with a single conversation ID')
    parser.add_argument('--force', action='store_true', help='Force regenerate even if already processed')
    parser.add_argument('--lang', default='en', help='Stanza language (default: en)')
    parser.add_argument('--processors', default='tokenize,ner,pos,lemma,depparse', help='Stanza processors')
    parser.add_argument('--device', choices=['cpu', 'cuda'], default=None, 
                       help='Device to use (cpu or cuda). Auto-detects GPU if available and not specified.')
    args = parser.parse_args()
    
    # Detect GPU availability for Stanza
    use_gpu = False
    try:
        import torch
        print(f"PyTorch version: {torch.__version__}")
        
        cuda_available = torch.cuda.is_available()
        print(f"CUDA available: {cuda_available}")
        
        if cuda_available:
            print(f"  CUDA version: {torch.version.cuda}")
            print(f"  Number of GPUs: {torch.cuda.device_count()}")
            for i in range(torch.cuda.device_count()):
                print(f"    GPU {i}: {torch.cuda.get_device_name(i)}")
        else:
            print("  CUDA not available. Possible reasons:")
            print("    - PyTorch was installed without CUDA support")
            print("    - NVIDIA drivers not installed or outdated")
            print("    - CUDA toolkit not installed")
            print("  To install PyTorch with CUDA support:")
            print("    pip install torch --index-url https://download.pytorch.org/whl/cu118")
        
        # Determine device preference
        if args.device == 'cuda':
            if cuda_available:
                use_gpu = True
            else:
                print("\nWarning: CUDA requested but not available. Using CPU.")
                use_gpu = False
        elif args.device == 'cpu':
            use_gpu = False
            print("CPU explicitly requested via --device cpu")
        else:
            # Auto-detect: use GPU if available
            use_gpu = cuda_available
        
        if use_gpu:
            print(f"\nStanza: Using GPU ({torch.cuda.get_device_name(0)})")
        else:
            print("\nStanza: Using CPU")
    except ImportError:
        print("PyTorch not found. Stanza will use CPU.")
        print("  Install PyTorch: pip install torch")
        print("  For GPU support: pip install torch --index-url https://download.pytorch.org/whl/cu118")
        use_gpu = False
    
    print("Note: Embeddings are processed by external API server (GPU usage depends on server config)")
    
    # Initialize Stanza
    print(f"Initializing Stanza pipeline (lang={args.lang}, processors={args.processors})...")
    try:
        # Stanza automatically uses GPU if PyTorch detects CUDA, but we can be explicit
        # Note: Stanza Pipeline accepts use_gpu parameter (boolean)
        nlp = stanza.Pipeline(args.lang, processors=args.processors, verbose=False, use_gpu=use_gpu)
    except Exception as e:
        print(f"Error initializing Stanza: {e}")
        print("Make sure Stanza is installed and language models are downloaded:")
        print(f"  python -m stanza.download {args.lang}")
        if use_gpu:
            print("\nNote: GPU initialization failed. Falling back to CPU.")
            print("Make sure PyTorch with CUDA support is installed if you want GPU:")
            print("  pip install torch --index-url https://download.pytorch.org/whl/cu118")
            try:
                nlp = stanza.Pipeline(args.lang, processors=args.processors, verbose=False, use_gpu=False)
                print("Initialized with CPU instead.")
            except:
                return
        else:
            return
    
    # Connect to database
    conn = sqlite3.connect(args.db)
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA busy_timeout=5000')
    
    try:
        if args.test:
            # Test mode: process single conversation
            print(f"\n{'='*60}")
            print(f"TEST MODE: Processing single conversation")
            print(f"  Conversation ID: {args.test}")
            print(f"  Force regenerate: {args.force}")
            print(f"{'='*60}\n")
            success = process_conversation(conn, args.test, nlp, args.force)
            if success:
                print(f"\n{'='*60}")
                print(f"[SUCCESS] Conversation {args.test} processed successfully")
                print(f"{'='*60}")
            else:
                print(f"\n{'='*60}")
                print(f"[SKIPPED] Conversation {args.test} (already processed or empty)")
                print(f"{'='*60}")
        else:
            # Process all conversations
            cursor = conn.execute('SELECT conversation_id FROM conversations ORDER BY create_time DESC')
            conversation_ids = [row[0] for row in cursor.fetchall()]
            
            total = len(conversation_ids)
            print(f"\n{'='*60}")
            print(f"Processing {total:,} conversations...")
            print(f"{'='*60}\n")
            
            processed = 0
            skipped = 0
            errors = 0
            start_time = datetime.now()
            
            for idx, conv_id in enumerate(conversation_ids, 1):
                try:
                    print(f"[{idx:,}/{total:,}] ", end="", flush=True)
                    success = process_conversation(conn, conv_id, nlp, args.force)
                    if success:
                        processed += 1
                        if idx % 10 == 0:
                            elapsed = (datetime.now() - start_time).total_seconds()
                            rate = idx / elapsed if elapsed > 0 else 0
                            remaining = (total - idx) / rate if rate > 0 else 0
                            print(f"\n[Progress] {idx:,}/{total:,} ({100*idx/total:.1f}%) | "
                                  f"Processed: {processed:,} | Skipped: {skipped:,} | Errors: {errors:,} | "
                                  f"Rate: {rate:.1f} conv/min | ETA: {remaining/60:.1f} min\n")
                    else:
                        skipped += 1
                        print(f"[Skipped] {conv_id} (already processed or empty)")
                except Exception as e:
                    errors += 1
                    print(f"\n[ERROR] Failed to process {conv_id}: {e}")
                    import traceback
                    traceback.print_exc()
            
            elapsed_total = (datetime.now() - start_time).total_seconds()
            print(f"\n{'='*60}")
            print(f"[FINAL STATS]")
            print(f"  Total conversations: {total:,}")
            print(f"  Processed: {processed:,}")
            print(f"  Skipped: {skipped:,}")
            print(f"  Errors: {errors:,}")
            print(f"  Time elapsed: {elapsed_total/60:.1f} minutes")
            if processed > 0:
                print(f"  Average time per conversation: {elapsed_total/processed:.2f} seconds")
            print(f"{'='*60}")
    finally:
        conn.close()


if __name__ == '__main__':
    main()

