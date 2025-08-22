"""
Unified Find Difference Service
Handles the complete workflow: capture screenshots → generate diffs for all viewports
"""

import os
import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Tuple, Optional, Dict
import pytz

from models import db
from models.project import ProjectPage
from screenshot.screenshot_service import ScreenshotService
from diff.diff_engine import VisualDiffEngine
from utils.path_manager import PathManager


class FindDifferenceService:
    def __init__(self, base_screenshots_dir: str = "screenshots"):
        """Initialize the unified Find Difference service"""
        self.logger = logging.getLogger(__name__)
        self.screenshot_service = ScreenshotService(base_screenshots_dir)
        self.diff_engine = VisualDiffEngine(base_screenshots_dir=base_screenshots_dir)
        self.path_manager = PathManager(base_screenshots_dir)
        
        # Viewport order for consistent processing
        self.viewport_order = ['desktop', 'tablet', 'mobile']
        
        # IST timezone for timestamping
        self.ist_timezone = pytz.timezone('Asia/Kolkata')
    
    def generate_run_id(self) -> str:
        """
        Generate a unique run ID using IST timestamp
        Format: YYYYMMDD-HHmmss (filesystem-safe)
        
        Returns:
            str: Run ID in format like "20250811-154210"
        """
        return self.path_manager.generate_process_timestamp()
    
    def get_run_directory(self, project_id: int, run_id: str) -> Path:
        """
        Get the directory path for a specific run
        
        Args:
            project_id: Project ID
            run_id: Run ID (timestamp)
            
        Returns:
            Path: Directory path for the run
        """
        return self.path_manager.get_project_directory(project_id, run_id)
    
    def get_screenshot_paths_for_run(self, project_id: int, run_id: str, page_path: str,
                                   viewport: str) -> Tuple[Path, Path]:
        """
        Get screenshot paths for a specific run using new structure
        
        Args:
            project_id: Project ID
            run_id: Run ID
            page_path: Page path
            viewport: Viewport type
            
        Returns:
            Tuple[Path, Path]: (staging_path, production_path)
        """
        production_path, staging_path, _ = self.path_manager.get_screenshot_paths(
            project_id, run_id, page_path, viewport
        )
        return (staging_path, production_path)
    
    def get_diff_path_for_run(self, project_id: int, run_id: str, page_path: str,
                             viewport: str) -> Path:
        """
        Get single diff image path for a specific run
        
        Args:
            project_id: Project ID
            run_id: Run ID
            page_path: Page path
            viewport: Viewport type
            
        Returns:
            Path: Single diff image path
        """
        _, _, diff_path = self.path_manager.get_screenshot_paths(
            project_id, run_id, page_path, viewport
        )
        return diff_path
    
    async def capture_page_screenshots_for_run(self, page_id: int, run_id: str, 
                                             viewports: List[str] = None) -> Dict[str, bool]:
        """
        Capture screenshots for a page in a specific run
        
        Args:
            page_id: ProjectPage ID
            run_id: Run ID
            viewports: List of viewports to capture (default: all)
            
        Returns:
            Dict[str, bool]: Success status per viewport
        """
        if viewports is None:
            viewports = self.viewport_order.copy()
        
        # Get page from database
        page = ProjectPage.query.get(page_id)
        if not page:
            self.logger.error(f"Page {page_id} not found")
            return {viewport: False for viewport in viewports}
        
        self.logger.info(f"Capturing screenshots for page: {page.path} (run: {run_id})")
        
        results = {}
        
        # Process viewports in order: desktop → tablet → mobile
        for viewport in viewports:
            try:
                # Get screenshot paths for this run
                staging_path, production_path = self.get_screenshot_paths_for_run(
                    page.project_id, run_id, page.path, viewport
                )
                
                # Capture staging screenshot
                staging_success = await self.screenshot_service.capture_screenshot(
                    page.staging_url, staging_path, viewport, timeout=30000
                )
                
                # Capture production screenshot
                production_success = await self.screenshot_service.capture_screenshot(
                    page.production_url, production_path, viewport, timeout=30000
                )
                
                viewport_success = staging_success and production_success
                results[viewport] = viewport_success
                
                if viewport_success:
                    self.logger.info(f"Successfully captured {viewport} screenshots for page: {page.path}")
                else:
                    self.logger.error(f"Failed to capture {viewport} screenshots for page: {page.path}")
                    
                    # Clean up partial files
                    if staging_path.exists() and not staging_success:
                        staging_path.unlink()
                    if production_path.exists() and not production_success:
                        production_path.unlink()
                        
            except Exception as e:
                self.logger.error(f"Error capturing {viewport} screenshots for page {page_id}: {str(e)}")
                results[viewport] = False
        
        return results
    
    def generate_page_diffs_for_run(self, page_id: int, run_id: str, baseline_run_id: str = None,
                                  viewports: List[str] = None) -> Dict[str, Dict]:
        """
        Generate diffs for a page by comparing staging vs production (no baseline required)
        
        Args:
            page_id: ProjectPage ID
            run_id: Current run ID
            baseline_run_id: Ignored - kept for compatibility
            viewports: List of viewports to process (default: all)
            
        Returns:
            Dict[str, Dict]: Results per viewport with metrics and status
        """
        if viewports is None:
            viewports = self.viewport_order.copy()
        
        # Get page from database
        page = ProjectPage.query.get(page_id)
        if not page:
            self.logger.error(f"Page {page_id} not found")
            return {viewport: {'success': False, 'error': 'Page not found'} for viewport in viewports}
        
        # Always generate staging vs production diff for current run
        self.logger.info(f"Generating staging vs production diffs for page: {page.path} (run: {run_id})")
        return self._generate_staging_vs_production_diffs(page_id, run_id, viewports)
    
    def _generate_staging_vs_production_diffs(self, page_id: int, run_id: str,
                                            viewports: List[str]) -> Dict[str, Dict]:
        """
        Generate staging vs production diffs - the primary comparison method
        
        Args:
            page_id: ProjectPage ID
            run_id: Current run ID
            viewports: List of viewports to process
            
        Returns:
            Dict[str, Dict]: Results per viewport with metrics and status
        """
        # Get page from database
        page = ProjectPage.query.get(page_id)
        if not page:
            self.logger.error(f"Page {page_id} not found")
            return {viewport: {'success': False, 'error': 'Page not found'} for viewport in viewports}
        
        self.logger.info(f"Generating staging vs production diffs for page: {page.path} (run: {run_id})")
        
        results = {}
        
        for viewport in viewports:
            try:
                # Get current run screenshot paths
                staging_path, production_path = self.get_screenshot_paths_for_run(
                    page.project_id, run_id, page.path, viewport
                )
                
                # Check if screenshots exist
                if not staging_path.exists() or not production_path.exists():
                    results[viewport] = {
                        'success': False,
                        'error': f'Screenshots not found for {viewport}'
                    }
                    continue
                
                # Generate staging vs production diff directly
                diff_result = self._generate_direct_staging_vs_production_diff(
                    staging_path, production_path,
                    page.project_id, run_id, page.path, viewport
                )
                
                # Mark as staging vs production comparison
                if diff_result.get('success'):
                    diff_result['status'] = 'staging_vs_production'
                    diff_result['message'] = 'Staging vs Production comparison'
                
                results[viewport] = diff_result
                
            except Exception as e:
                self.logger.error(f"Error generating staging vs production diff for {viewport}: {str(e)}")
                results[viewport] = {
                    'success': False,
                    'error': str(e)
                }
        
        return results
    
    def _generate_direct_staging_vs_production_diff(self, staging_path: Path, production_path: Path,
                                                  project_id: int, run_id: str, page_path: str, viewport: str) -> Dict:
        """
        Generate diff directly comparing staging vs production screenshots
        Creates a single grayscale overlay image with color-coded highlights
        
        Args:
            staging_path: Path to staging screenshot
            production_path: Path to production screenshot
            project_id: Project ID
            run_id: Run ID
            page_path: Page path
            viewport: Viewport type
            
        Returns:
            Dict: Result with success status, metrics, and paths
        """
        try:
            from PIL import Image, ImageChops
            import numpy as np
            
            self.logger.info(f"Generating staging vs production diff for {viewport} viewport...")
            
            # Load images
            staging_image = Image.open(staging_path)
            production_image = Image.open(production_path)
            
            # Normalize images for comparison
            norm_staging, norm_production = self.diff_engine.normalize_images(
                staging_image, production_image
            )
            
            # Generate diff (staging vs production)
            diff_mask = self.diff_engine.compute_diff_mask(norm_staging, norm_production)
            bboxes = self.diff_engine.extract_bounding_boxes(diff_mask)
            metrics = self.diff_engine.calculate_metrics(diff_mask, bboxes)
            
            # Check if there are any differences
            if metrics['diff_mismatch_pct'] == 0.0:
                self.logger.info(f"No differences found between staging and production for {viewport} viewport")
                return {
                    'success': True,
                    'status': 'no_changes',
                    'message': 'No visual differences detected between staging and production'
                }
            
            # Get single output path
            diff_path = self.get_diff_path_for_run(
                project_id, run_id, page_path, viewport
            )
            
            # Create single diff image with exact specifications
            diff_image = self._create_single_diff_overlay(
                norm_staging, norm_production, diff_mask, bboxes
            )
            diff_image.save(diff_path, 'PNG')
            
            # Log success
            self.logger.info(f"Successfully generated staging vs production diff for {viewport} viewport "
                              f"({metrics['diff_mismatch_pct']}% difference)")
            self.logger.info(f"Saved single diff file: {diff_path}")
            
            return {
                'success': True,
                'status': 'completed',
                'metrics': metrics,
                'diff_path': str(diff_path),
                'mismatch_pct': metrics['diff_mismatch_pct'],
                'pixels_changed': metrics['diff_pixels_changed'],
                'bounding_boxes': metrics['diff_bounding_boxes']
            }
            
        except Exception as e:
            self.logger.error(f"Error generating staging vs production diff for {viewport}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _generate_viewport_diff(self, current_staging_path: Path, current_production_path: Path,
                               baseline_staging_path: Path, baseline_production_path: Path,
                               project_id: int, run_id: str, page_path: str, viewport: str) -> Dict:
        """
        Generate diff for a specific viewport with overlay and highlighted versions
        
        Returns:
            Dict: Result with success status, metrics, and paths
        """
        try:
            from PIL import Image, ImageChops
            
            self.logger.info(f"Generating diff for {viewport} viewport...")
            
            # Load current images
            current_staging = Image.open(current_staging_path)
            current_production = Image.open(current_production_path)
            
            # Load baseline images
            baseline_staging = Image.open(baseline_staging_path)
            baseline_production = Image.open(baseline_production_path)
            
            # Normalize images for comparison
            norm_current_staging, norm_baseline_staging = self.diff_engine.normalize_images(
                current_staging, baseline_staging
            )
            norm_current_production, norm_baseline_production = self.diff_engine.normalize_images(
                current_production, baseline_production
            )
            
            # Generate staging diff (use staging as primary)
            staging_diff_mask = self.diff_engine.compute_diff_mask(norm_current_staging, norm_baseline_staging)
            staging_bboxes = self.diff_engine.extract_bounding_boxes(staging_diff_mask)
            staging_metrics = self.diff_engine.calculate_metrics(staging_diff_mask, staging_bboxes)
            
            # Generate production diff for comparison
            production_diff_mask = self.diff_engine.compute_diff_mask(norm_current_production, norm_baseline_production)
            production_bboxes = self.diff_engine.extract_bounding_boxes(production_diff_mask)
            production_metrics = self.diff_engine.calculate_metrics(production_diff_mask, production_bboxes)
            
            # Check if there are any differences
            if staging_metrics['diff_mismatch_pct'] == 0.0 and production_metrics['diff_mismatch_pct'] == 0.0:
                self.logger.info(f"No differences found for {viewport} viewport")
                return {
                    'success': True,
                    'status': 'no_changes',
                    'message': 'No visual differences detected between baseline and current screenshots'
                }
            
            # This method is deprecated - we now only use staging vs production comparison
            # Redirect to the single diff generation
            return self._generate_direct_staging_vs_production_diff(
                current_staging_path, current_production_path,
                project_id, run_id, page_path, viewport
            )
            
        except Exception as e:
            self.logger.error(f"Error generating {viewport} diff: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    # Removed old multi-file generation methods - now only generate single diff output
    
    def _create_single_diff_overlay(self, staging_image: 'Image.Image', production_image: 'Image.Image',
                                   diff_mask: 'Image.Image', bboxes: list) -> 'Image.Image':
        """
        Create a single diff overlay exactly matching the user's required format:
        - Bright red/orange highlights for differences
        - Grayscale background for unchanged areas
        - "Spot the difference" style visualization
        
        Args:
            staging_image: The staging screenshot
            production_image: The production screenshot
            diff_mask: Binary mask showing differences
            bboxes: List of bounding boxes for differences
            
        Returns:
            PIL Image with exact "spot the difference" style as shown in reference
        """
        from PIL import Image, ImageDraw, ImageFilter
        import numpy as np
        
        # Use staging image as the base (current state)
        base_image = staging_image.convert('RGBA')
        base_array = np.array(base_image)
        
        # Create result image starting with the base
        result_array = base_array.copy()
        
        # Convert diff mask to numpy array
        diff_array = np.array(diff_mask.convert('L'))
        
        # Step 1: Convert ENTIRE image to grayscale first
        # This creates the muted background effect shown in the reference
        grayscale_values = np.dot(base_array[:, :, :3], [0.299, 0.587, 0.114])
        
        # Apply grayscale to all areas (will be overridden for differences)
        for i in range(3):  # RGB channels
            result_array[:, :, i] = grayscale_values.astype(np.uint8)
        
        # Step 2: Apply bright red/orange highlights ONLY to difference areas
        # This matches the exact format shown in the reference image
        diff_pixels = diff_array > 30  # Threshold for detecting differences
        
        if np.any(diff_pixels):
            # Apply bright red/orange color to ALL difference pixels
            # Using a vibrant red-orange color (#FF4500) as shown in reference
            result_array[diff_pixels, 0] = 255  # Red channel - full intensity
            result_array[diff_pixels, 1] = 69   # Green channel - slight orange tint
            result_array[diff_pixels, 2] = 0    # Blue channel - none
        
        # Step 3: Enhance difference visibility with slight expansion
        # This ensures small differences are clearly visible
        try:
            from scipy import ndimage
            # Slightly dilate the difference areas to make them more prominent
            diff_expanded = ndimage.binary_dilation(diff_pixels, iterations=1)
            
            # Apply the same bright color to expanded areas
            result_array[diff_expanded, 0] = 255  # Red
            result_array[diff_expanded, 1] = 69   # Orange tint
            result_array[diff_expanded, 2] = 0    # Blue
        except ImportError:
            # If scipy not available, use original diff pixels
            pass
        
        # Convert back to PIL Image
        result = Image.fromarray(result_array, 'RGBA')
        
        return result.convert('RGB')
    
    async def run_find_difference(self, project_id: int, page_ids: List[int] = None,
                                scheduler=None) -> Tuple[int, int, str]:
        """
        Execute the complete Find Difference workflow with improved error handling
        
        Args:
            project_id: Project ID
            page_ids: Optional list of specific page IDs (default: all pages)
            scheduler: Optional scheduler for job control
            
        Returns:
            Tuple[int, int, str]: (successful_count, failed_count, run_id)
        """
        # Generate run ID
        run_id = self.generate_run_id()
        
        self.logger.info(f"Starting Find Difference workflow for project {project_id} (run: {run_id})")
        
        # Add workflow timeout protection (30 minutes max)
        import asyncio
        workflow_start_time = datetime.now(timezone.utc)
        max_workflow_duration = 30 * 60  # 30 minutes in seconds
        
        # Get pages to process
        if page_ids:
            pages = ProjectPage.query.filter(
                ProjectPage.id.in_(page_ids),
                ProjectPage.project_id == project_id
            ).all()
        else:
            pages = ProjectPage.query.filter_by(project_id=project_id).all()
        
        if not pages:
            self.logger.info(f"No pages found for project {project_id}")
            return (0, 0, run_id)
        
        successful_count = 0
        failed_count = 0
        
        for i, page in enumerate(pages, 1):
            try:
                # Check for workflow timeout
                current_time = datetime.now(timezone.utc)
                elapsed_seconds = (current_time - workflow_start_time).total_seconds()
                if elapsed_seconds > max_workflow_duration:
                    self.logger.error(f"Find Difference workflow timed out after {elapsed_seconds:.1f} seconds for project {project_id}")
                    raise TimeoutError(f"Workflow exceeded maximum duration of {max_workflow_duration} seconds")
                
                # Check for stop signal
                if scheduler and hasattr(scheduler, '_should_stop') and scheduler._should_stop(project_id):
                    self.logger.info(f"Find Difference stopped by user signal for project {project_id}")
                    break
                
                # Handle pause signal
                if scheduler and hasattr(scheduler, '_should_pause'):
                    while scheduler._should_pause(project_id):
                        self.logger.info(f"Find Difference paused for project {project_id}")
                        await asyncio.sleep(1)
                        
                        # Check timeout even while paused
                        current_time = datetime.now(timezone.utc)
                        elapsed_seconds = (current_time - workflow_start_time).total_seconds()
                        if elapsed_seconds > max_workflow_duration:
                            self.logger.error(f"Find Difference workflow timed out while paused for project {project_id}")
                            raise TimeoutError(f"Workflow exceeded maximum duration of {max_workflow_duration} seconds")
                        
                        if scheduler._should_stop(project_id):
                            self.logger.info(f"Find Difference stopped while paused for project {project_id}")
                            return (successful_count, failed_count, run_id)
                
                self.logger.info(f"Processing page {i}/{len(pages)}: {page.path}")
                
                # Start processing timer for this page with timeout protection
                page_start_time = datetime.now(timezone.utc)
                page.start_processing()
                page.current_run_id = run_id
                page.last_run_at = page_start_time
                db.session.commit()
                
                # Set per-page timeout (5 minutes max per page)
                page_timeout = 5 * 60  # 5 minutes in seconds
                
                try:
                    self.logger.info(f"Status: Capturing screenshots for {page.path}")
                    
                    # Step 1: Capture screenshots for all viewports with timeout
                    screenshot_task = asyncio.create_task(
                        self.capture_page_screenshots_for_run(page.id, run_id, self.viewport_order)
                    )
                    
                    try:
                        screenshot_results = await asyncio.wait_for(screenshot_task, timeout=page_timeout)
                    except asyncio.TimeoutError:
                        self.logger.error(f"Screenshot capture timed out for page: {page.path}")
                        page.fail_processing(f"Screenshot capture timed out after {page_timeout} seconds")
                        db.session.commit()
                        failed_count += 1
                        continue
                    
                    # Check if all screenshots were captured successfully
                    all_screenshots_success = all(screenshot_results.values())
                    
                    if not all_screenshots_success:
                        self.logger.error(f"Failed to capture screenshots for page: {page.path}")
                        page.fail_processing("Failed to capture screenshots")
                        db.session.commit()
                        failed_count += 1
                        continue
                
                except Exception as page_error:
                    self.logger.error(f"Error during screenshot capture for page {page.path}: {str(page_error)}")
                    page.fail_processing(f"Screenshot error: {str(page_error)}")
                    db.session.commit()
                    failed_count += 1
                    continue
                
                # Update status to captured
                page.find_diff_status = 'captured'
                db.session.commit()
                
                try:
                    self.logger.info(f"Status: Generating diffs for {page.path}")
                    
                    # Step 2: Generate diffs for all viewports with timeout
                    page.find_diff_status = 'diffing'
                    db.session.commit()
                    
                    # Generate diffs with timeout protection
                    diff_task = asyncio.create_task(
                        asyncio.to_thread(
                            self.generate_page_diffs_for_run,
                            page.id, run_id, page.baseline_run_id, self.viewport_order
                        )
                    )
                    
                    try:
                        diff_results = await asyncio.wait_for(diff_task, timeout=page_timeout)
                    except asyncio.TimeoutError:
                        self.logger.error(f"Diff generation timed out for page: {page.path}")
                        page.fail_processing(f"Diff generation timed out after {page_timeout} seconds")
                        db.session.commit()
                        failed_count += 1
                        continue
                
                except Exception as diff_error:
                    self.logger.error(f"Error during diff generation for page {page.path}: {str(diff_error)}")
                    page.fail_processing(f"Diff generation error: {str(diff_error)}")
                    db.session.commit()
                    failed_count += 1
                    continue
                
                # Update diff status per viewport
                for viewport in self.viewport_order:
                    result = diff_results.get(viewport, {})
                    status_field = f'diff_status_{viewport}'
                    error_field = f'diff_error_{viewport}'
                    
                    if result.get('success'):
                        status = result.get('status', 'completed')
                        if status == 'no_changes':
                            setattr(page, status_field, 'completed')  # Use 'completed' for no changes
                        elif status == 'staging_vs_production':
                            setattr(page, status_field, 'completed')
                            # Update metrics for staging vs production comparison
                            if viewport == 'desktop':
                                page.diff_mismatch_pct_desktop = result.get('mismatch_pct')
                                page.diff_pixels_changed_desktop = result.get('pixels_changed')
                            elif viewport == 'tablet':
                                page.diff_mismatch_pct_tablet = result.get('mismatch_pct')
                                page.diff_pixels_changed_tablet = result.get('pixels_changed')
                            elif viewport == 'mobile':
                                page.diff_mismatch_pct_mobile = result.get('mismatch_pct')
                                page.diff_pixels_changed_mobile = result.get('pixels_changed')
                        else:
                            setattr(page, status_field, 'completed')
                            # Update metrics for this viewport
                            if viewport == 'desktop':
                                page.diff_mismatch_pct_desktop = result.get('mismatch_pct')
                                page.diff_pixels_changed_desktop = result.get('pixels_changed')
                            elif viewport == 'tablet':
                                page.diff_mismatch_pct_tablet = result.get('mismatch_pct')
                                page.diff_pixels_changed_tablet = result.get('pixels_changed')
                            elif viewport == 'mobile':
                                page.diff_mismatch_pct_mobile = result.get('mismatch_pct')
                                page.diff_pixels_changed_mobile = result.get('pixels_changed')
                    else:
                        setattr(page, status_field, 'failed')
                        setattr(page, error_field, result.get('error', 'Unknown error'))
                
                # Determine overall status
                all_diffs_success = all(
                    result.get('success', False) for result in diff_results.values()
                )
                
                # Check if any viewport has actual changes (not just no_changes status)
                has_actual_changes = any(
                    result.get('status') in ['completed', 'staging_vs_production'] for result in diff_results.values()
                )
                
                if all_diffs_success:
                    page.complete_processing()
                    # No need to set baseline - we always compare staging vs production
                    successful_count += 1
                    self.logger.info(f"Status: Completed processing {page.path} in {page.duration_formatted} "
                                   f"({'changes detected' if has_actual_changes else 'no changes'})")
                else:
                    page.fail_processing("Failed to generate diffs")
                    failed_count += 1
                    self.logger.error(f"Status: Failed processing {page.path} after {page.duration_formatted}")
                
                db.session.commit()
                
                # Small delay between pages
                await asyncio.sleep(0.5)
                
            except Exception as e:
                self.logger.error(f"Error processing page {page.id}: {str(e)}")
                page.fail_processing(f"Exception: {str(e)}")
                db.session.commit()
                failed_count += 1
        
        self.logger.info(
            f"Find Difference completed for project {project_id} (run: {run_id}). "
            f"Successful: {successful_count}, Failed: {failed_count}"
        )
        
        return (successful_count, failed_count, run_id)
    
    async def capture_only(self, project_id: int, page_id: int, run_id: str = None,
                          viewports: List[str] = None, envs: List[str] = None) -> Dict:
        """
        Capture screenshots only (no diff generation) for a specific page
        
        Args:
            project_id: Project ID
            page_id: ProjectPage ID
            run_id: Optional run ID (generates new if None)
            viewports: Optional list of viewports (default: all)
            envs: Optional list of environments (default: both staging and production)
            
        Returns:
            Dict: Result with run_id, page_id, updated_status, and screenshot_paths_by_viewport
        """
        if run_id is None:
            run_id = self.generate_run_id()
        
        if viewports is None:
            viewports = self.viewport_order.copy()
        
        if envs is None:
            envs = ['staging', 'production']
        
        self.logger.info(f"Starting capture-only for page {page_id} (run: {run_id})")
        
        # Get page from database
        page = ProjectPage.query.get(page_id)
        if not page:
            self.logger.error(f"Page {page_id} not found")
            return {
                'success': False,
                'error': 'Page not found',
                'run_id': run_id,
                'page_id': page_id
            }
        
        # Check for idempotency - avoid duplicate work for same (project_id, page_id, run_id)
        if page.current_run_id == run_id and page.find_diff_status in ['capturing', 'captured']:
            self.logger.info(f"Page {page_id} already being processed for run {run_id}")
            return {
                'success': True,
                'message': 'Already processing or completed for this run',
                'run_id': run_id,
                'page_id': page_id,
                'updated_status': page.find_diff_status
            }
        
        # Update page status
        page.find_diff_status = 'capturing'
        page.current_run_id = run_id
        page.last_run_at = datetime.now(timezone.utc)
        db.session.commit()
        
        try:
            screenshot_paths_by_viewport = {}
            all_success = True
            
            # Process each viewport
            for viewport in viewports:
                viewport_paths = {}
                viewport_success = True
                
                # Get screenshot paths for this run
                staging_path, production_path = self.get_screenshot_paths_for_run(
                    project_id, run_id, page.path, viewport
                )
                
                # Capture based on requested environments
                if 'staging' in envs:
                    staging_success = await self.screenshot_service.capture_screenshot(
                        page.staging_url, staging_path, viewport
                    )
                    if staging_success:
                        viewport_paths['staging'] = str(staging_path)
                        # Update database field with relative path
                        relative_staging_path = self.path_manager.get_relative_path(staging_path)
                        setattr(page, f'staging_screenshot_path_{viewport}', relative_staging_path)
                    else:
                        viewport_success = False
                        all_success = False
                
                if 'production' in envs:
                    production_success = await self.screenshot_service.capture_screenshot(
                        page.production_url, production_path, viewport
                    )
                    if production_success:
                        viewport_paths['production'] = str(production_path)
                        # Update database field with relative path
                        relative_production_path = self.path_manager.get_relative_path(production_path)
                        setattr(page, f'production_screenshot_path_{viewport}', relative_production_path)
                    else:
                        viewport_success = False
                        all_success = False
                
                screenshot_paths_by_viewport[viewport] = viewport_paths
                
                if viewport_success:
                    self.logger.info(f"Successfully captured {viewport} screenshots for page: {page.path}")
                else:
                    self.logger.error(f"Failed to capture {viewport} screenshots for page: {page.path}")
            
            # Update final status
            if all_success:
                page.find_diff_status = 'captured'
                # No need to set baseline - we always compare staging vs production
            else:
                page.find_diff_status = 'failed'
            
            db.session.commit()
            
            return {
                'success': all_success,
                'message': 'Screenshots captured successfully' if all_success else 'Some screenshots failed',
                'run_id': run_id,
                'page_id': page_id,
                'updated_status': page.find_diff_status,
                'screenshot_paths_by_viewport': screenshot_paths_by_viewport
            }
            
        except Exception as e:
            self.logger.error(f"Error in capture-only for page {page_id}: {str(e)}")
            page.find_diff_status = 'failed'
            db.session.commit()
            return {
                'success': False,
                'error': str(e),
                'run_id': run_id,
                'page_id': page_id,
                'updated_status': 'failed'
            }
    
    async def capture_and_diff(self, project_id: int, page_id: int, run_id: str = None,
                              viewports: List[str] = None) -> Dict:
        """
        Enhanced Capture: Capture screenshots AND generate diff image in one operation
        
        This method implements the enhanced Capture button functionality:
        1. Captures screenshots with complete page load detection
        2. Generates single diff overlay image using same logic as Find difference
        3. Ensures dynamic content, animations, and lazy-loading are handled
        
        Args:
            project_id: Project ID
            page_id: ProjectPage ID
            run_id: Optional run ID (generates new if None)
            viewports: Optional list of viewports (default: all)
            
        Returns:
            Dict: Result with run_id, page_id, updated_status, screenshot_paths, and diff_paths
        """
        if run_id is None:
            run_id = self.generate_run_id()
        
        if viewports is None:
            viewports = self.viewport_order.copy()
        
        self.logger.info(f"Starting enhanced capture+diff for page {page_id} (run: {run_id})")
        
        # Get page from database
        page = ProjectPage.query.get(page_id)
        if not page:
            self.logger.error(f"Page {page_id} not found")
            return {
                'success': False,
                'error': 'Page not found',
                'run_id': run_id,
                'page_id': page_id
            }
        
        # Update page status
        page.find_diff_status = 'capturing'
        page.current_run_id = run_id
        page.last_run_at = datetime.now(timezone.utc)
        db.session.commit()
        
        try:
            screenshot_paths_by_viewport = {}
            diff_paths_by_viewport = {}
            all_success = True
            
            # Process each viewport
            for viewport in viewports:
                self.logger.info(f"Processing {viewport} viewport for enhanced capture+diff...")
                
                # Step 1: Capture screenshots with enhanced page loading
                staging_path, production_path = self.get_screenshot_paths_for_run(
                    project_id, run_id, page.path, viewport
                )
                
                # Capture staging screenshot with enhanced dynamic content handling
                self.logger.info(f"Capturing staging screenshot with enhanced dynamic content detection...")
                staging_success = await self.screenshot_service.capture_screenshot(
                    page.staging_url, staging_path, viewport, timeout=30000, wait_for_dynamic=True
                )
                
                # Capture production screenshot with enhanced dynamic content handling
                self.logger.info(f"Capturing production screenshot with enhanced dynamic content detection...")
                production_success = await self.screenshot_service.capture_screenshot(
                    page.production_url, production_path, viewport, timeout=30000, wait_for_dynamic=True
                )
                
                if not (staging_success and production_success):
                    self.logger.error(f"Failed to capture {viewport} screenshots")
                    all_success = False
                    continue
                
                # Store screenshot paths
                screenshot_paths_by_viewport[viewport] = {
                    'staging': str(staging_path),
                    'production': str(production_path)
                }
                
                # Step 2: Generate diff image using same logic as Find difference
                diff_result = self._generate_direct_staging_vs_production_diff(
                    staging_path, production_path,
                    project_id, run_id, page.path, viewport
                )
                
                if diff_result.get('success'):
                    diff_paths_by_viewport[viewport] = {
                        'diff_path': diff_result.get('diff_path'),
                        'mismatch_pct': diff_result.get('mismatch_pct', 0),
                        'pixels_changed': diff_result.get('pixels_changed', 0),
                        'status': diff_result.get('status', 'completed')
                    }
                    
                    # Update database fields for this viewport with relative paths
                    relative_staging_path = self.path_manager.get_relative_path(staging_path)
                    relative_production_path = self.path_manager.get_relative_path(production_path)
                    setattr(page, f'staging_screenshot_path_{viewport}', relative_staging_path)
                    setattr(page, f'production_screenshot_path_{viewport}', relative_production_path)
                    
                    # Update diff metrics
                    if viewport == 'desktop':
                        page.diff_mismatch_pct_desktop = diff_result.get('mismatch_pct')
                        page.diff_pixels_changed_desktop = diff_result.get('pixels_changed')
                        page.diff_status_desktop = 'completed'
                    elif viewport == 'tablet':
                        page.diff_mismatch_pct_tablet = diff_result.get('mismatch_pct')
                        page.diff_pixels_changed_tablet = diff_result.get('pixels_changed')
                        page.diff_status_tablet = 'completed'
                    elif viewport == 'mobile':
                        page.diff_mismatch_pct_mobile = diff_result.get('mismatch_pct')
                        page.diff_pixels_changed_mobile = diff_result.get('pixels_changed')
                        page.diff_status_mobile = 'completed'
                    
                    self.logger.info(f"Successfully generated {viewport} capture+diff "
                                   f"({diff_result.get('mismatch_pct', 0):.2f}% difference)")
                else:
                    self.logger.error(f"Failed to generate {viewport} diff: {diff_result.get('error', 'Unknown error')}")
                    all_success = False
            
            # Update final status
            if all_success:
                page.find_diff_status = 'completed'
                page.status = 'diff_generated'  # Use valid enum value
            else:
                page.find_diff_status = 'failed'
                page.status = 'diff_failed'  # Use valid enum value
            
            db.session.commit()
            
            return {
                'success': all_success,
                'message': 'Enhanced capture+diff completed successfully' if all_success else 'Some operations failed',
                'run_id': run_id,
                'page_id': page_id,
                'updated_status': page.find_diff_status,
                'screenshot_paths_by_viewport': screenshot_paths_by_viewport,
                'diff_paths_by_viewport': diff_paths_by_viewport
            }
            
        except Exception as e:
            self.logger.error(f"Error in enhanced capture+diff for page {page_id}: {str(e)}")
            page.find_diff_status = 'failed'
            page.status = 'capture_and_diff_failed'
            db.session.commit()
            return {
                'success': False,
                'error': str(e),
                'run_id': run_id,
                'page_id': page_id,
                'updated_status': 'failed'
            }
    
    async def run_manual_capture(self, page_id: int, viewports: List[str] = None,
                               envs: List[str] = None) -> Dict:
        """
        Run manual capture for a single page (screenshots only, no diff)
        
        Args:
            page_id: ProjectPage ID
            viewports: Optional list of viewports (default: all)
            envs: Optional list of environments (default: both)
            
        Returns:
            Dict: Result with success status and details
        """
        # Get page to determine project_id
        page = ProjectPage.query.get(page_id)
        if not page:
            return {
                'success': False,
                'error': 'Page not found',
                'page_id': page_id
            }
        
        # Use capture_only method for manual capture
        return await self.capture_only(
            project_id=page.project_id,
            page_id=page_id,
            viewports=viewports,
            envs=envs
        )