"""
Import report tracking for transparency and debugging.
"""
import sqlite3
import json
from typing import Dict, Optional, List
from datetime import datetime


DB_PATH = 'conversations.db'


def start_import_report(
    db_path: str,
    import_batch_id: str,
    source_file: str,
    import_type: str
) -> bool:
    """
    Start a new import report.
    
    Args:
        db_path: Database path
        import_batch_id: Unique identifier for this import run
        source_file: Path to the source file being imported
        import_type: Type of import ('openai', 'claude', etc.)
    
    Returns:
        True if successful
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO import_reports 
            (import_batch_id, source_file, import_type, started_at, status)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP, 'in_progress')
        ''', (import_batch_id, source_file, import_type))
        
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # Batch ID already exists
        return False
    finally:
        conn.close()


def log_import_success(
    db_path: str,
    import_batch_id: str,
    conversation_id: str,
    missing_fields: Optional[Dict] = None
) -> bool:
    """
    Log a successful conversation import.
    
    Args:
        db_path: Database path
        import_batch_id: Import batch ID
        conversation_id: Conversation ID that was imported
        missing_fields: Dict of missing fields (e.g., {'title': False, 'timestamp': True})
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    missing_fields_json = json.dumps(missing_fields) if missing_fields else None
    
    cursor.execute('''
        INSERT INTO import_results 
        (import_batch_id, conversation_id, status, missing_fields_json)
        VALUES (?, ?, 'success', ?)
    ''', (import_batch_id, conversation_id, missing_fields_json))
    
    # Update report counts
    cursor.execute('''
        UPDATE import_reports
        SET successful_conversations = successful_conversations + 1,
            total_conversations = total_conversations + 1
        WHERE import_batch_id = ?
    ''', (import_batch_id,))
    
    conn.commit()
    conn.close()
    return True


def log_import_failure(
    db_path: str,
    import_batch_id: str,
    conversation_id: Optional[str],
    error_message: str
) -> bool:
    """
    Log a failed conversation import.
    
    Args:
        db_path: Database path
        import_batch_id: Import batch ID
        conversation_id: Conversation ID (if available)
        error_message: Error message describing the failure
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO import_results 
        (import_batch_id, conversation_id, status, error_message)
        VALUES (?, ?, 'failed', ?)
    ''', (import_batch_id, conversation_id, error_message))
    
    # Update report counts
    cursor.execute('''
        UPDATE import_reports
        SET failed_conversations = failed_conversations + 1,
            total_conversations = total_conversations + 1
        WHERE import_batch_id = ?
    ''', (import_batch_id,))
    
    conn.commit()
    conn.close()
    return True


def complete_import_report(
    db_path: str,
    import_batch_id: str,
    status: str = 'success'
) -> bool:
    """
    Complete an import report.
    
    Args:
        db_path: Database path
        import_batch_id: Import batch ID
        status: Final status ('success', 'partial', 'failed')
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Collect errors
    cursor.execute('''
        SELECT error_message
        FROM import_results
        WHERE import_batch_id = ? AND status = 'failed'
    ''', (import_batch_id,))
    
    errors = [row[0] for row in cursor.fetchall() if row[0]]
    errors_json = json.dumps(errors) if errors else None
    
    # Collect missing fields summary
    cursor.execute('''
        SELECT missing_fields_json
        FROM import_results
        WHERE import_batch_id = ? AND missing_fields_json IS NOT NULL
    ''', (import_batch_id,))
    
    all_missing = {}
    for row in cursor.fetchall():
        if row[0]:
            missing = json.loads(row[0])
            for field, is_missing in missing.items():
                if is_missing:
                    all_missing[field] = all_missing.get(field, 0) + 1
    
    missing_fields_json = json.dumps(all_missing) if all_missing else None
    
    # Update report
    cursor.execute('''
        UPDATE import_reports
        SET completed_at = CURRENT_TIMESTAMP,
            status = ?,
            errors_json = ?,
            missing_fields_json = ?
        WHERE import_batch_id = ?
    ''', (status, errors_json, missing_fields_json, import_batch_id))
    
    conn.commit()
    conn.close()
    return True


def get_import_report(db_path: str, import_batch_id: str) -> Optional[Dict]:
    """Get a complete import report."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute('''
        SELECT * FROM import_reports WHERE import_batch_id = ?
    ''', (import_batch_id,))
    
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None
    
    report = dict(row)
    
    # Get detailed results
    cursor = conn.execute('''
        SELECT conversation_id, status, error_message, missing_fields_json
        FROM import_results
        WHERE import_batch_id = ?
        ORDER BY imported_at
    ''', (import_batch_id,))
    
    report['results'] = []
    for result_row in cursor.fetchall():
        result = dict(result_row)
        if result['missing_fields_json']:
            result['missing_fields'] = json.loads(result['missing_fields_json'])
        else:
            result['missing_fields'] = None
        del result['missing_fields_json']
        report['results'].append(result)
    
    # Parse JSON fields
    if report['errors_json']:
        report['errors'] = json.loads(report['errors_json'])
    else:
        report['errors'] = []
    
    if report['missing_fields_json']:
        report['missing_fields_summary'] = json.loads(report['missing_fields_json'])
    else:
        report['missing_fields_summary'] = {}
    
    conn.close()
    return report


def list_import_reports(db_path: str, limit: int = 10) -> List[Dict]:
    """List all import reports, most recent first."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute('''
        SELECT 
            import_batch_id,
            source_file,
            import_type,
            started_at,
            completed_at,
            status,
            total_conversations,
            successful_conversations,
            failed_conversations
        FROM import_reports
        ORDER BY started_at DESC
        LIMIT ?
    ''', (limit,))
    
    reports = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return reports


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python import_report.py <command> [args...]")
        print("\nCommands:")
        print("  start <batch_id> <source_file> <import_type>")
        print("  success <batch_id> <conversation_id> [missing_fields_json]")
        print("  failure <batch_id> <conversation_id> <error_message>")
        print("  complete <batch_id> [status]")
        print("  get <batch_id>")
        print("  list [limit]")
        sys.exit(1)
    
    command = sys.argv[1]
    args = sys.argv[2:]
    
    try:
        if command == 'start':
            batch_id, source_file, import_type = args[0], args[1], args[2]
            if start_import_report(DB_PATH, batch_id, source_file, import_type):
                print(f"Started import report: {batch_id}")
        
        elif command == 'success':
            batch_id, conv_id = args[0], args[1]
            missing = json.loads(args[2]) if len(args) > 2 else None
            log_import_success(DB_PATH, batch_id, conv_id, missing)
            print(f"Logged success: {conv_id}")
        
        elif command == 'failure':
            batch_id, conv_id, error = args[0], args[1], args[2]
            log_import_failure(DB_PATH, batch_id, conv_id, error)
            print(f"Logged failure: {conv_id}")
        
        elif command == 'complete':
            batch_id = args[0]
            status = args[1] if len(args) > 1 else 'success'
            complete_import_report(DB_PATH, batch_id, status)
            print(f"Completed import report: {batch_id}")
        
        elif command == 'get':
            batch_id = args[0]
            report = get_import_report(DB_PATH, batch_id)
            if report:
                print(f"Import Report: {batch_id}")
                print(f"  Status: {report['status']}")
                print(f"  Total: {report['total_conversations']}")
                print(f"  Success: {report['successful_conversations']}")
                print(f"  Failed: {report['failed_conversations']}")
            else:
                print(f"Report not found: {batch_id}")
        
        elif command == 'list':
            limit = int(args[0]) if args else 10
            reports = list_import_reports(DB_PATH, limit)
            print(f"Import Reports (showing {len(reports)}):")
            for r in reports:
                print(f"  {r['import_batch_id']}: {r['status']} - {r['successful_conversations']}/{r['total_conversations']}")
        
        else:
            print(f"Unknown command: {command}")
    
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

