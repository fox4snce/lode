"""
Database connection and initialization helpers.
"""
import sqlite3
from pathlib import Path
import sys
import os


def get_db_path() -> Path:
    """Get the database path, using user data directory when packaged."""
    if getattr(sys, 'frozen', False):
        # Running as executable
        if os.name == 'nt':  # Windows
            data_dir = Path(os.getenv('APPDATA', Path.home())) / 'ChatVault'
        else:
            data_dir = Path.home() / '.local' / 'share' / 'ChatVault'
    else:
        # Running as script
        data_dir = Path(__file__).parent.parent
    
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / 'conversations.db'


def get_db_connection():
    """Get a database connection."""
    db_path = get_db_path()
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def check_database_initialized() -> bool:
    """Check if database is initialized by looking for conversations table."""
    try:
        conn = get_db_connection()
        cursor = conn.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='conversations'
        """)
        exists = cursor.fetchone() is not None
        conn.close()
        return exists
    except:
        return False


def initialize_database():
    """Initialize all database tables."""
    import create_database
    import create_metadata_tables
    import create_organization_tables
    import create_metadata_calc_tables
    import create_fts5_tables
    import create_user_state_table
    import create_deduplication_tables
    import create_import_report_tables
    import create_entity_keyword_tables
    
    db_path = get_db_path()
    
    # Run all table creation scripts
    create_database.create_database(str(db_path))
    create_metadata_tables.create_metadata_tables(str(db_path))
    create_organization_tables.create_organization_tables(str(db_path))
    create_metadata_calc_tables.create_metadata_calc_tables(str(db_path))
    create_fts5_tables.create_fts5_tables(str(db_path))
    create_user_state_table.create_user_state_table(str(db_path))
    create_deduplication_tables.create_deduplication_tables(str(db_path))
    create_import_report_tables.create_import_report_tables(str(db_path))
    create_entity_keyword_tables.create_entity_keyword_tables(str(db_path))
    
    return True

