"""
Migration to add multi-viewport screenshot support for MySQL
Adds columns for desktop, tablet, and mobile screenshots and diffs
"""

import sys
import os
import pymysql
from sqlalchemy import create_engine, text

# Add the parent directory to the path so we can import the models
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def get_database_url():
    """Get database URL from environment or config"""
    try:
        from config import Config
        return Config.SQLALCHEMY_DATABASE_URI
    except:
        # Fallback to environment variables
        db_user = os.getenv('DB_USER', 'root')
        db_password = os.getenv('DB_PASSWORD', '')
        db_host = os.getenv('DB_HOST', 'localhost')
        db_name = os.getenv('DB_NAME', 'ui_diff_dashboard')
        return f"mysql+pymysql://{db_user}:{db_password}@{db_host}/{db_name}"

def run_migration():
    """Run the migration to add multi-viewport fields"""
    
    try:
        # Get database connection
        database_url = get_database_url()
        engine = create_engine(database_url)
        
        print("Adding multi-viewport screenshot and diff fields to MySQL...")
        print(f"Database URL: {database_url.split('@')[1] if '@' in database_url else 'localhost'}")
        
        with engine.connect() as conn:
            # Start transaction
            trans = conn.begin()
            
            try:
                # List of columns to add
                columns_to_add = [
                    # Screenshot paths
                    "ADD COLUMN staging_screenshot_path_desktop TEXT",
                    "ADD COLUMN staging_screenshot_path_tablet TEXT", 
                    "ADD COLUMN staging_screenshot_path_mobile TEXT",
                    "ADD COLUMN production_screenshot_path_desktop TEXT",
                    "ADD COLUMN production_screenshot_path_tablet TEXT",
                    "ADD COLUMN production_screenshot_path_mobile TEXT",
                    
                    # Diff image paths
                    "ADD COLUMN diff_image_path_desktop TEXT",
                    "ADD COLUMN diff_image_path_tablet TEXT",
                    "ADD COLUMN diff_image_path_mobile TEXT",
                    "ADD COLUMN diff_raw_image_path_desktop TEXT",
                    "ADD COLUMN diff_raw_image_path_tablet TEXT",
                    "ADD COLUMN diff_raw_image_path_mobile TEXT",
                    
                    # Diff metrics
                    "ADD COLUMN diff_mismatch_pct_desktop DECIMAL(6,3)",
                    "ADD COLUMN diff_mismatch_pct_tablet DECIMAL(6,3)",
                    "ADD COLUMN diff_mismatch_pct_mobile DECIMAL(6,3)",
                    "ADD COLUMN diff_pixels_changed_desktop INTEGER",
                    "ADD COLUMN diff_pixels_changed_tablet INTEGER",
                    "ADD COLUMN diff_pixels_changed_mobile INTEGER",
                    "ADD COLUMN diff_bounding_boxes_desktop TEXT",
                    "ADD COLUMN diff_bounding_boxes_tablet TEXT",
                    "ADD COLUMN diff_bounding_boxes_mobile TEXT"
                ]
                
                # Add columns one by one
                for i, column_def in enumerate(columns_to_add, 1):
                    try:
                        sql = f"ALTER TABLE project_pages {column_def}"
                        conn.execute(text(sql))
                        print(f"  [{i:2d}/21] Added: {column_def.split('ADD COLUMN ')[1].split(' ')[0]}")
                    except Exception as e:
                        if "Duplicate column name" in str(e):
                            print(f"  [{i:2d}/21] Skipped: {column_def.split('ADD COLUMN ')[1].split(' ')[0]} (already exists)")
                        else:
                            print(f"  [{i:2d}/21] Error: {column_def.split('ADD COLUMN ')[1].split(' ')[0]} - {str(e)}")
                            raise
                
                # Commit the transaction
                trans.commit()
                print("\n[SUCCESS] Successfully added multi-viewport fields to project_pages table")
                
                # Verify the changes
                result = conn.execute(text("DESCRIBE project_pages"))
                columns = [row[0] for row in result.fetchall()]
                
                # Check for new columns
                expected_columns = [
                    'staging_screenshot_path_desktop', 'staging_screenshot_path_tablet', 'staging_screenshot_path_mobile',
                    'production_screenshot_path_desktop', 'production_screenshot_path_tablet', 'production_screenshot_path_mobile',
                    'diff_image_path_desktop', 'diff_image_path_tablet', 'diff_image_path_mobile',
                    'diff_raw_image_path_desktop', 'diff_raw_image_path_tablet', 'diff_raw_image_path_mobile',
                    'diff_mismatch_pct_desktop', 'diff_mismatch_pct_tablet', 'diff_mismatch_pct_mobile',
                    'diff_pixels_changed_desktop', 'diff_pixels_changed_tablet', 'diff_pixels_changed_mobile',
                    'diff_bounding_boxes_desktop', 'diff_bounding_boxes_tablet', 'diff_bounding_boxes_mobile'
                ]
                
                missing_columns = [col for col in expected_columns if col not in columns]
                
                if missing_columns:
                    print(f"\n[WARNING] Some columns were not added: {missing_columns}")
                    return False
                else:
                    print(f"\n[SUCCESS] All {len(expected_columns)} multi-viewport columns verified successfully")
                    return True
                    
            except Exception as e:
                trans.rollback()
                raise
                
    except Exception as e:
        print(f"\n[ERROR] Migration failed: {str(e)}")
        
        # Check if it's a connection issue
        if "Access denied" in str(e):
            print("\nTroubleshooting:")
            print("1. Check database credentials in .env file")
            print("2. Ensure MySQL server is running")
            print("3. Verify database exists and user has ALTER privileges")
        elif "Unknown database" in str(e):
            print("\nTroubleshooting:")
            print("1. Create the database first")
            print("2. Check database name in configuration")
        
        return False

def check_existing_columns():
    """Check which columns already exist"""
    try:
        database_url = get_database_url()
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            result = conn.execute(text("DESCRIBE project_pages"))
            existing_columns = [row[0] for row in result.fetchall()]
            
            viewport_columns = [col for col in existing_columns if any(vp in col for vp in ['_desktop', '_tablet', '_mobile'])]
            
            print(f"Found {len(viewport_columns)} existing viewport columns:")
            for col in sorted(viewport_columns):
                print(f"  - {col}")
                
            return viewport_columns
            
    except Exception as e:
        print(f"Error checking existing columns: {str(e)}")
        return []

if __name__ == "__main__":
    print("Multi-Viewport MySQL Migration")
    print("=" * 40)
    
    # Check existing columns first
    existing = check_existing_columns()
    
    if len(existing) >= 21:
        print(f"\n[INFO] All viewport columns appear to already exist ({len(existing)} found)")
        print("Migration may not be necessary.")
    else:
        print(f"\n[INFO] Found {len(existing)} existing viewport columns, proceeding with migration...")
        
    # Run migration
    success = run_migration()
    
    if success:
        print("\n" + "=" * 40)
        print("[COMPLETE] Migration finished successfully!")
    else:
        print("\n" + "=" * 40)
        print("[FAILED] Migration encountered errors!")
        sys.exit(1)