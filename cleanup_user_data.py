#!/usr/bin/env python3
"""
User Data Cleanup Script for UI Regression Platform

This script deletes all test data for a specific user while preserving the user account.
It removes:
- All projects owned by the user
- All project pages associated with those projects
- All crawl jobs for those projects
- All screenshot files and directories
- All diff files and directories
- All run directories

Usage:
    python cleanup_user_data.py --username <username>
    python cleanup_user_data.py --user-id <user_id>

Examples:
    python cleanup_user_data.py --username demo
    python cleanup_user_data.py --user-id 1
"""

import os
import sys
import argparse
import shutil
from pathlib import Path
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
from models import db
from models.user import User
from models.project import Project, ProjectPage
from models.crawl_job import CrawlJob
from utils.path_manager import PathManager


def setup_app():
    """Setup Flask app with database configuration"""
    app = Flask(__name__)
    
    # Load configuration
    from dotenv import load_dotenv
    from urllib.parse import quote_plus
    
    load_dotenv()
    
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Build database URI
    db_user = os.getenv('DB_USER', 'root')
    db_password = os.getenv('DB_PASSWORD', '')
    db_host = os.getenv('DB_HOST', 'localhost')
    db_name = os.getenv('DB_NAME', 'ui_diff_dashboard')
    
    if db_password:
        encoded_password = quote_plus(db_password)
        app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://{db_user}:{encoded_password}@{db_host}/{db_name}"
    else:
        app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://{db_user}@{db_host}/{db_name}"
    
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize database
    db.init_app(app)
    
    return app


def get_user_by_username(username: str) -> User:
    """Get user by username"""
    user = User.query.filter_by(username=username).first()
    if not user:
        raise ValueError(f"User with username '{username}' not found")
    return user


def get_user_by_id(user_id: int) -> User:
    """Get user by ID"""
    user = User.query.get(user_id)
    if not user:
        raise ValueError(f"User with ID {user_id} not found")
    return user


def cleanup_database_records(user: User) -> dict:
    """
    Clean up all database records for a user
    
    Args:
        user: User object
        
    Returns:
        dict: Cleanup statistics
    """
    stats = {
        'projects_deleted': 0,
        'pages_deleted': 0,
        'jobs_deleted': 0,
        'errors': []
    }
    
    try:
        # Get all projects for the user
        projects = Project.query.filter_by(user_id=user.id).all()
        project_ids = [p.id for p in projects]
        
        print(f"Found {len(projects)} projects for user '{user.username}'")
        
        if not projects:
            print("No projects found for user. Nothing to clean up.")
            return stats
        
        # Delete crawl jobs first (due to foreign key constraints)
        crawl_jobs = CrawlJob.query.filter(CrawlJob.project_id.in_(project_ids)).all()
        stats['jobs_deleted'] = len(crawl_jobs)
        
        print(f"Deleting {len(crawl_jobs)} crawl jobs...")
        for job in crawl_jobs:
            db.session.delete(job)
        
        # Delete project pages
        project_pages = ProjectPage.query.filter(ProjectPage.project_id.in_(project_ids)).all()
        stats['pages_deleted'] = len(project_pages)
        
        print(f"Deleting {len(project_pages)} project pages...")
        for page in project_pages:
            db.session.delete(page)
        
        # Delete projects
        stats['projects_deleted'] = len(projects)
        
        print(f"Deleting {len(projects)} projects...")
        for project in projects:
            db.session.delete(project)
        
        # Commit all deletions
        db.session.commit()
        print("Database cleanup completed successfully!")
        
        return stats
        
    except Exception as e:
        db.session.rollback()
        error_msg = f"Database cleanup failed: {str(e)}"
        print(f"ERROR: {error_msg}")
        stats['errors'].append(error_msg)
        return stats


def cleanup_file_system(user: User, project_ids: list) -> dict:
    """
    Clean up all file system data for user's projects
    
    Args:
        user: User object
        project_ids: List of project IDs to clean up
        
    Returns:
        dict: Cleanup statistics
    """
    stats = {
        'directories_deleted': 0,
        'files_deleted': 0,
        'errors': []
    }
    
    if not project_ids:
        print("No project IDs provided for file system cleanup")
        return stats
    
    try:
        # Initialize path manager
        path_manager = PathManager()
        
        # Directories to clean up
        base_directories = [
            'screenshots',
            'diffs', 
            'runs',
            'test_screenshots'
        ]
        
        total_files_deleted = 0
        total_dirs_deleted = 0
        
        for base_dir in base_directories:
            if not os.path.exists(base_dir):
                continue
                
            print(f"Cleaning up {base_dir} directory...")
            
            for project_id in project_ids:
                project_dir = Path(base_dir) / str(project_id)
                
                if project_dir.exists():
                    try:
                        # Count files before deletion
                        file_count = sum(1 for _ in project_dir.rglob('*') if _.is_file())
                        dir_count = sum(1 for _ in project_dir.rglob('*') if _.is_dir())
                        
                        print(f"  Deleting project {project_id} directory: {project_dir}")
                        print(f"    Contains {file_count} files and {dir_count} subdirectories")
                        
                        # Delete the entire project directory
                        shutil.rmtree(project_dir)
                        
                        total_files_deleted += file_count
                        total_dirs_deleted += dir_count + 1  # +1 for the project directory itself
                        
                    except Exception as e:
                        error_msg = f"Failed to delete {project_dir}: {str(e)}"
                        print(f"    ERROR: {error_msg}")
                        stats['errors'].append(error_msg)
        
        stats['files_deleted'] = total_files_deleted
        stats['directories_deleted'] = total_dirs_deleted
        
        print(f"File system cleanup completed!")
        print(f"  Total files deleted: {total_files_deleted}")
        print(f"  Total directories deleted: {total_dirs_deleted}")
        
        return stats
        
    except Exception as e:
        error_msg = f"File system cleanup failed: {str(e)}"
        print(f"ERROR: {error_msg}")
        stats['errors'].append(error_msg)
        return stats


def cleanup_user_data(user: User, dry_run: bool = False) -> dict:
    """
    Clean up all data for a specific user
    
    Args:
        user: User object
        dry_run: If True, only show what would be deleted without actually deleting
        
    Returns:
        dict: Complete cleanup statistics
    """
    print(f"{'DRY RUN: ' if dry_run else ''}Starting cleanup for user: {user.username} (ID: {user.id})")
    print(f"Created: {user.created_at}")
    print("-" * 60)
    
    # Get project IDs before database cleanup
    projects = Project.query.filter_by(user_id=user.id).all()
    project_ids = [p.id for p in projects]
    
    if dry_run:
        print("DRY RUN MODE - No actual deletions will be performed")
        print(f"Would delete {len(projects)} projects:")
        for project in projects:
            print(f"  - {project.name} (ID: {project.id})")
        
        # Count pages and jobs
        page_count = ProjectPage.query.filter(ProjectPage.project_id.in_(project_ids)).count() if project_ids else 0
        job_count = CrawlJob.query.filter(CrawlJob.project_id.in_(project_ids)).count() if project_ids else 0
        
        print(f"Would delete {page_count} project pages")
        print(f"Would delete {job_count} crawl jobs")
        
        # Check file system
        for base_dir in ['screenshots', 'diffs', 'runs', 'test_screenshots']:
            if os.path.exists(base_dir):
                for project_id in project_ids:
                    project_dir = Path(base_dir) / str(project_id)
                    if project_dir.exists():
                        file_count = sum(1 for _ in project_dir.rglob('*') if _.is_file())
                        print(f"Would delete {file_count} files from {project_dir}")
        
        return {
            'dry_run': True,
            'projects_found': len(projects),
            'pages_found': page_count,
            'jobs_found': job_count
        }
    
    # Perform actual cleanup
    total_stats = {
        'user': user.username,
        'user_id': user.id,
        'cleanup_time': datetime.now().isoformat(),
        'database_stats': {},
        'filesystem_stats': {},
        'total_errors': []
    }
    
    # Clean up database records
    print("Phase 1: Database cleanup")
    db_stats = cleanup_database_records(user)
    total_stats['database_stats'] = db_stats
    total_stats['total_errors'].extend(db_stats.get('errors', []))
    
    # Clean up file system
    print("\nPhase 2: File system cleanup")
    fs_stats = cleanup_file_system(user, project_ids)
    total_stats['filesystem_stats'] = fs_stats
    total_stats['total_errors'].extend(fs_stats.get('errors', []))
    
    return total_stats


def print_summary(stats: dict):
    """Print cleanup summary"""
    print("\n" + "=" * 60)
    print("CLEANUP SUMMARY")
    print("=" * 60)
    
    if stats.get('dry_run'):
        print("DRY RUN - No actual changes were made")
        print(f"Projects found: {stats.get('projects_found', 0)}")
        print(f"Pages found: {stats.get('pages_found', 0)}")
        print(f"Jobs found: {stats.get('jobs_found', 0)}")
        return
    
    print(f"User: {stats.get('user', 'Unknown')}")
    print(f"User ID: {stats.get('user_id', 'Unknown')}")
    print(f"Cleanup time: {stats.get('cleanup_time', 'Unknown')}")
    
    db_stats = stats.get('database_stats', {})
    print(f"\nDatabase cleanup:")
    print(f"  Projects deleted: {db_stats.get('projects_deleted', 0)}")
    print(f"  Pages deleted: {db_stats.get('pages_deleted', 0)}")
    print(f"  Jobs deleted: {db_stats.get('jobs_deleted', 0)}")
    
    fs_stats = stats.get('filesystem_stats', {})
    print(f"\nFile system cleanup:")
    print(f"  Files deleted: {fs_stats.get('files_deleted', 0)}")
    print(f"  Directories deleted: {fs_stats.get('directories_deleted', 0)}")
    
    errors = stats.get('total_errors', [])
    if errors:
        print(f"\nErrors encountered: {len(errors)}")
        for error in errors:
            print(f"  - {error}")
    else:
        print("\nNo errors encountered!")
    
    print("\nUser account preserved - login credentials remain intact.")


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description='Clean up all test data for a specific user while preserving the user account',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cleanup_user_data.py --username demo
  python cleanup_user_data.py --user-id 1
  python cleanup_user_data.py --username demo --dry-run
        """
    )
    
    # User identification (mutually exclusive)
    user_group = parser.add_mutually_exclusive_group(required=True)
    user_group.add_argument('--username', type=str, help='Username to clean up')
    user_group.add_argument('--user-id', type=int, help='User ID to clean up')
    
    # Options
    parser.add_argument('--dry-run', action='store_true', 
                       help='Show what would be deleted without actually deleting')
    parser.add_argument('--confirm', action='store_true',
                       help='Skip confirmation prompt (use with caution)')
    
    args = parser.parse_args()
    
    # Setup Flask app and database
    app = setup_app()
    
    with app.app_context():
        try:
            # Get user
            if args.username:
                user = get_user_by_username(args.username)
            else:
                user = get_user_by_id(args.user_id)
            
            print(f"Found user: {user.username} (ID: {user.id})")
            
            # Confirmation prompt (unless --confirm or --dry-run)
            if not args.dry_run and not args.confirm:
                print("\nWARNING: This will permanently delete ALL data for this user!")
                print("This includes:")
                print("- All projects")
                print("- All project pages") 
                print("- All crawl jobs")
                print("- All screenshots and diff images")
                print("- All run directories")
                print("\nThe user account will be preserved.")
                
                response = input(f"\nAre you sure you want to delete all data for user '{user.username}'? (yes/no): ")
                if response.lower() not in ['yes', 'y']:
                    print("Cleanup cancelled.")
                    return
            
            # Perform cleanup
            stats = cleanup_user_data(user, dry_run=args.dry_run)
            
            # Print summary
            print_summary(stats)
            
        except ValueError as e:
            print(f"ERROR: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"UNEXPECTED ERROR: {e}")
            sys.exit(1)


if __name__ == '__main__':
    main()