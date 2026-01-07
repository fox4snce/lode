"""
Quick script to run metadata extraction for a few conversations as a test.
"""
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

