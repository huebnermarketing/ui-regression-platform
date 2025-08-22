"""
Screenshot capture service using Playwright
Enhanced with PathResolver for consistent file management
"""

import os
import re
import asyncio
import logging
from pathlib import Path
from typing import Tuple, Optional
from urllib.parse import urlparse
from playwright.async_api import async_playwright, Browser, Page
from models import db
from models.project import ProjectPage
from .dynamic_content_handler import DynamicContentHandler
from utils.path_resolver import PathResolver

class ScreenshotService:
    def __init__(self, base_screenshot_dir: str = "screenshots"):
        """
        Initialize screenshot service with PathResolver
        
        Args:
            base_screenshot_dir (str): Base directory for storing screenshots
        """
        self.base_screenshot_dir = Path(base_screenshot_dir)
        self.logger = logging.getLogger(__name__)
        self.path_resolver = PathResolver(base_screenshot_dir)
        
        # Viewport configurations
        self.viewports = {
            'desktop': {'width': 1920, 'height': 1080},
            'tablet': {'width': 768, 'height': 1024},
            'mobile': {'width': 375, 'height': 667}
        }
        
        # Configuration options with defaults
        self.config = {
            'settling_delay': int(os.getenv('SCREENSHOT_SETTLING_DELAY', '2500')),  # 1-3 seconds
            'network_idle_window': int(os.getenv('SCREENSHOT_NETWORK_IDLE_WINDOW', '2000')),  # 2 seconds
            'scroll_step_pause': int(os.getenv('SCREENSHOT_SCROLL_STEP_PAUSE', '150')),  # 150ms per viewport
            'scroll_step_distance': int(os.getenv('SCREENSHOT_SCROLL_STEP_DISTANCE', '100')),  # pixels per step
            'device_pixel_ratio': float(os.getenv('SCREENSHOT_DEVICE_PIXEL_RATIO', '1.0')),  # DPR for quality
            'wait_for_dynamic': os.getenv('SCREENSHOT_WAIT_FOR_DYNAMIC', 'true').lower() == 'true',
            'debug_mode': os.getenv('SCREENSHOT_DEBUG_MODE', 'false').lower() == 'true'
        }
        
        # Initialize enhanced dynamic content handler
        self.dynamic_handler = DynamicContentHandler({
            'max_wait_time': int(os.getenv('SCREENSHOT_MAX_WAIT_TIME', '30000')),
            'network_idle_timeout': self.config['network_idle_window'],
            'layout_stability_timeout': int(os.getenv('SCREENSHOT_LAYOUT_STABILITY_TIMEOUT', '2000')),
            'animation_settle_timeout': self.config['settling_delay'],
            'scroll_step_size': self.config['scroll_step_distance'],
            'scroll_step_delay': self.config['scroll_step_pause'],
            'debug_mode': self.config['debug_mode']
        })
        
        # Ensure base directory exists
        self.base_screenshot_dir.mkdir(exist_ok=True)
    
    def slugify_path(self, path: str) -> str:
        """
        Convert a URL path to a safe filename
        
        Args:
            path (str): URL path to slugify
            
        Returns:
            str: Slugified filename (limited to safe length)
        """
        # Remove leading/trailing slashes and replace with underscores
        path = path.strip('/')
        
        # If empty path (root), use 'home'
        if not path:
            return 'home'
        
        # Replace slashes and special characters with underscores
        slug = re.sub(r'[/\\:*?"<>|]', '_', path)
        
        # Replace multiple underscores with single underscore
        slug = re.sub(r'_+', '_', slug)
        
        # Remove leading/trailing underscores
        slug = slug.strip('_')
        
        # Ensure it's not empty
        if not slug:
            return 'page'
        
        # Limit filename length to prevent filesystem issues (Windows has 260 char limit)
        # Reserve 4 characters for .png extension
        max_length = 250  # Leave some buffer for full path
        
        if len(slug) > max_length:
            # Truncate and add hash for uniqueness
            import hashlib
            # Take first portion and append hash of full path
            hash_suffix = hashlib.md5(path.encode()).hexdigest()[:8]
            slug = slug[:max_length-9] + '_' + hash_suffix  # -9 for underscore and 8 char hash
        
        return slug
    
    def get_screenshot_paths(self, project_id: int, page_path: str, viewport: str,
                           run_id: str) -> Tuple[Path, Path]:
        """
        Get canonical file paths for staging and production screenshots
        
        Args:
            project_id (int): Project ID
            page_path (str): Page path
            viewport (str): Viewport type (desktop, tablet, mobile)
            run_id (str): Run ID timestamp
            
        Returns:
            Tuple[Path, Path]: (staging_path, production_path)
        """
        page_slug = self.path_resolver.slugify_page_path(page_path)
        
        staging_path = self.path_resolver.get_canonical_path(
            project_id, run_id, viewport, page_slug, 'staging'
        )
        production_path = self.path_resolver.get_canonical_path(
            project_id, run_id, viewport, page_slug, 'production'
        )
        
        return (staging_path, production_path)
    
    async def capture_screenshot(self, url: str, output_path: Path, viewport: str = 'desktop',
                               timeout: int = 30000, wait_for_dynamic: bool = None) -> bool:
        """
        Capture a full-page screenshot of a URL with enhanced dynamic content handling
        
        Args:
            url (str): URL to capture
            output_path (Path): Path to save the screenshot
            viewport (str): Viewport type (desktop, tablet, mobile)
            timeout (int): Page load timeout in milliseconds
            wait_for_dynamic (bool): Whether to wait for dynamic content
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            async with async_playwright() as p:
                # Launch browser in headless mode with additional args for stability
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-accelerated-2d-canvas',
                        '--no-first-run',
                        '--no-zygote',
                        '--disable-gpu'
                    ]
                )
                
                try:
                    # Create a new page
                    page = await browser.new_page()
                    
                    # Set viewport size based on viewport type
                    viewport_config = self.viewports.get(viewport, self.viewports['desktop'])
                    await page.set_viewport_size(viewport_config)
                    
                    # Set user agent for mobile viewport
                    if viewport == 'mobile':
                        await page.set_extra_http_headers({
                            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) '
                                         'AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Mobile/15E148 Safari/604.1'
                        })
                    elif viewport == 'tablet':
                        await page.set_extra_http_headers({
                            'User-Agent': 'Mozilla/5.0 (iPad; CPU OS 14_7_1 like Mac OS X) '
                                         'AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Mobile/15E148 Safari/604.1'
                        })
                    
                    # Navigate to the URL
                    self.logger.info(f"Navigating to: {url} ({viewport} viewport)")
                    await page.goto(url, timeout=timeout, wait_until="networkidle")
                    
                    # Use config default if wait_for_dynamic is None
                    should_wait_for_dynamic = wait_for_dynamic if wait_for_dynamic is not None else self.config['wait_for_dynamic']
                    
                    if should_wait_for_dynamic:
                        # Enhanced dynamic content handling using new handler
                        load_results = await self.dynamic_handler.wait_for_complete_page_load(page)
                        
                        if not load_results['success']:
                            self.logger.warning(f"Dynamic content loading had issues: {load_results.get('warnings', [])}")
                            if load_results.get('errors'):
                                self.logger.error(f"Dynamic content loading errors: {load_results['errors']}")
                        else:
                            self.logger.info(f"Enhanced dynamic content loading completed successfully in {load_results['total_wait_time']:.0f}ms")
                            self.logger.info(f"Steps completed: {', '.join(load_results['steps_completed'])}")
                    
                    # Ensure output directory exists
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Take full page screenshot at device pixel ratio to preserve detail
                    device_pixel_ratio = self.config['device_pixel_ratio']
                    await page.emulate_media(color_scheme="light")  # Ensure consistent colors
                    await page.screenshot(
                        path=str(output_path),
                        full_page=True,
                        scale="device" if device_pixel_ratio > 1.0 else "css"
                    )
                    
                    self.logger.info(f"Screenshot saved: {output_path}")
                    return True
                    
                except Exception as e:
                    self.logger.error(f"Error capturing screenshot for {url} ({viewport}): {str(e)}")
                    return False
                    
                finally:
                    await browser.close()
                    
        except Exception as e:
            self.logger.error(f"Error launching browser for {url} ({viewport}): {str(e)}")
            return False
    
    # Old _wait_for_dynamic_content method removed - now using DynamicContentHandler
    
    async def capture_page_screenshots(self, page_id: int, viewports: list = None,
                                     run_id: str = None) -> bool:
        """
        Capture screenshots for both staging and production URLs of a page across multiple viewports
        
        Args:
            page_id (int): ProjectPage ID
            viewports (list): List of viewport types to capture (default: all viewports)
            run_id (str): Run ID timestamp (auto-generated if None)
            
        Returns:
            bool: True if all screenshots were captured successfully
        """
        try:
            # Get page from database
            page = db.session.get(ProjectPage, page_id)
            if not page:
                self.logger.error(f"Page {page_id} not found")
                return False
            
            # Default to all viewports if none specified
            if viewports is None:
                viewports = self.path_resolver.viewports
            
            # Generate run ID if not provided
            if run_id is None:
                run_id = self.path_resolver.generate_run_id()
            
            # Generate page slug
            page_slug = self.path_resolver.slugify_page_path(page.path)
            
            self.logger.info(f"Capturing screenshots for page: {page.path} (viewports: {viewports}, run_id: {run_id})")
            
            # Create directories for this run
            self.path_resolver.create_directories(page.project_id, run_id)
            
            all_success = True
            
            # Capture screenshots for each viewport
            for viewport in viewports:
                # Get screenshot paths for this viewport
                staging_path, production_path = self.get_screenshot_paths(
                    page.project_id, page.path, viewport, run_id
                )
                
                # Capture staging screenshot
                staging_success = await self.capture_screenshot(
                    page.staging_url, staging_path, viewport
                )
                
                # Capture production screenshot
                production_success = await self.capture_screenshot(
                    page.production_url, production_path, viewport
                )
                
                viewport_success = staging_success and production_success
                all_success = all_success and viewport_success
                
                if viewport_success:
                    # Update status for this viewport
                    setattr(page, f'screenshot_status_{viewport}', 'completed')
                    self.logger.info(f"Successfully captured {viewport} screenshots for page: {page.path}")
                else:
                    # Update status and error for this viewport
                    setattr(page, f'screenshot_status_{viewport}', 'failed')
                    setattr(page, f'screenshot_error_{viewport}', f"Failed to capture {viewport} screenshots")
                    self.logger.error(f"Failed to capture {viewport} screenshots for page: {page.path}")
                    
                    # Clean up partial files
                    if staging_path.exists() and not staging_success:
                        staging_path.unlink()
                    if production_path.exists() and not production_success:
                        production_path.unlink()
            
            # Update database with results
            if all_success:
                # Store run ID and page slug for URL generation
                page.current_run_id = run_id
                page.page_slug = page_slug
                page.status = 'screenshot_complete'
                page.last_run_at = db.func.now()
                self.logger.info(f"Successfully captured all screenshots for page: {page.path}")
            else:
                page.status = 'screenshot_failed'
                self.logger.error(f"Failed to capture some screenshots for page: {page.path}")
            
            db.session.commit()
            return all_success
            
        except Exception as e:
            self.logger.error(f"Error capturing screenshots for page {page_id}: {str(e)}")
            db.session.rollback()
            return False
    async def capture_manual_screenshots(self, page_ids: list, viewports: list = None,
                                       environments: list = None, process_timestamp: str = None) -> Tuple[int, int]:
        """
        Capture screenshots for manually selected pages
        
        Args:
            page_ids (list): List of ProjectPage IDs to capture
            viewports (list): List of viewport types (default: all)
            environments (list): List of environments ['staging', 'production'] (default: both)
            process_timestamp (str): Process timestamp for new structure (auto-generated if None)
            
        Returns:
            Tuple[int, int]: (successful_count, failed_count)
        """
        try:
            if not page_ids:
                self.logger.info("No pages selected for manual screenshot capture")
                return (0, 0)
            
            # Default to all viewports and environments if none specified
            if viewports is None:
                viewports = ['desktop', 'tablet', 'mobile']
            if environments is None:
                environments = ['staging', 'production']
            
            # Generate process timestamp if not provided
            if process_timestamp is None:
                process_timestamp = self.path_manager.generate_process_timestamp()
            
            self.logger.info(f"Starting manual screenshot capture for {len(page_ids)} pages")
            self.logger.info(f"Viewports: {viewports}, Environments: {environments}, Timestamp: {process_timestamp}")
            
            successful_count = 0
            failed_count = 0
            
            for page_id in page_ids:
                try:
                    # Get page from database
                    page = db.session.get(ProjectPage, page_id)
                    if not page:
                        self.logger.error(f"Page {page_id} not found")
                        failed_count += 1
                        continue
                    
                    self.logger.info(f"Processing page: {page.path}")
                    
                    page_success = True
                    captured_paths = {}
                    
                    # Capture screenshots for each viewport
                    for viewport in viewports:
                        # Get screenshot paths for this viewport using new structure
                        staging_path, production_path = self.get_screenshot_paths(
                            page.project_id, page.path, viewport, process_timestamp
                        )
                        
                        # Capture based on selected environments
                        if 'staging' in environments:
                            staging_success = await self.capture_screenshot(
                                page.staging_url, staging_path, viewport
                            )
                            if staging_success:
                                captured_paths[f'staging_{viewport}'] = self.path_manager.get_relative_path(staging_path)
                            else:
                                page_success = False
                        
                        if 'production' in environments:
                            production_success = await self.capture_screenshot(
                                page.production_url, production_path, viewport
                            )
                            if production_success:
                                captured_paths[f'production_{viewport}'] = self.path_manager.get_relative_path(production_path)
                            else:
                                page_success = False
                    
                    # Update database with results
                    if page_success:
                        # Update multi-viewport paths
                        for viewport in viewports:
                            if f'staging_{viewport}' in captured_paths:
                                setattr(page, f'staging_screenshot_path_{viewport}', captured_paths[f'staging_{viewport}'])
                            if f'production_{viewport}' in captured_paths:
                                setattr(page, f'production_screenshot_path_{viewport}', captured_paths[f'production_{viewport}'])
                        
                        # Update legacy paths for backward compatibility (use desktop as default)
                        if 'staging_desktop' in captured_paths:
                            page.staging_screenshot_path = captured_paths['staging_desktop']
                        if 'production_desktop' in captured_paths:
                            page.production_screenshot_path = captured_paths['production_desktop']
                        
                        # Store process timestamp for tracking
                        page.current_run_id = process_timestamp
                        page.status = 'screenshot_complete'
                        successful_count += 1
                        self.logger.info(f"Successfully captured screenshots for page: {page.path}")
                    else:
                        page.status = 'screenshot_failed'
                        failed_count += 1
                        self.logger.error(f"Failed to capture screenshots for page: {page.path}")
                    
                    db.session.commit()
                    
                except Exception as e:
                    self.logger.error(f"Error processing page {page_id}: {str(e)}")
                    failed_count += 1
                    db.session.rollback()
            
            self.logger.info(
                f"Manual screenshot capture completed. "
                f"Successful: {successful_count}, Failed: {failed_count}"
            )
            
            return (successful_count, failed_count)
            
        except Exception as e:
            self.logger.error(f"Error in manual screenshot capture: {str(e)}")
            return (0, len(page_ids) if page_ids else 0)
    
    async def capture_project_screenshots(self, project_id: int, scheduler=None) -> Tuple[int, int]:
        """
        Capture screenshots for all ready pages in a project
        
        Args:
            project_id (int): Project ID
            scheduler: Optional scheduler for job control
            
        Returns:
            Tuple[int, int]: (successful_count, failed_count)
        """
        try:
            # Get pages ready for screenshot
            pages = ProjectPage.query.filter(
                ProjectPage.project_id == project_id,
                ProjectPage.status.in_(['crawled', 'ready_for_screenshot'])
            ).all()
            
            if not pages:
                self.logger.info(f"No pages ready for screenshot in project {project_id}")
                return (0, 0)
            
            self.logger.info(f"Starting screenshot capture for {len(pages)} pages in project {project_id}")
            
            successful_count = 0
            failed_count = 0
            
            for i, page in enumerate(pages, 1):
                # Check for stop signal
                if scheduler and hasattr(scheduler, '_should_stop') and scheduler._should_stop(project_id):
                    self.logger.info(f"Screenshot capture stopped by user signal for project {project_id}")
                    break
                
                # Handle pause signal
                if scheduler and hasattr(scheduler, '_should_pause'):
                    while scheduler._should_pause(project_id):
                        self.logger.info(f"Screenshot capture paused for project {project_id}")
                        await asyncio.sleep(1)
                        
                        # Check for stop while paused
                        if scheduler._should_stop(project_id):
                            self.logger.info(f"Screenshot capture stopped while paused for project {project_id}")
                            return (successful_count, failed_count)
                
                self.logger.info(f"Processing page {i}/{len(pages)}: {page.path}")
                
                # Update page status to indicate processing
                page.status = 'ready_for_screenshot'
                db.session.commit()
                
                # Capture screenshots
                success = await self.capture_page_screenshots(page.id)
                
                if success:
                    successful_count += 1
                else:
                    failed_count += 1
                
                # Small delay between pages to be respectful
                await asyncio.sleep(1)
            
            self.logger.info(
                f"Screenshot capture completed for project {project_id}. "
                f"Successful: {successful_count}, Failed: {failed_count}"
            )
            
            return (successful_count, failed_count)
            
        except Exception as e:
            self.logger.error(f"Error capturing project screenshots for project {project_id}: {str(e)}")
            return (0, len(pages) if 'pages' in locals() else 0)
    
    def run_capture_project_screenshots(self, project_id: int, scheduler=None) -> Tuple[int, int]:
        """
        Synchronous wrapper for capturing project screenshots
        
        Args:
            project_id (int): Project ID
            scheduler: Optional scheduler for job control
            
        Returns:
            Tuple[int, int]: (successful_count, failed_count)
        """
        return asyncio.run(self.capture_project_screenshots(project_id, scheduler))
    
    def get_screenshot_url(self, screenshot_path: str) -> str:
        """
        Get the URL to access a screenshot file
        
        Args:
            screenshot_path (str): Relative path to screenshot
            
        Returns:
            str: URL to access the screenshot
        """
        return self.path_manager.get_url_path(screenshot_path)
    
    def cleanup_project_screenshots(self, project_id: int, keep_latest: int = 0) -> bool:
        """
        Remove screenshots for a project
        
        Args:
            project_id (int): Project ID
            keep_latest (int): Number of latest runs to keep (0 = delete all)
            
        Returns:
            bool: True if cleanup was successful
        """
        try:
            success = self.path_manager.cleanup_project_screenshots(project_id, keep_latest)
            if success:
                if keep_latest == 0:
                    self.logger.info(f"Cleaned up all screenshots for project {project_id}")
                else:
                    self.logger.info(f"Cleaned up old screenshots for project {project_id}, kept latest {keep_latest} runs")
            return success
            
        except Exception as e:
            self.logger.error(f"Error cleaning up screenshots for project {project_id}: {str(e)}")
            return False