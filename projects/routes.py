from flask import render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import login_required, current_user
from models import db
from models.project import Project, ProjectPage
from urllib.parse import urlparse
import re
import os
from pathlib import Path

def register_project_routes(app, crawler_scheduler):
    @app.route('/projects')
    @login_required
    def projects_list():
        """List all projects for the current user with job status"""
        projects = Project.query.filter_by(user_id=current_user.id).order_by(Project.created_at.desc()).all()
        
        # Get job status for each project
        from models.crawl_job import CrawlJob
        projects_with_status = []
        
        for project in projects:
            # Get scheduler status
            scheduler_status = crawler_scheduler.get_job_status(project.id)
            
            # Get the latest CrawlJob from database for accurate status
            latest_job = CrawlJob.query.filter_by(project_id=project.id).order_by(CrawlJob.created_at.desc()).first()
            
            # Determine the actual job status by combining scheduler and database info
            if scheduler_status.get('status') == 'scheduled':
                # Job is actively running in scheduler
                job_status = {'status': 'scheduled', 'db_status': latest_job.status if latest_job else None}
            elif latest_job:
                # Use database status when not actively scheduled
                job_status = {'status': latest_job.status, 'db_status': latest_job.status}
            else:
                # No job found
                job_status = {'status': 'not_scheduled', 'db_status': None}
            
            # Get page count
            page_count = ProjectPage.query.filter_by(project_id=project.id).count()
            
            projects_with_status.append({
                'project': project,
                'job_status': job_status,
                'page_count': page_count
            })
        
        return render_template('projects/list.html', projects_with_status=projects_with_status)
    
    @app.route('/projects/add', methods=['GET', 'POST'])
    @login_required
    def add_project():
        """Add a new project"""
        if request.method == 'POST':
            name = request.form.get('name', '').strip()
            staging_url = request.form.get('staging_url', '').strip()
            production_url = request.form.get('production_url', '').strip()
            
            # Validation
            if not name:
                flash('Project name is required', 'error')
                return render_template('projects/add.html')
            
            if not staging_url or not production_url:
                flash('Both staging and production URLs are required', 'error')
                return render_template('projects/add.html')
            
            # Validate URL format
            if not _is_valid_url(staging_url):
                flash('Staging URL must start with http:// or https://', 'error')
                return render_template('projects/add.html')
            
            if not _is_valid_url(production_url):
                flash('Production URL must start with http:// or https://', 'error')
                return render_template('projects/add.html')
            
            # Check if project name already exists for this user
            existing_project = Project.query.filter_by(
                name=name, 
                user_id=current_user.id
            ).first()
            
            if existing_project:
                flash('A project with this name already exists', 'error')
                return render_template('projects/add.html')
            
            # Create new project
            try:
                project = Project(
                    name=name,
                    staging_url=staging_url,
                    production_url=production_url,
                    user_id=current_user.id
                )
                db.session.add(project)
                db.session.commit()
                
                flash('Project created successfully!', 'success')
                return redirect(url_for('project_details', project_id=project.id))
                
            except Exception as e:
                db.session.rollback()
                flash('Error creating project. Please try again.', 'error')
                app.logger.error(f"Error creating project: {str(e)}")
                return render_template('projects/add.html')
        
        return render_template('projects/add.html')
    
    @app.route('/projects/<int:project_id>')
    @login_required
    def project_details(project_id):
        """View project details and pages with search, filter, and pagination"""
        project = Project.query.filter_by(
            id=project_id,
            user_id=current_user.id
        ).first_or_404()
        
        # Get query parameters for search, filter, and pagination
        search_query = request.args.get('search', '').strip()
        status_filter = request.args.get('status', '')
        page_num = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)  # Default 20 items per page
        
        # Build base query
        query = ProjectPage.query.filter_by(project_id=project_id)
        
        # Apply search filter
        if search_query:
            query = query.filter(
                db.or_(
                    ProjectPage.path.ilike(f'%{search_query}%'),
                    ProjectPage.page_name.ilike(f'%{search_query}%'),
                    ProjectPage.staging_url.ilike(f'%{search_query}%'),
                    ProjectPage.production_url.ilike(f'%{search_query}%')
                )
            )
        
        # Apply status filter
        if status_filter:
            query = query.filter(ProjectPage.status == status_filter)
        
        # Order by last_crawled (newest first), then by path (MySQL compatible)
        query = query.order_by(ProjectPage.last_crawled.desc(), ProjectPage.path)
        
        # Paginate results
        pagination = query.paginate(
            page=page_num,
            per_page=per_page,
            error_out=False
        )
        
        pages = pagination.items
        
        # Get enhanced job status (combining scheduler and database info)
        scheduler_status = crawler_scheduler.get_job_status(project_id)
        
        # Get the latest CrawlJob from database for accurate status
        from models.crawl_job import CrawlJob
        latest_job = CrawlJob.query.filter_by(project_id=project_id).order_by(CrawlJob.created_at.desc()).first()
        
        # Determine the actual job status by combining scheduler and database info
        if scheduler_status.get('status') == 'scheduled':
            # Job is actively running in scheduler
            job_status = {'status': 'scheduled', 'db_status': latest_job.status if latest_job else None}
        elif latest_job:
            # Use database status when not actively scheduled
            job_status = {'status': latest_job.status, 'db_status': latest_job.status}
        else:
            # No job found
            job_status = {'status': 'not_scheduled', 'db_status': None}
        
        # Get available statuses for filter dropdown
        available_statuses = db.session.query(ProjectPage.status).filter_by(project_id=project_id).distinct().all()
        available_statuses = [status[0] for status in available_statuses]
        
        return render_template('projects/details.html',
                             project=project,
                             pages=pages,
                             pagination=pagination,
                             job_status=job_status,
                             search_query=search_query,
                             status_filter=status_filter,
                             available_statuses=available_statuses,
                             per_page=per_page)
    
    @app.route('/projects/<int:project_id>/crawl', methods=['POST'])
    @login_required
    def start_crawl(project_id):
        """Start crawling for a project"""
        project = Project.query.filter_by(
            id=project_id, 
            user_id=current_user.id
        ).first_or_404()
        
        try:
            # Schedule the crawl job
            crawler_scheduler.schedule_crawl(project_id)
            flash('Crawling started! This may take a few minutes.', 'success')
            
        except Exception as e:
            flash('Error starting crawl. Please try again.', 'error')
            app.logger.error(f"Error starting crawl for project {project_id}: {str(e)}")
        
        return redirect(url_for('project_details', project_id=project_id))
    
    @app.route('/projects/<int:project_id>/status')
    @login_required
    def crawl_status(project_id):
        """Get crawl status for a project with progress information (AJAX endpoint)"""
        project = Project.query.filter_by(
            id=project_id,
            user_id=current_user.id
        ).first_or_404()
        
        # Get scheduler status
        scheduler_status = crawler_scheduler.get_job_status(project_id)
        page_count = ProjectPage.query.filter_by(project_id=project_id).count()
        
        # Get the latest CrawlJob from database for accurate status
        from models.crawl_job import CrawlJob
        latest_job = CrawlJob.query.filter_by(project_id=project_id).order_by(CrawlJob.created_at.desc()).first()
        
        # Determine the actual job status by combining scheduler and database info
        if scheduler_status.get('status') == 'scheduled':
            # Job is actively running in scheduler
            job_status = {'status': 'scheduled', 'db_status': latest_job.status if latest_job else None}
        elif latest_job:
            # Use database status when not actively scheduled
            job_status = {'status': latest_job.status, 'db_status': latest_job.status}
        else:
            # No job found
            job_status = {'status': 'not_scheduled', 'db_status': None}
        
        # Get progress information if crawling
        progress_info = {}
        if scheduler_status.get('status') == 'scheduled':
            # Get additional progress details from crawler if available
            progress_info = crawler_scheduler.get_progress_info(project_id)
        
        return jsonify({
            'job_status': job_status,
            'page_count': page_count,
            'progress': progress_info,
            'latest_job': {
                'id': latest_job.id if latest_job else None,
                'status': latest_job.status if latest_job else None,
                'created_at': latest_job.created_at.isoformat() if latest_job else None,
                'completed_at': latest_job.completed_at.isoformat() if latest_job and latest_job.completed_at else None,
                'error_message': latest_job.error_message if latest_job else None
            }
        })
    
    @app.route('/projects/<int:project_id>/cancel', methods=['POST'])
    @login_required
    def cancel_crawl(project_id):
        """Cancel crawling for a project"""
        project = Project.query.filter_by(
            id=project_id, 
            user_id=current_user.id
        ).first_or_404()
        
        try:
            success = crawler_scheduler.cancel_crawl(project_id)
            if success:
                flash('Crawl cancelled successfully.', 'info')
            else:
                flash('No active crawl job found.', 'warning')
                
        except Exception as e:
            flash('Error cancelling crawl.', 'error')
            app.logger.error(f"Error cancelling crawl for project {project_id}: {str(e)}")
        
        return redirect(url_for('project_details', project_id=project_id))
    
    @app.route('/projects/<int:project_id>/delete', methods=['POST'])
    @login_required
    def delete_project(project_id):
        """Delete a project and all its pages"""
        project = Project.query.filter_by(
            id=project_id, 
            user_id=current_user.id
        ).first_or_404()
        
        try:
            # Cancel any running crawl jobs
            crawler_scheduler.cancel_crawl(project_id)
            
            # Delete project (pages will be deleted due to cascade)
            db.session.delete(project)
            db.session.commit()
            
            flash(f'Project "{project.name}" deleted successfully.', 'success')
            
        except Exception as e:
            db.session.rollback()
            flash('Error deleting project.', 'error')
            app.logger.error(f"Error deleting project {project_id}: {str(e)}")
        
        return redirect(url_for('projects_list'))
    
    @app.route('/projects/<int:project_id>/capture-screenshots', methods=['POST'])
    @login_required
    def capture_screenshots(project_id):
        """Start screenshot capture for a project"""
        project = Project.query.filter_by(
            id=project_id,
            user_id=current_user.id
        ).first_or_404()
        
        try:
            # Import screenshot service
            from screenshot.screenshot_service import ScreenshotService
            
            # Check if there are pages ready for screenshot
            ready_pages = ProjectPage.query.filter(
                ProjectPage.project_id == project_id,
                ProjectPage.status.in_(['crawled', 'ready_for_screenshot'])
            ).count()
            
            if ready_pages == 0:
                flash('No pages ready for screenshot capture. Please crawl the project first.', 'warning')
                return redirect(url_for('project_details', project_id=project_id))
            
            # Schedule screenshot capture job
            crawler_scheduler.schedule_screenshot_capture(project_id)
            flash(f'Screenshot capture started for {ready_pages} pages! This may take a few minutes.', 'success')
            
        except Exception as e:
            flash('Error starting screenshot capture. Please try again.', 'error')
            app.logger.error(f"Error starting screenshot capture for project {project_id}: {str(e)}")
        
        return redirect(url_for('project_details', project_id=project_id))
    
    @app.route('/projects/<int:project_id>/capture-manual-screenshots', methods=['POST'])
    @login_required
    def capture_manual_screenshots(project_id):
        """Start manual screenshot capture for selected pages"""
        project = Project.query.filter_by(
            id=project_id,
            user_id=current_user.id
        ).first_or_404()
        
        try:
            # Get form data
            selected_pages = request.form.getlist('selected_pages')
            viewport_filter = request.form.get('viewport', '')
            
            if not selected_pages:
                flash('No pages selected for screenshot capture.', 'warning')
                return redirect(url_for('project_details', project_id=project_id))
            
            # Determine viewports to capture based on filter
            if viewport_filter and viewport_filter != '':
                selected_viewports = [viewport_filter]
            else:
                selected_viewports = ['desktop', 'tablet', 'mobile']  # Default to all if no filter
            
            # Convert page IDs to integers
            page_ids = [int(pid) for pid in selected_pages]
            
            # Import screenshot service
            from screenshot.screenshot_service import ScreenshotService
            screenshot_service = ScreenshotService()
            
            # Run manual screenshot capture (always capture both staging and production)
            import asyncio
            successful_count, failed_count = asyncio.run(
                screenshot_service.capture_manual_screenshots(
                    page_ids=page_ids,
                    viewports=selected_viewports,
                    environments=['staging', 'production']  # Always capture both
                )
            )
            
            if successful_count > 0:
                flash(f'Successfully captured screenshots for {successful_count} pages '
                      f'({len(selected_viewports)} viewports). '
                      f'Failed: {failed_count}', 'success')
            else:
                flash(f'Failed to capture screenshots. Failed: {failed_count}', 'error')
            
        except Exception as e:
            flash('Error starting manual screenshot capture. Please try again.', 'error')
            app.logger.error(f"Error starting manual screenshot capture for project {project_id}: {str(e)}")
        
        return redirect(url_for('project_details', project_id=project_id))
    
    @app.route('/projects/<int:project_id>/generate-diffs', methods=['POST'])
    @login_required
    def generate_diffs(project_id):
        """Start diff generation for a project"""
        project = Project.query.filter_by(
            id=project_id,
            user_id=current_user.id
        ).first_or_404()
        
        try:
            # Check if there are pages ready for diff generation
            ready_pages = ProjectPage.query.filter(
                ProjectPage.project_id == project_id,
                ProjectPage.status.in_(['screenshot_complete'])
            ).count()
            
            if ready_pages == 0:
                flash('No pages ready for diff generation. Please capture screenshots first.', 'warning')
                return redirect(url_for('project_details', project_id=project_id))
            
            # Schedule diff generation job
            crawler_scheduler.schedule_diff_generation(project_id)
            flash(f'Diff generation started for {ready_pages} pages! This may take a few minutes.', 'success')
            
        except Exception as e:
            flash('Error starting diff generation. Please try again.', 'error')
            app.logger.error(f"Error starting diff generation for project {project_id}: {str(e)}")
        
        return redirect(url_for('project_details', project_id=project_id))
    
    @app.route('/projects/<int:project_id>/find-difference', methods=['POST'])
    @login_required
    def find_difference(project_id):
        """Start the unified Find Difference workflow for a project"""
        project = Project.query.filter_by(
            id=project_id,
            user_id=current_user.id
        ).first_or_404()
        
        try:
            # Get form data for selected pages (if any)
            selected_pages = request.form.getlist('selected_pages')
            
            # Check if there are pages to process
            if selected_pages:
                # Process only selected pages
                page_ids = [int(pid) for pid in selected_pages]
                pages_count = len(page_ids)
                
                # Verify all selected pages belong to this project
                valid_pages = ProjectPage.query.filter(
                    ProjectPage.id.in_(page_ids),
                    ProjectPage.project_id == project_id
                ).count()
                
                if valid_pages != pages_count:
                    flash('Some selected pages are invalid.', 'error')
                    return redirect(url_for('project_details', project_id=project_id))
            else:
                # Process all pages in the project
                page_ids = None
                pages_count = ProjectPage.query.filter_by(project_id=project_id).count()
            
            if pages_count == 0:
                flash('No pages found to process. Please crawl the project first.', 'warning')
                return redirect(url_for('project_details', project_id=project_id))
            
            # Schedule Find Difference job
            crawler_scheduler.schedule_find_difference(project_id)
            
            if selected_pages:
                flash(f'Find Difference started for {pages_count} selected pages! This will capture screenshots and generate diffs for all viewports.', 'success')
            else:
                flash(f'Find Difference started for all {pages_count} pages! This will capture screenshots and generate diffs for all viewports.', 'success')
            
        except Exception as e:
            flash('Error starting Find Difference workflow. Please try again.', 'error')
            app.logger.error(f"Error starting Find Difference for project {project_id}: {str(e)}")
        
        return redirect(url_for('project_details', project_id=project_id))
    
    @app.route('/projects/<int:project_id>/manual-capture/<int:page_id>', methods=['POST'])
    @login_required
    def manual_capture_page(project_id, page_id):
        """Enhanced Manual Capture: Capture screenshots AND generate diff image in one operation"""
        try:
            # Verify project access first
            project = Project.query.filter_by(
                id=project_id,
                user_id=current_user.id
            ).first()
            
            if not project:
                return jsonify({
                    'success': False,
                    'message': 'Project not found or access denied'
                }), 404
            
            # Verify page belongs to this project
            page = ProjectPage.query.filter_by(
                id=page_id,
                project_id=project_id
            ).first()
            
            if not page:
                return jsonify({
                    'success': False,
                    'message': 'Page not found'
                }), 404
            
            # Get request parameters with proper error handling
            try:
                request_data = request.get_json() or {}
            except Exception as json_error:
                app.logger.error(f"JSON parsing error: {str(json_error)}")
                return jsonify({
                    'success': False,
                    'message': 'Invalid JSON data'
                }), 400
            
            viewports = request_data.get('viewports', ['desktop', 'tablet', 'mobile'])
            
            # Import Find Difference service with error handling
            try:
                from services.find_difference_service import FindDifferenceService
                find_diff_service = FindDifferenceService()
            except ImportError as import_error:
                app.logger.error(f"Import error for FindDifferenceService: {str(import_error)}")
                return jsonify({
                    'success': False,
                    'message': 'Service initialization failed'
                }), 500
            
            # Run enhanced capture+diff (screenshots + diff generation) with error handling
            try:
                import asyncio
                result = asyncio.run(find_diff_service.capture_and_diff(
                    project_id=project_id,
                    page_id=page_id,
                    viewports=viewports
                ))
            except Exception as capture_error:
                app.logger.error(f"Enhanced capture+diff execution error: {str(capture_error)}")
                return jsonify({
                    'success': False,
                    'message': f"Enhanced capture+diff failed: {str(capture_error)}"
                }), 500
            
            if result['success']:
                # Safely determine viewport count
                if isinstance(viewports, list):
                    viewport_count = len(viewports)
                elif isinstance(viewports, str):
                    viewport_count = 1
                else:
                    viewport_count = 3  # Default fallback
                
                # Count successful diffs
                diff_paths = result.get('diff_paths_by_viewport', {})
                successful_diffs = len([v for v in diff_paths.values() if v.get('status') == 'completed'])
                
                return jsonify({
                    'success': True,
                    'message': f"Enhanced capture+diff completed for '{page.page_name or page.path}' across {viewport_count} viewports. Generated {successful_diffs} diff images.",
                    'run_id': result['run_id'],
                    'page_id': page_id,
                    'updated_status': result['updated_status'],
                    'screenshot_paths_by_viewport': result.get('screenshot_paths_by_viewport', {}),
                    'diff_paths_by_viewport': diff_paths
                })
            else:
                return jsonify({
                    'success': False,
                    'message': result.get('message', f"Failed to complete enhanced capture+diff for '{page.page_name or page.path}'"),
                    'error': result.get('error', 'Unknown error')
                })
            
        except Exception as e:
            app.logger.error(f"Unexpected error in enhanced capture+diff for page {page_id}: {str(e)}")
            return jsonify({
                'success': False,
                'message': f"Error in enhanced capture+diff: {str(e)}"
            }), 500
    
    @app.route('/runs/<path:filename>')
    @login_required
    def serve_run_file(filename):
        """Serve files from timestamped runs (screenshots and diffs)"""
        try:
            # Normalize the filename by replacing backslashes with forward slashes
            normalized_filename = filename.replace('\\', '/')
            
            # Extract project_id from the path
            path_parts = normalized_filename.split('/')
            if len(path_parts) < 3:  # Should be project_id/run_id/...
                return "Invalid run file path", 404
            
            project_id = int(path_parts[0])
            
            # Verify user has access to this project
            project = Project.query.filter_by(
                id=project_id,
                user_id=current_user.id
            ).first()
            
            if not project:
                return "Access denied", 403
            
            # Construct file path - use os.path.join for proper OS path handling
            runs_dir = "runs"
            file_path = os.path.join(runs_dir, *path_parts)
            
            # Convert to Path object for existence check
            file_path_obj = Path(file_path)
            
            if not file_path_obj.exists():
                app.logger.error(f"Run file not found: {file_path}")
                return "File not found", 404
            
            # Determine MIME type based on file extension
            if file_path.lower().endswith('.png'):
                mimetype = 'image/png'
            elif file_path.lower().endswith('.jpg') or file_path.lower().endswith('.jpeg'):
                mimetype = 'image/jpeg'
            else:
                mimetype = 'application/octet-stream'
            
            return send_file(str(file_path_obj), mimetype=mimetype)
            
        except (ValueError, IndexError):
            return "Invalid run file path", 404
        except Exception as e:
            app.logger.error(f"Error serving run file {filename}: {str(e)}")
            return "Error serving file", 500
    
    @app.route('/diffs/<path:filename>')
    @login_required
    def serve_diff(filename):
        """Serve diff image files"""
        try:
            # Normalize the filename by replacing backslashes with forward slashes
            normalized_filename = filename.replace('\\', '/')
            
            # Extract project_id from the path
            path_parts = normalized_filename.split('/')
            if len(path_parts) < 2:  # Should be project_id/filename.png
                return "Invalid diff path", 404
            
            project_id = int(path_parts[0])
            
            # Verify user has access to this project
            project = Project.query.filter_by(
                id=project_id,
                user_id=current_user.id
            ).first()
            
            if not project:
                return "Access denied", 403
            
            # Construct file path - use os.path.join for proper OS path handling
            diff_dir = "diffs"
            file_path = os.path.join(diff_dir, *path_parts)
            
            # Convert to Path object for existence check
            file_path_obj = Path(file_path)
            
            if not file_path_obj.exists():
                app.logger.error(f"Diff file not found: {file_path}")
                return "Diff image not found", 404
            
            return send_file(str(file_path_obj), mimetype='image/png')
            
        except (ValueError, IndexError):
            return "Invalid diff path", 404
        except Exception as e:
            app.logger.error(f"Error serving diff {filename}: {str(e)}")
            return "Error serving diff image", 500
    
    @app.route('/screenshots/<path:filename>')
    @login_required
    def serve_screenshot(filename):
        """Serve screenshot files"""
        try:
            # Normalize the filename by replacing backslashes with forward slashes
            normalized_filename = filename.replace('\\', '/')
            
            # Extract project_id from the path
            path_parts = normalized_filename.split('/')
            if len(path_parts) < 3:  # Should be project_id/staging_or_production/filename.png
                return "Invalid screenshot path", 404
            
            project_id = int(path_parts[0])
            
            # Verify user has access to this project
            project = Project.query.filter_by(
                id=project_id,
                user_id=current_user.id
            ).first()
            
            if not project:
                return "Access denied", 403
            
            # Construct file path - use os.path.join for proper OS path handling
            screenshot_dir = "screenshots"
            file_path = os.path.join(screenshot_dir, *path_parts)
            
            # Convert to Path object for existence check
            file_path_obj = Path(file_path)
            
            if not file_path_obj.exists():
                app.logger.error(f"Screenshot file not found: {file_path}")
                return "Screenshot not found", 404
            
            return send_file(str(file_path_obj), mimetype='image/png')
            
        except (ValueError, IndexError):
            return "Invalid screenshot path", 404
        except Exception as e:
            app.logger.error(f"Error serving screenshot {filename}: {str(e)}")
            return "Error serving screenshot", 500

def _is_valid_url(url):
    """
    Validate that URL starts with http:// or https://
    
    Args:
        url (str): URL to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    if not url:
        return False
    
    # Check if URL starts with http:// or https://
    url_pattern = re.compile(r'^https?://.+')
    return bool(url_pattern.match(url))