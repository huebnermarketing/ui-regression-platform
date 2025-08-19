"""
Migration: Add is_page_restricted field to projects table
This field controls whether crawling should be restricted to the specific page and its subpages
"""

import sqlite3
import os

def add_page_restricted_field():
    """Add is_page_restricted field to projects table"""
    db_path = os.path.join('instance', 'ui_diff_dashboard.db')
    
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if column already exists
        cursor.execute("PRAGMA table_info(projects)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'is_page_restricted' in columns:
            print("Column 'is_page_restricted' already exists in projects table")
            conn.close()
            return True
        
        # Add the is_page_restricted column with default value False
        cursor.execute("""
            ALTER TABLE projects 
            ADD COLUMN is_page_restricted BOOLEAN DEFAULT 0 NOT NULL
        """)
        
        # Update existing records to have default value
        cursor.execute("""
            UPDATE projects 
            SET is_page_restricted = 0 
            WHERE is_page_restricted IS NULL
        """)
        
        conn.commit()
        print("Successfully added 'is_page_restricted' column to projects table")
        
        # Verify the column was added
        cursor.execute("PRAGMA table_info(projects)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'is_page_restricted' in columns:
            print("✓ Column 'is_page_restricted' verified in projects table")
            conn.close()
            return True
        else:
            print("✗ Failed to verify 'is_page_restricted' column")
            conn.close()
            return False
            
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        if conn:
            conn.close()
        return False
    except Exception as e:
        print(f"Error: {e}")
        if conn:
            conn.close()
        return False

def rollback_page_restricted_field():
    """Remove is_page_restricted field from projects table"""
    db_path = os.path.join('instance', 'ui_diff_dashboard.db')
    
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if column exists
        cursor.execute("PRAGMA table_info(projects)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'is_page_restricted' not in columns:
            print("Column 'is_page_restricted' does not exist in projects table")
            conn.close()
            return True
        
        # SQLite doesn't support DROP COLUMN directly, so we need to recreate the table
        # First, get the current table structure
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='projects'")
        create_sql = cursor.fetchone()[0]
        
        # Create a backup table
        cursor.execute("""
            CREATE TABLE projects_backup AS 
            SELECT id, name, staging_url, production_url, user_id, created_at 
            FROM projects
        """)
        
        # Drop the original table
        cursor.execute("DROP TABLE projects")
        
        # Recreate the table without the is_page_restricted column
        cursor.execute("""
            CREATE TABLE projects (
                id INTEGER PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                staging_url TEXT NOT NULL,
                production_url TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                created_at DATETIME,
                FOREIGN KEY (user_id) REFERENCES users (id),
                UNIQUE (name, user_id)
            )
        """)
        
        # Restore data from backup
        cursor.execute("""
            INSERT INTO projects (id, name, staging_url, production_url, user_id, created_at)
            SELECT id, name, staging_url, production_url, user_id, created_at
            FROM projects_backup
        """)
        
        # Drop backup table
        cursor.execute("DROP TABLE projects_backup")
        
        conn.commit()
        print("Successfully removed 'is_page_restricted' column from projects table")
        
        conn.close()
        return True
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        if conn:
            conn.close()
        return False
    except Exception as e:
        print(f"Error: {e}")
        if conn:
            conn.close()
        return False

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'rollback':
        success = rollback_page_restricted_field()
    else:
        success = add_page_restricted_field()
    
    if success:
        print("Migration completed successfully!")
    else:
        print("Migration failed!")
        sys.exit(1)