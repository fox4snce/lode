import pytest

# Manual integration script (requires LM Studio running locally).
pytest.skip("manual integration script (requires LM Studio)", allow_module_level=True)

"""
Test metadata extraction using LM Studio backend.

Tests the _extract_metadata_via_lmstudio function with a real conversation.
"""
import sqlite3
import json
from extract_conversation_metadata import (
    get_conversation_messages,
    format_conversation_for_llm,
    _extract_metadata_via_lmstudio,
)
import sys
from pathlib import Path

# Add database directory to path for imports
project_root = Path(__file__).parent.parent
database_dir = project_root / "database"
if str(database_dir) not in sys.path:
    sys.path.insert(0, str(database_dir))

from create_metadata_tables import create_metadata_tables

DB_PATH = 'conversations.db'
LMSTUDIO_URL = 'http://localhost:1234/v1'

def main():
    # Ensure tables exist
    create_metadata_tables(DB_PATH)
    
    # Connect to database
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    # Get a test conversation
    cursor = conn.execute('''
        SELECT conversation_id, title
        FROM conversations
        ORDER BY create_time DESC
        LIMIT 1
    ''')
    
    row = cursor.fetchone()
    if not row:
        print("No conversations found in database.")
        conn.close()
        return
    
    conversation_id = row[0]
    title = row[1] or "Untitled"
    
    print(f"Testing metadata extraction for conversation:")
    print(f"  ID: {conversation_id}")
    print(f"  Title: {title}")
    print(f"  Backend: LM Studio ({LMSTUDIO_URL})")
    print("=" * 70)
    
    # Get messages
    messages = get_conversation_messages(conn, conversation_id)
    if not messages:
        print("No messages found for this conversation.")
        conn.close()
        return
    
    # Format conversation text (limit for testing)
    conversation_text = format_conversation_for_llm(messages, max_chars=5000)
    
    print(f"\nConversation text (truncated to 5000 chars for test):")
    print(f"  Length: {len(conversation_text)} chars")
    print(f"  Messages: {len(messages)}")
    print("\n" + "=" * 70)
    print("Calling LM Studio to extract metadata...")
    print("=" * 70 + "\n")
    
    try:
        metadata = _extract_metadata_via_lmstudio(
            conversation_text=conversation_text,
            conversation_id=conversation_id,
            lmstudio_url=LMSTUDIO_URL,
            stream=False,  # Don't show streaming to keep output clean
            temperature=0.2
        )
        
        print("\n" + "=" * 70)
        print("SUCCESS! Metadata extracted and validated!")
        print("=" * 70)
        
        # Print full metadata as JSON for inspection (using ensure_ascii=True for Windows console)
        metadata_dict = metadata.model_dump()
        print("\nFull Metadata (JSON):")
        json_output = json.dumps(metadata_dict, indent=2, ensure_ascii=True)
        print(json_output)
        
        # Also save to file for easier inspection
        output_file = "test_metadata_output.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(metadata_dict, f, indent=2, ensure_ascii=False)
        print(f"\n(Also saved to {output_file} for full Unicode viewing)")
        
        print("\n" + "=" * 70)
        print("Validation: Metadata object is valid and matches schema!")
        print("=" * 70)
        
    except Exception as e:
        print("\n" + "=" * 70)
        print("ERROR: Failed to extract metadata")
        print("=" * 70)
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
    
    conn.close()

if __name__ == '__main__':
    main()

