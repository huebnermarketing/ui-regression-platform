"""
Path Manager for UI Regression Platform
Handles consistent nested folder structure for screenshots and diffs
"""

import os
import re
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Tuple, Optional
import pytz


class PathManager:
    """
    Manages file paths for screenshots and diffs with consistent nested structure:
    
    /screenshots/
      {project_id}/
        {process_timestamp}/        # e.g., 20250813-113309 (YYYYMMDD-HHmmss)
          Desktop/
            {page_name}-production.png
            {page_name}-staging.png
            {page_name}-diff.png
          Tablet/
            {page_name}-production.png
            {page_name}-staging.png
            {page_name}-diff.png
          Mobile/
            {page_name}-production.png
            {page_name}-staging.png
            {page_name}-diff.png
    """
    
    def __init__(self, base_screenshots_dir: str = "screenshots"):
        """
        Initialize path manager
        
        Args:
            base_screenshots_dir: Base directory for screenshots (default: "screenshots")
        """
        self.base_screenshots_dir = Path(base_screenshots_dir)
        self.ist_timezone = pytz.timezone('Asia/Kolkata')
        
        # Viewport names (capitalized for folder structure)
        self.viewport_folders = {
            'desktop': 'Desktop',
            'tablet': 'Tablet', 
            'mobile': 'Mobile'
        }
        
        # Environment names
        self.environments = ['production', 'staging', 'diff']
        
        # Ensure base directory exists
        self.base_screenshots_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_process_timestamp(self) -> str:
        """
        Generate process timestamp in IST timezone
        Format: YYYYMMDD-HHmmss (filesystem-safe)
        
        Returns:
            str: Process timestamp like "20250813-113309"
        """
        ist_now = datetime.now(self.ist_timezone)
        return ist_now.strftime('%Y%m%d-%H%M%S')
    
    def slugify_page_name(self, page_path: str) -> str:
        """
        Convert a URL path to a safe filename slug
        
        Args:
            page_path: URL path to slugify
            
        Returns:
            str: Slugified filename (limited to safe length)
        """
        # Remove leading/trailing slashes and replace with underscores
        path = page_path.strip('/')
        
        # If empty path (root), use 'home'
        if not path:
            return 'home'
        
        # Replace slashes and special characters with underscores
        slug = re.sub(r'[/\\:*?"<>|=!@#$%^&*()]+', '_', path)
        
        # Replace multiple underscores with single underscore
        slug = re.sub(r'_+', '_', slug)
        
        # Remove leading/trailing underscores
        slug = slug.strip('_')
        
        # Ensure it's not empty
        if not slug:
            return 'page'
        
        # Limit filename length to prevent filesystem issues (Windows has 260 char limit)
        # Reserve space for environment suffix and extension: "-production.png" = 15 chars
        max_length = 200  # Leave buffer for full path
        
        if len(slug) > max_length:
            # Truncate and add hash for uniqueness
            hash_suffix = hashlib.md5(page_path.encode()).hexdigest()[:8]
            slug = slug[:max_length-9] + '_' + hash_suffix  # -9 for underscore and 8 char hash
        
        return slug
    
    def get_project_directory(self, project_id: int, process_timestamp: str) -> Path:
        """
        Get project directory path for a specific process run
        
        Args:
            project_id: Project ID
            process_timestamp: Process timestamp (YYYYMMDD-HHmmss)
            
        Returns:
            Path: Project directory path
        """
        return self.base_screenshots_dir / str(project_id) / process_timestamp
    
    def get_viewport_directory(self, project_id: int, process_timestamp: str, viewport: str) -> Path:
        """
        Get viewport directory path
        
        Args:
            project_id: Project ID
            process_timestamp: Process timestamp
            viewport: Viewport type (desktop, tablet, mobile)
            
        Returns:
            Path: Viewport directory path
        """
        project_dir = self.get_project_directory(project_id, process_timestamp)
        viewport_folder = self.viewport_folders.get(viewport.lower(), viewport.capitalize())
        return project_dir / viewport_folder
    
    def get_screenshot_paths(self, project_id: int, process_timestamp: str, 
                           page_path: str, viewport: str) -> Tuple[Path, Path, Path]:
        """
        Get file paths for production, staging, and diff images
        
        Args:
            project_id: Project ID
            process_timestamp: Process timestamp
            page_path: Page path for slugification
            viewport: Viewport type (desktop, tablet, mobile)
            
        Returns:
            Tuple[Path, Path, Path]: (production_path, staging_path, diff_path)
        """
        viewport_dir = self.get_viewport_directory(project_id, process_timestamp, viewport)
        
        # Create directory if it doesn't exist
        viewport_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename
        page_slug = self.slugify_page_name(page_path)
        
        # Create file paths
        production_path = viewport_dir / f"{page_slug}-production.png"
        staging_path = viewport_dir / f"{page_slug}-staging.png"
        diff_path = viewport_dir / f"{page_slug}-diff.png"
        
        return production_path, staging_path, diff_path
    
    def get_screenshot_path_by_environment(self, project_id: int, process_timestamp: str,
                                         page_path: str, viewport: str, environment: str) -> Path:
        """
        Get file path for a specific environment
        
        Args:
            project_id: Project ID
            process_timestamp: Process timestamp
            page_path: Page path for slugification
            viewport: Viewport type
            environment: Environment (production, staging, diff)
            
        Returns:
            Path: File path for the specified environment
        """
        production_path, staging_path, diff_path = self.get_screenshot_paths(
            project_id, process_timestamp, page_path, viewport
        )
        
        if environment == 'production':
            return production_path
        elif environment == 'staging':
            return staging_path
        elif environment == 'diff':
            return diff_path
        else:
            raise ValueError(f"Invalid environment: {environment}. Must be one of: {self.environments}")
    
    def get_relative_path(self, absolute_path: Path) -> str:
        """
        Get relative path from base screenshots directory
        
        Args:
            absolute_path: Absolute file path
            
        Returns:
            str: Relative path from base screenshots directory (with forward slashes)
        """
        try:
            relative_path = absolute_path.relative_to(self.base_screenshots_dir)
            # Ensure forward slashes for consistency across platforms
            return str(relative_path).replace('\\', '/')
        except ValueError:
            # If path is not relative to base directory, return as-is with forward slashes
            return str(absolute_path).replace('\\', '/')
    
    def get_url_path(self, relative_path: str) -> str:
        """
        Get URL path for accessing a screenshot file
        
        Args:
            relative_path: Relative path from base screenshots directory
            
        Returns:
            str: URL path for accessing the file
        """
        return f"/screenshots/{relative_path}"
    
    def list_process_runs(self, project_id: int) -> list:
        """
        List all process runs for a project (sorted by timestamp, newest first)
        
        Args:
            project_id: Project ID
            
        Returns:
            list: List of process timestamps
        """
        project_base_dir = self.base_screenshots_dir / str(project_id)
        
        if not project_base_dir.exists():
            return []
        
        # Get all directories that match timestamp pattern
        timestamp_pattern = re.compile(r'^\d{8}-\d{6}$')  # YYYYMMDD-HHmmss
        runs = []
        
        for item in project_base_dir.iterdir():
            if item.is_dir() and timestamp_pattern.match(item.name):
                runs.append(item.name)
        
        # Sort by timestamp (newest first)
        runs.sort(reverse=True)
        return runs
    
    def cleanup_project_screenshots(self, project_id: int, keep_latest: int = 0) -> bool:
        """
        Clean up old screenshots for a project
        
        Args:
            project_id: Project ID
            keep_latest: Number of latest runs to keep (0 = delete all)
            
        Returns:
            bool: True if cleanup was successful
        """
        try:
            project_base_dir = self.base_screenshots_dir / str(project_id)
            
            if not project_base_dir.exists():
                return True
            
            if keep_latest == 0:
                # Delete entire project directory
                import shutil
                shutil.rmtree(project_base_dir)
                return True
            
            # Get all runs and keep only the latest ones
            runs = self.list_process_runs(project_id)
            
            if len(runs) <= keep_latest:
                return True  # Nothing to clean up
            
            # Delete older runs
            runs_to_delete = runs[keep_latest:]
            for run_timestamp in runs_to_delete:
                run_dir = project_base_dir / run_timestamp
                if run_dir.exists():
                    import shutil
                    shutil.rmtree(run_dir)
            
            return True
            
        except Exception as e:
            print(f"Error cleaning up screenshots for project {project_id}: {str(e)}")
            return False
    
    def validate_structure(self, project_id: int, process_timestamp: str) -> dict:
        """
        Validate that the directory structure exists and is correct
        
        Args:
            project_id: Project ID
            process_timestamp: Process timestamp
            
        Returns:
            dict: Validation results with status and details
        """
        results = {
            'valid': True,
            'project_dir_exists': False,
            'viewport_dirs': {},
            'errors': []
        }
        
        try:
            # Check project directory
            project_dir = self.get_project_directory(project_id, process_timestamp)
            results['project_dir_exists'] = project_dir.exists()
            
            if not results['project_dir_exists']:
                results['errors'].append(f"Project directory does not exist: {project_dir}")
                results['valid'] = False
            
            # Check viewport directories
            for viewport in self.viewport_folders.keys():
                viewport_dir = self.get_viewport_directory(project_id, process_timestamp, viewport)
                viewport_exists = viewport_dir.exists()
                results['viewport_dirs'][viewport] = viewport_exists
                
                if not viewport_exists:
                    results['errors'].append(f"Viewport directory does not exist: {viewport_dir}")
                    results['valid'] = False
            
        except Exception as e:
            results['valid'] = False
            results['errors'].append(f"Validation error: {str(e)}")
        
        return results
    
    def migrate_old_structure(self, old_base_dir: str = "runs") -> dict:
        """
        Migrate from old structure (runs/{project_id}/{timestamp}/...) to new structure
        
        Args:
            old_base_dir: Old base directory (default: "runs")
            
        Returns:
            dict: Migration results
        """
        results = {
            'success': True,
            'migrated_projects': [],
            'migrated_runs': [],
            'errors': []
        }
        
        try:
            old_base_path = Path(old_base_dir)
            
            if not old_base_path.exists():
                results['errors'].append(f"Old base directory does not exist: {old_base_dir}")
                return results
            
            # Process each project directory
            for project_dir in old_base_path.iterdir():
                if not project_dir.is_dir():
                    continue
                
                try:
                    project_id = int(project_dir.name)
                except ValueError:
                    continue  # Skip non-numeric directories
                
                # Process each run directory
                for run_dir in project_dir.iterdir():
                    if not run_dir.is_dir():
                        continue
                    
                    process_timestamp = run_dir.name
                    
                    # Check if this looks like a timestamp
                    if not re.match(r'^\d{8}-\d{6}$', process_timestamp):
                        continue
                    
                    try:
                        self._migrate_single_run(project_id, process_timestamp, run_dir, results)
                        results['migrated_runs'].append(f"{project_id}/{process_timestamp}")
                    except Exception as e:
                        results['errors'].append(f"Error migrating run {project_id}/{process_timestamp}: {str(e)}")
                        results['success'] = False
                
                if project_id not in results['migrated_projects']:
                    results['migrated_projects'].append(project_id)
        
        except Exception as e:
            results['success'] = False
            results['errors'].append(f"Migration error: {str(e)}")
        
        return results
    
    def _migrate_single_run(self, project_id: int, process_timestamp: str, old_run_dir: Path, results: dict):
        """
        Migrate a single run from old structure to new structure
        
        Args:
            project_id: Project ID
            process_timestamp: Process timestamp
            old_run_dir: Old run directory path
            results: Results dictionary to update
        """
        import shutil
        
        # Old structure: runs/{project_id}/{timestamp}/screenshots/{environment}/{viewport}/
        # New structure: screenshots/{project_id}/{timestamp}/{viewport}/
        
        old_screenshots_dir = old_run_dir / "screenshots"
        if not old_screenshots_dir.exists():
            return
        
        # Process each environment directory
        for env_dir in old_screenshots_dir.iterdir():
            if not env_dir.is_dir():
                continue
            
            environment = env_dir.name  # staging or production
            if environment not in ['staging', 'production']:
                continue
            
            # Process each viewport directory
            for viewport_dir in env_dir.iterdir():
                if not viewport_dir.is_dir():
                    continue
                
                viewport = viewport_dir.name  # desktop, tablet, mobile
                if viewport not in self.viewport_folders:
                    continue
                
                # Process each screenshot file
                for screenshot_file in viewport_dir.iterdir():
                    if not screenshot_file.is_file() or not screenshot_file.name.endswith('.png'):
                        continue
                    
                    # Extract page name from filename
                    page_name = screenshot_file.stem
                    
                    # Get new file path
                    new_file_path = self.get_screenshot_path_by_environment(
                        project_id, process_timestamp, page_name, viewport, environment
                    )
                    
                    # Copy file to new location
                    new_file_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(screenshot_file, new_file_path)
        
        # Also migrate diff files if they exist
        old_diffs_dir = old_run_dir / "diffs"
        if old_diffs_dir.exists():
            for viewport_dir in old_diffs_dir.iterdir():
                if not viewport_dir.is_dir():
                    continue
                
                viewport = viewport_dir.name
                if viewport not in self.viewport_folders:
                    continue
                
                for diff_file in viewport_dir.iterdir():
                    if not diff_file.is_file() or not diff_file.name.endswith('.png'):
                        continue
                    
                    # Extract page name from diff filename (remove _diff suffix)
                    page_name = diff_file.stem.replace('_diff', '')
                    
                    # Get new diff file path
                    new_diff_path = self.get_screenshot_path_by_environment(
                        project_id, process_timestamp, page_name, viewport, 'diff'
                    )
                    
                    # Copy diff file to new location
                    new_diff_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(diff_file, new_diff_path)