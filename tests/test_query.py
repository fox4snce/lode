import sqlite3

DB_PATH = 'conversations.db'

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

# Test the exact query from the script
cursor = conn.execute('''
    SELECT c.conversation_id, c.title
    FROM conversations c
    LEFT JOIN conversation_metadata m ON c.conversation_id = m.conversation_id
    WHERE m.conversation_id IS NULL
    ORDER BY c.create_time DESC
    LIMIT 1000
''')

conversations = cursor.fetchall()
total = len(conversations)

print(f"Query returned {total} conversations")

if total > 0:
    print(f"First conversation: {conversations[0]['conversation_id']} - {conversations[0]['title']}")
else:
    print("No conversations found!")
    # Check if table exists
    cursor2 = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='conversation_metadata'")
    if cursor2.fetchone():
        print("conversation_metadata table exists")
    else:
        print("conversation_metadata table does NOT exist")
    
    # Check total conversations
    cursor3 = conn.execute("SELECT COUNT(*) FROM conversations")
    total_conv = cursor3.fetchone()[0]
    print(f"Total conversations in DB: {total_conv}")
    
    # Check how many have metadata
    cursor4 = conn.execute("SELECT COUNT(*) FROM conversation_metadata")
    total_meta = cursor4.fetchone()[0]
    print(f"Total conversations with metadata: {total_meta}")

conn.close()


