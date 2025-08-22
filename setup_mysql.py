#!/usr/bin/env python3
"""
MySQL Database Setup Script for UI Diff Dashboard
This script helps set up the MySQL database and create initial user
"""

import os
import sys
from dotenv import load_dotenv
import pymysql
from werkzeug.security import generate_password_hash

# Load environment variables
load_dotenv()

def test_mysql_connection():
    """Test if MySQL server is running and accessible"""
    try:
        connection = pymysql.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD'),
            charset='utf8mb4'
        )
        print("[SUCCESS] MySQL connection successful!")
        connection.close()
        return True
    except Exception as e:
        print(f"[ERROR] MySQL connection failed: {e}")
        return False

def create_database():
    """Create the database if it doesn't exist"""
    try:
        connection = pymysql.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD'),
            charset='utf8mb4'
        )
        
        cursor = connection.cursor()
        db_name = os.getenv('DB_NAME', 'ui_diff_dashboard')
        
        # Create database
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
        print(f"[SUCCESS] Database '{db_name}' created successfully!")
        
        cursor.close()
        connection.close()
        return True
    except Exception as e:
        print(f"[ERROR] Database creation failed: {e}")
        return False

def create_tables_and_user():
    """Create tables and initial user using Flask app context"""
    try:
        # Add current directory to Python path to ensure imports work
        import sys
        if '.' not in sys.path:
            sys.path.insert(0, '.')
            
        # Import Flask app
        from app import app
        from models import db
        from models.user import User
        
        print("Checking database connection...")
        
        with app.app_context():
            # Test database connection first
            try:
                with db.engine.connect() as connection:
                    connection.execute(db.text('SELECT 1'))
                print("[SUCCESS] Database connection verified!")
            except Exception as conn_error:
                print(f"[ERROR] Database connection failed: {conn_error}")
                return False
            
            # Create all tables
            print("Creating database tables...")
            db.create_all()
            print("[SUCCESS] Database tables created successfully!")
            
            # Verify tables were created
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            print(f"Created tables: {tables}")
            
            # Check if admin user exists
            existing_user = User.query.filter_by(username='admin').first()
            if not existing_user:
                # Create admin user
                print("Creating admin user...")
                admin_user = User(username='admin')
                admin_user.set_password('admin123')
                db.session.add(admin_user)
                db.session.commit()
                print("[SUCCESS] Admin user created successfully!")
                print("   Username: admin")
                print("   Password: admin123")
            else:
                print("[INFO] Admin user already exists")
            
            # Also create a demo user for consistency
            existing_demo = User.query.filter_by(username='demo').first()
            if not existing_demo:
                print("Creating demo user...")
                demo_user = User(username='demo')
                demo_user.set_password('demo123')
                db.session.add(demo_user)
                db.session.commit()
                print("[SUCCESS] Demo user created successfully!")
                print("   Username: demo")
                print("   Password: demo123")
            else:
                print("[INFO] Demo user already exists")
                
        return True
    except ImportError as ie:
        print(f"[ERROR] Import failed: {ie}")
        print("   Make sure you're running this script from the project root directory")
        print("   and all required packages are installed (pip install -r requirements.txt)")
        return False
    except Exception as e:
        print(f"[ERROR] Table/User creation failed: {e}")
        print(f"   Error details: {type(e).__name__}: {str(e)}")
        import traceback
        print("   Full traceback:")
        traceback.print_exc()
        return False

def main():
    """Main setup function"""
    print("UI Diff Dashboard - MySQL Setup")
    print("=" * 40)
    
    # Check if .env file exists
    if not os.path.exists('.env'):
        print("[ERROR] .env file not found!")
        print("Please create .env file with your MySQL credentials")
        return False
    
    # Load and display current configuration
    db_host = os.getenv('DB_HOST', 'localhost')
    db_user = os.getenv('DB_USER', 'root')
    db_name = os.getenv('DB_NAME', 'ui_diff_dashboard')
    
    print(f"Database Host: {db_host}")
    print(f"Database User: {db_user}")
    print(f"Database Name: {db_name}")
    print("-" * 40)
    
    # Step 1: Test MySQL connection
    print("Step 1: Testing MySQL connection...")
    if not test_mysql_connection():
        print("\nMySQL Setup Instructions:")
        print("1. Install MySQL Server from: https://dev.mysql.com/downloads/mysql/")
        print("2. Or install XAMPP from: https://www.apachefriends.org/")
        print("3. Update your .env file with correct MySQL password")
        print("4. Make sure MySQL service is running")
        return False
    
    # Step 2: Create database
    print("\nStep 2: Creating database...")
    if not create_database():
        return False
    
    # Step 3: Create tables and user
    print("\nStep 3: Creating tables and initial user...")
    if not create_tables_and_user():
        return False
    
    print("\n[SUCCESS] MySQL setup completed successfully!")
    print("\nYou can now run the application with:")
    print("   python app.py")
    print("\nLogin credentials:")
    print("   Username: admin")
    print("   Password: admin123")
    
    return True

if __name__ == "__main__":
    main()