from flask import render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import login_required, current_user
from models import db
from models.project import Project, ProjectPage
from urllib.parse import urlparse
import re
import os
from pathlib import Path
from datetime import datetime
from utils.timestamp_utils import format_jobs_history_datetime

def register_project_routes(app, crawler_scheduler):
    @app.route('/projects')
    @login_required
    def projects_list():
        """List all projects for the current user with unified pipeline status"""
        projects = Project.query.filter_by(user_id=current_user.id).order_by(Project.created_at.desc()).all()
        
        # Initialize run state service
        from services.run_state_service import RunStateService
        run_state_service = RunStateService(crawler_scheduler)
        
        # Get run states for all projects
        project_ids = [p.id for p in projects]
        run_states = run_state_service.get_multiple_projects_run_state(project_ids) if project_ids else {}
        
        # Build projects with unified status
        projects_with_status = []
        
        for project in projects:
            # Get unified run state
            run_state = run_states.get(project.id, {
                'state': 'not_started',
                'progress': 0,
                'message': 'No runs yet',
                'has_failures': False,
                'failure_reason': None,
                'run_id': None,
                'last_updated': None
            })
            
            # Get page count
            page_count = ProjectPage.query.filter_by(project_id=project.id).count()
            
            projects_with_status.append({
                'project': project,
                'run_state': run_state,
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
            is_page_restricted = bool(request.form.get('is_page_restricted'))
            
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
                    user_id=current_user.id,
                    is_page_restricted=is_page_restricted
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
        
        # Get unified run state
        from services.run_state_service import RunStateService
        run_state_service = RunStateService(crawler_scheduler)
        run_state = run_state_service.get_project_run_state(project_id)
        
        # Get available statuses for filter dropdown
        available_statuses = db.session.query(ProjectPage.status).filter_by(project_id=project_id).distinct().all()
        available_statuses = [status[0] for status in available_statuses]
        
        return render_template('projects/details.html',
                             project=project,
                             pages=pages,
                             pagination=pagination,
                             run_state=run_state,
                             search_query=search_query,
                             status_filter=status_filter,
                             available_statuses=available_statuses,
                             per_page=per_page)
    
    @app.route('/projects/<int:project_id>/crawl', methods=['POST'])
    @login_required
    def start_crawl(project_id):
        """Start crawling for a project - FIXED: Single job enforcement"""
        project = Project.query.filter_by(
            id=project_id,
            user_id=current_user.id
        ).first_or_404()
        
        try:
            # Schedule the crawl job with duplicate prevention
            scheduled = crawler_scheduler.schedule_crawl(project_id)
            
            if scheduled:
                flash('Crawling started! This may take a few minutes.', 'success')
            else:
                flash('A crawling job is already running for this project.', 'warning')
            
        except Exception as e:
            flash('Error starting crawl. Please try again.', 'error')
            app.logger.error(f"Error starting crawl for project {project_id}: {str(e)}")
        
        return redirect(url_for('project_details', project_id=project_id))
    
    @app.route('/projects/<int:project_id>/status')
    @login_required
    def crawl_status(project_id):
        """Get unified pipeline status for a project (AJAX endpoint)"""
        project = Project.query.filter_by(
            id=project_id,
            user_id=current_user.id
        ).first_or_404()
        
        # Get unified run state
        from services.run_state_service import RunStateService
        run_state_service = RunStateService(crawler_scheduler)
        run_state = run_state_service.get_project_run_state(project_id)
        
        # Get page count
        page_count = ProjectPage.query.filter_by(project_id=project_id).count()
        
        # Get the latest CrawlJob from database for backward compatibility
        from models.crawl_job import CrawlJob
        latest_job = CrawlJob.query.filter_by(project_id=project_id).order_by(CrawlJob.created_at.desc()).first()
        
        return jsonify({
            'run_state': run_state,
            'page_count': page_count,
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
        """Start the unified Find Difference workflow - advances same run through phases"""
        project = Project.query.filter_by(
            id=project_id,
            user_id=current_user.id
        ).first_or_404()
        
        try:
            # Get form data for selected pages (if any) and job_id (if from existing job)
            selected_pages = request.form.getlist('selected_pages')
            job_id = request.form.get('job_id')  # For existing job workflow
            
            # PHASE-BASED WORKFLOW: Handle existing job workflow (the correct approach)
            if job_id:
                # This is a find difference request for an existing crawled job
                from models.crawl_job import CrawlJob
                crawl_job = db.session.get(CrawlJob, job_id)
                
                if not crawl_job or crawl_job.project_id != project_id:
                    flash('Invalid job ID.', 'error')
                    return redirect(url_for('project_details', project_id=project_id))
                
                if crawl_job.status != 'Crawled':
                    flash('Job must be in Crawled status to find differences.', 'warning')
                    return redirect(url_for('project_details', project_id=project_id))
                
                # PHASE TRANSITION: Crawled → Finding Difference (same run, no new job)
                crawl_job.start_find_difference()
                db.session.commit()
                
                # Schedule find difference for this specific job
                crawler_scheduler.schedule_find_difference_for_job(job_id)
                flash(f'Find Difference started for Run #{crawl_job.job_number}! Status: Crawled → Finding Difference → Ready.', 'success')
                
                return redirect(url_for('project_details', project_id=project_id))
            
            # FALLBACK: If no job_id provided, find the latest Crawled or stuck finding_difference job
            from models.crawl_job import CrawlJob
            
            # First, try to find a Crawled job
            latest_crawled_job = CrawlJob.query.filter_by(
                project_id=project_id,
                status='Crawled'
            ).order_by(CrawlJob.job_number.desc()).first()
            
            # If no Crawled job, check for stuck finding_difference job that needs to be failed
            if not latest_crawled_job:
                stuck_job = CrawlJob.query.filter_by(
                    project_id=project_id,
                    status='finding_difference'
                ).order_by(CrawlJob.job_number.desc()).first()
                
                if stuck_job:
                    # Check if the job has been stuck for more than 10 minutes
                    from datetime import timedelta
                    time_threshold = datetime.utcnow() - timedelta(minutes=10)
                    
                    if stuck_job.fd_started_at and stuck_job.fd_started_at < time_threshold:
                        # Job has been stuck for too long - mark as failed instead of resetting
                        stuck_job.fail_find_difference("Job was stuck in finding_difference status for more than 10 minutes")
                        db.session.commit()
                        flash(f'Find Difference job #{stuck_job.job_number} was stuck and has been marked as failed. Please try again.', 'warning')
                    else:
                        # Job is still within reasonable time - don't interfere
                        flash(f'Find Difference job #{stuck_job.job_number} is currently running. Please wait for it to complete.', 'info')
                        return redirect(url_for('project_details', project_id=project_id))
            
            if not latest_crawled_job:
                flash('No crawled job found. Please crawl the project first.', 'warning')
                return redirect(url_for('project_details', project_id=project_id))
            
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
                
                # Update find_diff_status for selected pages to 'finding_difference'
                ProjectPage.query.filter(
                    ProjectPage.id.in_(page_ids),
                    ProjectPage.project_id == project_id
                ).update({
                    'find_diff_status': 'finding_difference'
                }, synchronize_session=False)
                
                db.session.commit()
                
            else:
                # Process all pages in the project
                page_ids = None
                pages_count = ProjectPage.query.filter_by(project_id=project_id).count()
                
                # Update find_diff_status for all pages to 'finding_difference'
                ProjectPage.query.filter_by(project_id=project_id).update({
                    'find_diff_status': 'finding_difference'
                }, synchronize_session=False)
                
                db.session.commit()
            
            if pages_count == 0:
                flash('No pages found to process. Please crawl the project first.', 'warning')
                return redirect(url_for('project_details', project_id=project_id))
            
            # PHASE TRANSITION: Advance the latest crawled job to Finding Difference
            latest_crawled_job.start_find_difference()
            db.session.commit()
            
            # Schedule Find Difference job with selected page IDs
            if selected_pages:
                # Pass selected page IDs to the scheduler
                crawler_scheduler.schedule_find_difference_for_job(latest_crawled_job.id, page_ids=page_ids)
                flash(f'Find Difference started for Run #{latest_crawled_job.job_number} with {pages_count} selected pages! Status: Crawled → Finding Difference → Ready.', 'success')
            else:
                # Process all pages
                crawler_scheduler.schedule_find_difference_for_job(latest_crawled_job.id)
                flash(f'Find Difference started for Run #{latest_crawled_job.job_number} with all {pages_count} pages! Status: Crawled → Finding Difference → Ready.', 'success')
            
        except Exception as e:
            flash('Error starting Find Difference workflow. Please try again.', 'error')
            app.logger.error(f"Error starting Find Difference for project {project_id}: {str(e)}")
        
        return redirect(url_for('project_details', project_id=project_id))
    
    @app.route('/projects/<int:project_id>/manual-capture/<int:page_id>', methods=['POST'])
    @login_required
    def manual_capture_page(project_id, page_id):
        """Asynchronous Manual Capture: Queue screenshot capture job for background processing"""
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
            
            # Check if a job is already running for this page
            job_status = crawler_scheduler.get_page_job_status(project_id, page_id)
            if job_status['status'] == 'scheduled':
                return jsonify({
                    'success': False,
                    'message': 'A capture job is already running for this page. Please wait for it to complete.'
                }), 409
            
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
            
            # Schedule the background job
            try:
                job_id = crawler_scheduler.schedule_manual_page_capture(
                    project_id=project_id,
                    page_id=page_id,
                    viewports=viewports
                )
                
                if job_id is None:
                    return jsonify({
                        'success': False,
                        'message': 'Failed to schedule capture job. A job may already be running.'
                    }), 409
                
                # Clean up page name for display
                display_name = (page.page_name or page.path or 'Unknown Page').strip()
                if not display_name or display_name.isspace():
                    display_name = page.path or f"Page {page_id}"
                
                return jsonify({
                    'success': True,
                    'message': f"Screenshot capture job queued for '{display_name}'. Processing in background...",
                    'job_id': job_id,
                    'page_id': page_id,
                    'updated_status': 'pending'
                })
                
            except Exception as schedule_error:
                app.logger.error(f"Error scheduling capture job for page {page_id}: {str(schedule_error)}")
                return jsonify({
                    'success': False,
                    'message': f"Failed to schedule capture job: {str(schedule_error)}"
                }), 500
            
        except Exception as e:
            app.logger.error(f"Unexpected error in manual capture for page {page_id}: {str(e)}")
            return jsonify({
                'success': False,
                'message': f"Error in manual capture: {str(e)}"
            }), 500
    
    @app.route('/projects/<int:project_id>/manual-capture/<int:page_id>/status')
    @login_required
    def manual_capture_status(project_id, page_id):
        """Get status of manual page capture job (AJAX endpoint)"""
        try:
            # Verify project access
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
            
            # Get job status from scheduler
            job_status = crawler_scheduler.get_page_job_status(project_id, page_id)
            progress_info = crawler_scheduler.get_page_progress_info(project_id, page_id)
            
            # Get current page status from database
            db.session.refresh(page)  # Refresh to get latest status
            
            return jsonify({
                'success': True,
                'job_status': job_status,
                'progress': progress_info,
                'page_status': page.find_diff_status,
                'current_run_id': page.current_run_id,
                'last_run_at': page.last_run_at.isoformat() if page.last_run_at else None,
                'page_id': page_id
            })
            
        except Exception as e:
            app.logger.error(f"Error getting manual capture status for page {page_id}: {str(e)}")
            return jsonify({
                'success': False,
                'message': f"Error getting status: {str(e)}"
            }), 500
    
    @app.route('/runs/<path:filename>')
    @login_required
    def serve_run_file(filename):
        """Serve files from timestamped runs (screenshots and diffs) - Universal Dynamic Handler"""
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
            
            # Universal file resolution strategy
            file_path_obj = None
            attempted_paths = []
            
            # Strategy 1: Try the exact path in runs directory (new structure)
            runs_path = os.path.join("runs", *path_parts)
            file_path_obj = Path(runs_path)
            attempted_paths.append(str(file_path_obj))
            
            if not file_path_obj.exists():
                # Strategy 2: Try screenshots directory with intelligent path conversion
                project_id_str = path_parts[0]
                run_id = path_parts[1]
                
                # Handle different URL patterns dynamically
                remaining_parts = path_parts[2:]
                
                # Case conversion mapping for viewports
                viewport_map = {
                    'mobile': 'Mobile',
                    'tablet': 'Tablet',
                    'desktop': 'Desktop'
                }
                
                # Pattern 1: /runs/project/run/diffs/viewport/filename
                if len(remaining_parts) >= 3 and remaining_parts[0] == 'diffs':
                    viewport = remaining_parts[1]
                    filename_part = remaining_parts[2]
                    
                    # Convert viewport case
                    viewport_proper = viewport_map.get(viewport.lower(), viewport.capitalize())
                    
                    # Convert filename patterns
                    filename_converted = filename_part
                    if '_diff.png' in filename_part:
                        filename_converted = filename_part.replace('_diff.png', '-diff.png')
                    elif '_diff.jpg' in filename_part:
                        filename_converted = filename_part.replace('_diff.jpg', '-diff.jpg')
                    
                    screenshots_path = os.path.join('screenshots', project_id_str, run_id, viewport_proper, filename_converted)
                    file_path_obj = Path(screenshots_path)
                    attempted_paths.append(str(file_path_obj))
                
                # Pattern 2: /runs/project/run/viewport/filename (direct screenshots)
                elif len(remaining_parts) >= 2:
                    viewport = remaining_parts[0]
                    filename_part = remaining_parts[1]
                    
                    # Convert viewport case
                    viewport_proper = viewport_map.get(viewport.lower(), viewport.capitalize())
                    
                    # Try different filename patterns
                    filename_variations = [
                        filename_part,  # Original
                        filename_part.replace('_', '-'),  # underscore to dash
                        filename_part.replace('-', '_'),  # dash to underscore
                    ]
                    
                    for filename_var in filename_variations:
                        screenshots_path = os.path.join('screenshots', project_id_str, run_id, viewport_proper, filename_var)
                        test_path = Path(screenshots_path)
                        attempted_paths.append(str(test_path))
                        if test_path.exists():
                            file_path_obj = test_path
                            break
                
                # Pattern 3: Try all possible combinations if above patterns fail
                if not file_path_obj or not file_path_obj.exists():
                    # Get all possible viewport directories
                    screenshots_base = Path('screenshots') / project_id_str / run_id
                    if screenshots_base.exists():
                        for viewport_dir in screenshots_base.iterdir():
                            if viewport_dir.is_dir():
                                # Try to find any file that matches the requested filename pattern
                                target_filename = remaining_parts[-1] if remaining_parts else ''
                                
                                # Generate filename variations
                                filename_variations = [
                                    target_filename,
                                    target_filename.replace('_', '-'),
                                    target_filename.replace('-', '_'),
                                    target_filename.replace('_diff.', '-diff.'),
                                    target_filename.replace('-diff.', '_diff.'),
                                ]
                                
                                for filename_var in filename_variations:
                                    test_file = viewport_dir / filename_var
                                    attempted_paths.append(str(test_file))
                                    if test_file.exists():
                                        file_path_obj = test_file
                                        break
                                
                                if file_path_obj and file_path_obj.exists():
                                    break
            
            # Final check - if still not found, log all attempted paths
            if not file_path_obj or not file_path_obj.exists():
                app.logger.error(f"File not found. Original request: {filename}")
                app.logger.error(f"Attempted paths: {attempted_paths}")
                return "File not found", 404
            
            # Determine MIME type based on file extension
            file_ext = str(file_path_obj).lower()
            if file_ext.endswith('.png'):
                mimetype = 'image/png'
            elif file_ext.endswith(('.jpg', '.jpeg')):
                mimetype = 'image/jpeg'
            elif file_ext.endswith('.gif'):
                mimetype = 'image/gif'
            elif file_ext.endswith('.webp'):
                mimetype = 'image/webp'
            else:
                mimetype = 'application/octet-stream'
            
            app.logger.info(f"Serving file: {file_path_obj} for request: {filename}")
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
    
    # Jobs History API Endpoints
    @app.route('/api/projects/<int:project_id>/jobs')
    @login_required
    def get_jobs_history(project_id):
        """Get jobs history for a project with unified status display"""
        try:
            # Verify project access
            project = Project.query.filter_by(
                id=project_id,
                user_id=current_user.id
            ).first()
            
            if not project:
                return jsonify({
                    'success': False,
                    'error': 'Project not found or access denied'
                }), 404
            
            # Get jobs from CrawlJob table
            from models.crawl_job import CrawlJob
            jobs = CrawlJob.query.filter_by(project_id=project_id).order_by(CrawlJob.job_number.desc()).all()
            
            # Get the unified project status from RunStateService
            from services.run_state_service import RunStateService
            run_state_service = RunStateService(crawler_scheduler)
            project_run_state = run_state_service.get_project_run_state(project_id)
            unified_project_status = project_run_state.get('state', 'not_started')

            # Get all pages for this project
            pages = ProjectPage.query.filter_by(project_id=project_id).all()
            
            jobs_data = []
            for i, job in enumerate(jobs):
                # Format updated_at timestamp
                updated_at_formatted = format_jobs_history_datetime(job.updated_at)
                
                # Determine the display status for consistency
                display_status = job.status
                if i == 0:
                    # For the most recent job, use the unified project status
                    display_status = unified_project_status
                else:
                    # For older jobs, map to a consistent status vocabulary
                    if job.status == 'ready' or job.status == 'completed':
                        display_status = 'Result'
                    elif job.status == 'diff_failed':
                        display_status = 'Job Failed'

                # Determine page count based on job status
                job_pages = job.total_pages or 0
                if job.status == 'Crawled' and not job.total_pages:
                    job_pages = len(pages)

                jobs_data.append({
                    'id': job.id,
                    'job_number': job.job_number,
                    'status': display_status,
                    'updated_at': updated_at_formatted,
                    'pages': job_pages,
                    'startTime': job.created_at.isoformat() if job.created_at else None,
                    'endTime': job.completed_at.isoformat() if job.completed_at else None,
                })
            
            return jsonify({
                'success': True,
                'jobs': jobs_data
            })
            
        except Exception as e:
            app.logger.error(f"Error getting jobs history for project {project_id}: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'Failed to load jobs history'
            }), 500
    
    @app.route('/api/projects/<int:project_id>/start-crawl-job', methods=['POST'])
    @login_required
    def start_crawl_job(project_id):
        """Start a new crawling job with job tracking and stuck job detection"""
        try:
            # Verify project access
            project = Project.query.filter_by(
                id=project_id,
                user_id=current_user.id
            ).first()
            
            if not project:
                return jsonify({
                    'success': False,
                    'message': 'Project not found or access denied'
                }), 404
            
            # Check for and fail stuck jobs before starting a new one
            from models.crawl_job import CrawlJob
            from datetime import datetime, timedelta

            stuck_jobs = CrawlJob.query.filter(
                CrawlJob.project_id == project_id,
                CrawlJob.status.in_(['Crawling', 'finding_difference']),
                CrawlJob.updated_at < datetime.utcnow() - timedelta(minutes=10)
            ).all()

            if stuck_jobs:
                for job in stuck_jobs:
                    job.status = 'Job Failed'
                    job.error_message = 'Job marked as failed due to being stuck.'
                    job.completed_at = datetime.utcnow()
                db.session.commit()
                return jsonify({
                    'success': False,
                    'message': 'A previously stuck job was found and marked as failed. You can now start a new job.'
                }), 409

            # Check if there's already an active job (Crawling or pending status) for this project
            running_job = CrawlJob.query.filter_by(
                project_id=project_id
            ).filter(CrawlJob.status.in_(['Crawling', 'pending', 'finding_difference'])).first()
            
            if running_job:
                return jsonify({
                    'success': False,
                    'message': 'A crawling job is already running for this project'
                }), 409
            
            # FIXED: Always create a new job for each run to avoid confusion
            # This ensures proper job state transitions: pending -> Crawling -> Crawled
            new_job = CrawlJob(project_id=project_id)
            new_job.status = 'pending'
            new_job.updated_at = datetime.utcnow()
            new_job.job_type = 'full_crawl'
            db.session.add(new_job)
            
            db.session.commit()
            
            # Schedule the crawl job - scheduler will find the pending job and start it
            scheduled_job_id = crawler_scheduler.schedule_crawl(project_id)
            
            if scheduled_job_id is None:
                # Job could not be scheduled (already running or other issue)
                db.session.rollback()
                return jsonify({
                    'success': False,
                    'message': 'A crawling job is already running for this project or could not be scheduled'
                }), 409
            
            return jsonify({
                'success': True,
                'message': 'Crawling job started successfully',
                'job': {
                    'id': new_job.id,
                    'job_number': new_job.job_number,
                    'status': new_job.status
                }
            })
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error starting crawl job for project {project_id}: {str(e)}")
            return jsonify({
                'success': False,
                'message': f'Failed to start crawling job: {str(e)}'
            }), 500
    
    @app.route('/api/projects/<int:project_id>/jobs/<job_id>/status')
    @login_required
    def get_job_status(project_id, job_id):
        """Get status of a specific job"""
        try:
            # Verify project access
            project = Project.query.filter_by(
                id=project_id,
                user_id=current_user.id
            ).first()
            
            if not project:
                return jsonify({
                    'success': False,
                    'message': 'Project not found or access denied'
                }), 404
            
            # Get unified run state
            from services.run_state_service import RunStateService
            run_state_service = RunStateService(crawler_scheduler)
            run_state_data = run_state_service.get_project_run_state(project_id)
            
            # Extract the actual state from the run state data
            if isinstance(run_state_data, dict):
                run_state = run_state_data.get('state', 'not_started')
            else:
                run_state = run_state_data if run_state_data else 'not_started'
            
            # Get latest job from database
            from models.crawl_job import CrawlJob
            latest_job = CrawlJob.query.filter_by(project_id=project_id).order_by(CrawlJob.job_number.desc()).first()
            
            if not latest_job:
                return jsonify({
                    'success': False,
                    'message': 'Job not found'
                }), 404
            
            # Format updated_at in IST timezone
            updated_at_formatted = format_jobs_history_datetime(latest_job.updated_at)
            
            job_data = {
                'id': latest_job.id,
                'job_number': latest_job.job_number,
                'status': latest_job.status,
                'updated_at': updated_at_formatted,
                'pages': latest_job.total_pages,
                'endTime': latest_job.completed_at.isoformat() if latest_job.completed_at else None
            }
            
            return jsonify({
                'success': True,
                'job': job_data
            })
            
        except Exception as e:
            app.logger.error(f"Error getting job status for project {project_id}, job {job_id}: {str(e)}")
            return jsonify({
                'success': False,
                'message': 'Failed to get job status'
            }), 500
    
    @app.route('/api/projects/<int:project_id>/jobs/<int:job_number>/details')
    @login_required
    def get_job_details(project_id, job_number):
        """Get job details including timestamp for history retrieval"""
        try:
            # Verify project access
            project = Project.query.filter_by(
                id=project_id,
                user_id=current_user.id
            ).first()
            
            if not project:
                return jsonify({
                    'success': False,
                    'message': 'Project not found or access denied'
                }), 404
            
            # Get job by job number
            from models.crawl_job import CrawlJob
            job = CrawlJob.query.filter_by(
                project_id=project_id,
                job_number=job_number
            ).first()
            
            if not job:
                return jsonify({
                    'success': False,
                    'message': f'Job #{job_number} not found'
                }), 404
            
            # Check if job is in a state that has completion data
            if job.status not in ['Crawled', 'ready', 'diff_failed', 'completed']:
                return jsonify({
                    'success': False,
                    'message': f'Job #{job_number} is not completed yet (status: {job.status})'
                }), 400
            
            # Try multiple timestamp sources in order of preference
            timestamp_source = None
            timestamp_source_name = None
            
            # Priority order: crawl_completed_at > completed_at > fd_completed_at > updated_at
            if job.crawl_completed_at:
                timestamp_source = job.crawl_completed_at
                timestamp_source_name = 'crawl_completed_at'
            elif job.completed_at:
                timestamp_source = job.completed_at
                timestamp_source_name = 'completed_at'
            elif job.fd_completed_at:
                timestamp_source = job.fd_completed_at
                timestamp_source_name = 'fd_completed_at'
            elif job.updated_at:
                timestamp_source = job.updated_at
                timestamp_source_name = 'updated_at'
            
            if not timestamp_source:
                return jsonify({
                    'success': False,
                    'message': f'Job #{job_number} has no valid timestamp for history retrieval'
                }), 400
            
            # Convert to PathResolver timestamp format (YYYYMMDD-HHMMSS) for history API compatibility
            try:
                timestamp_formatted = timestamp_source.strftime('%Y%m%d-%H%M%S')
            except Exception as ts_error:
                app.logger.error(f"Error formatting timestamp for job {job_number}: {str(ts_error)}")
                return jsonify({
                    'success': False,
                    'message': f'Invalid timestamp format for job #{job_number}'
                }), 400
            
            # Format updated_at in IST timezone for display
            updated_at_formatted = format_jobs_history_datetime(job.updated_at)
            
            job_data = {
                'id': job.id,
                'job_number': job.job_number,
                'status': job.status,
                'updated_at': updated_at_formatted,
                'pages': job.total_pages or 0,
                'timestamp': timestamp_formatted,
                'timestamp_source': timestamp_source_name,
                'crawl_completed_at': job.crawl_completed_at.isoformat() if job.crawl_completed_at else None,
                'completed_at': job.completed_at.isoformat() if job.completed_at else None,
                'fd_completed_at': job.fd_completed_at.isoformat() if job.fd_completed_at else None
            }
            
            app.logger.info(f"Successfully retrieved job details for job #{job_number}: timestamp={timestamp_formatted}, source={timestamp_source_name}")
            
            return jsonify({
                'success': True,
                'job': job_data
            })
            
        except Exception as e:
            app.logger.error(f"Error getting job details for project {project_id}, job {job_number}: {str(e)}")
            return jsonify({
                'success': False,
                'message': f'Failed to get job details: {str(e)}'
            }), 500
    
    @app.route('/api/projects/<int:project_id>/jobs/<int:job_number>/pages')
    @login_required
    def get_job_pages(project_id, job_number):
        """Get pages for a specific job with status-based filtering"""
        try:
            # Verify project access
            project = Project.query.filter_by(
                id=project_id,
                user_id=current_user.id
            ).first()
            
            if not project:
                return jsonify({
                    'success': False,
                    'message': 'Project not found or access denied'
                }), 404
            
            # Get job by job number
            from models.crawl_job import CrawlJob
            job = CrawlJob.query.filter_by(
                project_id=project_id,
                job_number=job_number
            ).first()
            
            if not job:
                return jsonify({
                    'success': False,
                    'message': f'Job #{job_number} not found'
                }), 404
            
            # Get all pages for this project
            pages = ProjectPage.query.filter_by(project_id=project_id).all()
            
            # Filter and format pages based on job status
            pages_data = []
            
            if job.status == 'Crawled':
                # For Crawled jobs: show only crawled pages, no duration/results
                for page in pages:
                    pages_data.append({
                        'id': page.id,
                        'page_title': page.page_name or page.path or 'Untitled Page',
                        'staging_url': page.staging_url,
                        'production_url': page.production_url,
                        'status': 'crawled',
                        'last_run': format_jobs_history_datetime(page.last_crawled) if page.last_crawled else None,
                        # No duration or results for crawled status
                        'duration': None,
                        'results': None
                    })
            
            elif job.status == 'ready':
                # For Ready jobs: show pages with diff results, include duration and results
                for page in pages:
                    # Check if page has any completed diff results
                    has_results = any([
                        page.diff_status_desktop == 'completed',
                        page.diff_status_tablet == 'completed',
                        page.diff_status_mobile == 'completed'
                    ])
                    
                    if has_results:
                        # Calculate duration (mock for now - you can implement actual duration calculation)
                        duration = "2.3s"  # This should be calculated from actual timing data
                        
                        # Collect viewport results
                        results = {}
                        if page.diff_status_desktop == 'completed':
                            results['desktop'] = {
                                'status': 'completed',
                                'diff_url': f"/runs/{project_id}/{job.job_number}/diffs/desktop/{page.path.replace('/', '_')}_diff.png"
                            }
                        if page.diff_status_tablet == 'completed':
                            results['tablet'] = {
                                'status': 'completed',
                                'diff_url': f"/runs/{project_id}/{job.job_number}/diffs/tablet/{page.path.replace('/', '_')}_diff.png"
                            }
                        if page.diff_status_mobile == 'completed':
                            results['mobile'] = {
                                'status': 'completed',
                                'diff_url': f"/runs/{project_id}/{job.job_number}/diffs/mobile/{page.path.replace('/', '_')}_diff.png"
                            }
                        
                        pages_data.append({
                            'id': page.id,
                            'page_title': page.page_name or page.path or 'Untitled Page',
                            'staging_url': page.staging_url,
                            'production_url': page.production_url,
                            'status': 'ready',
                            'last_run': format_jobs_history_datetime(page.last_run_at) if page.last_run_at else None,
                            'duration': duration,
                            'results': results
                        })
            
            elif job.status in ['Job Failed', 'diff_failed']:
                # For Failed jobs: show all pages with mixed statuses, include duration and results where available
                for page in pages:
                    # Determine page status based on diff completion
                    page_status = 'failed'
                    if any([
                        page.diff_status_desktop == 'completed',
                        page.diff_status_tablet == 'completed',
                        page.diff_status_mobile == 'completed'
                    ]):
                        page_status = 'ready'
                    elif page.last_crawled:
                        page_status = 'crawled'
                    
                    # Calculate duration if available
                    duration = "1.8s" if page_status in ['ready', 'failed'] else None
                    
                    # Collect results if available
                    results = None
                    if page_status == 'ready':
                        results = {}
                        if page.diff_status_desktop == 'completed':
                            results['desktop'] = {
                                'status': 'completed',
                                'diff_url': f"/runs/{project_id}/{job.job_number}/diffs/desktop/{page.path.replace('/', '_')}_diff.png"
                            }
                        if page.diff_status_tablet == 'completed':
                            results['tablet'] = {
                                'status': 'completed',
                                'diff_url': f"/runs/{project_id}/{job.job_number}/diffs/tablet/{page.path.replace('/', '_')}_diff.png"
                            }
                        if page.diff_status_mobile == 'completed':
                            results['mobile'] = {
                                'status': 'completed',
                                'diff_url': f"/runs/{project_id}/{job.job_number}/diffs/mobile/{page.path.replace('/', '_')}_diff.png"
                            }
                    
                    pages_data.append({
                        'id': page.id,
                        'page_title': page.page_name or page.path or 'Untitled Page',
                        'staging_url': page.staging_url,
                        'production_url': page.production_url,
                        'status': page_status,
                        'last_run': format_jobs_history_datetime(page.last_run_at) if page.last_run_at else None,
                        'duration': duration,
                        'results': results
                    })
            
            else:
                # Default case for other statuses
                for page in pages:
                    pages_data.append({
                        'id': page.id,
                        'page_title': page.page_name or page.path or 'Untitled Page',
                        'staging_url': page.staging_url,
                        'production_url': page.production_url,
                        'status': 'unknown',
                        'last_run': format_jobs_history_datetime(page.last_crawled) if page.last_crawled else None,
                        'duration': None,
                        'results': None
                    })
            
            return jsonify({
                'success': True,
                'job': {
                    'id': job.id,
                    'job_number': job.job_number,
                    'status': job.status,
                    'updated_at': format_jobs_history_datetime(job.updated_at)
                },
                'pages': pages_data,
                'total_pages': len(pages_data)
            })
            
        except Exception as e:
            app.logger.error(f"Error getting job pages for project {project_id}, job {job_number}: {str(e)}")
            return jsonify({
                'success': False,
                'message': f'Failed to get job pages: {str(e)}'
            }), 500
    
    @app.route('/api/projects/status')
    @login_required
    def get_projects_status():
        """API endpoint to get real-time status of all projects for polling"""
        try:
            # Get all projects for the current user
            projects = Project.query.filter_by(user_id=current_user.id).all()
            
            # Initialize run state service
            from services.run_state_service import RunStateService
            run_state_service = RunStateService(crawler_scheduler)
            
            # Get run states for all projects
            project_ids = [p.id for p in projects]
            run_states = run_state_service.get_multiple_projects_run_state(project_ids) if project_ids else {}
            
            projects_status = []
            for project in projects:
                # Get unified run state
                run_state = run_states.get(project.id, {
                    'state': 'not_started'
                })
                
                # Get the state directly from run_state (no mapping needed)
                state = run_state.get('state', 'not_started')
                
                # Get page count
                page_count = ProjectPage.query.filter_by(project_id=project.id).count()
                
                projects_status.append({
                    'id': project.id,
                    'status': state,  # Use state directly
                    'page_count': page_count
                })
            
            return jsonify({
                'success': True,
                'projects': projects_status
            })
            
        except Exception as e:
            app.logger.error(f"Error getting projects status: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'Failed to get projects status'
            }), 500

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