from flask import render_template, jsonify, request
from flask_login import login_required, current_user
from models.crawl_job import CrawlJob
from models.project import Project
from models import db
from sqlalchemy import desc, func
from datetime import datetime, timezone, timedelta

def register_crawl_queue_routes(app, crawler_scheduler=None):
    """Register crawl queue routes with the Flask app"""
    
    @app.route('/crawl-queue')
    @login_required
    def crawl_queue():
        """Display the crawl queue page with all jobs"""
        # Get filter and pagination parameters
        status_filter = request.args.get('status', '')
        search_query = request.args.get('search', '')
        page_num = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        # Base query - only show jobs for current user's projects
        base_query = db.session.query(CrawlJob).join(Project).filter(
            Project.user_id == current_user.id
        )
        
        # Get KPI statistics
        kpi_stats = db.session.query(
            CrawlJob.status,
            func.count(CrawlJob.id).label('count')
        ).join(Project).filter(
            Project.user_id == current_user.id
        ).group_by(CrawlJob.status).all()
        
        # Convert to dictionary for easy access
        kpis = {
            'queued': 0,
            'running': 0,
            'completed': 0,
            'failed': 0
        }
        
        for stat in kpi_stats:
            if stat.status == 'pending':
                kpis['queued'] = stat.count
            elif stat.status in kpis:
                kpis[stat.status] = stat.count
        
        # Get active (running) jobs - filter by both database status and scheduler status
        db_running_jobs = base_query.filter(CrawlJob.status == 'running').order_by(desc(CrawlJob.started_at)).all()
        
        # Filter out jobs that are not actually running in the scheduler
        active_jobs = []
        for job in db_running_jobs:
            # Check if job is actually running in scheduler
            if crawler_scheduler and job.project_id in crawler_scheduler.running_jobs:
                active_jobs.append(job)
            else:
                # Job is marked as running in DB but not in scheduler
                # This could be due to:
                # 1. Job completed successfully but cleanup hasn't run yet
                # 2. Job failed or was terminated unexpectedly
                # 3. Application restart with orphaned jobs
                
                # Only update status if job has been running for more than 30 seconds
                # and is not in scheduler (to avoid race conditions with cleanup)
                current_utc = datetime.now(timezone.utc)
                if job.started_at and job.started_at.tzinfo is None:
                    # If job.started_at is naive, assume it's UTC
                    job_start_time = job.started_at.replace(tzinfo=timezone.utc)
                else:
                    job_start_time = job.started_at
                time_since_start = current_utc - job_start_time if job_start_time else timedelta(seconds=0)
                
                # SAFE ORPHAN CLEANUP RULE: DB is the source of truth
                # Only fail jobs that are truly orphaned (no completion, running too long)
                # Use generous grace period to avoid race conditions
                
                if time_since_start.total_seconds() > 600:  # 10 minutes grace period
                    try:
                        # Use atomic update to only fail truly orphaned jobs
                        from sqlalchemy import text
                        current_utc = datetime.now(timezone.utc)
                        result = db.session.execute(text('''
                            UPDATE crawl_jobs
                            SET status='failed',
                                error_message='Job process terminated unexpectedly (orphaned)',
                                completed_at=:current_time
                            WHERE id=:job_id
                              AND status='running'
                              AND completed_at IS NULL
                              AND started_at < :cutoff_time
                        '''), {
                            'job_id': job.id,
                            'current_time': current_utc,
                            'cutoff_time': current_utc - timedelta(minutes=10)
                        })
                        
                        if result.rowcount > 0:
                            print(f"Marked truly orphaned job {job.id} as failed (running >10min without completion)")
                            # Update local object
                            job.status = 'failed'
                            job.error_message = 'Job process terminated unexpectedly (orphaned)'
                            job.completed_at = current_utc
                        else:
                            print(f"Job {job.id} was not orphaned (already completed or not old enough)")
                            # Refresh from DB to get current status
                            db.session.refresh(job)
                            if job.status == 'completed':
                                print(f"Job {job.id} was actually completed - no action needed")
                        
                        db.session.commit()
                    except Exception as e:
                        print(f"Error in safe orphan cleanup for job {job.id}: {e}")
                        db.session.rollback()
                else:
                    # Job is recent or not in scheduler temporarily - keep as active
                    # This prevents race conditions during normal completion
                    active_jobs.append(job)
        
        # Apply filters for all jobs query
        query = base_query
        if status_filter and status_filter != 'all':
            query = query.filter(CrawlJob.status == status_filter)
        
        # Apply search filter (search in project name)
        if search_query:
            query = query.filter(Project.name.ilike(f'%{search_query}%'))
        
        # Order by created_at descending (newest first)
        query = query.order_by(desc(CrawlJob.created_at))
        
        # Paginate results
        pagination = query.paginate(
            page=page_num,
            per_page=per_page,
            error_out=False
        )
        
        all_jobs = pagination.items
        
        # Check if any jobs are running for auto-refresh
        has_running_jobs = len(active_jobs) > 0
        
        return render_template('crawl_queue/list.html',
                             kpis=kpis,
                             active_jobs=active_jobs,
                             all_jobs=all_jobs,
                             pagination=pagination,
                             has_running_jobs=has_running_jobs,
                             status_filter=status_filter,
                             search_query=search_query,
                             per_page=per_page)
    
    @app.route('/api/crawl-jobs')
    @login_required
    def api_crawl_jobs():
        """API endpoint to get crawl jobs data (for auto-refresh)"""
        # Get filter and pagination parameters
        status_filter = request.args.get('status', '')
        search_query = request.args.get('search', '')
        page_num = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        # Base query - only show jobs for current user's projects
        base_query = db.session.query(CrawlJob).join(Project).filter(
            Project.user_id == current_user.id
        )
        
        # Get KPI statistics
        kpi_stats = db.session.query(
            CrawlJob.status,
            func.count(CrawlJob.id).label('count')
        ).join(Project).filter(
            Project.user_id == current_user.id
        ).group_by(CrawlJob.status).all()
        
        # Convert to dictionary for easy access
        kpis = {
            'queued': 0,
            'running': 0,
            'completed': 0,
            'failed': 0
        }
        
        for stat in kpi_stats:
            if stat.status == 'pending':
                kpis['queued'] = stat.count
            elif stat.status in kpis:
                kpis[stat.status] = stat.count
        
        # Get active (running) jobs - filter by both database status and scheduler status
        db_running_jobs = base_query.filter(CrawlJob.status == 'running').order_by(desc(CrawlJob.started_at)).all()
        
        # Filter out jobs that are not actually running in the scheduler
        active_jobs = []
        for job in db_running_jobs:
            # Check if job is actually running in scheduler
            if crawler_scheduler and job.project_id in crawler_scheduler.running_jobs:
                active_jobs.append(job)
            else:
                # Job is marked as running in DB but not in scheduler
                # This could be due to:
                # 1. Job completed successfully but cleanup hasn't run yet
                # 2. Job failed or was terminated unexpectedly
                # 3. Application restart with orphaned jobs
                
                # Only update status if job has been running for more than 30 seconds
                # and is not in scheduler (to avoid race conditions with cleanup)
                current_utc = datetime.now(timezone.utc)
                if job.started_at and job.started_at.tzinfo is None:
                    # If job.started_at is naive, assume it's UTC
                    job_start_time = job.started_at.replace(tzinfo=timezone.utc)
                else:
                    job_start_time = job.started_at
                time_since_start = current_utc - job_start_time if job_start_time else timedelta(seconds=0)
                
                # SAFE ORPHAN CLEANUP RULE: DB is the source of truth
                # Only fail jobs that are truly orphaned (no completion, running too long)
                # Use generous grace period to avoid race conditions
                
                if time_since_start.total_seconds() > 600:  # 10 minutes grace period
                    try:
                        # Use atomic update to only fail truly orphaned jobs
                        from sqlalchemy import text
                        current_utc = datetime.now(timezone.utc)
                        result = db.session.execute(text('''
                            UPDATE crawl_jobs
                            SET status='failed',
                                error_message='Job process terminated unexpectedly (orphaned)',
                                completed_at=:current_time
                            WHERE id=:job_id
                              AND status='running'
                              AND completed_at IS NULL
                              AND started_at < :cutoff_time
                        '''), {
                            'job_id': job.id,
                            'current_time': current_utc,
                            'cutoff_time': current_utc - timedelta(minutes=10)
                        })
                        
                        if result.rowcount > 0:
                            print(f"Marked truly orphaned job {job.id} as failed (running >10min without completion)")
                            # Update local object
                            job.status = 'failed'
                            job.error_message = 'Job process terminated unexpectedly (orphaned)'
                            job.completed_at = current_utc
                        else:
                            print(f"Job {job.id} was not orphaned (already completed or not old enough)")
                            # Refresh from DB to get current status
                            db.session.refresh(job)
                            if job.status == 'completed':
                                print(f"Job {job.id} was actually completed - no action needed")
                        
                        db.session.commit()
                    except Exception as e:
                        print(f"Error in safe orphan cleanup for job {job.id}: {e}")
                        db.session.rollback()
                else:
                    # Job is recent or not in scheduler temporarily - keep as active
                    # This prevents race conditions during normal completion
                    active_jobs.append(job)
        
        # Apply filters for all jobs query
        query = base_query
        if status_filter and status_filter != 'all':
            query = query.filter(CrawlJob.status == status_filter)
        
        # Apply search filter
        if search_query:
            query = query.filter(Project.name.ilike(f'%{search_query}%'))
        
        # Order by created_at descending
        query = query.order_by(desc(CrawlJob.created_at))
        
        # Paginate results
        pagination = query.paginate(
            page=page_num,
            per_page=per_page,
            error_out=False
        )
        
        all_jobs = pagination.items
        
        # Convert active jobs to JSON format
        active_jobs_data = []
        for job in active_jobs:
            # Convert datetime to IST 12-hour format
            from app import to_ist_datetime
            started_at_ist = to_ist_datetime(job.started_at) if job.started_at else None
            
            active_jobs_data.append({
                'id': job.id,
                'project_name': job.project.name,
                'status': job.status,
                'total_pages': job.total_pages,
                'started_at': started_at_ist,
                'duration_formatted': job.duration_formatted,
                'project_id': job.project_id
            })
        
        # Convert all jobs to JSON format
        all_jobs_data = []
        for job in all_jobs:
            # Convert datetime to IST 12-hour format
            from app import to_ist_datetime
            started_at_ist = to_ist_datetime(job.started_at) if job.started_at else None
            completed_at_ist = to_ist_datetime(job.completed_at) if job.completed_at else None
            
            all_jobs_data.append({
                'id': job.id,
                'project_name': job.project.name,
                'status': job.status,
                'total_pages': job.total_pages,
                'started_at': started_at_ist,
                'completed_at': completed_at_ist,
                'duration_formatted': job.duration_formatted,
                'error_message': job.error_message,
                'project_id': job.project_id
            })
        
        # Check if any jobs are running
        has_running_jobs = len(active_jobs) > 0
        
        return jsonify({
            'kpis': kpis,
            'active_jobs': active_jobs_data,
            'all_jobs': all_jobs_data,
            'has_running_jobs': has_running_jobs,
            'pagination': {
                'page': pagination.page,
                'pages': pagination.pages,
                'per_page': pagination.per_page,
                'total': pagination.total,
                'has_prev': pagination.has_prev,
                'has_next': pagination.has_next,
                'prev_num': pagination.prev_num,
                'next_num': pagination.next_num
            }
        })
    
    @app.route('/api/crawl-jobs/<int:job_id>')
    @login_required
    def api_crawl_job_detail(job_id):
        """API endpoint to get specific crawl job details"""
        # Get job and verify it belongs to current user
        job = db.session.query(CrawlJob).join(Project).filter(
            CrawlJob.id == job_id,
            Project.user_id == current_user.id
        ).first()
        
        if not job:
            return jsonify({'error': 'Job not found'}), 404
        
        # Convert datetime to IST 12-hour format
        from app import to_ist_datetime
        started_at_ist = to_ist_datetime(job.started_at) if job.started_at else None
        completed_at_ist = to_ist_datetime(job.completed_at) if job.completed_at else None
        created_at_ist = to_ist_datetime(job.created_at)
        
        return jsonify({
            'id': job.id,
            'project_name': job.project.name,
            'status': job.status,
            'total_pages': job.total_pages,
            'started_at': started_at_ist,
            'completed_at': completed_at_ist,
            'duration_formatted': job.duration_formatted,
            'error_message': job.error_message,
            'project_id': job.project_id,
            'created_at': created_at_ist
        })
    
    @app.route('/api/crawl-jobs/<int:job_id>/start', methods=['POST'])
    @login_required
    def api_start_crawl_job(job_id):
        """API endpoint to start a crawl job"""
        try:
            # Get job and verify it belongs to current user
            job = db.session.query(CrawlJob).join(Project).filter(
                CrawlJob.id == job_id,
                Project.user_id == current_user.id
            ).first()
            
            if not job:
                return jsonify({'success': False, 'message': 'Job not found'}), 404
            
            # Check if job can be started
            if job.status not in ['pending', 'paused']:
                return jsonify({'success': False, 'message': f'Cannot start job with status: {job.status}'}), 400
            
            # Use scheduler to start/resume the job
            if crawler_scheduler:
                success = crawler_scheduler.start_job(job_id)
                if success:
                    # Update job status in database
                    job.start()
                    db.session.commit()
                    return jsonify({'success': True, 'message': 'Job started successfully'})
                else:
                    return jsonify({'success': False, 'message': 'Failed to start job in scheduler'}), 500
            else:
                # Fallback: just update database status
                job.start()
                db.session.commit()
                return jsonify({'success': True, 'message': 'Job started successfully'})
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)}), 500
    
    @app.route('/api/crawl-jobs/<int:job_id>/pause', methods=['POST'])
    @login_required
    def api_pause_crawl_job(job_id):
        """API endpoint to pause a crawl job"""
        try:
            # Get job and verify it belongs to current user
            job = db.session.query(CrawlJob).join(Project).filter(
                CrawlJob.id == job_id,
                Project.user_id == current_user.id
            ).first()
            
            if not job:
                return jsonify({'success': False, 'message': 'Job not found'}), 404
            
            # Check if job can be paused
            if job.status != 'running':
                return jsonify({'success': False, 'message': f'Cannot pause job with status: {job.status}. Job is currently {job.status}.'}), 400
            
            # Use scheduler to pause the job
            if crawler_scheduler:
                success = crawler_scheduler.pause_job(job_id)
                if success:
                    return jsonify({'success': True, 'message': 'Job pause signal sent successfully'})
                else:
                    # Job not found in scheduler (probably already completed)
                    return jsonify({'success': False, 'message': f'Job is not currently running. Current status: {job.status}'}), 400
            else:
                # Fallback: just update database status
                job.pause()
                db.session.commit()
                return jsonify({'success': True, 'message': 'Job paused successfully'})
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)}), 500
    
    @app.route('/api/crawl-jobs/<int:job_id>/stop', methods=['POST'])
    @login_required
    def api_stop_crawl_job(job_id):
        """API endpoint to stop a crawl job"""
        try:
            # Get job and verify it belongs to current user
            job = db.session.query(CrawlJob).join(Project).filter(
                CrawlJob.id == job_id,
                Project.user_id == current_user.id
            ).first()
            
            if not job:
                return jsonify({'success': False, 'message': 'Job not found'}), 404
            
            # Check if job can be stopped
            if job.status not in ['running', 'pending', 'paused']:
                return jsonify({'success': False, 'message': f'Cannot stop job with status: {job.status}. Job is already {job.status}.'}), 400
            
            # Use scheduler to stop the job
            if crawler_scheduler:
                success = crawler_scheduler.stop_job(job_id)
                if success:
                    return jsonify({'success': True, 'message': 'Job stop signal sent successfully'})
                else:
                    # Job not found in scheduler (probably already completed)
                    # Update database status directly
                    if job.status in ['running', 'pending', 'paused']:
                        job.fail_job('Job stopped by user')
                        db.session.commit()
                        return jsonify({'success': True, 'message': 'Job stopped successfully'})
                    else:
                        return jsonify({'success': False, 'message': f'Job is already {job.status}'}), 400
            else:
                # Fallback: just update database status
                job.fail_job('Job stopped by user')
                db.session.commit()
                return jsonify({'success': True, 'message': 'Job stopped successfully'})
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)}), 500