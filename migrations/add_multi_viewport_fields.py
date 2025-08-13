"""
Migration to add multi-viewport screenshot support
Adds columns for desktop, tablet, and mobile screenshots and diffs
"""

import sqlite3
import sys
import os

# Add the parent directory to the path so we can import the models
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def run_migration():
    """Run the migration to add multi-viewport fields"""
    
    # Connect to the database
    db_path = os.path.join(os.path.dirname(__file__), '..', 'instance', 'ui_diff_dashboard.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("Adding multi-viewport screenshot and diff fields...")
        
        # Add desktop viewport fields
        cursor.execute('''
            ALTER TABLE project_pages 
            ADD COLUMN staging_screenshot_path_desktop TEXT
        ''')
        
        cursor.execute('''
            ALTER TABLE project_pages 
            ADD COLUMN staging_screenshot_path_tablet TEXT
        ''')
        
        cursor.execute('''
            ALTER TABLE project_pages 
            ADD COLUMN staging_screenshot_path_mobile TEXT
        ''')
        
        cursor.execute('''
            ALTER TABLE project_pages 
            ADD COLUMN production_screenshot_path_desktop TEXT
        ''')
        
        cursor.execute('''
            ALTER TABLE project_pages 
            ADD COLUMN production_screenshot_path_tablet TEXT
        ''')
        
        cursor.execute('''
            ALTER TABLE project_pages 
            ADD COLUMN production_screenshot_path_mobile TEXT
        ''')
        
        # Add diff fields for each viewport
        cursor.execute('''
            ALTER TABLE project_pages 
            ADD COLUMN diff_image_path_desktop TEXT
        ''')
        
        cursor.execute('''
            ALTER TABLE project_pages 
            ADD COLUMN diff_image_path_tablet TEXT
        ''')
        
        cursor.execute('''
            ALTER TABLE project_pages 
            ADD COLUMN diff_image_path_mobile TEXT
        ''')
        
        cursor.execute('''
            ALTER TABLE project_pages 
            ADD COLUMN diff_raw_image_path_desktop TEXT
        ''')
        
        cursor.execute('''
            ALTER TABLE project_pages 
            ADD COLUMN diff_raw_image_path_tablet TEXT
        ''')
        
        cursor.execute('''
            ALTER TABLE project_pages 
            ADD COLUMN diff_raw_image_path_mobile TEXT
        ''')
        
        # Add viewport-specific metrics
        cursor.execute('''
            ALTER TABLE project_pages 
            ADD COLUMN diff_mismatch_pct_desktop DECIMAL(6,3)
        ''')
        
        cursor.execute('''
            ALTER TABLE project_pages 
            ADD COLUMN diff_mismatch_pct_tablet DECIMAL(6,3)
        ''')
        
        cursor.execute('''
            ALTER TABLE project_pages 
            ADD COLUMN diff_mismatch_pct_mobile DECIMAL(6,3)
        ''')
        
        cursor.execute('''
            ALTER TABLE project_pages 
            ADD COLUMN diff_pixels_changed_desktop INTEGER
        ''')
        
        cursor.execute('''
            ALTER TABLE project_pages 
            ADD COLUMN diff_pixels_changed_tablet INTEGER
        ''')
        
        cursor.execute('''
            ALTER TABLE project_pages 
            ADD COLUMN diff_pixels_changed_mobile INTEGER
        ''')
        
        cursor.execute('''
            ALTER TABLE project_pages 
            ADD COLUMN diff_bounding_boxes_desktop TEXT
        ''')
        
        cursor.execute('''
            ALTER TABLE project_pages 
            ADD COLUMN diff_bounding_boxes_tablet TEXT
        ''')
        
        cursor.execute('''
            ALTER TABLE project_pages 
            ADD COLUMN diff_bounding_boxes_mobile TEXT
        ''')
        
        # Commit the changes
        conn.commit()
        print("Successfully added multi-viewport fields to project_pages table")
        
        # Verify the changes
        cursor.execute("PRAGMA table_info(project_pages)")
        columns = cursor.fetchall()
        
        # Check for new columns
        new_columns = [
            'staging_screenshot_path_desktop', 'staging_screenshot_path_tablet', 'staging_screenshot_path_mobile',
            'production_screenshot_path_desktop', 'production_screenshot_path_tablet', 'production_screenshot_path_mobile',
            'diff_image_path_desktop', 'diff_image_path_tablet', 'diff_image_path_mobile',
            'diff_raw_image_path_desktop', 'diff_raw_image_path_tablet', 'diff_raw_image_path_mobile',
            'diff_mismatch_pct_desktop', 'diff_mismatch_pct_tablet', 'diff_mismatch_pct_mobile',
            'diff_pixels_changed_desktop', 'diff_pixels_changed_tablet', 'diff_pixels_changed_mobile',
            'diff_bounding_boxes_desktop', 'diff_bounding_boxes_tablet', 'diff_bounding_boxes_mobile'
        ]
        
        column_names = [col[1] for col in columns]
        missing_columns = [col for col in new_columns if col not in column_names]
        
        if missing_columns:
            print(f"Warning: Some columns were not added: {missing_columns}")
        else:
            print("All multi-viewport columns verified successfully")
            
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("Some columns already exist, skipping...")
        else:
            print(f"Error during migration: {e}")
            raise
    except Exception as e:
        print(f"Unexpected error during migration: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    run_migration()