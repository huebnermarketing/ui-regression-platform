"""
Backfill script to migrate existing files to canonical PathResolver format
Renames old files to canonical naming convention and updates database
"""

import os
import sys
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Add the parent directory to the path so we can import from the project
sys.path.append(str(Path(__file__).parent.parent))

from utils.path_resolver import PathResolver
from models import db
from models.project import Project, ProjectPage
from app import app


class CanonicalPathBackfill:
    """Backfill existing files to canonical PathResolver format"""
    
    def __init__(self, dry_run: bool = True):
        """
        Initialize backfill processor
        
        Args:
            dry_run: If True, only log what would be done without making changes
        """
        self.dry_run = dry_run
        self.path_resolver = PathResolver()
        self.stats = {
            'files_found': 0,
            'files_migrated': 0,
            'files_failed': 0,
            'directories_created': 0,
            'database_updates': 0
        }
        
        print(f"Backfill initialized (dry_run={dry_run})")
    
    def find_legacy_files(self) -> List[Dict]:
        """
        Find all legacy screenshot and diff files
        
        Returns:
            List[Dict]: List of file info dicts
        """
        legacy_files = []
        base_dirs = ['screenshots', 'runs', 'diffs']
        
        for base_dir in base_dirs:
            base_path = Path(base_dir)
            if not base_path.exists():
                continue
            
            print(f"Scanning {base_dir}/ for legacy files...")
            
            # Recursively find all image files
            for file_path in base_path.rglob('*.png'):
                if file_path.is_file():
                    file_info = self._analyze_legacy_file(file_path, base_dir)
                    if file_info:
                        legacy_files.append(file_info)
                        self.stats['files_found'] += 1
            
            # Also check for jpg files
            for file_path in base_path.rglob('*.jpg'):
                if file_path.is_file():
                    file_info = self._analyze_legacy_file(file_path, base_dir)
                    if file_info:
                        legacy_files.append(file_info)
                        self.stats['files_found'] += 1
        
        print(f"Found {len(legacy_files)} legacy files")
        return legacy_files
    
    def _analyze_legacy_file(self, file_path: Path, base_dir: str) -> Optional[Dict]:
        """
        Analyze a legacy file to extract components
        
        Args:
            file_path: Path to the legacy file
            base_dir: Base directory (screenshots, runs, diffs)
            
        Returns:
            Optional[Dict]: File info dict or None if not parseable
        """
        try:
            # Get relative path from base directory
            rel_path = file_path.relative_to(Path(base_dir))
            path_parts = rel_path.parts
            
            # Try different legacy patterns
            file_info = None
            
            if base_dir == 'screenshots':
                file_info = self._parse_screenshots_path(path_parts, file_path)
            elif base_dir == 'runs':
                file_info = self._parse_runs_path(path_parts, file_path)
            elif base_dir == 'diffs':
                file_info = self._parse_diffs_path(path_parts, file_path)
            
            if file_info:
                file_info['original_path'] = file_path
                file_info['base_dir'] = base_dir
            
            return file_info
            
        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")
            return None
    
    def _parse_screenshots_path(self, path_parts: Tuple, file_path: Path) -> Optional[Dict]:
        """Parse screenshots directory structure"""
        
        # Pattern 1: screenshots/{project_id}/{run_id}/{viewport}/{filename}
        if len(path_parts) == 4:
            project_id, run_id, viewport, filename = path_parts
            
            # Validate run_id format (YYYYMMDD-HHmmss)
            if re.match(r'^\d{8}-\d{6}$', run_id):
                parsed = self._parse_filename(filename)
                if parsed:
                    return {
                        'project_id': project_id,
                        'run_id': run_id,
                        'viewport': viewport,
                        'page_slug': parsed['page_slug'],
                        'environment': parsed['environment'],
                        'extension': parsed['extension'],
                        'pattern': 'new_structure'
                    }
        
        # Pattern 2: screenshots/{project_id}/{viewport}/{environment}/{filename}
        elif len(path_parts) == 4:
            project_id, viewport, environment, filename = path_parts
            
            if environment in ['staging', 'production']:
                parsed = self._parse_filename(filename)
                if parsed:
                    return {
                        'project_id': project_id,
                        'run_id': None,  # Will need to generate
                        'viewport': viewport,
                        'page_slug': parsed['page_slug'],
                        'environment': environment,
                        'extension': parsed['extension'],
                        'pattern': 'legacy_viewport_env'
                    }
        
        # Pattern 3: screenshots/{project_id}/{environment}/{filename}
        elif len(path_parts) == 3:
            project_id, environment, filename = path_parts
            
            if environment in ['staging', 'production']:
                parsed = self._parse_filename(filename)
                if parsed:
                    return {
                        'project_id': project_id,
                        'run_id': None,  # Will need to generate
                        'viewport': 'desktop',  # Default
                        'page_slug': parsed['page_slug'],
                        'environment': environment,
                        'extension': parsed['extension'],
                        'pattern': 'legacy_env_only'
                    }
        
        return None
    
    def _parse_runs_path(self, path_parts: Tuple, file_path: Path) -> Optional[Dict]:
        """Parse runs directory structure"""
        
        # Pattern: runs/{project_id}/{run_id}/...
        if len(path_parts) >= 3:
            project_id = path_parts[0]
            run_id = path_parts[1]
            
            # Validate run_id format
            if re.match(r'^\d{8}-\d{6}$', run_id):
                # Extract viewport and filename from remaining parts
                remaining = path_parts[2:]
                
                if len(remaining) >= 2:
                    # Could be diffs/viewport/filename or screenshots/env/viewport/filename
                    if remaining[0] == 'diffs' and len(remaining) == 3:
                        viewport, filename = remaining[1], remaining[2]
                        parsed = self._parse_filename(filename)
                        if parsed:
                            return {
                                'project_id': project_id,
                                'run_id': run_id,
                                'viewport': viewport,
                                'page_slug': parsed['page_slug'],
                                'environment': 'diff',
                                'extension': parsed['extension'],
                                'pattern': 'runs_diffs'
                            }
                    
                    elif remaining[0] == 'screenshots' and len(remaining) == 4:
                        environment, viewport, filename = remaining[1], remaining[2], remaining[3]
                        parsed = self._parse_filename(filename)
                        if parsed:
                            return {
                                'project_id': project_id,
                                'run_id': run_id,
                                'viewport': viewport,
                                'page_slug': parsed['page_slug'],
                                'environment': environment,
                                'extension': parsed['extension'],
                                'pattern': 'runs_screenshots'
                            }
        
        return None
    
    def _parse_diffs_path(self, path_parts: Tuple, file_path: Path) -> Optional[Dict]:
        """Parse diffs directory structure"""
        
        # Pattern: diffs/{project_id}/{filename}
        if len(path_parts) == 2:
            project_id, filename = path_parts
            parsed = self._parse_filename(filename)
            if parsed:
                return {
                    'project_id': project_id,
                    'run_id': None,  # Will need to generate
                    'viewport': 'desktop',  # Default
                    'page_slug': parsed['page_slug'],
                    'environment': 'diff',
                    'extension': parsed['extension'],
                    'pattern': 'legacy_diffs'
                }
        
        return None
    
    def _parse_filename(self, filename: str) -> Optional[Dict]:
        """
        Parse filename to extract page_slug and environment
        
        Args:
            filename: Filename to parse
            
        Returns:
            Optional[Dict]: Parsed components or None
        """
        # Remove extension
        name_parts = filename.rsplit('.', 1)
        if len(name_parts) != 2:
            return None
        
        name_without_ext = name_parts[0]
        extension = name_parts[1].lower()
        
        # Try different patterns
        patterns = [
            r'^(.+)[-_](staging|production|diff)$',  # page-env or page_env
            r'^(.+)[-_]diff$',  # page-diff or page_diff
            r'^(.+)$'  # just page name
        ]
        
        for pattern in patterns:
            match = re.match(pattern, name_without_ext)
            if match:
                if len(match.groups()) == 2:
                    page_slug, environment = match.groups()
                else:
                    page_slug = match.group(1)
                    environment = 'unknown'
                
                # Clean up page_slug
                page_slug = re.sub(r'[^a-z0-9_-]', '_', page_slug.lower())
                page_slug = re.sub(r'_+', '_', page_slug).strip('_')
                
                if not page_slug:
                    page_slug = 'page'
                
                return {
                    'page_slug': page_slug,
                    'environment': environment.lower(),
                    'extension': extension
                }
        
        return None
    
    def migrate_files(self, legacy_files: List[Dict]) -> None:
        """
        Migrate legacy files to canonical format
        
        Args:
            legacy_files: List of legacy file info dicts
        """
        print(f"\nStarting migration of {len(legacy_files)} files...")
        
        # Group files by project and run for better organization
        grouped_files = self._group_files_by_run(legacy_files)
        
        for (project_id, run_id), files in grouped_files.items():
            print(f"\nProcessing project {project_id}, run {run_id} ({len(files)} files)")
            
            if not self.dry_run:
                # Create directories for this run
                try:
                    self.path_resolver.create_directories(int(project_id), run_id)
                    self.stats['directories_created'] += 1
                except Exception as e:
                    print(f"Error creating directories: {e}")
                    continue
            
            # Migrate each file
            for file_info in files:
                self._migrate_single_file(file_info)
    
    def _group_files_by_run(self, legacy_files: List[Dict]) -> Dict[Tuple[str, str], List[Dict]]:
        """Group files by project_id and run_id"""
        grouped = {}
        
        for file_info in legacy_files:
            project_id = file_info['project_id']
            run_id = file_info['run_id']
            
            # Generate run_id if missing
            if not run_id:
                run_id = self.path_resolver.generate_run_id()
                file_info['run_id'] = run_id
            
            key = (project_id, run_id)
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(file_info)
        
        return grouped
    
    def _migrate_single_file(self, file_info: Dict) -> bool:
        """
        Migrate a single file to canonical format
        
        Args:
            file_info: File info dict
            
        Returns:
            bool: True if successful
        """
        try:
            # Get canonical path
            canonical_path = self.path_resolver.get_canonical_path(
                int(file_info['project_id']),
                file_info['run_id'],
                file_info['viewport'].lower(),
                file_info['page_slug'],
                file_info['environment']
            )
            
            original_path = file_info['original_path']
            
            print(f"  {original_path} -> {canonical_path}")
            
            if not self.dry_run:
                # Check if canonical path already exists
                if canonical_path.exists():
                    print(f"    WARNING: Canonical path already exists, skipping")
                    return False
                
                # Copy file to canonical location
                import shutil
                canonical_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(original_path, canonical_path)
                
                # Verify copy was successful
                if canonical_path.exists():
                    self.stats['files_migrated'] += 1
                    print(f"    SUCCESS: File migrated")
                    return True
                else:
                    self.stats['files_failed'] += 1
                    print(f"    ERROR: Copy failed")
                    return False
            else:
                print(f"    DRY RUN: Would migrate file")
                return True
                
        except Exception as e:
            self.stats['files_failed'] += 1
            print(f"    ERROR: {e}")
            return False
    
    def update_database(self) -> None:
        """Update database records to use component storage"""
        print("\nUpdating database records...")
        
        with app.app_context():
            # Get all project pages
            pages = ProjectPage.query.all()
            
            for page in pages:
                try:
                    # Generate page_slug if not set
                    if not page.page_slug:
                        page.page_slug = self.path_resolver.slugify_page_path(page.path)
                    
                    # Set default run_id if not set
                    if not page.current_run_id:
                        page.current_run_id = self.path_resolver.generate_run_id()
                    
                    # Set default status values
                    for viewport in self.path_resolver.viewports:
                        if not getattr(page, f'screenshot_status_{viewport}', None):
                            setattr(page, f'screenshot_status_{viewport}', 'pending')
                        if not getattr(page, f'diff_status_{viewport}', None):
                            setattr(page, f'diff_status_{viewport}', 'pending')
                    
                    if not page.find_diff_status:
                        page.find_diff_status = 'pending'
                    
                    if not self.dry_run:
                        db.session.add(page)
                        self.stats['database_updates'] += 1
                    else:
                        print(f"  DRY RUN: Would update page {page.id} ({page.path})")
                
                except Exception as e:
                    print(f"Error updating page {page.id}: {e}")
            
            if not self.dry_run:
                db.session.commit()
                print(f"Updated {self.stats['database_updates']} database records")
    
    def print_stats(self) -> None:
        """Print migration statistics"""
        print("\n" + "="*50)
        print("MIGRATION STATISTICS")
        print("="*50)
        print(f"Files found:        {self.stats['files_found']}")
        print(f"Files migrated:     {self.stats['files_migrated']}")
        print(f"Files failed:       {self.stats['files_failed']}")
        print(f"Directories created: {self.stats['directories_created']}")
        print(f"Database updates:   {self.stats['database_updates']}")
        print(f"Mode:               {'DRY RUN' if self.dry_run else 'LIVE'}")
        print("="*50)


def main():
    """Main backfill function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Backfill canonical paths')
    parser.add_argument('--live', action='store_true', 
                       help='Run in live mode (default is dry run)')
    parser.add_argument('--database-only', action='store_true',
                       help='Only update database, skip file migration')
    
    args = parser.parse_args()
    
    dry_run = not args.live
    
    print("PathResolver Canonical Path Backfill")
    print("="*50)
    
    backfill = CanonicalPathBackfill(dry_run=dry_run)
    
    if not args.database_only:
        # Find and migrate files
        legacy_files = backfill.find_legacy_files()
        if legacy_files:
            backfill.migrate_files(legacy_files)
    
    # Update database
    backfill.update_database()
    
    # Print statistics
    backfill.print_stats()
    
    if dry_run:
        print("\nThis was a DRY RUN. Use --live to actually migrate files.")


if __name__ == '__main__':
    main()