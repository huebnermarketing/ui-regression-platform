"""
Dynamic Asset Resolver Route
Single endpoint for serving all screenshots/diffs with strict naming rules and fallback logic
"""

from flask import send_file, abort, current_app
from flask_login import login_required, current_user
from pathlib import Path
from typing import Optional
import mimetypes

from models import db
from models.project import Project
from utils.path_resolver import PathResolver


def register_asset_resolver_routes(app):
    """Register the dynamic asset resolver routes"""
    
    # Initialize path resolver
    path_resolver = PathResolver()
    
    @app.route('/assets/runs/<project_id>/<run_id>/<viewport>/<filename>')
    @login_required
    def serve_asset(project_id: str, run_id: str, viewport: str, filename: str):
        """
        Universal dynamic asset resolver
        
        Route: /assets/runs/<project_id>/<run_id>/<viewport>/<page_slug>-<env>.png
        
        Features:
        - Strict canonical naming with fallback to legacy patterns
        - Automatic placeholder serving for missing files
        - Security: User access verification
        - Supports all image formats (PNG, JPG, WebP)
        
        Args:
            project_id: Project ID (normalized to lowercase)
            run_id: Run ID timestamp (normalized to lowercase)
            viewport: Viewport type (normalized to lowercase)
            filename: Filename in format {page_slug}-{environment}.{ext}
        """
        try:
            # Normalize inputs
            project_id = path_resolver.normalize_component(project_id)
            run_id = path_resolver.normalize_component(run_id)
            viewport = path_resolver.normalize_component(viewport)
            
            # Verify user has access to this project
            try:
                project_id_int = int(project_id)
            except ValueError:
                current_app.logger.error(f"Invalid project_id: {project_id}")
                return _serve_placeholder("error")
            
            project = Project.query.filter_by(
                id=project_id_int,
                user_id=current_user.id
            ).first()
            
            if not project:
                current_app.logger.warning(f"Access denied for project {project_id} by user {current_user.id}")
                return _serve_placeholder("error")
            
            # Parse filename to extract page_slug and environment
            parsed = _parse_filename(filename)
            if not parsed:
                current_app.logger.error(f"Invalid filename format: {filename}")
                return _serve_placeholder("error")
            
            page_slug = parsed['page_slug']
            environment = parsed['environment']
            extension = parsed['extension']
            
            # Validate components
            if viewport not in path_resolver.viewports:
                current_app.logger.error(f"Invalid viewport: {viewport}")
                return _serve_placeholder("error")
            
            if environment not in path_resolver.environments:
                current_app.logger.error(f"Invalid environment: {environment}")
                return _serve_placeholder("error")
            
            # Handle "current" run ID by finding the most recent run
            actual_run_id = run_id
            if run_id.lower() == 'current':
                # Get the most recent run for this project
                recent_runs = path_resolver.list_project_runs(project_id_int)
                if recent_runs:
                    actual_run_id = recent_runs[0]  # Most recent run (sorted newest first)
                    current_app.logger.info(f"Resolved 'current' run ID to: {actual_run_id}")
                else:
                    current_app.logger.warning(f"No runs found for project {project_id_int}, cannot resolve 'current'")
                    return _serve_placeholder("not_found")
            
            # Try to resolve the file
            resolved_path = path_resolver.resolve_file(
                project_id_int, actual_run_id, viewport, page_slug, environment
            )
            
            if resolved_path and resolved_path.exists():
                # File found - serve it
                mimetype = _get_mimetype(resolved_path)
                current_app.logger.info(f"Serving resolved file: {resolved_path}")
                return send_file(str(resolved_path), mimetype=mimetype)
            
            # File not found - determine appropriate placeholder
            placeholder_type = _determine_placeholder_type(environment, run_id)
            current_app.logger.info(f"File not found, serving placeholder: {placeholder_type}")
            return _serve_placeholder(placeholder_type)
            
        except Exception as e:
            current_app.logger.error(f"Error in asset resolver: {str(e)}")
            return _serve_placeholder("error")
    
    @app.route('/assets/placeholder/<placeholder_type>')
    def serve_placeholder_direct(placeholder_type: str):
        """
        Direct placeholder serving endpoint
        
        Args:
            placeholder_type: Type of placeholder (not_found, no_baseline, processing, error)
        """
        return _serve_placeholder(placeholder_type)
    
    def _parse_filename(filename: str) -> Optional[dict]:
        """
        Parse filename to extract components
        
        Expected format: {page_slug}-{environment}.{ext}
        
        Args:
            filename: Filename to parse
            
        Returns:
            Optional[dict]: Parsed components or None if invalid
        """
        # Split by extension
        parts = filename.rsplit('.', 1)
        if len(parts) != 2:
            return None
        
        name_part = parts[0]
        extension = parts[1].lower()
        
        # Split by last dash to get environment
        if '-' not in name_part:
            return None
        
        page_slug, environment = name_part.rsplit('-', 1)
        
        # Validate extension
        valid_extensions = ['png', 'jpg', 'jpeg', 'webp', 'gif']
        if extension not in valid_extensions:
            return None
        
        return {
            'page_slug': page_slug.lower(),
            'environment': environment.lower(),
            'extension': extension
        }
    
    def _get_mimetype(file_path: Path) -> str:
        """
        Get MIME type for file
        
        Args:
            file_path: Path to file
            
        Returns:
            str: MIME type
        """
        mimetype, _ = mimetypes.guess_type(str(file_path))
        if mimetype:
            return mimetype
        
        # Fallback based on extension
        ext = file_path.suffix.lower()
        mime_map = {
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.webp': 'image/webp',
            '.gif': 'image/gif'
        }
        
        return mime_map.get(ext, 'application/octet-stream')
    
    def _determine_placeholder_type(environment: str, run_id: str) -> str:
        """
        Determine appropriate placeholder type based on context
        
        Args:
            environment: Environment (staging, production, diff)
            run_id: Run ID
            
        Returns:
            str: Placeholder type
        """
        if environment == 'diff':
            # For diff images, could be no differences found
            return 'no_baseline'
        
        # For screenshots, could be not captured yet
        return 'not_found'
    
    def _serve_placeholder(placeholder_type: str):
        """
        Serve placeholder image
        
        Args:
            placeholder_type: Type of placeholder
            
        Returns:
            Flask response with placeholder image
        """
        try:
            placeholder_path = path_resolver.get_placeholder_path(placeholder_type)
            
            # If placeholder doesn't exist, create a simple one
            if not placeholder_path or not placeholder_path.exists():
                current_app.logger.info(f"Creating placeholder for type: {placeholder_type}")
                placeholder_path = _create_placeholder(placeholder_type)
            
            if placeholder_path and placeholder_path.exists():
                current_app.logger.info(f"Serving placeholder: {placeholder_path}")
                return send_file(str(placeholder_path), mimetype='image/png')
            else:
                # Last resort - create a minimal placeholder in memory
                current_app.logger.warning(f"Could not create placeholder file, generating minimal response")
                return _create_minimal_placeholder_response(placeholder_type)
                
        except Exception as e:
            current_app.logger.error(f"Error serving placeholder {placeholder_type}: {str(e)}")
            return _create_minimal_placeholder_response("error")
    
    def _create_minimal_placeholder_response(placeholder_type: str):
        """
        Create a minimal placeholder response when file creation fails
        
        Args:
            placeholder_type: Type of placeholder
            
        Returns:
            Flask response with minimal placeholder
        """
        try:
            from flask import Response
            import base64
            
            # Create a minimal 1x1 PNG in base64
            minimal_png = base64.b64decode(
                'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=='
            )
            
            return Response(
                minimal_png,
                mimetype='image/png',
                headers={
                    'Cache-Control': 'no-cache, no-store, must-revalidate',
                    'Pragma': 'no-cache',
                    'Expires': '0'
                }
            )
        except Exception as e:
            current_app.logger.error(f"Error creating minimal placeholder: {str(e)}")
            abort(500)
    
    def _create_placeholder(placeholder_type: str) -> Optional[Path]:
        """
        Create a simple placeholder image if none exists
        
        Args:
            placeholder_type: Type of placeholder
            
        Returns:
            Optional[Path]: Path to created placeholder or None
        """
        try:
            from PIL import Image, ImageDraw, ImageFont
            
            # Create placeholder directory
            placeholder_dir = Path("static") / "placeholders"
            placeholder_dir.mkdir(parents=True, exist_ok=True)
            
            # Create 400x300 placeholder image
            img = Image.new('RGB', (400, 300), color='#f8f9fa')
            draw = ImageDraw.Draw(img)
            
            # Placeholder messages
            messages = {
                'not_found': ['Screenshot', 'Not Found'],
                'no_baseline': ['No Baseline', 'Available'],
                'processing': ['Processing...', 'Please Wait'],
                'error': ['Error', 'Loading Image']
            }
            
            lines = messages.get(placeholder_type, ['Image', 'Unavailable'])
            
            # Try to use a font, fallback to default
            try:
                font = ImageFont.truetype("arial.ttf", 24)
            except:
                font = ImageFont.load_default()
            
            # Draw text
            y_offset = 120
            for line in lines:
                bbox = draw.textbbox((0, 0), line, font=font)
                text_width = bbox[2] - bbox[0]
                x = (400 - text_width) // 2
                draw.text((x, y_offset), line, fill='#6c757d', font=font)
                y_offset += 40
            
            # Save placeholder
            placeholder_path = placeholder_dir / f"{placeholder_type}.png"
            img.save(placeholder_path, 'PNG')
            
            return placeholder_path
            
        except Exception as e:
            current_app.logger.error(f"Error creating placeholder {placeholder_type}: {str(e)}")
            return None