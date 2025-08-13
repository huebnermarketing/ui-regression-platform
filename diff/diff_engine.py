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
    
    def __init__(self, config: Optional[DiffConfig] = None):
        """
        Initialize the diff engine
        
        Args:
            config: Configuration object, uses defaults if None
        """
        self.config = config or DiffConfig()
        self.logger = logging.getLogger(__name__)
        
        # Ensure output directory exists
        Path(self.config.output_dir).mkdir(parents=True, exist_ok=True)
    
    def normalize_images(self, img1: Image.Image, img2: Image.Image) -> Tuple[Image.Image, Image.Image]:
        """
        Normalize two images to same size and format for comparison
        
        Args:
            img1: First image (staging)
            img2: Second image (production)
            
        Returns:
            Tuple of normalized images
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
        
        # Paste original images at top-left (0,0)
        normalized_img1.paste(img1, (0, 0))
        normalized_img2.paste(img2, (0, 0))
        
        # Apply optional blur for anti-alias noise reduction
        if self.config.enable_blur:
            normalized_img1 = normalized_img1.filter(ImageFilter.GaussianBlur(radius=self.config.blur_radius))
            normalized_img2 = normalized_img2.filter(ImageFilter.GaussianBlur(radius=self.config.blur_radius))
        
        return normalized_img1, normalized_img2
    
    def compute_diff_mask(self, img1: Image.Image, img2: Image.Image) -> Image.Image:
        """
        Compute binary mask of differences between two images
        
        Args:
            img1: First normalized image
            img2: Second normalized image
            
        Returns:
            Binary mask image (L mode, 0/255 values)
        """
        # Compute absolute difference
        diff = ImageChops.difference(img1, img2)
        
        # Convert to grayscale for thresholding
        diff_gray = diff.convert('L')
        
        # Apply threshold to create binary mask
        threshold = self.config.per_pixel_threshold
        diff_array = np.array(diff_gray)
        
        # Create binary mask: pixels above threshold become 255, others become 0
        mask_array = np.where(diff_array > threshold, 255, 0).astype(np.uint8)
        
        # Apply morphological operations to clean up the mask
        if self.config.dilate_iterations > 0:
            # Dilate to close gaps
            mask_array = ndimage.binary_dilation(
                mask_array > 0, 
                iterations=self.config.dilate_iterations
            ).astype(np.uint8) * 255
        
        if self.config.erode_iterations > 0:
            # Erode to tidy edges
            mask_array = ndimage.binary_erosion(
                mask_array > 0, 
                iterations=self.config.erode_iterations
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
    
    def create_highlighted_diff(self, base_image: Image.Image, mask: Image.Image, 
                              bounding_boxes: List[List[int]]) -> Image.Image:
        """
        Create highlighted diff image with red overlay on differences
        
        Args:
            base_image: Base image (usually production)
            mask: Binary difference mask
            bounding_boxes: List of bounding boxes to highlight
            
        Returns:
            Highlighted diff image
        """
        # Convert base image to RGBA if needed
        if base_image.mode != 'RGBA':
            base_image = base_image.convert('RGBA')
        
        # Create a copy for modification
        result = base_image.copy()
        
        # Create red overlay for differences
        overlay = Image.new('RGBA', base_image.size, (255, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        
        # Apply red overlay where mask is white
        mask_array = np.array(mask)
        overlay_array = np.array(overlay)
        
        # Set red overlay with alpha where differences exist
        red_mask = mask_array > 0
        overlay_array[red_mask] = [255, 0, 0, self.config.overlay_alpha]
        
        overlay = Image.fromarray(overlay_array, 'RGBA')
        
        # Composite overlay onto base image
        result = Image.alpha_composite(result, overlay)
        
        # Draw bounding box rectangles
        draw = ImageDraw.Draw(result)
        for bbox in bounding_boxes:
            x, y, width, height = bbox
            # Draw semi-transparent rectangle outline
            draw.rectangle(
                [x, y, x + width - 1, y + height - 1],
                outline=(255, 0, 0, 200),
                width=2
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
    
    def get_diff_paths(self, project_id: int, page_path: str) -> Tuple[Path, Path]:
        """
        Get file paths for diff images
        
        Args:
            project_id: Project ID
            page_path: Page path for slugification
            
        Returns:
            Tuple of (highlighted_diff_path, raw_diff_path)
        """
        from screenshot.screenshot_service import ScreenshotService
        
        # Use same slugification as screenshot service
        screenshot_service = ScreenshotService()
        slug = screenshot_service.slugify_path(page_path)
        
        project_dir = Path(self.config.output_dir) / str(project_id)
        project_dir.mkdir(parents=True, exist_ok=True)
        
        highlighted_path = project_dir / f"{slug}_diff.png"
        raw_path = project_dir / f"{slug}_diff_raw.png"
        
        return highlighted_path, raw_path
    
    def process_page_diff(self, page_id: int) -> bool:
        """
        Process visual diff for a single page
        
        Args:
            page_id: ProjectPage ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get page from database
            page = ProjectPage.query.get(page_id)
            if not page:
                self.logger.error(f"Page {page_id} not found")
                return False
            
            # Check if screenshots exist
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
            
            self.logger.info(f"Processing diff for page: {page.path}")
            
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
            
            # Create diff images
            highlighted_diff = self.create_highlighted_diff(norm_production, diff_mask, bounding_boxes)
            raw_diff = self.create_raw_diff(diff_mask)
            
            # Get output paths
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
            
            self.logger.info(f"Successfully generated diff for page: {page.path} "
                           f"({metrics['diff_mismatch_pct']}% changed, {len(bounding_boxes)} regions)")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error processing diff for page {page_id}: {str(e)}")
            try:
                page = ProjectPage.query.get(page_id)
                if page:
                    page.status = 'diff_failed'
                    page.diff_error = str(e)
                    db.session.commit()
            except:
                db.session.rollback()
            return False
    
    def process_project_diffs(self, project_id: int, page_ids: Optional[List[int]] = None, 
                            retry_failed: bool = False, scheduler=None) -> Tuple[int, int]:
        """
        Process visual diffs for all pages in a project
        
        Args:
            project_id: Project ID
            page_ids: Optional list of specific page IDs to process
            retry_failed: Whether to retry previously failed pages
            scheduler: Optional scheduler for job control
            
        Returns:
            Tuple of (successful_count, failed_count)
        """
        try:
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
            
            self.logger.info(f"Starting diff generation for {len(pages)} pages in project {project_id}")
            
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
                    
                    # Process the diff
                    success = self.process_page_diff(page.id)
                    
                    if success:
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