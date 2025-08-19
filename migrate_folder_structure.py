#!/usr/bin/env python3
"""
Migration script to convert from old folder structure to new folder structure

Old structure: runs/{project_id}/{timestamp}/screenshots/{environment}/{viewport}/
New structure: screenshots/{project_id}/{timestamp}/{viewport}/{page}-{environment}.png

This script:
1. Migrates existing files from old structure to new structure
2. Updates database references to use new paths
3. Provides rollback capability
4. Validates migration results
"""

import os
import sys
import shutil
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple
import argparse

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.path_manager import PathManager
from models import db
from models.project import ProjectPage
from app import app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('migration.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class FolderStructureMigration:
    """Handles migration from old to new folder structure"""
    
    def __init__(self, old_base_dir: str = "runs", new_base_dir: str = "screenshots", 
                 backup_dir: str = "backup_runs"):
        """
        Initialize migration
        
        Args:
            old_base_dir: Old base directory (default: "runs")
            new_base_dir: New base directory (default: "screenshots")
            backup_dir: Backup directory for rollback (default: "backup_runs")
        """
        self.old_base_dir = Path(old_base_dir)
        self.new_base_dir = Path(new_base_dir)
        self.backup_dir = Path(backup_dir)
        self.path_manager = PathManager(new_base_dir)
        
        # Migration statistics
        self.stats = {
            'projects_processed': 0,
            'runs_processed': 0,
            'files_migrated': 0,
            'database_records_updated': 0,
            'errors': []
        }
    
    def validate_prerequisites(self) -> bool:
        """
        Validate that migration can proceed
        
        Returns:
            bool: True if migration can proceed
        """
        logger.info("Validating migration prerequisites...")
        
        # Check if old directory exists
        if not self.old_base_dir.exists():
            logger.error(f"Old base directory does not exist: {self.old_base_dir}")
            return False
        
        # Check if new directory already has content (warn but don't block)
        if self.new_base_dir.exists() and any(self.new_base_dir.iterdir()):
            logger.warning(f"New base directory already has content: {self.new_base_dir}")
            response = input("Continue anyway? (y/N): ")
            if response.lower() != 'y':
                return False
        
        # Check database connectivity
        try:
            with app.app_context():
                db.engine.execute("SELECT 1")
            logger.info("Database connection verified")
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            return False
        
        logger.info("Prerequisites validation passed")
        return True
    
    def create_backup(self) -> bool:
        """
        Create backup of old structure
        
        Returns:
            bool: True if backup was successful
        """
        try:
            logger.info(f"Creating backup of {self.old_base_dir} to {self.backup_dir}")
            
            if self.backup_dir.exists():
                shutil.rmtree(self.backup_dir)
            
            shutil.copytree(self.old_base_dir, self.backup_dir)
            logger.info("Backup created successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return False
    
    def migrate_files(self, dry_run: bool = False) -> bool:
        """
        Migrate files from old structure to new structure
        
        Args:
            dry_run: If True, only simulate migration without moving files
            
        Returns:
            bool: True if migration was successful
        """
        try:
            logger.info(f"Starting file migration (dry_run={dry_run})")
            
            # Process each project directory
            for project_dir in self.old_base_dir.iterdir():
                if not project_dir.is_dir():
                    continue
                
                try:
                    project_id = int(project_dir.name)
                except ValueError:
                    logger.warning(f"Skipping non-numeric directory: {project_dir.name}")
                    continue
                
                logger.info(f"Processing project {project_id}")
                self.stats['projects_processed'] += 1
                
                # Process each run directory
                for run_dir in project_dir.iterdir():
                    if not run_dir.is_dir():
                        continue
                    
                    process_timestamp = run_dir.name
                    
                    # Validate timestamp format
                    if not self._is_valid_timestamp(process_timestamp):
                        logger.warning(f"Skipping invalid timestamp directory: {process_timestamp}")
                        continue
                    
                    logger.info(f"Processing run {process_timestamp}")
                    self.stats['runs_processed'] += 1
                    
                    # Migrate screenshots
                    screenshots_dir = run_dir / "screenshots"
                    if screenshots_dir.exists():
                        self._migrate_screenshots(project_id, process_timestamp, screenshots_dir, dry_run)
                    
                    # Migrate diffs
                    diffs_dir = run_dir / "diffs"
                    if diffs_dir.exists():
                        self._migrate_diffs(project_id, process_timestamp, diffs_dir, dry_run)
            
            logger.info(f"File migration completed. Files migrated: {self.stats['files_migrated']}")
            return True
            
        except Exception as e:
            logger.error(f"File migration failed: {e}")
            self.stats['errors'].append(f"File migration error: {e}")
            return False
    
    def _is_valid_timestamp(self, timestamp: str) -> bool:
        """Check if timestamp matches expected format YYYYMMDD-HHmmss"""
        import re
        return bool(re.match(r'^\d{8}-\d{6}$', timestamp))
    
    def _migrate_screenshots(self, project_id: int, process_timestamp: str, 
                           screenshots_dir: Path, dry_run: bool):
        """Migrate screenshot files from old to new structure"""
        
        # Old structure: screenshots/{environment}/{viewport}/
        # New structure: {viewport}/{page}-{environment}.png
        
        for env_dir in screenshots_dir.iterdir():
            if not env_dir.is_dir():
                continue
            
            environment = env_dir.name  # staging or production
            if environment not in ['staging', 'production']:
                continue
            
            for viewport_dir in env_dir.iterdir():
                if not viewport_dir.is_dir():
                    continue
                
                viewport = viewport_dir.name  # desktop, tablet, mobile
                if viewport not in ['desktop', 'tablet', 'mobile']:
                    continue
                
                for screenshot_file in viewport_dir.iterdir():
                    if not screenshot_file.is_file() or not screenshot_file.name.endswith('.png'):
                        continue
                    
                    # Extract page name from filename
                    page_name = screenshot_file.stem
                    
                    # Get new file path
                    new_file_path = self.path_manager.get_screenshot_path_by_environment(
                        project_id, process_timestamp, page_name, viewport, environment
                    )
                    
                    if dry_run:
                        logger.info(f"Would migrate: {screenshot_file} -> {new_file_path}")
                    else:
                        # Create directory and copy file
                        new_file_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(screenshot_file, new_file_path)
                        logger.debug(f"Migrated: {screenshot_file} -> {new_file_path}")
                    
                    self.stats['files_migrated'] += 1
    
    def _migrate_diffs(self, project_id: int, process_timestamp: str, 
                      diffs_dir: Path, dry_run: bool):
        """Migrate diff files from old to new structure"""
        
        # Old structure: diffs/{viewport}/
        # New structure: {viewport}/{page}-diff.png
        
        for viewport_dir in diffs_dir.iterdir():
            if not viewport_dir.is_dir():
                continue
            
            viewport = viewport_dir.name
            if viewport not in ['desktop', 'tablet', 'mobile']:
                continue
            
            for diff_file in viewport_dir.iterdir():
                if not diff_file.is_file() or not diff_file.name.endswith('.png'):
                    continue
                
                # Extract page name from diff filename (remove _diff suffix)
                page_name = diff_file.stem.replace('_diff', '').replace('_overlay', '').replace('_raw', '')
                
                # Get new diff file path
                new_diff_path = self.path_manager.get_screenshot_path_by_environment(
                    project_id, process_timestamp, page_name, viewport, 'diff'
                )
                
                if dry_run:
                    logger.info(f"Would migrate: {diff_file} -> {new_diff_path}")
                else:
                    # Create directory and copy file
                    new_diff_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(diff_file, new_diff_path)
                    logger.debug(f"Migrated: {diff_file} -> {new_diff_path}")
                
                self.stats['files_migrated'] += 1
    
    def update_database_paths(self, dry_run: bool = False) -> bool:
        """
        Update database paths to use new structure
        
        Args:
            dry_run: If True, only simulate database updates
            
        Returns:
            bool: True if database update was successful
        """
        try:
            logger.info(f"Starting database path updates (dry_run={dry_run})")
            
            with app.app_context():
                # Get all pages with screenshot paths
                pages = ProjectPage.query.filter(
                    db.or_(
                        ProjectPage.staging_screenshot_path.isnot(None),
                        ProjectPage.production_screenshot_path.isnot(None),
                        ProjectPage.staging_screenshot_path_desktop.isnot(None),
                        ProjectPage.production_screenshot_path_desktop.isnot(None),
                        ProjectPage.staging_screenshot_path_tablet.isnot(None),
                        ProjectPage.production_screenshot_path_tablet.isnot(None),
                        ProjectPage.staging_screenshot_path_mobile.isnot(None),
                        ProjectPage.production_screenshot_path_mobile.isnot(None)
                    )
                ).all()
                
                logger.info(f"Found {len(pages)} pages with screenshot paths to update")
                
                for page in pages:
                    if self._update_page_paths(page, dry_run):
                        self.stats['database_records_updated'] += 1
                
                if not dry_run:
                    db.session.commit()
                    logger.info("Database changes committed")
                else:
                    db.session.rollback()
                    logger.info("Database changes rolled back (dry run)")
            
            logger.info(f"Database update completed. Records updated: {self.stats['database_records_updated']}")
            return True
            
        except Exception as e:
            logger.error(f"Database update failed: {e}")
            self.stats['errors'].append(f"Database update error: {e}")
            return False
    
    def _update_page_paths(self, page: ProjectPage, dry_run: bool) -> bool:
        """Update paths for a single page"""
        try:
            updated = False
            
            # Get the process timestamp (use current_run_id if available)
            process_timestamp = getattr(page, 'current_run_id', None)
            if not process_timestamp:
                # Try to extract from existing path
                process_timestamp = self._extract_timestamp_from_path(page)
            
            if not process_timestamp:
                logger.warning(f"Could not determine process timestamp for page {page.id}")
                return False
            
            # Update viewport-specific paths
            for viewport in ['desktop', 'tablet', 'mobile']:
                for environment in ['staging', 'production']:
                    old_path_attr = f'{environment}_screenshot_path_{viewport}'
                    old_path = getattr(page, old_path_attr, None)
                    
                    if old_path:
                        # Generate new path
                        new_path = self.path_manager.get_relative_path(
                            self.path_manager.get_screenshot_path_by_environment(
                                page.project_id, process_timestamp, page.path, viewport, environment
                            )
                        )
                        
                        if dry_run:
                            logger.info(f"Would update {old_path_attr}: {old_path} -> {new_path}")
                        else:
                            setattr(page, old_path_attr, new_path)
                            logger.debug(f"Updated {old_path_attr}: {old_path} -> {new_path}")
                        
                        updated = True
            
            # Update legacy paths (use desktop as default)
            if hasattr(page, 'staging_screenshot_path') and page.staging_screenshot_path:
                new_staging_path = self.path_manager.get_relative_path(
                    self.path_manager.get_screenshot_path_by_environment(
                        page.project_id, process_timestamp, page.path, 'desktop', 'staging'
                    )
                )
                
                if not dry_run:
                    page.staging_screenshot_path = new_staging_path
                updated = True
            
            if hasattr(page, 'production_screenshot_path') and page.production_screenshot_path:
                new_production_path = self.path_manager.get_relative_path(
                    self.path_manager.get_screenshot_path_by_environment(
                        page.project_id, process_timestamp, page.path, 'desktop', 'production'
                    )
                )
                
                if not dry_run:
                    page.production_screenshot_path = new_production_path
                updated = True
            
            return updated
            
        except Exception as e:
            logger.error(f"Error updating paths for page {page.id}: {e}")
            return False
    
    def _extract_timestamp_from_path(self, page: ProjectPage) -> str:
        """Try to extract timestamp from existing path"""
        # Look for timestamp pattern in existing paths
        import re
        timestamp_pattern = r'(\d{8}-\d{6})'
        
        for attr in ['staging_screenshot_path', 'production_screenshot_path',
                     'staging_screenshot_path_desktop', 'production_screenshot_path_desktop']:
            path = getattr(page, attr, None)
            if path:
                match = re.search(timestamp_pattern, path)
                if match:
                    return match.group(1)
        
        # Fallback: use current timestamp
        return self.path_manager.generate_process_timestamp()
    
    def validate_migration(self) -> bool:
        """
        Validate that migration was successful
        
        Returns:
            bool: True if validation passed
        """
        logger.info("Validating migration results...")
        
        validation_errors = []
        
        # Check that new structure exists
        if not self.new_base_dir.exists():
            validation_errors.append("New base directory does not exist")
        
        # Check that files were migrated
        if self.stats['files_migrated'] == 0:
            validation_errors.append("No files were migrated")
        
        # Check database consistency
        try:
            with app.app_context():
                pages_with_paths = ProjectPage.query.filter(
                    db.or_(
                        ProjectPage.staging_screenshot_path.isnot(None),
                        ProjectPage.production_screenshot_path.isnot(None)
                    )
                ).count()
                
                if pages_with_paths != self.stats['database_records_updated']:
                    validation_errors.append(
                        f"Database record count mismatch: {pages_with_paths} vs {self.stats['database_records_updated']}"
                    )
        except Exception as e:
            validation_errors.append(f"Database validation error: {e}")
        
        if validation_errors:
            logger.error("Migration validation failed:")
            for error in validation_errors:
                logger.error(f"  - {error}")
            return False
        
        logger.info("Migration validation passed")
        return True
    
    def rollback(self) -> bool:
        """
        Rollback migration by restoring from backup
        
        Returns:
            bool: True if rollback was successful
        """
        try:
            logger.info("Starting migration rollback...")
            
            if not self.backup_dir.exists():
                logger.error("Backup directory does not exist, cannot rollback")
                return False
            
            # Remove new structure
            if self.new_base_dir.exists():
                shutil.rmtree(self.new_base_dir)
            
            # Restore old structure
            shutil.copytree(self.backup_dir, self.old_base_dir)
            
            logger.info("Migration rollback completed")
            return True
            
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False
    
    def cleanup_old_structure(self) -> bool:
        """
        Remove old structure after successful migration
        
        Returns:
            bool: True if cleanup was successful
        """
        try:
            logger.info("Cleaning up old structure...")
            
            if self.old_base_dir.exists():
                shutil.rmtree(self.old_base_dir)
                logger.info("Old structure removed")
            
            return True
            
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            return False
    
    def print_summary(self):
        """Print migration summary"""
        logger.info("Migration Summary:")
        logger.info(f"  Projects processed: {self.stats['projects_processed']}")
        logger.info(f"  Runs processed: {self.stats['runs_processed']}")
        logger.info(f"  Files migrated: {self.stats['files_migrated']}")
        logger.info(f"  Database records updated: {self.stats['database_records_updated']}")
        
        if self.stats['errors']:
            logger.error(f"  Errors encountered: {len(self.stats['errors'])}")
            for error in self.stats['errors']:
                logger.error(f"    - {error}")


def main():
    """Main migration function"""
    parser = argparse.ArgumentParser(description='Migrate folder structure from old to new format')
    parser.add_argument('--dry-run', action='store_true', help='Simulate migration without making changes')
    parser.add_argument('--rollback', action='store_true', help='Rollback previous migration')
    parser.add_argument('--cleanup', action='store_true', help='Clean up old structure after migration')
    parser.add_argument('--old-dir', default='runs', help='Old base directory (default: runs)')
    parser.add_argument('--new-dir', default='screenshots', help='New base directory (default: screenshots)')
    parser.add_argument('--backup-dir', default='backup_runs', help='Backup directory (default: backup_runs)')
    
    args = parser.parse_args()
    
    migration = FolderStructureMigration(args.old_dir, args.new_dir, args.backup_dir)
    
    if args.rollback:
        logger.info("Starting migration rollback...")
        success = migration.rollback()
        if success:
            logger.info("Rollback completed successfully")
        else:
            logger.error("Rollback failed")
        return 0 if success else 1
    
    if args.cleanup:
        logger.info("Starting cleanup of old structure...")
        success = migration.cleanup_old_structure()
        if success:
            logger.info("Cleanup completed successfully")
        else:
            logger.error("Cleanup failed")
        return 0 if success else 1
    
    # Normal migration process
    logger.info("Starting folder structure migration...")
    
    # Validate prerequisites
    if not migration.validate_prerequisites():
        logger.error("Prerequisites validation failed")
        return 1
    
    # Create backup (skip for dry run)
    if not args.dry_run:
        if not migration.create_backup():
            logger.error("Backup creation failed")
            return 1
    
    # Migrate files
    if not migration.migrate_files(args.dry_run):
        logger.error("File migration failed")
        return 1
    
    # Update database
    if not migration.update_database_paths(args.dry_run):
        logger.error("Database update failed")
        return 1
    
    # Validate migration (skip for dry run)
    if not args.dry_run:
        if not migration.validate_migration():
            logger.error("Migration validation failed")
            return 1
    
    # Print summary
    migration.print_summary()
    
    if args.dry_run:
        logger.info("Dry run completed successfully")
    else:
        logger.info("Migration completed successfully")
        logger.info("You can now run with --cleanup to remove the old structure")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())