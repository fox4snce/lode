"""
Organization features API.

Provides functions for:
- Tags (create, list, add/remove from conversations)
- Folders (create, list, assign conversations)
- Bookmarks (pin specific messages)
- Notes (attach notes to conversations/messages)
- Custom titles (override imported titles)
- Star/favorite conversations
- Conversation relationships (merge/split/link)
"""
import sqlite3
from typing import List, Dict, Optional
from datetime import datetime


DB_PATH = 'conversations.db'


# ============================================================================
# TAGS
# ============================================================================

def create_tag(db_path: str, name: str, color: Optional[str] = None) -> int:
    """Create a new tag. Returns tag_id."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO tags (name, color)
            VALUES (?, ?)
        ''', (name, color))
        tag_id = cursor.lastrowid
        conn.commit()
        return tag_id
    except sqlite3.IntegrityError:
        # Tag already exists, return existing ID
        cursor.execute('SELECT tag_id FROM tags WHERE name = ?', (name,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None
    finally:
        conn.close()


def list_tags(db_path: str) -> List[Dict]:
    """List all tags."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute('SELECT tag_id, name, color FROM tags ORDER BY name')
    
    tags = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return tags


def add_tag_to_conversation(db_path: str, conversation_id: str, tag_name: str) -> bool:
    """Add a tag to a conversation. Creates tag if it doesn't exist."""
    conn = sqlite3.connect(db_path)
    
    # Get or create tag
    tag_id = create_tag(db_path, tag_name)
    if not tag_id:
        conn.close()
        return False
    
    try:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO conversation_tags (conversation_id, tag_id)
            VALUES (?, ?)
        ''', (conversation_id, tag_id))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # Already tagged
        return False
    finally:
        conn.close()


def remove_tag_from_conversation(db_path: str, conversation_id: str, tag_name: str) -> bool:
    """Remove a tag from a conversation."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        DELETE FROM conversation_tags
        WHERE conversation_id = ? 
        AND tag_id = (SELECT tag_id FROM tags WHERE name = ?)
    ''', (conversation_id, tag_name))
    
    removed = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return removed


def get_conversation_tags(db_path: str, conversation_id: str) -> List[str]:
    """Get all tags for a conversation."""
    conn = sqlite3.connect(db_path)
    cursor = conn.execute('''
        SELECT t.name
        FROM tags t
        JOIN conversation_tags ct ON ct.tag_id = t.tag_id
        WHERE ct.conversation_id = ?
        ORDER BY t.name
    ''', (conversation_id,))
    
    tags = [row[0] for row in cursor.fetchall()]
    conn.close()
    return tags


# ============================================================================
# FOLDERS
# ============================================================================

def create_folder(db_path: str, name: str, parent_folder_id: Optional[int] = None, color: Optional[str] = None) -> int:
    """Create a new folder. Returns folder_id."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO folders (name, parent_folder_id, color)
        VALUES (?, ?, ?)
    ''', (name, parent_folder_id, color))
    
    folder_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return folder_id


def list_folders(db_path: str) -> List[Dict]:
    """List all folders."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute('''
        SELECT folder_id, name, parent_folder_id, color
        FROM folders
        ORDER BY name
    ''')
    
    folders = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return folders


def assign_conversation_to_folder(db_path: str, conversation_id: str, folder_name: str) -> bool:
    """Assign a conversation to a folder. Creates folder if it doesn't exist."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get or create folder
    cursor.execute('SELECT folder_id FROM folders WHERE name = ?', (folder_name,))
    row = cursor.fetchone()
    
    if row:
        folder_id = row[0]
    else:
        cursor.execute('INSERT INTO folders (name) VALUES (?)', (folder_name,))
        folder_id = cursor.lastrowid
    
    # Assign conversation
    try:
        cursor.execute('''
            INSERT INTO conversation_folders (conversation_id, folder_id)
            VALUES (?, ?)
        ''', (conversation_id, folder_id))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # Already assigned
        conn.close()
        return False
    finally:
        conn.close()


def remove_conversation_from_folder(db_path: str, conversation_id: str) -> bool:
    """Remove a conversation from its folder."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        DELETE FROM conversation_folders
        WHERE conversation_id = ?
    ''', (conversation_id,))
    
    removed = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return removed


# ============================================================================
# BOOKMARKS
# ============================================================================

def create_bookmark(db_path: str, conversation_id: str, message_id: Optional[str] = None, note: Optional[str] = None) -> int:
    """Create a bookmark. Returns bookmark_id."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO bookmarks (conversation_id, message_id, note)
        VALUES (?, ?, ?)
    ''', (conversation_id, message_id, note))
    
    bookmark_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return bookmark_id


def list_bookmarks(db_path: str, conversation_id: Optional[str] = None) -> List[Dict]:
    """List bookmarks, optionally filtered by conversation."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    if conversation_id:
        cursor = conn.execute('''
            SELECT bookmark_id, conversation_id, message_id, note, created_at
            FROM bookmarks
            WHERE conversation_id = ?
            ORDER BY created_at DESC
        ''', (conversation_id,))
    else:
        cursor = conn.execute('''
            SELECT bookmark_id, conversation_id, message_id, note, created_at
            FROM bookmarks
            ORDER BY created_at DESC
        ''')
    
    bookmarks = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return bookmarks


def delete_bookmark(db_path: str, bookmark_id: int) -> bool:
    """Delete a bookmark."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM bookmarks WHERE bookmark_id = ?', (bookmark_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


# ============================================================================
# NOTES
# ============================================================================

def create_note(db_path: str, conversation_id: str, note_text: str, message_id: Optional[str] = None) -> int:
    """Create a note attached to a conversation or message. Returns note_id."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO notes (conversation_id, message_id, note_text)
        VALUES (?, ?, ?)
    ''', (conversation_id, message_id, note_text))
    
    note_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return note_id


def list_notes(db_path: str, conversation_id: Optional[str] = None, message_id: Optional[str] = None) -> List[Dict]:
    """List notes, optionally filtered by conversation or message."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    where_parts = []
    params = []
    
    if conversation_id:
        where_parts.append("conversation_id = ?")
        params.append(conversation_id)
    
    if message_id:
        where_parts.append("message_id = ?")
        params.append(message_id)
    
    where_clause = " AND ".join(where_parts) if where_parts else "1=1"
    
    cursor = conn.execute(f'''
        SELECT note_id, conversation_id, message_id, note_text, created_at, updated_at
        FROM notes
        WHERE {where_clause}
        ORDER BY created_at DESC
    ''', params)
    
    notes = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return notes


def update_note(db_path: str, note_id: int, note_text: str) -> bool:
    """Update a note."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE notes
        SET note_text = ?, updated_at = CURRENT_TIMESTAMP
        WHERE note_id = ?
    ''', (note_text, note_id))
    
    updated = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return updated


def delete_note(db_path: str, note_id: int) -> bool:
    """Delete a note."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM notes WHERE note_id = ?', (note_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


# ============================================================================
# CUSTOM TITLES
# ============================================================================

def set_custom_title(db_path: str, conversation_id: str, custom_title: str) -> bool:
    """Set a custom title for a conversation (overrides imported title)."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR REPLACE INTO custom_titles (conversation_id, custom_title, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
    ''', (conversation_id, custom_title))
    
    conn.commit()
    conn.close()
    return True


def get_custom_title(db_path: str, conversation_id: str) -> Optional[str]:
    """Get custom title for a conversation."""
    conn = sqlite3.connect(db_path)
    cursor = conn.execute('''
        SELECT custom_title FROM custom_titles WHERE conversation_id = ?
    ''', (conversation_id,))
    
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None


def clear_custom_title(db_path: str, conversation_id: str) -> bool:
    """Clear custom title (revert to imported title)."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM custom_titles WHERE conversation_id = ?', (conversation_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


def get_display_title(db_path: str, conversation_id: str) -> str:
    """Get display title (custom if set, otherwise imported)."""
    custom = get_custom_title(db_path, conversation_id)
    if custom:
        return custom
    
    conn = sqlite3.connect(db_path)
    cursor = conn.execute('SELECT title FROM conversations WHERE conversation_id = ?', (conversation_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else "(no title)"


# ============================================================================
# STAR/FAVORITE
# ============================================================================

def star_conversation(db_path: str, conversation_id: str) -> bool:
    """Star/favorite a conversation."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE conversations
        SET is_starred = 1
        WHERE conversation_id = ?
    ''', (conversation_id,))
    
    updated = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return updated


def unstar_conversation(db_path: str, conversation_id: str) -> bool:
    """Unstar a conversation."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE conversations
        SET is_starred = 0
        WHERE conversation_id = ?
    ''', (conversation_id,))
    
    updated = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return updated


# ============================================================================
# CONVERSATION RELATIONSHIPS
# ============================================================================

def link_conversations(
    db_path: str,
    conversation_id_1: str,
    conversation_id_2: str,
    relationship_type: str = 'related',
    notes: Optional[str] = None
) -> int:
    """
    Link two conversations.
    
    relationship_type: 'merged', 'split', 'related', 'duplicate'
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Ensure consistent ordering (smaller ID first)
    if conversation_id_1 > conversation_id_2:
        conversation_id_1, conversation_id_2 = conversation_id_2, conversation_id_1
    
    cursor.execute('''
        INSERT INTO conversation_relationships 
        (conversation_id_1, conversation_id_2, relationship_type, notes)
        VALUES (?, ?, ?, ?)
    ''', (conversation_id_1, conversation_id_2, relationship_type, notes))
    
    rel_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return rel_id


def get_conversation_relationships(db_path: str, conversation_id: str) -> List[Dict]:
    """Get all relationships for a conversation."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute('''
        SELECT id, conversation_id_1, conversation_id_2, relationship_type, notes, created_at
        FROM conversation_relationships
        WHERE conversation_id_1 = ? OR conversation_id_2 = ?
    ''', (conversation_id, conversation_id))
    
    relationships = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return relationships


def delete_relationship(db_path: str, relationship_id: int) -> bool:
    """Delete a conversation relationship."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM conversation_relationships WHERE id = ?', (relationship_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python organization_api.py <command> [args...]")
        print("\nCommands:")
        print("  tag-create <name> [color]")
        print("  tag-list")
        print("  tag-add <conversation_id> <tag_name>")
        print("  tag-remove <conversation_id> <tag_name>")
        print("  tag-get <conversation_id>")
        print("  folder-create <name> [parent_id] [color]")
        print("  folder-list")
        print("  folder-assign <conversation_id> <folder_name>")
        print("  folder-remove <conversation_id>")
        print("  bookmark-create <conversation_id> [message_id] [note]")
        print("  bookmark-list [conversation_id]")
        print("  bookmark-delete <bookmark_id>")
        print("  note-create <conversation_id> <note_text> [message_id]")
        print("  note-list [conversation_id] [message_id]")
        print("  note-update <note_id> <note_text>")
        print("  note-delete <note_id>")
        print("  title-set <conversation_id> <title>")
        print("  title-get <conversation_id>")
        print("  title-clear <conversation_id>")
        print("  star <conversation_id>")
        print("  unstar <conversation_id>")
        print("  link <conversation_id_1> <conversation_id_2> [type] [notes]")
        print("  relationships <conversation_id>")
        sys.exit(1)
    
    command = sys.argv[1]
    args = sys.argv[2:]
    
    try:
        if command == 'tag-create':
            name = args[0]
            color = args[1] if len(args) > 1 else None
            tag_id = create_tag(DB_PATH, name, color)
            print(f"Created tag: {name} (ID: {tag_id})")
        
        elif command == 'tag-list':
            tags = list_tags(DB_PATH)
            print(f"Tags ({len(tags)}):")
            for tag in tags:
                print(f"  {tag['name']} (ID: {tag['tag_id']})")
        
        elif command == 'tag-add':
            conv_id, tag_name = args[0], args[1]
            if add_tag_to_conversation(DB_PATH, conv_id, tag_name):
                print(f"Added tag '{tag_name}' to conversation {conv_id}")
            else:
                print(f"Tag '{tag_name}' already on conversation {conv_id}")
        
        elif command == 'tag-remove':
            conv_id, tag_name = args[0], args[1]
            if remove_tag_from_conversation(DB_PATH, conv_id, tag_name):
                print(f"Removed tag '{tag_name}' from conversation {conv_id}")
            else:
                print(f"Tag '{tag_name}' not found on conversation {conv_id}")
        
        elif command == 'tag-get':
            conv_id = args[0]
            tags = get_conversation_tags(DB_PATH, conv_id)
            print(f"Tags for {conv_id}: {', '.join(tags) if tags else '(none)'}")
        
        elif command == 'star':
            conv_id = args[0]
            if star_conversation(DB_PATH, conv_id):
                print(f"Starred conversation {conv_id}")
        
        elif command == 'unstar':
            conv_id = args[0]
            if unstar_conversation(DB_PATH, conv_id):
                print(f"Unstarred conversation {conv_id}")
        
        elif command == 'title-set':
            conv_id, title = args[0], args[1]
            if set_custom_title(DB_PATH, conv_id, title):
                print(f"Set custom title for {conv_id}: {title}")
        
        elif command == 'title-get':
            conv_id = args[0]
            title = get_display_title(DB_PATH, conv_id)
            print(f"Title for {conv_id}: {title}")
        
        else:
            print(f"Unknown command: {command}")
    
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

