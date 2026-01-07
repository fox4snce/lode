"""
Create tables for tracking import reports.
"""
import sqlite3


def create_import_report_tables(db_path='conversations.db'):
    """Create tables for import reporting."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Main import reports table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS import_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            import_batch_id TEXT UNIQUE NOT NULL,
            source_file TEXT NOT NULL,
            import_type TEXT NOT NULL,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            status TEXT,
            total_conversations INTEGER DEFAULT 0,
            successful_conversations INTEGER DEFAULT 0,
            failed_conversations INTEGER DEFAULT 0,
            errors_json TEXT,
            missing_fields_json TEXT
        )
    ''')
    
    # Individual conversation import results
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS import_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            import_batch_id TEXT NOT NULL,
            conversation_id TEXT,
            status TEXT NOT NULL,
            error_message TEXT,
            missing_fields_json TEXT,
            imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (import_batch_id) REFERENCES import_reports(import_batch_id)
        )
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_import_batch_id 
        ON import_reports(import_batch_id)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_import_results_batch 
        ON import_results(import_batch_id)
    ''')
    
    conn.commit()
    conn.close()
    print(f"Import report tables created in {db_path}")


if __name__ == '__main__':
    create_import_report_tables()

