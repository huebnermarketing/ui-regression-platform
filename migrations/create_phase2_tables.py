"""
Database migration script for Phase 2 tables
Creates projects and project_pages tables
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from models.project import Project, ProjectPage

def create_tables():
    """Create the Phase 2 tables"""
    with app.app_context():
        try:
            # Create all tables
            db.create_all()
            print("✅ Successfully created Phase 2 tables:")
            print("   - projects")
            print("   - project_pages")
            
            # Verify tables were created
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            
            if 'projects' in tables:
                print("✅ projects table created successfully")
            else:
                print("❌ projects table not found")
                
            if 'project_pages' in tables:
                print("✅ project_pages table created successfully")
            else:
                print("❌ project_pages table not found")
                
        except Exception as e:
            print(f"❌ Error creating tables: {str(e)}")
            return False
            
    return True

if __name__ == "__main__":
    print("Creating Phase 2 database tables...")
    success = create_tables()
    if success:
        print("\n🎉 Phase 2 database migration completed successfully!")
    else:
        print("\n💥 Phase 2 database migration failed!")
        sys.exit(1)