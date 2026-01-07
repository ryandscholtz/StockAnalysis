"""
Migration script to add business_type and analysis_weights columns to stock_analyses table
Run this script to update existing SQLite database with new schema
"""
import sqlite3
import sys
from pathlib import Path
import os

def migrate_database(db_path: str = "stock_analysis.db"):
    """Add new columns to stock_analyses table"""

    # Get absolute path
    if not os.path.isabs(db_path):
        # Assume backend directory
        backend_dir = Path(__file__).parent.parent
        db_path = str(backend_dir / db_path)

    if not os.path.exists(db_path):
        print(f"Database file not found: {db_path}")
        print("Creating new database with schema...")
        # Database will be created by SQLAlchemy on first use
        return

    print(f"Migrating database: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(stock_analyses)")
        columns = [row[1] for row in cursor.fetchall()]

        changes_made = False

        # Add business_type column if it doesn't exist
        if 'business_type' not in columns:
            print("Adding business_type column...")
            cursor.execute("""
                ALTER TABLE stock_analyses
                ADD COLUMN business_type VARCHAR(50)
            """)
            # Create index
            try:
                cursor.execute("""
                    CREATE INDEX idx_business_type ON stock_analyses(business_type)
                """)
            except sqlite3.OperationalError as e:
                if "already exists" not in str(e).lower():
                    raise
            changes_made = True
            print("[OK] Added business_type column")
        else:
            print("[OK] business_type column already exists")

        # Add analysis_weights column if it doesn't exist
        if 'analysis_weights' not in columns:
            print("Adding analysis_weights column...")
            cursor.execute("""
                ALTER TABLE stock_analyses
                ADD COLUMN analysis_weights JSON
            """)
            changes_made = True
            print("[OK] Added analysis_weights column")
        else:
            print("[OK] analysis_weights column already exists")

        conn.commit()

        if changes_made:
            print("\n[SUCCESS] Migration completed successfully!")
        else:
            print("\n[INFO] Database already up to date")

    except sqlite3.Error as e:
        conn.rollback()
        print(f"\n✗ Migration failed: {e}")
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    # Allow db path as command line argument
    db_path = sys.argv[1] if len(sys.argv) > 1 else "stock_analysis.db"
    migrate_database(db_path)
