#!/usr/bin/env python3
"""
Script to delete project ID 68 (collage) by handling the enum issue
"""

import os
import pymysql
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def delete_project_68():
    """Delete project with ID 68 and handle enum issues"""
    
    # Database connection parameters
    config = {
        'user': os.getenv('DB_USER', 'root'),
        'password': os.getenv('DB_PASSWORD', ''),
        'host': os.getenv('DB_HOST', 'localhost'),
        'database': os.getenv('DB_NAME', 'ui_diff_dashboard'),
        'charset': 'utf8mb4'
    }
    
    try:
        # Connect to MySQL
        connection = pymysql.connect(**config)
        cursor = connection.cursor()
        
        print("Connected to MySQL database")
        
        # First, check if project 68 exists
        cursor.execute("SELECT id, name FROM projects WHERE id = 68")
        project = cursor.fetchone()
        
        if not project:
            print("Project with ID 68 not found.")
            return True
            
        print(f"Found project: ID {project[0]}, Name: {project[1]}")
        
        # Check for pages with invalid status
        cursor.execute("""
            SELECT COUNT(*) FROM project_pages 
            WHERE project_id = 68 AND status = 'capture_and_diff_complete'
        """)
        invalid_pages = cursor.fetchone()[0]
        
        if invalid_pages > 0:
            print(f"Found {invalid_pages} pages with invalid 'capture_and_diff_complete' status")
            
            # Update invalid status to a valid one before deletion
            cursor.execute("""
                UPDATE project_pages 
                SET status = 'diff_generated' 
                WHERE project_id = 68 AND status = 'capture_and_diff_complete'
            """)
            print(f"Updated {invalid_pages} pages to 'diff_generated' status")
        
        # Delete crawl jobs for this project first (foreign key constraint)
        cursor.execute("DELETE FROM crawl_jobs WHERE project_id = 68")
        deleted_jobs = cursor.rowcount
        print(f"Deleted {deleted_jobs} crawl jobs")
        
        # Delete project pages (should cascade, but let's be explicit)
        cursor.execute("DELETE FROM project_pages WHERE project_id = 68")
        deleted_pages = cursor.rowcount
        print(f"Deleted {deleted_pages} project pages")
        
        # Finally delete the project
        cursor.execute("DELETE FROM projects WHERE id = 68")
        deleted_projects = cursor.rowcount
        
        if deleted_projects > 0:
            print(f"Successfully deleted project '{project[1]}' (ID: 68)")
        else:
            print("Project was not deleted (may have been already deleted)")
        
        # Commit all changes
        connection.commit()
        print("All changes committed successfully!")
        
        return True
        
    except pymysql.Error as err:
        print(f"Database Error: {err}")
        if connection:
            connection.rollback()
            print("Transaction rolled back")
        return False
        
    except Exception as e:
        print(f"Unexpected Error: {e}")
        if connection:
            connection.rollback()
            print("Transaction rolled back")
        return False
        
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()
            print("Database connection closed")

if __name__ == '__main__':
    print("Deleting project ID 68 (collage)...")
    print("=" * 50)
    
    if delete_project_68():
        print("\nSUCCESS: Project deleted successfully!")
    else:
        print("\nERROR: Failed to delete project!")
        print("Please check the error messages above.")