"""
Wipe imported raw export files after successful ingest.

Provides safe deletion of imported files, keeping only the database.
"""
import sqlite3
import os
from typing import List, Dict, Optional
from pathlib import Path


DB_PATH = 'conversations.db'


def list_imported_files(db_path: str, import_batch_id: Optional[str] = None) -> List[Dict]:
    """
    List all imported files from import reports.
    
    Args:
        db_path: Database path
        import_batch_id: Optional filter by batch ID
    
    Returns:
        List of dicts with file info
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    if import_batch_id:
        cursor = conn.execute('''
            SELECT import_batch_id, source_file, import_type, status, completed_at
            FROM import_reports
            WHERE import_batch_id = ?
        ''', (import_batch_id,))
    else:
        cursor = conn.execute('''
            SELECT import_batch_id, source_file, import_type, status, completed_at
            FROM import_reports
            WHERE status IN ('success', 'partial')
            ORDER BY completed_at DESC
        ''')
    
    files = []
    for row in cursor.fetchall():
        file_info = dict(row)
        file_info['exists'] = os.path.exists(file_info['source_file'])
        files.append(file_info)
    
    conn.close()
    return files


def wipe_imported_files(
    db_path: str,
    import_batch_id: Optional[str] = None,
    verify: bool = True,
    dry_run: bool = False
) -> Dict:
    """
    Delete imported files after successful import.
    
    Args:
        db_path: Database path
        import_batch_id: Optional filter by batch ID
        verify: If True, only delete if import was successful
        dry_run: If True, don't actually delete, just report
    
    Returns:
        Dict with deletion results
    """
    files = list_imported_files(db_path, import_batch_id)
    
    deleted = []
    skipped = []
    errors = []
    
    for file_info in files:
        file_path = file_info['source_file']
        
        # Verify if requested
        if verify and file_info['status'] not in ('success', 'partial'):
            skipped.append({
                'file': file_path,
                'reason': f"Import status: {file_info['status']}"
            })
            continue
        
        # Check if file exists
        if not file_info['exists']:
            skipped.append({
                'file': file_path,
                'reason': 'File does not exist'
            })
            continue
        
        if dry_run:
            deleted.append({
                'file': file_path,
                'batch_id': file_info['import_batch_id']
            })
        else:
            try:
                os.remove(file_path)
                deleted.append({
                    'file': file_path,
                    'batch_id': file_info['import_batch_id']
                })
            except Exception as e:
                errors.append({
                    'file': file_path,
                    'error': str(e)
                })
    
    return {
        'deleted': deleted,
        'skipped': skipped,
        'errors': errors,
        'total': len(files)
    }


def archive_imported_files(
    db_path: str,
    archive_dir: str,
    import_batch_id: Optional[str] = None,
    verify: bool = True
) -> Dict:
    """
    Move imported files to archive directory instead of deleting.
    
    Args:
        db_path: Database path
        archive_dir: Directory to move files to
        import_batch_id: Optional filter by batch ID
        verify: If True, only archive if import was successful
    
    Returns:
        Dict with archiving results
    """
    files = list_imported_files(db_path, import_batch_id)
    
    # Create archive directory
    archive_path = Path(archive_dir)
    archive_path.mkdir(parents=True, exist_ok=True)
    
    archived = []
    skipped = []
    errors = []
    
    for file_info in files:
        file_path = Path(file_info['source_file'])
        
        # Verify if requested
        if verify and file_info['status'] not in ('success', 'partial'):
            skipped.append({
                'file': str(file_path),
                'reason': f"Import status: {file_info['status']}"
            })
            continue
        
        # Check if file exists
        if not file_path.exists():
            skipped.append({
                'file': str(file_path),
                'reason': 'File does not exist'
            })
            continue
        
        try:
            # Create subdirectory by import type
            type_dir = archive_path / file_info['import_type']
            type_dir.mkdir(exist_ok=True)
            
            # Move file
            dest = type_dir / file_path.name
            file_path.rename(dest)
            
            archived.append({
                'file': str(file_path),
                'archived_to': str(dest),
                'batch_id': file_info['import_batch_id']
            })
        except Exception as e:
            errors.append({
                'file': str(file_path),
                'error': str(e)
            })
    
    return {
        'archived': archived,
        'skipped': skipped,
        'errors': errors,
        'total': len(files)
    }


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python wipe_imported_files.py <command> [args...]")
        print("\nCommands:")
        print("  list [batch_id]")
        print("  wipe [batch_id] [--dry-run] [--no-verify]")
        print("  archive <archive_dir> [batch_id] [--no-verify]")
        sys.exit(1)
    
    command = sys.argv[1]
    args = sys.argv[2:]
    
    try:
        if command == 'list':
            batch_id = args[0] if args else None
            files = list_imported_files(DB_PATH, batch_id)
            print(f"Imported Files ({len(files)}):")
            for f in files:
                status = "EXISTS" if f['exists'] else "MISSING"
                print(f"  [{status}] {f['source_file']} ({f['import_batch_id']}) - {f['status']}")
        
        elif command == 'wipe':
            batch_id = None
            dry_run = False
            verify = True
            
            for arg in args:
                if arg == '--dry-run':
                    dry_run = True
                elif arg == '--no-verify':
                    verify = False
                elif not batch_id:
                    batch_id = arg
            
            result = wipe_imported_files(DB_PATH, batch_id, verify=verify, dry_run=dry_run)
            
            if dry_run:
                print(f"DRY RUN - Would delete {len(result['deleted'])} files:")
            else:
                print(f"Deleted {len(result['deleted'])} files:")
            
            for d in result['deleted']:
                print(f"  - {d['file']}")
            
            if result['skipped']:
                print(f"\nSkipped {len(result['skipped'])} files:")
                for s in result['skipped']:
                    print(f"  - {s['file']}: {s['reason']}")
            
            if result['errors']:
                print(f"\nErrors ({len(result['errors'])}):")
                for e in result['errors']:
                    print(f"  - {e['file']}: {e['error']}")
        
        elif command == 'archive':
            if not args:
                print("Error: archive_dir required")
                sys.exit(1)
            
            archive_dir = args[0]
            batch_id = args[1] if len(args) > 1 else None
            verify = '--no-verify' not in args
            
            result = archive_imported_files(DB_PATH, archive_dir, batch_id, verify=verify)
            
            print(f"Archived {len(result['archived'])} files to {archive_dir}:")
            for a in result['archived']:
                print(f"  - {a['file']} -> {a['archived_to']}")
            
            if result['skipped']:
                print(f"\nSkipped {len(result['skipped'])} files:")
                for s in result['skipped']:
                    print(f"  - {s['file']}: {s['reason']}")
        
        else:
            print(f"Unknown command: {command}")
    
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

