"""
Rollback script to remove multi-viewport screenshot support fields
This undoes the changes made by add_multi_viewport_fields.py and add_multi_viewport_fields_mysql.py
"""

import pymysql
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_database_config():
    """Get database configuration from environment"""
    return {
        'user': os.getenv('DB_USER', 'root'),
        'password': os.getenv('DB_PASSWORD', ''),
        'host': os.getenv('DB_HOST', 'localhost'),
        'database': os.getenv('DB_NAME', 'ui_diff_dashboard'),
        'charset': 'utf8mb4'
    }

def rollback_multi_viewport_fields():
    """Remove multi-viewport fields from project_pages table"""
    
    config = get_database_config()
    
    try:
        # Connect to MySQL
        connection = pymysql.connect(**config)
        cursor = connection.cursor()
        
        print("Connected to MySQL database")
        print("Rolling back multi-viewport fields from project_pages table...")
        
        # List of columns to remove
        columns_to_remove = [
            # Screenshot paths
            'staging_screenshot_path_desktop',
            'staging_screenshot_path_tablet', 
            'staging_screenshot_path_mobile',
            'production_screenshot_path_desktop',
            'production_screenshot_path_tablet',
            'production_screenshot_path_mobile',
            
            # Diff image paths
            'diff_image_path_desktop',
            'diff_image_path_tablet',
            'diff_image_path_mobile',
            'diff_raw_image_path_desktop',
            'diff_raw_image_path_tablet',
            'diff_raw_image_path_mobile',
            
            # Diff metrics
            'diff_mismatch_pct_desktop',
            'diff_mismatch_pct_tablet',
            'diff_mismatch_pct_mobile',
            'diff_pixels_changed_desktop',
            'diff_pixels_changed_tablet',
            'diff_pixels_changed_mobile',
            'diff_bounding_boxes_desktop',
            'diff_bounding_boxes_tablet',
            'diff_bounding_boxes_mobile'
        ]
        
        # Check which columns exist
        cursor.execute("""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = %s 
            AND TABLE_NAME = 'project_pages'
        """, (config['database'],))
        
        existing_columns = [row[0] for row in cursor.fetchall()]
        columns_to_drop = [col for col in columns_to_remove if col in existing_columns]
        
        if not columns_to_drop:
            print("WARNING: No multi-viewport columns found. Nothing to rollback.")
            return True
        
        print(f"Found {len(columns_to_drop)} multi-viewport columns to remove:")
        for col in columns_to_drop:
            print(f"  - {col}")
        
        # Remove columns one by one
        for i, column in enumerate(columns_to_drop, 1):
            try:
                cursor.execute(f"ALTER TABLE project_pages DROP COLUMN {column}")
                print(f"  [{i:2d}/{len(columns_to_drop)}] Removed: {column}")
            except pymysql.Error as e:
                print(f"  [{i:2d}/{len(columns_to_drop)}] Error removing {column}: {e}")
                # Continue with other columns
        
        # Commit the changes
        connection.commit()
        print(f"\n[SUCCESS] Removed {len(columns_to_drop)} multi-viewport columns from project_pages table")
        print("[SUCCESS] Rollback completed successfully!")
        
    except pymysql.Error as err:
        print(f"Error: {err}")
        if connection:
            connection.rollback()
        return False
        
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()
            print("Database connection closed")
    
    return True

def check_existing_columns():
    """Check which multi-viewport columns exist"""
    config = get_database_config()
    
    try:
        connection = pymysql.connect(**config)
        cursor = connection.cursor()
        
        cursor.execute("""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = %s 
            AND TABLE_NAME = 'project_pages'
        """, (config['database'],))
        
        existing_columns = [row[0] for row in cursor.fetchall()]
        viewport_columns = [col for col in existing_columns if any(vp in col for vp in ['_desktop', '_tablet', '_mobile'])]
        
        return viewport_columns
        
    except pymysql.Error as err:
        print(f"Error checking existing columns: {err}")
        return []
        
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

if __name__ == "__main__":
    print("Multi-Viewport Fields Rollback")
    print("=" * 40)
    
    # Check existing columns first
    existing = check_existing_columns()
    
    if not existing:
        print("No multi-viewport columns found. Nothing to rollback.")
    else:
        print(f"Found {len(existing)} multi-viewport columns to remove:")
        for col in sorted(existing):
            print(f"  - {col}")
        
        print(f"\nProceeding with rollback...")
        
        # Run rollback
        success = rollback_multi_viewport_fields()
        
        if success:
            print("\n" + "=" * 40)
            print("[COMPLETE] Multi-viewport fields rollback finished successfully!")
        else:
            print("\n" + "=" * 40)
            print("[FAILED] Multi-viewport fields rollback encountered errors!")