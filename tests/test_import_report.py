"""
Tests for import report functionality.
"""
import sqlite3
import os
import tempfile
import json
from import_report import (
    start_import_report,
    log_import_success,
    log_import_failure,
    complete_import_report,
    get_import_report
)


def test_import_report_lifecycle():
    """Test complete import report lifecycle."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        import sys
        from pathlib import Path
        project_root = Path(__file__).parent.parent
        database_dir = project_root / "database"
        if str(database_dir) not in sys.path:
            sys.path.insert(0, str(database_dir))
        from create_import_report_tables import create_import_report_tables
        create_import_report_tables(db_path)
        
        batch_id = "test-batch-001"
        source_file = "data/test.json"
        
        # Start report
        start_import_report(db_path, batch_id, source_file, "openai")
        
        # Log successes
        log_import_success(db_path, batch_id, "conv-001", {"title": False})
        log_import_success(db_path, batch_id, "conv-002")
        
        # Log failure
        log_import_failure(db_path, batch_id, "conv-003", "Invalid JSON")
        
        # Complete report
        complete_import_report(db_path, batch_id, "partial")
        
        # Get report
        report = get_import_report(db_path, batch_id)
        
        assert report is not None
        assert report['import_batch_id'] == batch_id
        assert report['successful_conversations'] == 2
        assert report['failed_conversations'] == 1
        assert report['total_conversations'] == 3
        assert report['status'] == 'partial'
        
        print("[PASS] test_import_report_lifecycle")
    
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


if __name__ == '__main__':
    test_import_report_lifecycle()
    print("\nAll import report tests passed!")

