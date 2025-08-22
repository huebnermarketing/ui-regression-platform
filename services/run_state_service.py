"""
Run State Service - Computes unified pipeline status for UI regression testing runs

This service implements the 6-state pipeline status system:
1. Not started - No jobs yet for a run
2. Crawling - A crawl job is running  
3. Crawled - Latest crawl job completed with pages > 0
4. Finding difference - A find_difference job is running OR any screenshot/diff job is running
5. Result - find_difference completed and at least one viewport diff/screenshot exists
6. Job failed - Any critical job has failed or orphaned status

The system uses deterministic precedence rules and provides consistent UI representation.
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple, Any
from sqlalchemy import desc, and_, or_
from models.crawl_job import CrawlJob
from models.project import Project, ProjectPage
from models import db


class RunStateService:
    """Service for computing unified run state across all job types"""
    
    # Pipeline states in precedence order (highest to lowest priority)
    PIPELINE_STATES = {
        'job_failed': {
            'priority': 1,
            'label': 'Job Failed',
            'description': 'Critical job failure or orphaned process',
            'color': '#ef4444',  # red
            'icon': 'fas fa-exclamation-triangle'
        },
        'finding_difference': {
            'priority': 2,
            'label': 'Finding Difference',
            'description': 'Processing screenshots and generating diffs',
            'color': '#9333ea',  # purple
            'icon': 'fas fa-search-plus'
        },
        'crawling': {
            'priority': 3,
            'label': 'Crawling',
            'description': 'Discovering pages on the website',
            'color': '#f59e0b',  # amber
            'icon': 'fas fa-spider'
        },
        'result': {
            'priority': 4,
            'label': 'Result',
            'description': 'Differences found and ready for review',
            'color': '#10b981',  # green
            'icon': 'fas fa-check-circle'
        },
        'crawled': {
            'priority': 5,
            'label': 'Crawled',
            'description': 'Pages discovered, ready for screenshot capture',
            'color': '#3b82f6',  # blue
            'icon': 'fas fa-list-ul'
        },
        'not_started': {
            'priority': 6,
            'label': 'Not Started',
            'description': 'No processing has begun',
            'color': '#6b7280',  # gray
            'icon': 'fas fa-minus-circle'
        }
    }
    
    def __init__(self, crawler_scheduler=None):
        """Initialize with optional crawler scheduler for real-time job status"""
        self.crawler_scheduler = crawler_scheduler
    
    def get_project_run_state(self, project_id: int, run_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get the unified run state for a project
        
        Args:
            project_id: The project ID
            run_id: Optional specific run ID, defaults to latest run
            
        Returns:
            Dict containing run_state, progress info, failure details, etc.
        """
        try:
            # Get project
            project = Project.query.filter_by(id=project_id).first()
            if not project:
                return self._create_error_state(f"Project {project_id} not found")
            
            # Get jobs for this project (latest run if run_id not specified)
            # FIXED: Always refresh from database to avoid caching issues
            jobs_query = CrawlJob.query.filter_by(project_id=project_id)
            
            if run_id:
                # Filter by specific run if provided
                jobs_query = jobs_query.filter_by(run_id=run_id)
            
            # FIXED: Ensure consistent ordering by creation time
            jobs = jobs_query.order_by(desc(CrawlJob.created_at)).all()
            
            # Get pages for this project/run
            # FIXED: Always refresh from database to avoid caching issues
            pages_query = ProjectPage.query.filter_by(project_id=project_id)
            if run_id:
                pages_query = pages_query.filter_by(current_run_id=run_id)
            
            pages = pages_query.all()
            
            # Compute run state based on jobs and pages
            run_state = self._compute_run_state(project_id, jobs, pages)
            
            # Add additional metadata
            run_state.update({
                'project_id': project_id,
                'run_id': run_id or 'latest',
                'total_jobs': len(jobs),
                'total_pages': len(pages),
                'last_updated': datetime.now(timezone.utc).isoformat(),
                'debug_info': {
                    'jobs_count': len(jobs),
                    'pages_count': len(pages),
                    'latest_job_status': jobs[0].status if jobs else None,
                    'latest_job_type': jobs[0].job_type if jobs else None
                }
            })
            
            return run_state
            
        except Exception as e:
            return self._create_error_state(f"Error computing run state: {str(e)}")
    
    def _compute_run_state(self, project_id: int, jobs: List[CrawlJob], pages: List[ProjectPage]) -> Dict[str, Any]:
        """
        Core logic to compute run state based on jobs and pages
        
        Precedence rules (highest to lowest priority):
        1. Job failed - Any critical job has failed or orphaned status
        2. Finding difference - A find_difference job is running OR any screenshot/diff job is running
        3. Crawling - A crawl job is running
        4. Result - find_difference completed and at least one viewport diff/screenshot exists
        5. Crawled - Latest crawl job completed with pages > 0
        6. Not started - No jobs yet for a run
        """
        
        # Check for job failures first (highest priority)
        failure_info = self._check_job_failures(project_id, jobs)
        if failure_info:
            return self._create_state('job_failed', **failure_info)
        
        # Check for active jobs (finding difference or crawling)
        active_job_info = self._check_active_jobs(project_id, jobs)
        if active_job_info:
            return self._create_state(active_job_info['state'], **active_job_info)
        
        # Check for completed states (result or crawled)
        completed_info = self._check_completed_states(jobs, pages)
        if completed_info:
            return self._create_state(completed_info['state'], **completed_info)
        
        # Default to not started
        return self._create_state('not_started', 
                                pages_total=len(pages),
                                pages_done=0,
                                progress_percentage=0)
    
    def _check_job_failures(self, project_id: int, jobs: List[CrawlJob]) -> Optional[Dict[str, Any]]:
        """Check for failed or orphaned jobs"""
        
        failed_jobs = [job for job in jobs if job.status in ['Job Failed', 'diff_failed']]
        if failed_jobs:
            latest_failed = failed_jobs[0]  # Most recent failed job
            return {
                'failure_reason': latest_failed.error_message or 'Job failed',
                'failure_details': f"Job {latest_failed.id} ({latest_failed.job_type}) failed",
                'failed_at': latest_failed.completed_at.isoformat() if latest_failed.completed_at else None,
                'pages_total': len(ProjectPage.query.filter_by(project_id=project_id).all()),
                'pages_done': 0,
                'progress_percentage': 0
            }
        
        # Check for orphaned jobs (running too long without scheduler)
        if self.crawler_scheduler:
            orphaned_jobs = self._check_orphaned_jobs(project_id, jobs)
            if orphaned_jobs:
                return {
                    'failure_reason': 'Job process terminated unexpectedly',
                    'failure_details': f"{len(orphaned_jobs)} orphaned job(s) detected",
                    'failed_at': datetime.now(timezone.utc).isoformat(),
                    'pages_total': len(ProjectPage.query.filter_by(project_id=project_id).all()),
                    'pages_done': 0,
                    'progress_percentage': 0
                }
        
        return None
    
    def _check_orphaned_jobs(self, project_id: int, jobs: List[CrawlJob]) -> List[CrawlJob]:
        """Check for jobs that are marked as running but not in scheduler"""
        if not self.crawler_scheduler:
            return []
        
        orphaned = []
        current_time = datetime.now(timezone.utc)
        
        for job in jobs:
            if (job.status == 'Crawling' and
                job.started_at and
                project_id not in self.crawler_scheduler.running_jobs):
                
                # Check if job has been running too long (>10 minutes)
                time_since_start = current_time - job.started_at
                if time_since_start.total_seconds() > 600:  # 10 minutes
                    orphaned.append(job)
        
        return orphaned
    
    def _check_active_jobs(self, project_id: int, jobs: List[CrawlJob]) -> Optional[Dict[str, Any]]:
        """Check for currently running jobs"""
        
        # Check scheduler status for real-time info
        scheduler_status = None
        if self.crawler_scheduler:
            scheduler_status = self.crawler_scheduler.get_job_status(project_id)
        
        # Check for running jobs in database - FIXED: Use correct enum values
        running_jobs = [job for job in jobs if job.status in ['Crawling', 'pending', 'finding_difference']]
        
        # Check if scheduler shows active job
        if scheduler_status and scheduler_status.get('status') == 'scheduled':
            running_jobs = [job for job in jobs if job.status == 'Crawling'] or running_jobs
        
        if running_jobs:
            latest_running = running_jobs[0]  # Most recent running job
            
            # Determine state based on job status first, then job type
            if latest_running.status == 'Crawling':
                state = 'crawling'
                description = 'Discovering pages on the website'
            elif latest_running.status == 'finding_difference':
                state = 'finding_difference'
                description = 'Processing screenshots and generating visual differences'
            elif latest_running.job_type in ['find_difference', 'screenshot', 'diff']:
                state = 'finding_difference'
                description = 'Processing screenshots and generating visual differences'
            elif latest_running.job_type in ['crawl', 'full_crawl']:
                state = 'crawling'
                description = 'Discovering pages on the website'
            else:
                # Default based on status if job_type is unclear
                if latest_running.status in ['Crawling', 'pending']:
                    state = 'crawling'
                    description = 'Discovering pages on the website'
                else:
                    state = 'finding_difference'
                    description = f'Processing {latest_running.job_type} job'
            
            # Get progress info
            progress_info = self._get_job_progress(project_id, latest_running)
            
            return {
                'state': state,
                'description': description,
                'job_id': latest_running.id,
                'job_type': latest_running.job_type,
                'started_at': latest_running.started_at.isoformat() if latest_running.started_at else None,
                **progress_info
            }
        
        return None
    
    def _get_job_progress(self, project_id: int, job: CrawlJob) -> Dict[str, Any]:
        """Get progress information for a running job"""
        
        # Get progress from scheduler if available
        if self.crawler_scheduler:
            progress_info = self.crawler_scheduler.get_progress_info(project_id)
            if progress_info:
                return {
                    'pages_total': progress_info.get('total_pages', 0),
                    'pages_done': progress_info.get('completed_pages', 0),
                    'progress_percentage': progress_info.get('progress', 0),
                    'current_operation': progress_info.get('message', 'Processing...')
                }
        
        # Fallback to database info
        total_pages = ProjectPage.query.filter_by(project_id=project_id).count()
        
        if job.job_type in ['crawl', 'full_crawl']:
            # For crawl jobs, pages_done is the number of pages discovered so far
            pages_done = total_pages
            progress = min(100, (pages_done / max(1, job.total_pages or 1)) * 100) if job.total_pages else 0
        else:
            # For other jobs, estimate based on page processing
            completed_pages = ProjectPage.query.filter(
                ProjectPage.project_id == project_id,
                or_(
                    ProjectPage.diff_status_desktop == 'completed',
                    ProjectPage.diff_status_tablet == 'completed',
                    ProjectPage.diff_status_mobile == 'completed'
                )
            ).count()
            pages_done = completed_pages
            progress = (pages_done / max(1, total_pages)) * 100 if total_pages > 0 else 0
        
        return {
            'pages_total': total_pages,
            'pages_done': pages_done,
            'progress_percentage': min(100, max(0, progress)),
            'current_operation': f'Processing {job.job_type}...'
        }
    
    def _check_completed_states(self, jobs: List[CrawlJob], pages: List[ProjectPage]) -> Optional[Dict[str, Any]]:
        """Check for completed states (result or crawled)"""
        
        if not jobs:
            return None
        
        # Get latest completed jobs by type - FIXED: Use correct enum values and sort by creation time
        completed_jobs = [job for job in jobs if job.status in ['Crawled', 'ready', 'diff_failed']]
        
        if not completed_jobs:
            return None
        
        # Sort completed jobs by creation time (most recent first) for consistent ordering
        completed_jobs.sort(key=lambda x: x.created_at, reverse=True)
        
        # Check for result state - jobs with 'ready' status that have completed the full lifecycle
        # This includes jobs that went through: Started → Crawling → Crawled → Finding difference → Ready
        ready_jobs = [job for job in completed_jobs if job.status == 'ready']
        if ready_jobs:
            # Sort ready jobs by creation time (most recent first)
            ready_jobs.sort(key=lambda x: x.created_at, reverse=True)
            latest_ready_job = ready_jobs[0]
            
            # Check if we have any completed diffs (indicating the full pipeline was completed)
            pages_with_diffs = [
                page for page in pages
                if any([
                    page.diff_status_desktop == 'completed',
                    page.diff_status_tablet == 'completed',
                    page.diff_status_mobile == 'completed'
                ])
            ]
            
            # If we have ready jobs and pages with diffs, show as "Result"
            if pages_with_diffs:
                total_diffs = sum([
                    1 for page in pages_with_diffs
                    for viewport in ['desktop', 'tablet', 'mobile']
                    if getattr(page, f'diff_status_{viewport}') == 'completed'
                ])
                
                return {
                    'state': 'result',
                    'pages_total': len(pages),
                    'pages_done': len(pages_with_diffs),
                    'progress_percentage': 100,
                    'total_diffs': total_diffs,
                    'completed_at': latest_ready_job.completed_at.isoformat() if latest_ready_job.completed_at else None
                }
            
            # If we have ready jobs but no diffs yet, still show as "Result" since the job completed
            # This handles cases where the job completed but diffs haven't been processed yet
            else:
                return {
                    'state': 'result',
                    'pages_total': len(pages),
                    'pages_done': len(pages),
                    'progress_percentage': 100,
                    'total_diffs': 0,
                    'completed_at': latest_ready_job.completed_at.isoformat() if latest_ready_job.completed_at else None
                }
        
        # Check for find_difference jobs specifically (backward compatibility)
        find_diff_jobs = [job for job in completed_jobs if job.job_type == 'find_difference' and job.status == 'ready']
        if find_diff_jobs:
            # Sort by creation time (most recent first)
            find_diff_jobs.sort(key=lambda x: x.created_at, reverse=True)
            latest_find_diff_job = find_diff_jobs[0]
            
            # Check if we have any completed diffs
            pages_with_diffs = [
                page for page in pages
                if any([
                    page.diff_status_desktop == 'completed',
                    page.diff_status_tablet == 'completed',
                    page.diff_status_mobile == 'completed'
                ])
            ]
            
            if pages_with_diffs:
                total_diffs = sum([
                    1 for page in pages_with_diffs
                    for viewport in ['desktop', 'tablet', 'mobile']
                    if getattr(page, f'diff_status_{viewport}') == 'completed'
                ])
                
                return {
                    'state': 'result',
                    'pages_total': len(pages),
                    'pages_done': len(pages_with_diffs),
                    'progress_percentage': 100,
                    'total_diffs': total_diffs,
                    'completed_at': latest_find_diff_job.completed_at.isoformat() if latest_find_diff_job.completed_at else None
                }
        
        # Check for crawled state - crawl completed with pages
        # FIXED: Only show crawled if there are no ready jobs (to ensure consistency)
        crawl_jobs = [job for job in completed_jobs if job.job_type in ['crawl', 'full_crawl'] and job.status == 'Crawled']
        if crawl_jobs and pages and not ready_jobs:
            # Sort by creation time (most recent first)
            crawl_jobs.sort(key=lambda x: x.created_at, reverse=True)
            latest_crawl_job = crawl_jobs[0]
            
            return {
                'state': 'crawled',
                'pages_total': len(pages),
                'pages_done': len(pages),
                'progress_percentage': 100,
                'completed_at': latest_crawl_job.completed_at.isoformat() if latest_crawl_job.completed_at else None
            }
        
        return None
    
    def _create_state(self, state_key: str, **kwargs) -> Dict[str, Any]:
        """Create a standardized state response"""
        state_config = self.PIPELINE_STATES.get(state_key, self.PIPELINE_STATES['not_started'])
        
        return {
            'state': state_key,  # FIXED: Use 'state' key to match template expectations
            'run_state': state_key,  # Keep for backward compatibility
            'label': state_config['label'],
            'description': kwargs.get('description', state_config['description']),
            'color': state_config['color'],
            'icon': state_config['icon'],
            'priority': state_config['priority'],
            'pages_total': kwargs.get('pages_total', 0),
            'pages_done': kwargs.get('pages_done', 0),
            'progress_percentage': kwargs.get('progress_percentage', 0),
            'failure_reason': kwargs.get('failure_reason'),
            'failure_details': kwargs.get('failure_details'),
            'failed_at': kwargs.get('failed_at'),
            'started_at': kwargs.get('started_at'),
            'completed_at': kwargs.get('completed_at'),
            'job_id': kwargs.get('job_id'),
            'job_type': kwargs.get('job_type'),
            'current_operation': kwargs.get('current_operation'),
            'total_diffs': kwargs.get('total_diffs', 0)
        }
    
    def _create_error_state(self, error_message: str) -> Dict[str, Any]:
        """Create an error state response"""
        return {
            'state': 'job_failed',  # FIXED: Use 'state' key to match template expectations
            'run_state': 'job_failed',  # Keep for backward compatibility
            'label': 'Error',
            'description': error_message,
            'color': '#ef4444',
            'icon': 'fas fa-exclamation-triangle',
            'priority': 1,
            'pages_total': 0,
            'pages_done': 0,
            'progress_percentage': 0,
            'failure_reason': error_message,
            'error': True
        }
    
    def get_multiple_projects_run_state(self, project_ids: List[int]) -> Dict[int, Dict[str, Any]]:
        """Get run states for multiple projects efficiently"""
        results = {}
        
        for project_id in project_ids:
            try:
                results[project_id] = self.get_project_run_state(project_id)
            except Exception as e:
                results[project_id] = self._create_error_state(f"Error: {str(e)}")
        
        return results
    
    def get_run_summary(self, project_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Get summary of recent runs for a project"""
        try:
            # Get recent runs (distinct run_ids from jobs)
            recent_runs = db.session.query(CrawlJob.run_id, CrawlJob.created_at).filter(
                CrawlJob.project_id == project_id,
                CrawlJob.run_id.isnot(None)
            ).distinct(CrawlJob.run_id).order_by(
                desc(CrawlJob.created_at)
            ).limit(limit).all()
            
            run_summaries = []
            for run_id, created_at in recent_runs:
                run_state = self.get_project_run_state(project_id, run_id)
                run_summaries.append({
                    'run_id': run_id,
                    'created_at': created_at.isoformat() if created_at else None,
                    **run_state
                })
            
            return run_summaries
            
        except Exception as e:
            return [self._create_error_state(f"Error getting run summary: {str(e)}")]