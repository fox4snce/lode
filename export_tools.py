"""
Export tools for conversations and search results.

Features:
- Export conversation to Markdown
- Export search results to Markdown/CSV/JSON
- Export bundle: selected convos + tags + notes into a zip
"""
import sqlite3
import json
import csv
import os
import zipfile
from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path


DB_PATH = 'conversations.db'


def export_conversation_to_markdown(
    db_path: str,
    conversation_id: str,
    output_path: Optional[str] = None,
    include_timestamps: bool = True,
    include_metadata: bool = True
) -> str:
    """
    Export a conversation to Markdown format.
    
    Args:
        db_path: Database path
        conversation_id: Conversation ID to export
        output_path: Optional file path to write to
        include_timestamps: Include message timestamps
        include_metadata: Include conversation metadata
    
    Returns:
        Markdown content as string
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    # Get conversation
    cursor = conn.execute('''
        SELECT conversation_id, title, create_time, update_time, ai_source
        FROM conversations
        WHERE conversation_id = ?
    ''', (conversation_id,))
    
    conv = cursor.fetchone()
    if not conv:
        conn.close()
        raise ValueError(f"Conversation {conversation_id} not found")
    
    # Get custom title if exists
    cursor = conn.execute('SELECT custom_title FROM custom_titles WHERE conversation_id = ?', (conversation_id,))
    custom_title_row = cursor.fetchone()
    display_title = custom_title_row[0] if custom_title_row else conv['title'] or '(no title)'
    
    # Get messages
    cursor = conn.execute('''
        SELECT role, content, create_time
        FROM messages
        WHERE conversation_id = ?
        ORDER BY create_time ASC, id ASC
    ''', (conversation_id,))
    
    messages = cursor.fetchall()
    
    # Get tags
    cursor = conn.execute('''
        SELECT t.name
        FROM tags t
        JOIN conversation_tags ct ON ct.tag_id = t.tag_id
        WHERE ct.conversation_id = ?
        ORDER BY t.name
    ''', (conversation_id,))
    tags = [row[0] for row in cursor.fetchall()]
    
    # Get notes
    cursor = conn.execute('''
        SELECT note_text, created_at
        FROM notes
        WHERE conversation_id = ? AND message_id IS NULL
        ORDER BY created_at
    ''', (conversation_id,))
    notes = cursor.fetchall()
    
    conn.close()
    
    # Build Markdown
    lines = []
    lines.append(f"# {display_title}")
    lines.append("")
    
    if include_metadata:
        lines.append("## Metadata")
        lines.append("")
        lines.append(f"- **Conversation ID**: `{conversation_id}`")
        lines.append(f"- **Source**: {conv['ai_source'] or 'unknown'}")
        if conv['create_time']:
            dt = datetime.fromtimestamp(conv['create_time'])
            lines.append(f"- **Created**: {dt.strftime('%Y-%m-%d %H:%M:%S')}")
        if conv['update_time']:
            dt = datetime.fromtimestamp(conv['update_time'])
            lines.append(f"- **Updated**: {dt.strftime('%Y-%m-%d %H:%M:%S')}")
        if tags:
            lines.append(f"- **Tags**: {', '.join(tags)}")
        lines.append("")
    
    if notes:
        lines.append("## Notes")
        lines.append("")
        for note in notes:
            lines.append(f"- {note['note_text']}")
        lines.append("")
    
    lines.append("## Messages")
    lines.append("")
    
    for msg in messages:
        role = msg['role'].upper()
        content = msg['content'] or ''
        
        if include_timestamps and msg['create_time']:
            try:
                dt = datetime.fromtimestamp(msg['create_time'])
                timestamp = dt.strftime('%Y-%m-%d %H:%M:%S')
                lines.append(f"### {role} - {timestamp}")
            except (ValueError, OSError):
                lines.append(f"### {role}")
        else:
            lines.append(f"### {role}")
        
        lines.append("")
        lines.append(content)
        lines.append("")
    
    markdown = "\n".join(lines)
    
    # Write to file if path provided
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(markdown)
    
    return markdown


def export_search_results(
    results: List[Dict],
    output_path: str,
    format: str = 'markdown'
):
    """
    Export search results to file.
    
    Args:
        results: List of search result dicts
        output_path: Output file path
        format: 'markdown', 'csv', or 'json'
    """
    if format == 'markdown':
        lines = []
        lines.append(f"# Search Results ({len(results)} found)")
        lines.append("")
        
        for i, result in enumerate(results, 1):
            lines.append(f"## Result {i}")
            lines.append("")
            lines.append(f"- **Conversation**: {result.get('conversation_title', 'N/A')}")
            lines.append(f"- **Role**: {result.get('role', 'N/A')}")
            if result.get('similarity'):
                lines.append(f"- **Similarity**: {result['similarity']:.4f}")
            lines.append("")
            lines.append("**Content:**")
            lines.append("")
            lines.append(result.get('content', '')[:500])
            lines.append("")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(lines))
    
    elif format == 'csv':
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['conversation_id', 'conversation_title', 'role', 'content', 'similarity'])
            writer.writeheader()
            for result in results:
                writer.writerow({
                    'conversation_id': result.get('conversation_id', ''),
                    'conversation_title': result.get('conversation_title', ''),
                    'role': result.get('role', ''),
                    'content': result.get('content', '')[:1000],  # Truncate for CSV
                    'similarity': result.get('similarity', '')
                })
    
    elif format == 'json':
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
    
    else:
        raise ValueError(f"Unknown format: {format}")


def export_bundle(
    db_path: str,
    conversation_ids: List[str],
    output_path: str,
    include_tags: bool = True,
    include_notes: bool = True,
    include_metadata: bool = True
):
    """
    Export a bundle of conversations with tags and notes to a zip file.
    
    Args:
        db_path: Database path
        conversation_ids: List of conversation IDs to export
        output_path: Output zip file path
        include_tags: Include tags in export
        include_notes: Include notes in export
        include_metadata: Include metadata in export
    """
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Export each conversation
        for conv_id in conversation_ids:
            try:
                markdown = export_conversation_to_markdown(
                    db_path, conv_id,
                    include_timestamps=True,
                    include_metadata=include_metadata
                )
                
                # Get safe filename
                conn = sqlite3.connect(db_path)
                cursor = conn.execute('SELECT title FROM conversations WHERE conversation_id = ?', (conv_id,))
                row = cursor.fetchone()
                title = row[0] if row else conv_id
                safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
                filename = f"{safe_title}_{conv_id[:8]}.md"
                conn.close()
                
                zipf.writestr(f"conversations/{filename}", markdown)
            except Exception as e:
                print(f"Warning: Failed to export {conv_id}: {e}")
        
        # Export tags if requested
        if include_tags:
            conn = sqlite3.connect(db_path)
            cursor = conn.execute('''
                SELECT t.name, GROUP_CONCAT(c.conversation_id) as conversation_ids
                FROM tags t
                JOIN conversation_tags ct ON ct.tag_id = t.tag_id
                JOIN conversations c ON c.conversation_id = ct.conversation_id
                WHERE c.conversation_id IN ({})
                GROUP BY t.tag_id, t.name
            '''.format(','.join(['?'] * len(conversation_ids))), conversation_ids)
            
            tags_data = []
            for row in cursor.fetchall():
                tags_data.append({
                    'tag': row[0],
                    'conversations': row[1].split(',')
                })
            
            if tags_data:
                zipf.writestr('tags.json', json.dumps(tags_data, indent=2))
            conn.close()
        
        # Export notes if requested
        if include_notes:
            conn = sqlite3.connect(db_path)
            cursor = conn.execute('''
                SELECT conversation_id, message_id, note_text, created_at
                FROM notes
                WHERE conversation_id IN ({})
                ORDER BY conversation_id, created_at
            '''.format(','.join(['?'] * len(conversation_ids))), conversation_ids)
            
            notes_data = [dict(row) for row in cursor.fetchall()]
            
            if notes_data:
                zipf.writestr('notes.json', json.dumps(notes_data, indent=2))
            conn.close()
        
        # Create manifest
        manifest = {
            'exported_at': datetime.now().isoformat(),
            'conversations': conversation_ids,
            'count': len(conversation_ids)
        }
        zipf.writestr('manifest.json', json.dumps(manifest, indent=2))


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python export_tools.py <command> [args...]")
        print("\nCommands:")
        print("  markdown <conversation_id> [output.md]")
        print("  bundle <conversation_id1> [conversation_id2] ... [output.zip]")
        sys.exit(1)
    
    command = sys.argv[1]
    args = sys.argv[2:]
    
    try:
        if command == 'markdown':
            conv_id = args[0]
            output = args[1] if len(args) > 1 else f"{conv_id[:8]}.md"
            
            markdown = export_conversation_to_markdown(DB_PATH, conv_id)
            with open(output, 'w', encoding='utf-8') as f:
                f.write(markdown)
            print(f"Exported conversation {conv_id} to {output}")
        
        elif command == 'bundle':
            if len(args) < 2:
                print("Error: Need at least one conversation ID and output path")
                sys.exit(1)
            
            conv_ids = args[:-1]
            output = args[-1]
            
            export_bundle(DB_PATH, conv_ids, output)
            print(f"Exported bundle with {len(conv_ids)} conversations to {output}")
        
        else:
            print(f"Unknown command: {command}")
    
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

