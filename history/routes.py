from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from models import db
from models.project import Project, ProjectPage
from models.crawl_job import CrawlJob
from utils.path_resolver import PathResolver
import os
from datetime import datetime
import pytz

def register_history_routes(app):
    """Register history-related routes"""
    
    @app.route('/api/history/runs/<int:project_id>')
    @login_required
    def get_project_runs(project_id):
        """Get all process runs for a project"""
        try:
            # Verify project ownership
            project = Project.query.filter_by(id=project_id, user_id=current_user.id).first()
            if not project:
                return jsonify({'error': 'Project not found'}), 404
            
            # Get all completed crawl jobs for this project
            completed_jobs = CrawlJob.query.filter_by(
                project_id=project_id,
                status='completed'
            ).order_by(CrawlJob.completed_at.desc()).all()
            
            # Get unique process runs from the file system using PathResolver
            path_resolver = PathResolver()
            
            runs = []
            # Use PathResolver to get all process runs for this project
            process_runs = path_resolver.list_project_runs(project_id)
            
            for timestamp in process_runs:
                try:
                    # Parse timestamp to datetime
                    dt = datetime.strptime(timestamp, '%Y%m%d-%H%M%S')
                    ist = pytz.timezone('Asia/Kolkata')
                    dt_ist = ist.localize(dt)
                    
                    # Find corresponding crawl job
                    job = next((j for j in completed_jobs
                              if j.completed_at and
                              abs((j.completed_at - dt_ist).total_seconds()) < 3600), None)
                    
                    # Count pages in this run by checking viewport directories
                    page_count = 0
                    project_dir = path_resolver.base_dir / str(project_id) / timestamp
                    
                    if project_dir.exists():
                        # Check each viewport directory for screenshots (both lowercase and capitalized)
                        for viewport in ['desktop', 'tablet', 'mobile']:
                            # Try lowercase first (PathResolver structure)
                            viewport_dir = project_dir / viewport
                            if not viewport_dir.exists():
                                # Try capitalized (PathManager structure)
                                viewport_dir = project_dir / viewport.capitalize()
                            
                            if viewport_dir.exists():
                                # Count diff files (they indicate completed comparisons)
                                diff_files = [f for f in viewport_dir.iterdir()
                                            if f.is_file() and f.name.endswith('-diff.png')]
                                page_count = max(page_count, len(diff_files))
                    
                    runs.append({
                        'run_id': timestamp,
                        'formatted_date': dt_ist.strftime('%Y-%m-%d %H:%M:%S'),
                        'job_id': job.id if job else None,
                        'pages_count': page_count,
                        'status': 'completed'
                    })
                except ValueError:
                    continue  # Skip invalid timestamp directories
            
            return jsonify({
                'success': True,
                'runs': runs,
                'project_name': project.name
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/history/pages/<int:project_id>/<timestamp>')
    @login_required
    def get_run_pages(project_id, timestamp):
        """Get all pages for a specific run with enhanced data structure"""
        try:
            # Verify project ownership
            project = Project.query.filter_by(id=project_id, user_id=current_user.id).first()
            if not project:
                return jsonify({'error': 'Project not found'}), 404
            
            # Validate timestamp format
            try:
                run_datetime = datetime.strptime(timestamp, '%Y%m%d-%H%M%S')
                ist = pytz.timezone('Asia/Kolkata')
                run_datetime_ist = ist.localize(run_datetime)
            except ValueError:
                return jsonify({'error': 'Invalid timestamp format'}), 400
            
            path_resolver = PathResolver()
            project_dir = path_resolver.base_dir / str(project_id) / timestamp
            
            if not project_dir.exists():
                return jsonify({'error': 'Run not found'}), 404
            
            pages = []
            
            # Get pages from database to get proper page information
            project_pages_db = ProjectPage.query.filter_by(project_id=project_id).all()
            
            # Create a dictionary to track unique pages across viewports
            page_data = {}
            
            # Scan each viewport directory for diff files (both lowercase and capitalized)
            for viewport in ['desktop', 'tablet', 'mobile']:
                # Try lowercase first (PathResolver structure)
                viewport_dir = project_dir / viewport
                if not viewport_dir.exists():
                    # Try capitalized (PathManager structure)
                    viewport_dir = project_dir / viewport.capitalize()
                if not viewport_dir.exists():
                    continue
                
                # Find all diff files
                diff_files = [f for f in viewport_dir.iterdir() if f.is_file() and f.name.endswith('-diff.png')]
                
                for diff_file in diff_files:
                    # Extract page slug from filename (remove -diff.png)
                    page_slug = diff_file.stem.replace('-diff', '')
                    
                    # Convert slug back to path (reverse the slugify process)
                    if page_slug == 'home':
                        page_path = '/'
                    else:
                        page_path = '/' + page_slug.replace('-', '_')
                    
                    # Find matching page in database
                    matching_page = None
                    for db_page in project_pages_db:
                        # Try exact path match first
                        if db_page.path == page_path:
                            matching_page = db_page
                            break
                        # Try slug matching
                        db_slug = path_resolver.slugify_page_path(db_page.path)
                        if db_slug == page_slug:
                            matching_page = db_page
                            break
                    
                    # Check if screenshot files exist
                    production_file = viewport_dir / f"{page_slug}-production.png"
                    staging_file = viewport_dir / f"{page_slug}-staging.png"
                    
                    production_exists = production_file.exists()
                    staging_exists = staging_file.exists()
                    diff_exists = diff_file.exists()
                        
                    if production_exists and staging_exists and diff_exists:
                            # Get diff percentage from database if available
                            diff_percentage = 0.0
                            if matching_page:
                                if viewport == 'desktop':
                                    diff_percentage = matching_page.diff_mismatch_pct_desktop or 0.0
                                elif viewport == 'tablet':
                                    diff_percentage = matching_page.diff_mismatch_pct_tablet or 0.0
                                elif viewport == 'mobile':
                                    diff_percentage = matching_page.diff_mismatch_pct_mobile or 0.0
                            
                            # Get page name and path
                            page_name = matching_page.page_name if matching_page else page_path
                            actual_path = matching_page.path if matching_page else page_path
                            page_id = matching_page.id if matching_page else None
                            
                            # Create unique page key
                            page_key = f"{actual_path}_{viewport}"
                            
                            # Generate screenshot URLs using the asset resolver
                            base_url = f"/assets/runs/{project_id}/{timestamp}/{viewport}"
                            screenshots = {
                                'production': f"{base_url}/{page_slug}-production.png",
                                'staging': f"{base_url}/{page_slug}-staging.png",
                                'diff': f"{base_url}/{page_slug}-diff.png"
                            }
                            
                            # Determine status
                            status = 'completed' if diff_percentage is not None else 'failed'
                            
                            pages.append({
                                'page_path': actual_path,
                                'page_name': page_name or 'Untitled Page',
                                'viewport': viewport.capitalize(),
                                'diff_percentage': round(diff_percentage, 1),
                                'status': status,
                                'last_crawled': run_datetime_ist.strftime('%Y-%m-%d %H:%M:%S'),
                                'screenshots': screenshots,
                                'page_id': page_id
                            })
            
            return jsonify({
                'success': True,
                'pages': pages,
                'timestamp': timestamp,
                'project_name': project.name
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/history/project/<int:project_id>/run/<timestamp>/screenshot/<viewport>/<filename>')
    @login_required
    def get_screenshot(project_id, timestamp, viewport, filename):
        """Serve screenshot files"""
        try:
            # Verify project ownership
            project = Project.query.filter_by(id=project_id, user_id=current_user.id).first()
            if not project:
                return jsonify({'error': 'Project not found'}), 404
            
            # Validate inputs
            if viewport not in ['desktop', 'tablet', 'mobile']:
                return jsonify({'error': 'Invalid viewport'}), 400
            
            try:
                datetime.strptime(timestamp, '%Y%m%d-%H%M%S')
            except ValueError:
                return jsonify({'error': 'Invalid timestamp format'}), 400
            
            # Construct file path using PathResolver (with backward compatibility)
            path_resolver = PathResolver()
            # Try lowercase first (PathResolver structure)
            viewport_dir = path_resolver.base_dir / str(project_id) / timestamp / viewport
            if not viewport_dir.exists():
                # Try capitalized (PathManager structure)
                viewport_dir = path_resolver.base_dir / str(project_id) / timestamp / viewport.capitalize()
            
            if not viewport_dir.exists():
                return jsonify({'error': 'Viewport directory not found'}), 404
            
            file_path = viewport_dir / filename
            
            if not file_path.exists():
                return jsonify({'error': 'Screenshot not found'}), 404
            
            # Security check - ensure file is within expected directory
            try:
                file_path.resolve().relative_to(viewport_dir.resolve())
            except ValueError:
                return jsonify({'error': 'Invalid file path'}), 400
            
            from flask import send_file
            return send_file(str(file_path), mimetype='image/png')
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/history/project/<int:project_id>/runs')
    @login_required
    def get_project_history_runs(project_id):
        """Get all process runs for a project (for project list page)"""
        try:
            # Verify project ownership
            project = Project.query.filter_by(id=project_id, user_id=current_user.id).first()
            if not project:
                return jsonify({'success': False, 'error': 'Project not found'}), 404
            
            # Get all completed crawl jobs for this project
            completed_jobs = CrawlJob.query.filter_by(
                project_id=project_id,
                status='completed'
            ).order_by(CrawlJob.completed_at.desc()).all()
            
            # Get unique process runs from the file system using PathResolver
            path_resolver = PathResolver()
            
            runs = []
            # Use PathResolver to get all process runs for this project
            process_runs = path_resolver.list_project_runs(project_id)
            
            for timestamp in process_runs:
                try:
                    # Parse timestamp to datetime
                    dt = datetime.strptime(timestamp, '%Y%m%d-%H%M%S')
                    ist = pytz.timezone('Asia/Kolkata')
                    dt_ist = ist.localize(dt)
                    
                    # Count pages in this run by checking viewport directories
                    page_count = 0
                    project_dir = path_resolver.base_dir / str(project_id) / timestamp
                    
                    if project_dir.exists():
                        # Check each viewport directory for screenshots (both lowercase and capitalized)
                        for viewport in ['desktop', 'tablet', 'mobile']:
                            # Try lowercase first (PathResolver structure)
                            viewport_dir = project_dir / viewport
                            if not viewport_dir.exists():
                                # Try capitalized (PathManager structure)
                                viewport_dir = project_dir / viewport.capitalize()
                            
                            if viewport_dir.exists():
                                # Count diff files (they indicate completed comparisons)
                                diff_files = [f for f in viewport_dir.iterdir()
                                            if f.is_file() and f.name.endswith('-diff.png')]
                                page_count = max(page_count, len(diff_files))
                    
                    runs.append({
                        'timestamp': timestamp,
                        'datetime': dt_ist.strftime('%Y-%m-%d %H:%M:%S'),
                        'page_count': page_count
                    })
                except ValueError:
                    continue  # Skip invalid timestamp directories
            
            return jsonify({
                'success': True,
                'runs': runs
            })
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/history/project/<int:project_id>/run/<timestamp>/pages')
    @login_required
    def get_run_pages_for_history(project_id, timestamp):
        """Get all pages for a specific run (for history modal) with proper grouping and pagination"""
        try:
            # Verify project ownership
            project = Project.query.filter_by(id=project_id, user_id=current_user.id).first()
            if not project:
                return jsonify({'success': False, 'error': 'Project not found'}), 404
            
            # Validate timestamp format
            try:
                run_datetime = datetime.strptime(timestamp, '%Y%m%d-%H%M%S')
                ist = pytz.timezone('Asia/Kolkata')
                run_datetime_ist = ist.localize(run_datetime)
            except ValueError:
                return jsonify({'success': False, 'error': 'Invalid timestamp format'}), 400
            
            # Get pagination parameters
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 10, type=int)
            per_page = min(per_page, 100)  # Limit to 100 items per page
            
            path_resolver = PathResolver()
            project_dir = path_resolver.base_dir / str(project_id) / timestamp
            
            # If project directory doesn't exist, try to get data from database
            if not project_dir.exists():
                print(f"Project directory not found: {project_dir}")
                # Fallback to database pages if filesystem data is missing
                project_pages_db = ProjectPage.query.filter_by(project_id=project_id).all()
                if not project_pages_db:
                    return jsonify({'success': False, 'error': 'No pages found for this run'}), 404
                
                # Create mock grouped pages from database
                grouped_pages = {}
                for db_page in project_pages_db:
                    grouped_pages[db_page.path] = {
                        'id': db_page.id,
                        'path': db_page.path,
                        'page_name': db_page.page_name or 'Untitled Page',
                        'staging_url': db_page.staging_url,
                        'last_run_at': run_datetime_ist.strftime('%Y-%m-%d %H:%M:%S'),
                        'diff_status_desktop': db_page.diff_status_desktop or 'pending',
                        'diff_status_tablet': db_page.diff_status_tablet or 'pending',
                        'diff_status_mobile': db_page.diff_status_mobile or 'pending',
                        'diff_mismatch_pct_desktop': db_page.diff_mismatch_pct_desktop or 0.0,
                        'diff_mismatch_pct_tablet': db_page.diff_mismatch_pct_tablet or 0.0,
                        'diff_mismatch_pct_mobile': db_page.diff_mismatch_pct_mobile or 0.0
                    }
                
                # Convert to list and apply pagination
                pages_list = list(grouped_pages.values())
                pages_list.sort(key=lambda x: x['path'])
                
                total_pages = len(pages_list)
                start_idx = (page - 1) * per_page
                end_idx = start_idx + per_page
                paginated_pages = pages_list[start_idx:end_idx]
                
                # Calculate pagination info
                total_pages_count = (total_pages + per_page - 1) // per_page if total_pages > 0 else 1
                has_prev = page > 1
                has_next = page < total_pages_count
                
                return jsonify({
                    'success': True,
                    'pages': paginated_pages,
                    'pagination': {
                        'page': page,
                        'per_page': per_page,
                        'total': total_pages,
                        'pages': total_pages_count,
                        'has_prev': has_prev,
                        'has_next': has_next,
                        'prev_num': page - 1 if has_prev else None,
                        'next_num': page + 1 if has_next else None
                    }
                })
            
            # Get pages from database to get proper page information
            project_pages_db = ProjectPage.query.filter_by(project_id=project_id).all()
            
            # Group pages by path first to avoid duplicates across viewports
            grouped_pages = {}
            
            # Scan each viewport directory for diff files (both lowercase and capitalized)
            for viewport in ['desktop', 'tablet', 'mobile']:
                # Try lowercase first (PathResolver structure)
                viewport_dir = project_dir / viewport
                if not viewport_dir.exists():
                    # Try capitalized (PathManager structure)
                    viewport_dir = project_dir / viewport.capitalize()
                if not viewport_dir.exists():
                    continue
                
                # Find all diff files
                diff_files = [f for f in viewport_dir.iterdir() if f.is_file() and f.name.endswith('-diff.png')]
                
                for diff_file in diff_files:
                    # Extract page slug from filename (remove -diff.png)
                    page_slug = diff_file.stem.replace('-diff', '')
                    
                    # Convert slug back to path (reverse the slugify process)
                    if page_slug == 'home':
                        page_path = '/'
                    else:
                        page_path = '/' + page_slug.replace('-', '_')
                    
                    # Find matching page in database
                    matching_page = None
                    for db_page in project_pages_db:
                        # Try exact path match first
                        if db_page.path == page_path:
                            matching_page = db_page
                            break
                        # Try slug matching
                        db_slug = path_resolver.slugify_page_path(db_page.path)
                        if db_slug == page_slug:
                            matching_page = db_page
                            break
                    
                    # Check if screenshot files exist
                    production_file = viewport_dir / f"{page_slug}-production.png"
                    staging_file = viewport_dir / f"{page_slug}-staging.png"
                    
                    production_exists = production_file.exists()
                    staging_exists = staging_file.exists()
                    diff_exists = diff_file.exists()
                        
                    if production_exists and staging_exists and diff_exists:
                        # Get page name and path
                        page_name = matching_page.page_name if matching_page else page_path
                        actual_path = matching_page.path if matching_page else page_path
                        page_id = matching_page.id if matching_page else None
                        
                        # Initialize grouped page if not exists
                        if actual_path not in grouped_pages:
                            grouped_pages[actual_path] = {
                                'id': page_id,
                                'path': actual_path,
                                'page_name': page_name or 'Untitled Page',
                                'staging_url': matching_page.staging_url if matching_page else None,
                                'last_run_at': run_datetime_ist.strftime('%Y-%m-%d %H:%M:%S'),
                                'diff_status_desktop': 'pending',
                                'diff_status_tablet': 'pending',
                                'diff_status_mobile': 'pending',
                                'diff_mismatch_pct_desktop': None,
                                'diff_mismatch_pct_tablet': None,
                                'diff_mismatch_pct_mobile': None
                            }
                        
                        # Update viewport-specific data
                        if matching_page:
                            if viewport == 'desktop':
                                grouped_pages[actual_path]['diff_status_desktop'] = 'completed'
                                grouped_pages[actual_path]['diff_mismatch_pct_desktop'] = matching_page.diff_mismatch_pct_desktop or 0.0
                            elif viewport == 'tablet':
                                grouped_pages[actual_path]['diff_status_tablet'] = 'completed'
                                grouped_pages[actual_path]['diff_mismatch_pct_tablet'] = matching_page.diff_mismatch_pct_tablet or 0.0
                            elif viewport == 'mobile':
                                grouped_pages[actual_path]['diff_status_mobile'] = 'completed'
                                grouped_pages[actual_path]['diff_mismatch_pct_mobile'] = matching_page.diff_mismatch_pct_mobile or 0.0
                        else:
                            # Set default completed status even without DB data
                            if viewport == 'desktop':
                                grouped_pages[actual_path]['diff_status_desktop'] = 'completed'
                                grouped_pages[actual_path]['diff_mismatch_pct_desktop'] = 0.0
                            elif viewport == 'tablet':
                                grouped_pages[actual_path]['diff_status_tablet'] = 'completed'
                                grouped_pages[actual_path]['diff_mismatch_pct_tablet'] = 0.0
                            elif viewport == 'mobile':
                                grouped_pages[actual_path]['diff_status_mobile'] = 'completed'
                                grouped_pages[actual_path]['diff_mismatch_pct_mobile'] = 0.0
            
            # Convert grouped pages to list and sort by path
            pages_list = list(grouped_pages.values())
            pages_list.sort(key=lambda x: x['path'])
            
            # Apply pagination to the grouped pages list
            total_pages = len(pages_list)
            start_idx = (page - 1) * per_page
            end_idx = start_idx + per_page
            paginated_pages = pages_list[start_idx:end_idx]
            
            # Calculate pagination info
            total_pages_count = (total_pages + per_page - 1) // per_page if total_pages > 0 else 1
            has_prev = page > 1
            has_next = page < total_pages_count
            
            return jsonify({
                'success': True,
                'pages': paginated_pages,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total_pages,
                    'pages': total_pages_count,
                    'has_prev': has_prev,
                    'has_next': has_next,
                    'prev_num': page - 1 if has_prev else None,
                    'next_num': page + 1 if has_next else None
                }
            })
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500