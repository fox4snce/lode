"""
Quick script to run metadata extraction for a few conversations as a test.
"""
import sys
from pathlib import Path

# Add database directory to path for imports
project_root = Path(__file__).parent
database_dir = project_root / "database"
if str(database_dir) not in sys.path:
    sys.path.insert(0, str(database_dir))

from extract_conversation_metadata import process_conversations
from create_metadata_tables import create_metadata_tables

# Create tables if they don't exist
create_metadata_tables()

# Process just a few conversations to test (or remove conversation_id to process all)
print("Starting metadata extraction...")
print("This will process conversations in batches.")
print("To process a specific conversation, pass its ID as an argument.")
print("")

# Process just 5 conversations as a test
process_conversations(batch_size=5, conversation_id=None)

