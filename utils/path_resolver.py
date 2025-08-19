"""
PathResolver - Single source of truth for all screenshot/diff file paths
Implements strict naming rules and canonical path resolution
"""

import os
import re
import hashlib
from pathlib import Path
from typing import Tuple, Optional, Dict, List
from datetime import datetime
import pytz


class PathResolver:
    """
    Centralized path resolver for all screenshot and diff files.
    
    Canonical Structure:
    /{project_id}/{run_id}/{viewport}/{page_slug}-{environment}.png
    
    Where:
    - project_id: lowercase string/int
    - run_id: lowercase timestamp (YYYYMMDD-HHmmss)
    - viewport: lowercase (desktop, tablet, mobile)
    - page_slug: slugified page path (lowercase, underscores)
    - environment: lowercase (staging, production, diff)
    """
    
    def __init__(self, base_dir: str = "screenshots"):
        """
        Initialize PathResolver
        
        Args:
            base_dir: Base directory for all assets (default: "screenshots")
        """
        self.base_dir = Path(base_dir)
        self.ist_timezone = pytz.timezone('Asia/Kolkata')
        
        # Canonical viewport names (lowercase)
        self.viewports = ['desktop', 'tablet', 'mobile']
        
        # Canonical environment names (lowercase)
        self.environments = ['staging', 'production', 'diff']
        
        # Legacy viewport mapping for fallback
        self.legacy_viewport_map = {
            'Desktop': 'desktop',
            'Tablet': 'tablet',
            'Mobile': 'mobile',
            'DESKTOP': 'desktop',
            'TABLET': 'tablet',
            'MOBILE': 'mobile'
        }
        
        # Legacy filename patterns for fallback
        self.legacy_patterns = [
            r'(.+)[-_](staging|production|diff)\.(png|jpg|jpeg)',
            r'(.+)[-_](diff)\.(png|jpg|jpeg)',
            r'(.+)\.(png|jpg|jpeg)'
        ]
        
        # Ensure base directory exists
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
    def normalize_component(self, component: str) -> str:
        """
        Normalize any component to lowercase
        
        Args:
            component: Component to normalize
            
        Returns:
            str: Normalized lowercase component
        """
        return str(component).lower().strip()
    
    def slugify_page_path(self, page_path: str) -> str:
        """
        Convert page path to canonical slug format
        
        Rules:
        - Lowercase everything
        - Replace /home/blog/ → home_blog
        - Replace special chars with underscores
        - Limit length for filesystem safety
        
        Args:
            page_path: Original page path
            
        Returns:
            str: Canonical page slug
        """
        # Remove leading/trailing slashes
        path = page_path.strip('/')
        
        # If empty path (root), use 'home'
        if not path:
            return 'home'
        
        # Convert to lowercase
        path = path.lower()
        
        # Replace slashes with underscores
        slug = path.replace('/', '_')
        
        # Replace special characters with underscores
        slug = re.sub(r'[^a-z0-9_-]', '_', slug)
        
        # Replace multiple underscores with single underscore
        slug = re.sub(r'_+', '_', slug)
        
        # Remove leading/trailing underscores
        slug = slug.strip('_')
        
        # Ensure it's not empty
        if not slug:
            return 'page'
        
        # Limit filename length (reserve space for suffix and extension)
        max_length = 200
        if len(slug) > max_length:
            # Truncate and add hash for uniqueness
            hash_suffix = hashlib.md5(page_path.encode()).hexdigest()[:8]
            slug = slug[:max_length-9] + '_' + hash_suffix
        
        return slug
    
    def generate_run_id(self) -> str:
        """
        Generate canonical run ID in IST timezone
        Format: YYYYMMDD-HHmmss (lowercase, filesystem-safe)
        
        Returns:
            str: Run ID like "20250813-143022"
        """
        ist_now = datetime.now(self.ist_timezone)
        return ist_now.strftime('%Y%m%d-%H%M%S').lower()
    
    def get_canonical_filename(self, page_slug: str, environment: str) -> str:
        """
        Generate canonical filename
        Format: {page_slug}-{environment}.png
        
        Args:
            page_slug: Slugified page path
            environment: Environment (staging, production, diff)
            
        Returns:
            str: Canonical filename
        """
        env = self.normalize_component(environment)
        return f"{page_slug}-{env}.png"
    
    def get_canonical_path(self, project_id: int, run_id: str, viewport: str, 
                          page_slug: str, environment: str) -> Path:
        """
        Generate canonical file path
        Format: /{project_id}/{run_id}/{viewport}/{page_slug}-{environment}.png
        
        Args:
            project_id: Project ID
            run_id: Run ID
            viewport: Viewport type
            page_slug: Slugified page path
            environment: Environment
            
        Returns:
            Path: Canonical file path
        """
        # Normalize all components
        proj_id = self.normalize_component(project_id)
        run_id = self.normalize_component(run_id)
        viewport = self.normalize_component(viewport)
        env = self.normalize_component(environment)
        
        # Validate components
        if viewport not in self.viewports:
            raise ValueError(f"Invalid viewport: {viewport}. Must be one of: {self.viewports}")
        if env not in self.environments:
            raise ValueError(f"Invalid environment: {env}. Must be one of: {self.environments}")
        
        filename = self.get_canonical_filename(page_slug, env)
        
        return self.base_dir / proj_id / run_id / viewport / filename
    
    def get_all_paths_for_page(self, project_id: int, run_id: str, page_path: str) -> Dict[str, Dict[str, Path]]:
        """
        Get all canonical paths for a page across all viewports and environments
        
        Args:
            project_id: Project ID
            run_id: Run ID
            page_path: Original page path
            
        Returns:
            Dict: Nested dict {viewport: {environment: Path}}
        """
        page_slug = self.slugify_page_path(page_path)
        paths = {}
        
        for viewport in self.viewports:
            paths[viewport] = {}
            for environment in self.environments:
                paths[viewport][environment] = self.get_canonical_path(
                    project_id, run_id, viewport, page_slug, environment
                )
        
        return paths
    
    def resolve_file(self, project_id: int, run_id: str, viewport: str, 
                    page_slug: str, environment: str) -> Optional[Path]:
        """
        Resolve file with fallback to legacy naming patterns
        
        Strategy:
        1. Try canonical path first
        2. Try legacy patterns with case variations
        3. Return None if not found
        
        Args:
            project_id: Project ID
            run_id: Run ID
            viewport: Viewport type
            page_slug: Page slug
            environment: Environment
            
        Returns:
            Optional[Path]: Resolved file path or None
        """
        # Try canonical path first
        try:
            canonical_path = self.get_canonical_path(
                project_id, run_id, viewport, page_slug, environment
            )
            if canonical_path.exists():
                return canonical_path
        except ValueError:
            # Invalid components, continue to fallback
            pass
        
        # Fallback to legacy patterns
        return self._resolve_legacy_file(project_id, run_id, viewport, page_slug, environment)
    
    def _resolve_legacy_file(self, project_id: int, run_id: str, viewport: str, 
                           page_slug: str, environment: str) -> Optional[Path]:
        """
        Resolve file using legacy naming patterns
        
        Args:
            project_id: Project ID
            run_id: Run ID
            viewport: Viewport type
            page_slug: Page slug
            environment: Environment
            
        Returns:
            Optional[Path]: Resolved legacy file path or None
        """
        # Normalize inputs
        proj_id = str(project_id).lower()
        run_id = str(run_id).lower()
        env = environment.lower()
        
        # Try different viewport case variations
        viewport_variations = [
            viewport.lower(),
            viewport.capitalize(),
            viewport.upper(),
            self.legacy_viewport_map.get(viewport, viewport)
        ]
        
        # Remove duplicates while preserving order
        seen = set()
        viewport_variations = [x for x in viewport_variations if not (x in seen or seen.add(x))]
        
        # Try different filename patterns with more variations
        filename_patterns = [
            f"{page_slug}-{env}.png",
            f"{page_slug}_{env}.png",
            f"{page_slug}-{env}.jpg",
            f"{page_slug}_{env}.jpg",
            f"{page_slug}.png",
            f"{page_slug}.jpg"
        ]
        
        # Add patterns for partial matches (in case of longer filenames)
        filename_patterns.extend([
            f"*{page_slug}*{env}*.png",
            f"*{page_slug}*{env}*.jpg",
            f"*{page_slug}*.png",
            f"*{page_slug}*.jpg"
        ])
        
        # Try different directory structures
        base_paths = [
            # New structure: /screenshots/{project_id}/{run_id}/{viewport}/
            self.base_dir / proj_id / run_id,
            # Legacy structure: /screenshots/{project_id}/{viewport}/
            self.base_dir / proj_id,
            # Very old structure: /screenshots/{project_id}/
            self.base_dir / proj_id,
            # Alternative base directories
            Path("runs") / proj_id / run_id,
            Path("diffs") / proj_id
        ]
        
        for base_path in base_paths:
            for viewport_var in viewport_variations:
                viewport_dir = base_path / viewport_var
                if viewport_dir.exists():
                    for filename in filename_patterns:
                        if '*' in filename:
                            # Use glob for wildcard patterns
                            import glob
                            pattern = str(viewport_dir / filename)
                            matches = glob.glob(pattern)
                            if matches:
                                return Path(matches[0])  # Return first match
                        else:
                            file_path = viewport_dir / filename
                            if file_path.exists():
                                return file_path
                
                # Also try without viewport subdirectory
                for filename in filename_patterns:
                    if '*' in filename:
                        # Use glob for wildcard patterns
                        import glob
                        pattern = str(base_path / filename)
                        matches = glob.glob(pattern)
                        if matches:
                            return Path(matches[0])  # Return first match
                    else:
                        file_path = base_path / filename
                        if file_path.exists():
                            return file_path
        
        return None
    
    def create_directories(self, project_id: int, run_id: str) -> None:
        """
        Create all necessary directories for a project run
        
        Args:
            project_id: Project ID
            run_id: Run ID
        """
        proj_id = self.normalize_component(project_id)
        run_id = self.normalize_component(run_id)
        
        for viewport in self.viewports:
            viewport_dir = self.base_dir / proj_id / run_id / viewport
            viewport_dir.mkdir(parents=True, exist_ok=True)
    
    def get_url_path(self, project_id: int, run_id: str, viewport: str, 
                    page_slug: str, environment: str) -> str:
        """
        Generate URL path for accessing a file
        
        Args:
            project_id: Project ID
            run_id: Run ID
            viewport: Viewport type
            page_slug: Page slug
            environment: Environment
            
        Returns:
            str: URL path for the resolver route
        """
        # Normalize components
        proj_id = self.normalize_component(project_id)
        run_id = self.normalize_component(run_id)
        viewport = self.normalize_component(viewport)
        env = self.normalize_component(environment)
        page_slug = page_slug.lower()
        
        filename = self.get_canonical_filename(page_slug, env)
        
        return f"/assets/runs/{proj_id}/{run_id}/{viewport}/{filename}"
    
    def parse_url_path(self, url_path: str) -> Optional[Dict[str, str]]:
        """
        Parse URL path to extract components
        
        Args:
            url_path: URL path like "/assets/runs/123/20250813-143022/desktop/home-staging.png"
            
        Returns:
            Optional[Dict]: Components dict or None if invalid
        """
        # Remove leading slash and split
        path = url_path.lstrip('/')
        parts = path.split('/')
        
        # Expected format: assets/runs/{project_id}/{run_id}/{viewport}/{filename}
        if len(parts) != 6 or parts[0] != 'assets' or parts[1] != 'runs':
            return None
        
        project_id = parts[2]
        run_id = parts[3]
        viewport = parts[4]
        filename = parts[5]
        
        # Parse filename to extract page_slug and environment
        # Expected format: {page_slug}-{environment}.{ext}
        name_parts = filename.rsplit('.', 1)
        if len(name_parts) != 2:
            return None
        
        name_without_ext = name_parts[0]
        extension = name_parts[1]
        
        # Split by last dash to get environment
        if '-' not in name_without_ext:
            return None
        
        page_slug, environment = name_without_ext.rsplit('-', 1)
        
        return {
            'project_id': project_id,
            'run_id': run_id,
            'viewport': viewport,
            'page_slug': page_slug,
            'environment': environment,
            'extension': extension
        }
    
    def list_project_runs(self, project_id: int) -> List[str]:
        """
        List all run IDs for a project (sorted newest first)
        
        Args:
            project_id: Project ID
            
        Returns:
            List[str]: List of run IDs
        """
        proj_id = self.normalize_component(project_id)
        project_dir = self.base_dir / proj_id
        
        if not project_dir.exists():
            return []
        
        # Get all directories that match run ID pattern
        run_pattern = re.compile(r'^\d{8}-\d{6}$')
        runs = []
        
        for item in project_dir.iterdir():
            if item.is_dir() and run_pattern.match(item.name):
                runs.append(item.name)
        
        # Sort by timestamp (newest first)
        runs.sort(reverse=True)
        return runs
    
    def cleanup_old_runs(self, project_id: int, keep_latest: int = 5) -> int:
        """
        Clean up old runs for a project
        
        Args:
            project_id: Project ID
            keep_latest: Number of latest runs to keep
            
        Returns:
            int: Number of runs deleted
        """
        runs = self.list_project_runs(project_id)
        
        if len(runs) <= keep_latest:
            return 0
        
        proj_id = self.normalize_component(project_id)
        project_dir = self.base_dir / proj_id
        
        runs_to_delete = runs[keep_latest:]
        deleted_count = 0
        
        for run_id in runs_to_delete:
            run_dir = project_dir / run_id
            if run_dir.exists():
                import shutil
                shutil.rmtree(run_dir)
                deleted_count += 1
        
        return deleted_count
    
    def migrate_legacy_file(self, legacy_path: Path, project_id: int, run_id: str, 
                           viewport: str, page_slug: str, environment: str) -> bool:
        """
        Migrate a legacy file to canonical location
        
        Args:
            legacy_path: Current file location
            project_id: Project ID
            run_id: Run ID
            viewport: Viewport type
            page_slug: Page slug
            environment: Environment
            
        Returns:
            bool: True if migration successful
        """
        try:
            canonical_path = self.get_canonical_path(
                project_id, run_id, viewport, page_slug, environment
            )
            
            # Create directory if needed
            canonical_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy file to canonical location
            import shutil
            shutil.copy2(legacy_path, canonical_path)
            
            return True
            
        except Exception as e:
            print(f"Error migrating {legacy_path} to canonical location: {e}")
            return False
    
    def get_placeholder_path(self, placeholder_type: str = "not_found") -> Path:
        """
        Get path to placeholder image
        
        Args:
            placeholder_type: Type of placeholder (not_found, no_baseline, processing)
            
        Returns:
            Path: Path to placeholder image
        """
        placeholder_dir = Path("static") / "placeholders"
        placeholder_map = {
            "not_found": "not_found.png",
            "no_baseline": "no_baseline.png", 
            "processing": "processing.png",
            "error": "error.png"
        }
        
        filename = placeholder_map.get(placeholder_type, "not_found.png")
        return placeholder_dir / filename