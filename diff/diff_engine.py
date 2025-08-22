"""
Visual Diff Engine for UI Regression Testing
Compares screenshots and generates highlighted diff images with metrics
"""

import os
import json
import logging
from pathlib import Path
from typing import Tuple, List, Dict, Optional
from datetime import datetime

import numpy as np
from PIL import Image, ImageChops, ImageFilter, ImageDraw
from scipy import ndimage
from models import db
from models.project import ProjectPage
from utils.path_manager import PathManager

class DiffConfig:
    """Configuration for diff generation"""
    
    def __init__(self):
        # Thresholds and parameters
        self.per_pixel_threshold = int(os.getenv('DIFF_PER_PIXEL_THRESHOLD', '12'))
        self.min_diff_area = int(os.getenv('DIFF_MIN_DIFF_AREA', '24'))
        self.overlay_alpha = int(os.getenv('DIFF_OVERLAY_ALPHA', '140'))
        self.batch_size = int(os.getenv('DIFF_BATCH_SIZE', '15'))
        self.output_dir = os.getenv('DIFF_OUTPUT_DIR', './diffs')
        
        # Image processing
        self.enable_blur = os.getenv('DIFF_ENABLE_BLUR', 'false').lower() == 'true'
        self.blur_radius = float(os.getenv('DIFF_BLUR_RADIUS', '0.5'))
        self.enable_heatmap = os.getenv('DIFF_HEATMAP', 'false').lower() == 'true'
        
        # Morphological operations
        self.dilate_iterations = int(os.getenv('DIFF_DILATE_ITERATIONS', '2'))
        self.erode_iterations = int(os.getenv('DIFF_ERODE_ITERATIONS', '1'))

class VisualDiffEngine:
    """Main visual diff engine for comparing screenshots"""
    
    def __init__(self, config: Optional[DiffConfig] = None, base_screenshots_dir: str = "screenshots"):
        """
        Initialize the diff engine
        
        Args:
            config: Configuration object, uses defaults if None
            base_screenshots_dir: Base directory for screenshots (default: "screenshots")
        """
        self.config = config or DiffConfig()
        self.logger = logging.getLogger(__name__)
        self.path_manager = PathManager(base_screenshots_dir)
        
        # Ensure output directory exists
        Path(self.config.output_dir).mkdir(parents=True, exist_ok=True)
    
    def normalize_images(self, img1: Image.Image, img2: Image.Image) -> Tuple[Image.Image, Image.Image]:
        """
        Normalize two images to same size and format for comparison with proper alignment
        
        Args:
            img1: First image (staging)
            img2: Second image (production)
            
        Returns:
            Tuple of normalized and aligned images
        """
        # Convert to RGBA for consistent processing
        if img1.mode != 'RGBA':
            img1 = img1.convert('RGBA')
        if img2.mode != 'RGBA':
            img2 = img2.convert('RGBA')
        
        # Get dimensions
        w1, h1 = img1.size
        w2, h2 = img2.size
        
        # Determine target dimensions (max of both)
        target_width = max(w1, w2)
        target_height = max(h1, h2)
        
        self.logger.debug(f"Normalizing images: {w1}x{h1} and {w2}x{h2} -> {target_width}x{target_height}")
        
        # Create new images with target size and white background
        normalized_img1 = Image.new('RGBA', (target_width, target_height), (255, 255, 255, 255))
        normalized_img2 = Image.new('RGBA', (target_width, target_height), (255, 255, 255, 255))
        
        # Center images for better alignment (instead of top-left)
        offset1_x = (target_width - w1) // 2
        offset1_y = (target_height - h1) // 2
        offset2_x = (target_width - w2) // 2
        offset2_y = (target_height - h2) // 2
        
        # Paste original images centered
        normalized_img1.paste(img1, (offset1_x, offset1_y))
        normalized_img2.paste(img2, (offset2_x, offset2_y))
        
        # Apply optional blur for anti-alias noise reduction
        if self.config.enable_blur:
            normalized_img1 = normalized_img1.filter(ImageFilter.GaussianBlur(radius=self.config.blur_radius))
            normalized_img2 = normalized_img2.filter(ImageFilter.GaussianBlur(radius=self.config.blur_radius))
        
        # Additional alignment check - if images are very similar in size, try to align them better
        if abs(w1 - w2) <= 10 and abs(h1 - h2) <= 10:
            # Images are nearly the same size, use exact positioning for pixel-perfect alignment
            normalized_img1 = Image.new('RGBA', (target_width, target_height), (255, 255, 255, 255))
            normalized_img2 = Image.new('RGBA', (target_width, target_height), (255, 255, 255, 255))
            
            # Paste at exact positions for pixel-perfect comparison
            normalized_img1.paste(img1, (0, 0))
            normalized_img2.paste(img2, (0, 0))
        
        return normalized_img1, normalized_img2
    
    def compute_diff_mask(self, img1: Image.Image, img2: Image.Image) -> Image.Image:
        """
        Compute precise pixel-level difference mask between two images
        
        Args:
            img1: First normalized image (staging)
            img2: Second normalized image (production)
            
        Returns:
            Binary mask image (L mode, 0/255 values) with precise pixel differences
        """
        # Convert images to numpy arrays for precise pixel comparison
        img1_array = np.array(img1)
        img2_array = np.array(img2)
        
        # Compute per-channel differences
        diff_r = np.abs(img1_array[:, :, 0].astype(np.float32) - img2_array[:, :, 0].astype(np.float32))
        diff_g = np.abs(img1_array[:, :, 1].astype(np.float32) - img2_array[:, :, 1].astype(np.float32))
        diff_b = np.abs(img1_array[:, :, 2].astype(np.float32) - img2_array[:, :, 2].astype(np.float32))
        
        # Calculate perceptual difference using weighted RGB (closer to human vision)
        # Standard weights for luminance calculation
        perceptual_diff = (0.299 * diff_r + 0.587 * diff_g + 0.114 * diff_b)
        
        # Apply threshold for pixel-level sensitivity
        threshold = self.config.per_pixel_threshold
        mask_array = np.where(perceptual_diff > threshold, 255, 0).astype(np.uint8)
        
        # Optional: Apply minimal morphological operations only if needed
        # Reduce morphological operations to preserve pixel-level precision
        if self.config.dilate_iterations > 0:
            # Use smaller structuring element for precise pixel detection
            structure = np.ones((3, 3))  # Smaller 3x3 instead of default
            mask_array = ndimage.binary_dilation(
                mask_array > 0,
                structure=structure,
                iterations=min(1, self.config.dilate_iterations)  # Limit to 1 iteration max
            ).astype(np.uint8) * 255
        
        # Skip erosion for pixel-perfect detection unless specifically needed
        if self.config.erode_iterations > 0 and self.config.dilate_iterations > 0:
            # Only erode if we dilated, and use minimal erosion
            structure = np.ones((3, 3))
            mask_array = ndimage.binary_erosion(
                mask_array > 0,
                structure=structure,
                iterations=min(1, self.config.erode_iterations)  # Limit to 1 iteration max
            ).astype(np.uint8) * 255
        
        return Image.fromarray(mask_array, mode='L')
    
    def extract_bounding_boxes(self, mask: Image.Image) -> List[List[int]]:
        """
        Extract bounding boxes of connected components from binary mask
        
        Args:
            mask: Binary mask image
            
        Returns:
            List of bounding boxes as [x, y, width, height]
        """
        mask_array = np.array(mask)
        
        # Find connected components
        labeled_array, num_features = ndimage.label(mask_array > 0)
        
        bounding_boxes = []
        
        for i in range(1, num_features + 1):
            # Find pixels belonging to this component
            component_mask = labeled_array == i
            
            # Get bounding box
            rows, cols = np.where(component_mask)
            if len(rows) == 0:
                continue
            
            min_row, max_row = rows.min(), rows.max()
            min_col, max_col = cols.min(), cols.max()
            
            x, y = min_col, min_row
            width = max_col - min_col + 1
            height = max_row - min_row + 1
            area = width * height
            
            # Filter out small regions
            if area >= self.config.min_diff_area:
                bounding_boxes.append([x, y, width, height])
        
        self.logger.debug(f"Found {len(bounding_boxes)} bounding boxes (filtered from {num_features} components)")
        return bounding_boxes
    
    def create_highlighted_diff(self, staging_image: Image.Image, production_image: Image.Image,
                              mask: Image.Image, bounding_boxes: List[List[int]]) -> Image.Image:
        """
        Create professional-quality highlighted diff image with bright highlights on changes
        and dimmed grayscale for unchanged areas
        
        Args:
            staging_image: Staging image (for reference)
            production_image: Production image (base for diff)
            mask: Binary difference mask
            bounding_boxes: List of bounding boxes to highlight
            
        Returns:
            High-quality highlighted diff image
        """
        # Convert images to RGBA if needed
        if staging_image.mode != 'RGBA':
            staging_image = staging_image.convert('RGBA')
        if production_image.mode != 'RGBA':
            production_image = production_image.convert('RGBA')
        
        # Convert to numpy arrays for pixel-level processing
        staging_array = np.array(staging_image)
        production_array = np.array(production_image)
        mask_array = np.array(mask)
        
        # Create result array starting with production image
        result_array = production_array.copy().astype(np.float32)
        
        # Create grayscale version of production image for unchanged areas
        grayscale_array = np.array(production_image.convert('L'))
        grayscale_rgba = np.stack([grayscale_array, grayscale_array, grayscale_array,
                                  np.full_like(grayscale_array, 255)], axis=-1).astype(np.float32)
        
        # Apply grayscale dimming to unchanged areas (10-20% opacity)
        unchanged_mask = mask_array == 0
        dimming_factor = 0.15  # 15% opacity for unchanged areas
        
        # Dim unchanged areas to grayscale
        result_array[unchanged_mask] = (
            grayscale_rgba[unchanged_mask] * dimming_factor +
            result_array[unchanged_mask] * (1 - dimming_factor)
        )
        
        # Highlight changed pixels with bright colors
        changed_mask = mask_array > 0
        
        if np.any(changed_mask):
            # Calculate pixel-level differences for intensity-based coloring
            diff_intensity = np.sqrt(np.sum((staging_array.astype(np.float32) -
                                           production_array.astype(np.float32))**2, axis=-1))
            
            # Normalize difference intensity
            max_diff = np.max(diff_intensity[changed_mask]) if np.any(changed_mask) else 1
            normalized_diff = diff_intensity / max_diff if max_diff > 0 else diff_intensity
            
            # Create color mapping for different intensities
            # Red for high differences, orange for medium, yellow for low
            highlight_colors = np.zeros_like(result_array)
            
            # High intensity differences (red)
            high_intensity = (normalized_diff > 0.7) & changed_mask
            highlight_colors[high_intensity] = [255, 0, 0, 255]  # Bright red
            
            # Medium intensity differences (orange)
            medium_intensity = (normalized_diff > 0.4) & (normalized_diff <= 0.7) & changed_mask
            highlight_colors[medium_intensity] = [255, 165, 0, 255]  # Orange
            
            # Low intensity differences (yellow)
            low_intensity = (normalized_diff <= 0.4) & changed_mask
            highlight_colors[low_intensity] = [255, 255, 0, 255]  # Yellow
            
            # Apply highlights with full opacity for changed pixels
            result_array[changed_mask] = highlight_colors[changed_mask]
        
        # Convert back to uint8 and create image
        result_array = np.clip(result_array, 0, 255).astype(np.uint8)
        result = Image.fromarray(result_array, 'RGBA')
        
        # Add subtle bounding box outlines for major change regions
        if bounding_boxes:
            draw = ImageDraw.Draw(result)
            for bbox in bounding_boxes:
                x, y, width, height = bbox
                area = width * height
                
                # Only draw boxes for significant regions
                if area > self.config.min_diff_area * 4:
                    # Use different colors based on region size
                    if area > 10000:  # Large changes
                        outline_color = (255, 0, 0, 180)  # Red
                        line_width = 3
                    elif area > 2500:  # Medium changes
                        outline_color = (255, 165, 0, 160)  # Orange
                        line_width = 2
                    else:  # Small changes
                        outline_color = (255, 255, 0, 140)  # Yellow
                        line_width = 1
                    
                    draw.rectangle(
                        [x, y, x + width - 1, y + height - 1],
                        outline=outline_color,
                        width=line_width
                    )
        
        return result
    
    def create_raw_diff(self, mask: Image.Image) -> Image.Image:
        """
        Create raw diff image (heatmap or grayscale visualization)
        
        Args:
            mask: Binary difference mask
            
        Returns:
            Raw diff visualization
        """
        if self.config.enable_heatmap:
            # Create heatmap visualization
            mask_array = np.array(mask)
            
            # Create RGB heatmap (red for differences)
            heatmap = np.zeros((*mask_array.shape, 3), dtype=np.uint8)
            heatmap[mask_array > 0] = [255, 0, 0]  # Red for differences
            
            return Image.fromarray(heatmap, 'RGB')
        else:
            # Return grayscale mask
            return mask.convert('RGB')
    
    def calculate_metrics(self, mask: Image.Image, bounding_boxes: List[List[int]]) -> Dict:
        """
        Calculate diff metrics from mask and bounding boxes
        
        Args:
            mask: Binary difference mask
            bounding_boxes: List of bounding boxes
            
        Returns:
            Dictionary with metrics
        """
        mask_array = np.array(mask)
        total_pixels = mask_array.size
        changed_pixels = np.sum(mask_array > 0)
        
        # Calculate percentage
        mismatch_pct = round((changed_pixels / total_pixels) * 100, 3) if total_pixels > 0 else 0.0
        
        # Find largest region
        largest_area = 0
        if bounding_boxes:
            largest_area = max(bbox[2] * bbox[3] for bbox in bounding_boxes)
        
        return {
            'diff_pixels_changed': int(changed_pixels),
            'diff_mismatch_pct': float(mismatch_pct),
            'diff_bounding_boxes': bounding_boxes,
            'largest_region_area': largest_area
        }
    
    def validate_images_for_diff(self, img1: Image.Image, img2: Image.Image) -> Tuple[bool, str]:
        """
        Validate images before generating diff
        
        Args:
            img1: First image
            img2: Second image
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check if images exist
        if not img1 or not img2:
            return False, "One or both images are missing"
        
        # Check image sizes
        if img1.size != img2.size:
            return False, f"Images have different sizes: {img1.size} vs {img2.size}"
        
        # Check image modes
        if img1.mode != img2.mode:
            # This is not necessarily an error, but good to log
            self.logger.warning(f"Images have different modes: {img1.mode} vs {img2.mode}")
        
        return True, ""
    
    def get_diff_paths(self, project_id: int, page_path: str, viewport: str = None,
                      process_timestamp: str = None) -> Tuple[Path, Path]:
        """
        Get file paths for diff images using new structure
        
        Args:
            project_id: Project ID
            page_path: Page path for slugification
            viewport: Viewport type (desktop, tablet, mobile) or None for legacy
            process_timestamp: Process timestamp (YYYYMMDD-HHmmss) or None for legacy
            
        Returns:
            Tuple of (highlighted_diff_path, raw_diff_path)
        """
        if viewport and process_timestamp:
            # New structure: use path manager
            _, _, diff_path = self.path_manager.get_screenshot_paths(
                project_id, process_timestamp, page_path, viewport
            )
            # For now, return same path for both highlighted and raw (can be extended later)
            return diff_path, diff_path
        else:
            # Legacy structure
            from screenshot.screenshot_service import ScreenshotService
            
            # Use same slugification as screenshot service
            screenshot_service = ScreenshotService()
            slug = screenshot_service.slugify_path(page_path)
            
            project_dir = Path(self.config.output_dir) / str(project_id)
            project_dir.mkdir(parents=True, exist_ok=True)
            
            highlighted_path = project_dir / f"{slug}_diff.png"
            raw_path = project_dir / f"{slug}_diff_raw.png"
            
            return highlighted_path, raw_path
    
    def process_page_diff(self, page_id: int, viewport: str = 'desktop',
                         process_timestamp: str = None) -> bool:
        """
        Process visual diff for a single page
        
        Args:
            page_id: ProjectPage ID
            viewport: Viewport type (desktop, tablet, mobile)
            process_timestamp: Process timestamp for new structure (None for legacy)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get page from database
            page = db.session.get(ProjectPage, page_id)
            if not page:
                self.logger.error(f"Page {page_id} not found")
                return False
            
            if process_timestamp:
                # New structure: get paths from path manager
                production_path, staging_path, diff_path = self.path_manager.get_screenshot_paths(
                    page.project_id, process_timestamp, page.path, viewport
                )
            else:
                # Legacy structure: check if screenshots exist
                if not page.staging_screenshot_path or not page.production_screenshot_path:
                    self.logger.error(f"Missing screenshot paths for page {page_id}")
                    page.status = 'diff_failed'
                    page.diff_error = "Missing screenshot paths"
                    db.session.commit()
                    return False
                
                # Construct full paths to screenshots
                staging_path = Path("screenshots") / page.staging_screenshot_path
                production_path = Path("screenshots") / page.production_screenshot_path
            
            # Check if files exist
            if not staging_path.exists() or not production_path.exists():
                self.logger.error(f"Screenshot files not found for page {page_id}")
                page.status = 'diff_failed'
                page.diff_error = "Screenshot files not found"
                db.session.commit()
                return False
            
            self.logger.info(f"Processing diff for page: {page.path} ({viewport} viewport)")
            
            # Load images
            staging_img = Image.open(staging_path)
            production_img = Image.open(production_path)
            
            # Normalize images
            norm_staging, norm_production = self.normalize_images(staging_img, production_img)
            
            # Compute difference mask
            diff_mask = self.compute_diff_mask(norm_staging, norm_production)
            
            # Extract bounding boxes
            bounding_boxes = self.extract_bounding_boxes(diff_mask)
            
            # Calculate metrics
            metrics = self.calculate_metrics(diff_mask, bounding_boxes)
            
            # Create diff images with enhanced highlighting
            highlighted_diff = self.create_highlighted_diff(norm_staging, norm_production, diff_mask, bounding_boxes)
            raw_diff = self.create_raw_diff(diff_mask)
            
            # Get output paths
            if process_timestamp:
                # New structure: save to diff path
                highlighted_diff.save(diff_path, 'PNG')
                # For now, save raw diff to same location (can be extended later)
                raw_diff.save(diff_path, 'PNG')
                
                # Update database with relative path
                relative_diff_path = self.path_manager.get_relative_path(diff_path)
                setattr(page, f'diff_image_path_{viewport}', relative_diff_path)
                setattr(page, f'diff_mismatch_pct_{viewport}', metrics['diff_mismatch_pct'])
                setattr(page, f'diff_pixels_changed_{viewport}', metrics['diff_pixels_changed'])
                
                # Also update legacy fields for backward compatibility (use desktop as default)
                if viewport == 'desktop':
                    page.diff_image_path = relative_diff_path
                    page.diff_mismatch_pct = metrics['diff_mismatch_pct']
                    page.diff_pixels_changed = metrics['diff_pixels_changed']
                    page.diff_bounding_boxes = metrics['diff_bounding_boxes']
            else:
                # Legacy structure
                highlighted_path, raw_path = self.get_diff_paths(page.project_id, page.path)
                
                # Save images
                highlighted_diff.save(highlighted_path, 'PNG')
                raw_diff.save(raw_path, 'PNG')
                
                # Update database
                page.diff_image_path = str(highlighted_path.relative_to(Path(self.config.output_dir)))
                page.diff_raw_image_path = str(raw_path.relative_to(Path(self.config.output_dir)))
                page.diff_mismatch_pct = metrics['diff_mismatch_pct']
                page.diff_pixels_changed = metrics['diff_pixels_changed']
                page.diff_bounding_boxes = metrics['diff_bounding_boxes']
            
            page.diff_generated_at = datetime.utcnow()
            page.diff_error = None
            page.status = 'diff_generated'
            
            db.session.commit()
            
            self.logger.info(f"Successfully generated diff for page: {page.path} ({viewport} viewport) "
                           f"({metrics['diff_mismatch_pct']}% changed, {len(bounding_boxes)} regions)")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error processing diff for page {page_id}: {str(e)}")
            try:
                page = db.session.get(ProjectPage, page_id)
                if page:
                    page.status = 'diff_failed'
                    page.diff_error = str(e)
                    db.session.commit()
            except:
                db.session.rollback()
            return False
    
    def process_project_diffs(self, project_id: int, page_ids: Optional[List[int]] = None,
                            retry_failed: bool = False, scheduler=None,
                            process_timestamp: str = None, viewports: List[str] = None) -> Tuple[int, int]:
        """
        Process visual diffs for all pages in a project
        
        Args:
            project_id: Project ID
            page_ids: Optional list of specific page IDs to process
            retry_failed: Whether to retry previously failed pages
            scheduler: Optional scheduler for job control
            process_timestamp: Process timestamp for new structure (None for legacy)
            viewports: List of viewports to process (default: all)
            
        Returns:
            Tuple of (successful_count, failed_count)
        """
        try:
            # Default viewports
            if viewports is None:
                viewports = ['desktop', 'tablet', 'mobile']
            
            # Generate process timestamp if not provided
            if process_timestamp is None:
                process_timestamp = self.path_manager.generate_process_timestamp()
            
            # Build query for pages to process
            query = ProjectPage.query.filter_by(project_id=project_id)
            
            if page_ids:
                query = query.filter(ProjectPage.id.in_(page_ids))
            else:
                # Default: process pages with completed screenshots
                if retry_failed:
                    query = query.filter(ProjectPage.status.in_(['screenshot_complete', 'diff_failed']))
                else:
                    query = query.filter_by(status='screenshot_complete')
            
            pages = query.all()
            
            if not pages:
                self.logger.info(f"No pages to process for project {project_id}")
                return (0, 0)
            
            self.logger.info(f"Starting diff generation for {len(pages)} pages in project {project_id} (timestamp: {process_timestamp})")
            
            successful_count = 0
            failed_count = 0
            
            # Process in batches
            for i in range(0, len(pages), self.config.batch_size):
                # Check for stop signal
                if scheduler and hasattr(scheduler, '_should_stop') and scheduler._should_stop(project_id):
                    self.logger.info(f"Diff generation stopped by user signal for project {project_id}")
                    break
                
                # Handle pause signal
                if scheduler and hasattr(scheduler, '_should_pause'):
                    while scheduler._should_pause(project_id):
                        self.logger.info(f"Diff generation paused for project {project_id}")
                        import time
                        time.sleep(1)
                        
                        # Check for stop while paused
                        if scheduler._should_stop(project_id):
                            self.logger.info(f"Diff generation stopped while paused for project {project_id}")
                            return (successful_count, failed_count)
                
                batch = pages[i:i + self.config.batch_size]
                self.logger.info(f"Processing batch {i//self.config.batch_size + 1}: pages {i+1}-{min(i+len(batch), len(pages))}")
                
                for page in batch:
                    # Update page status to indicate processing
                    page.status = 'diff_running'
                    db.session.commit()
                    
                    # Process diffs for all viewports
                    page_success = True
                    for viewport in viewports:
                        success = self.process_page_diff(page.id, viewport, process_timestamp)
                        if not success:
                            page_success = False
                    
                    if page_success:
                        successful_count += 1
                    else:
                        failed_count += 1
            
            self.logger.info(
                f"Diff generation completed for project {project_id}. "
                f"Successful: {successful_count}, Failed: {failed_count}"
            )
            
            return (successful_count, failed_count)
            
        except Exception as e:
            self.logger.error(f"Error processing project diffs for project {project_id}: {str(e)}")
            return (0, len(pages) if 'pages' in locals() else 0)


class DiffEngine:
    """Wrapper class for diff generation with job control integration"""
    
    def __init__(self):
        """Initialize the diff engine wrapper"""
        self.visual_diff_engine = VisualDiffEngine()
        self.logger = logging.getLogger(__name__)
    
    def run_generate_project_diffs(self, project_id: int, scheduler=None) -> Tuple[int, int]:
        """
        Run diff generation for a project with job control integration
        
        Args:
            project_id: Project ID to generate diffs for
            scheduler: Optional scheduler instance for job control
            
        Returns:
            Tuple of (successful_count, failed_count)
        """
        try:
            self.logger.info(f"Starting diff generation for project {project_id}")
            
            # Update scheduler progress if available
            if scheduler and hasattr(scheduler, 'progress_info') and project_id in scheduler.progress_info:
                scheduler.progress_info[project_id].update({
                    'stage': 'processing',
                    'progress': 30,
                    'message': 'Initializing diff generation...'
                })
            
            # Process diffs for the project
            successful_count, failed_count = self.visual_diff_engine.process_project_diffs(
                project_id=project_id,
                scheduler=scheduler
            )
            
            # Update scheduler progress if available
            if scheduler and hasattr(scheduler, 'progress_info') and project_id in scheduler.progress_info:
                scheduler.progress_info[project_id].update({
                    'stage': 'completed',
                    'progress': 90,
                    'message': f'Diff generation completed. Successful: {successful_count}, Failed: {failed_count}'
                })
            
            self.logger.info(f"Diff generation completed for project {project_id}. "
                           f"Successful: {successful_count}, Failed: {failed_count}")
            
            return (successful_count, failed_count)
            
        except Exception as e:
            self.logger.error(f"Error in diff generation for project {project_id}: {str(e)}")
            
            # Update scheduler progress if available
            if scheduler and hasattr(scheduler, 'progress_info') and project_id in scheduler.progress_info:
                scheduler.progress_info[project_id].update({
                    'stage': 'error',
                    'progress': 0,
                    'message': f'Error: {str(e)}'
                })
            
            return (0, 0)