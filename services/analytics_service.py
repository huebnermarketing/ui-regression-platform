from datetime import datetime, timedelta
from sqlalchemy import func, desc, and_, or_
from models import db
from models.project import Project, ProjectPage
from models.crawl_job import CrawlJob
from utils.timestamp_utils import utc_now
import json

class AnalyticsService:
    """Service for calculating analytics KPIs and generating reports"""
    
    def __init__(self):
        self.high_change_threshold = 15.0  # 15% threshold for high-change rate
    
    def get_dashboard_kpis(self, user_id, days_7=7, days_30=30):
        """
        Get top 6 KPIs for the analytics dashboard
        
        Returns:
            dict: Dictionary containing all KPI metrics
        """
        current_time = utc_now()
        seven_days_ago = current_time - timedelta(days=days_7)
        thirty_days_ago = current_time - timedelta(days=days_30)
        
        # Get user's projects for filtering
        user_projects = db.session.query(Project.id).filter_by(user_id=user_id).subquery()
        
        # 1. Total Runs (last 7D / 30D)
        runs_7d = db.session.query(CrawlJob).join(Project).filter(
            Project.user_id == user_id,
            CrawlJob.created_at >= seven_days_ago,
            CrawlJob.status.in_(['completed', 'ready', 'Job Failed', 'diff_failed'])
        ).count()
        
        runs_30d = db.session.query(CrawlJob).join(Project).filter(
            Project.user_id == user_id,
            CrawlJob.created_at >= thirty_days_ago,
            CrawlJob.status.in_(['completed', 'ready', 'Job Failed', 'diff_failed'])
        ).count()
        
        # 2. Success Rate (%)
        total_runs = db.session.query(CrawlJob).join(Project).filter(
            Project.user_id == user_id,
            CrawlJob.status.in_(['completed', 'ready', 'Job Failed', 'diff_failed'])
        ).count()
        
        successful_runs = db.session.query(CrawlJob).join(Project).filter(
            Project.user_id == user_id,
            CrawlJob.status.in_(['completed', 'ready'])
        ).count()
        
        success_rate = round((successful_runs / total_runs * 100) if total_runs > 0 else 0, 1)
        
        # 3. Failures (# + top reason)
        failed_runs = db.session.query(CrawlJob).join(Project).filter(
            Project.user_id == user_id,
            CrawlJob.status.in_(['Job Failed', 'diff_failed'])
        ).count()
        
        # Get top failure reason
        failure_reasons = db.session.query(
            CrawlJob.error_message,
            func.count(CrawlJob.id).label('count')
        ).join(Project).filter(
            Project.user_id == user_id,
            CrawlJob.status.in_(['Job Failed', 'diff_failed']),
            CrawlJob.error_message.isnot(None)
        ).group_by(CrawlJob.error_message).order_by(desc('count')).first()
        
        top_failure_reason = self._categorize_failure_reason(failure_reasons[0] if failure_reasons else None)
        
        # 4. Avg Total Processing Time
        avg_processing_time = db.session.query(
            func.avg(ProjectPage.duration)
        ).join(Project).filter(
            Project.user_id == user_id,
            ProjectPage.duration.isnot(None)
        ).scalar()
        
        avg_processing_time = float(avg_processing_time) if avg_processing_time else 0
        
        # 5. Change Rate (%) - % of diffs with visual changes > 0%
        total_diffs = db.session.query(ProjectPage).join(Project).filter(
            Project.user_id == user_id,
            ProjectPage.find_diff_status == 'completed',
            or_(
                ProjectPage.diff_mismatch_pct_desktop.isnot(None),
                ProjectPage.diff_mismatch_pct_tablet.isnot(None),
                ProjectPage.diff_mismatch_pct_mobile.isnot(None)
            )
        ).count()
        
        changed_diffs = db.session.query(ProjectPage).join(Project).filter(
            Project.user_id == user_id,
            ProjectPage.find_diff_status == 'completed',
            or_(
                ProjectPage.diff_mismatch_pct_desktop > 0,
                ProjectPage.diff_mismatch_pct_tablet > 0,
                ProjectPage.diff_mismatch_pct_mobile > 0
            )
        ).count()
        
        change_rate = round((changed_diffs / total_diffs * 100) if total_diffs > 0 else 0, 1)
        
        # 6. High-Change Rate (%) - % of diffs above threshold (≥15%)
        high_change_diffs = db.session.query(ProjectPage).join(Project).filter(
            Project.user_id == user_id,
            ProjectPage.find_diff_status == 'completed',
            or_(
                ProjectPage.diff_mismatch_pct_desktop >= self.high_change_threshold,
                ProjectPage.diff_mismatch_pct_tablet >= self.high_change_threshold,
                ProjectPage.diff_mismatch_pct_mobile >= self.high_change_threshold
            )
        ).count()
        
        high_change_rate = round((high_change_diffs / total_diffs * 100) if total_diffs > 0 else 0, 1)
        
        return {
            'total_runs': {
                '7d': runs_7d,
                '30d': runs_30d
            },
            'success_rate': success_rate,
            'failures': {
                'count': failed_runs,
                'top_reason': top_failure_reason
            },
            'avg_processing_time': {
                'seconds': avg_processing_time,
                'formatted': self._format_duration(avg_processing_time)
            },
            'change_rate': change_rate,
            'high_change_rate': high_change_rate
        }
    
    def get_runs_over_time(self, user_id, days=30):
        """
        Get runs over time data for trend chart
        
        Returns:
            dict: Chart data with dates and run counts
        """
        current_time = utc_now()
        start_date = current_time - timedelta(days=days)
        
        # Query runs grouped by date
        runs_by_date = db.session.query(
            func.date(CrawlJob.created_at).label('date'),
            func.count(CrawlJob.id).label('count')
        ).join(Project).filter(
            Project.user_id == user_id,
            CrawlJob.created_at >= start_date,
            CrawlJob.status.in_(['completed', 'ready', 'Job Failed', 'diff_failed'])
        ).group_by(func.date(CrawlJob.created_at)).order_by('date').all()
        
        # Fill in missing dates with 0 counts
        date_counts = {}
        for run in runs_by_date:
            date_counts[run.date.strftime('%Y-%m-%d')] = run.count
        
        # Generate complete date range
        chart_data = []
        for i in range(days):
            date = (start_date + timedelta(days=i)).date()
            date_str = date.strftime('%Y-%m-%d')
            chart_data.append({
                'date': date_str,
                'count': date_counts.get(date_str, 0)
            })
        
        return {
            'labels': [item['date'] for item in chart_data],
            'data': [item['count'] for item in chart_data]
        }
    
    def get_change_distribution(self, user_id):
        """
        Get change distribution histogram data
        
        Returns:
            dict: Histogram data for diff percentages
        """
        # Get all diff percentages (taking max across viewports)
        pages = db.session.query(
            ProjectPage.diff_mismatch_pct_desktop,
            ProjectPage.diff_mismatch_pct_tablet,
            ProjectPage.diff_mismatch_pct_mobile
        ).join(Project).filter(
            Project.user_id == user_id,
            ProjectPage.find_diff_status == 'completed',
            or_(
                ProjectPage.diff_mismatch_pct_desktop.isnot(None),
                ProjectPage.diff_mismatch_pct_tablet.isnot(None),
                ProjectPage.diff_mismatch_pct_mobile.isnot(None)
            )
        ).all()
        
        # Calculate max diff percentage for each page
        diff_percentages = []
        for page in pages:
            max_diff = 0
            if page.diff_mismatch_pct_desktop:
                max_diff = max(max_diff, float(page.diff_mismatch_pct_desktop))
            if page.diff_mismatch_pct_tablet:
                max_diff = max(max_diff, float(page.diff_mismatch_pct_tablet))
            if page.diff_mismatch_pct_mobile:
                max_diff = max(max_diff, float(page.diff_mismatch_pct_mobile))
            diff_percentages.append(max_diff)
        
        # Create histogram buckets
        buckets = [
            {'label': '0%', 'min': 0, 'max': 0, 'count': 0},
            {'label': '0-1%', 'min': 0.01, 'max': 1, 'count': 0},
            {'label': '1-5%', 'min': 1.01, 'max': 5, 'count': 0},
            {'label': '5-15%', 'min': 5.01, 'max': 15, 'count': 0},
            {'label': '15-30%', 'min': 15.01, 'max': 30, 'count': 0},
            {'label': '30%+', 'min': 30.01, 'max': float('inf'), 'count': 0}
        ]
        
        # Categorize diff percentages
        for diff_pct in diff_percentages:
            for bucket in buckets:
                if bucket['min'] <= diff_pct <= bucket['max']:
                    bucket['count'] += 1
                    break
        
        return {
            'labels': [bucket['label'] for bucket in buckets],
            'data': [bucket['count'] for bucket in buckets]
        }
    
    def get_failure_reasons(self, user_id, limit=10):
        """
        Get failure reasons bar chart data
        
        Returns:
            dict: Bar chart data for failure reasons
        """
        failure_reasons = db.session.query(
            CrawlJob.error_message,
            func.count(CrawlJob.id).label('count')
        ).join(Project).filter(
            Project.user_id == user_id,
            CrawlJob.status.in_(['Job Failed', 'diff_failed']),
            CrawlJob.error_message.isnot(None)
        ).group_by(CrawlJob.error_message).order_by(desc('count')).limit(limit).all()
        
        # Categorize and clean up failure reasons
        categorized_reasons = {}
        for reason, count in failure_reasons:
            category = self._categorize_failure_reason(reason)
            if category in categorized_reasons:
                categorized_reasons[category] += count
            else:
                categorized_reasons[category] = count
        
        # Sort by count
        sorted_reasons = sorted(categorized_reasons.items(), key=lambda x: x[1], reverse=True)
        
        return {
            'labels': [reason for reason, count in sorted_reasons],
            'data': [count for reason, count in sorted_reasons]
        }
    
    def get_top_changed_pages(self, user_id, limit=10):
        """
        Get top changed pages table data
        
        Returns:
            list: List of pages with highest diff percentages
        """
        pages = db.session.query(ProjectPage).join(Project).filter(
            Project.user_id == user_id,
            ProjectPage.find_diff_status == 'completed',
            or_(
                ProjectPage.diff_mismatch_pct_desktop.isnot(None),
                ProjectPage.diff_mismatch_pct_tablet.isnot(None),
                ProjectPage.diff_mismatch_pct_mobile.isnot(None)
            )
        ).all()
        
        # Calculate max diff percentage and sort
        page_data = []
        for page in pages:
            max_diff = 0
            max_viewport = 'desktop'
            
            if page.diff_mismatch_pct_desktop:
                desktop_diff = float(page.diff_mismatch_pct_desktop)
                if desktop_diff > max_diff:
                    max_diff = desktop_diff
                    max_viewport = 'desktop'
            
            if page.diff_mismatch_pct_tablet:
                tablet_diff = float(page.diff_mismatch_pct_tablet)
                if tablet_diff > max_diff:
                    max_diff = tablet_diff
                    max_viewport = 'tablet'
            
            if page.diff_mismatch_pct_mobile:
                mobile_diff = float(page.diff_mismatch_pct_mobile)
                if mobile_diff > max_diff:
                    max_diff = mobile_diff
                    max_viewport = 'mobile'
            
            if max_diff > 0:  # Only include pages with changes
                page_data.append({
                    'page_name': page.page_name or page.path,
                    'path': page.path,
                    'project_name': page.project.name,
                    'diff_percentage': max_diff,
                    'max_viewport': max_viewport,
                    'last_run': page.last_run_at
                })
        
        # Sort by diff percentage and limit
        page_data.sort(key=lambda x: x['diff_percentage'], reverse=True)
        return page_data[:limit]
    
    def get_slowest_pages(self, user_id, limit=10):
        """
        Get slowest pages table data
        
        Returns:
            list: List of pages with longest processing times
        """
        pages = db.session.query(ProjectPage).join(Project).filter(
            Project.user_id == user_id,
            ProjectPage.duration.isnot(None)
        ).order_by(desc(ProjectPage.duration)).limit(limit).all()
        
        return [{
            'page_name': page.page_name or page.path,
            'path': page.path,
            'project_name': page.project.name,
            'duration': float(page.duration),
            'duration_formatted': page.duration_formatted,
            'last_run': page.last_run_at
        } for page in pages]
    
    def get_storage_usage_by_project(self, user_id):
        """
        Get storage usage by project (estimated based on page counts)
        
        Returns:
            list: List of projects with estimated storage usage
        """
        projects = db.session.query(
            Project.name,
            func.count(ProjectPage.id).label('page_count')
        ).outerjoin(ProjectPage).filter(
            Project.user_id == user_id
        ).group_by(Project.id, Project.name).all()
        
        storage_data = []
        for project_name, page_count in projects:
            # Estimate storage: ~2MB per page (screenshots + diffs across viewports)
            estimated_mb = page_count * 2
            storage_data.append({
                'project_name': project_name,
                'page_count': page_count,
                'estimated_storage_mb': estimated_mb,
                'estimated_storage_formatted': self._format_storage(estimated_mb)
            })
        
        # Sort by storage usage
        storage_data.sort(key=lambda x: x['estimated_storage_mb'], reverse=True)
        return storage_data
    
    def _categorize_failure_reason(self, error_message):
        """Categorize error messages into common failure types"""
        if not error_message:
            return "Unknown Error"
        
        error_lower = error_message.lower()
        
        if 'timeout' in error_lower or 'timed out' in error_lower:
            return "Timeout"
        elif 'connection' in error_lower or 'network' in error_lower:
            return "Network Error"
        elif 'screenshot' in error_lower or 'capture' in error_lower:
            return "Screenshot Failure"
        elif 'diff' in error_lower or 'comparison' in error_lower:
            return "Diff Generation"
        elif 'crawl' in error_lower or 'spider' in error_lower:
            return "Crawling Error"
        elif 'permission' in error_lower or 'access' in error_lower or 'forbidden' in error_lower:
            return "Access Denied"
        elif 'not found' in error_lower or '404' in error_lower:
            return "Page Not Found"
        elif 'server error' in error_lower or '500' in error_lower:
            return "Server Error"
        else:
            return "Other Error"
    
    def _format_duration(self, seconds):
        """Format duration in seconds to human readable format"""
        if seconds is None or seconds == 0:
            return "0s"
        
        if seconds < 1:
            return f"{int(seconds * 1000)}ms"
        elif seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes}m {secs}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h {minutes}m"
    
    def _format_storage(self, mb):
        """Format storage size in MB to human readable format"""
        if mb < 1024:
            return f"{mb:.1f} MB"
        else:
            gb = mb / 1024
            return f"{gb:.1f} GB"
    
    def get_daily_scans_heatmap(self, user_id, days=30):
        """
        Get daily scans data for heatmap visualization
        
        Returns:
            dict: Daily scan data with dates, counts, and success rates
        """
        current_time = utc_now()
        start_date = current_time - timedelta(days=days)
        
        # Query daily scan data grouped by date (simplified approach)
        daily_scans = db.session.query(
            func.date(CrawlJob.created_at).label('date'),
            func.count(CrawlJob.id).label('total_scans')
        ).join(Project).filter(
            Project.user_id == user_id,
            CrawlJob.created_at >= start_date,
            CrawlJob.status.in_(['completed', 'ready', 'Job Failed', 'diff_failed'])
        ).group_by(func.date(CrawlJob.created_at)).order_by('date').all()
        
        # Get successful scans separately
        successful_scans_by_date = {}
        successful_scans = db.session.query(
            func.date(CrawlJob.created_at).label('date'),
            func.count(CrawlJob.id).label('count')
        ).join(Project).filter(
            Project.user_id == user_id,
            CrawlJob.created_at >= start_date,
            CrawlJob.status.in_(['completed', 'ready'])
        ).group_by(func.date(CrawlJob.created_at)).all()
        
        for scan in successful_scans:
            successful_scans_by_date[scan.date.strftime('%Y-%m-%d')] = scan.count
        
        # Get failed scans separately
        failed_scans_by_date = {}
        failed_scans = db.session.query(
            func.date(CrawlJob.created_at).label('date'),
            func.count(CrawlJob.id).label('count')
        ).join(Project).filter(
            Project.user_id == user_id,
            CrawlJob.created_at >= start_date,
            CrawlJob.status.in_(['Job Failed', 'diff_failed'])
        ).group_by(func.date(CrawlJob.created_at)).all()
        
        for scan in failed_scans:
            failed_scans_by_date[scan.date.strftime('%Y-%m-%d')] = scan.count
        
        # Create a complete date range with scan data
        heatmap_data = []
        scan_data_dict = {}
        
        # Convert query results to dictionary for easy lookup
        for scan in daily_scans:
            date_str = scan.date.strftime('%Y-%m-%d')
            successful_count = successful_scans_by_date.get(date_str, 0)
            failed_count = failed_scans_by_date.get(date_str, 0)
            total_count = int(scan.total_scans or 0)
            
            scan_data_dict[date_str] = {
                'total_scans': total_count,
                'successful_scans': successful_count,
                'failed_scans': failed_count,
                'avg_duration': 0,  # Simplified for now
                'success_rate': round((successful_count / total_count * 100) if total_count > 0 else 0, 1)
            }
        
        # Generate complete date range (last 30 days)
        for i in range(days):
            date = (start_date + timedelta(days=i)).date()
            date_str = date.strftime('%Y-%m-%d')
            
            if date_str in scan_data_dict:
                day_data = scan_data_dict[date_str]
            else:
                day_data = {
                    'total_scans': 0,
                    'successful_scans': 0,
                    'failed_scans': 0,
                    'avg_duration': 0,
                    'success_rate': 0
                }
            
            # Add date information
            day_data.update({
                'date': date_str,
                'day_of_week': date.weekday(),  # 0=Monday, 6=Sunday
                'day_of_month': date.day,
                'month': date.month,
                'year': date.year,
                'formatted_date': date.strftime('%b %d, %Y'),
                'intensity': self._calculate_scan_intensity(day_data['total_scans'])
            })
            
            heatmap_data.append(day_data)
        
        # Calculate summary statistics
        total_days_with_scans = len([d for d in heatmap_data if d['total_scans'] > 0])
        total_scans = sum(d['total_scans'] for d in heatmap_data)
        avg_scans_per_day = round(total_scans / days, 1) if days > 0 else 0
        busiest_day = max(heatmap_data, key=lambda x: x['total_scans']) if heatmap_data else None
        
        return {
            'heatmap_data': heatmap_data,
            'summary': {
                'total_days': days,
                'days_with_scans': total_days_with_scans,
                'total_scans': total_scans,
                'avg_scans_per_day': avg_scans_per_day,
                'busiest_day': {
                    'date': busiest_day['formatted_date'],
                    'scans': busiest_day['total_scans']
                } if busiest_day and busiest_day['total_scans'] > 0 else None
            }
        }
    
    def _calculate_scan_intensity(self, scan_count):
        """
        Calculate intensity level for heatmap coloring
        
        Returns:
            str: Intensity level (none, low, medium, high, very-high)
        """
        if scan_count == 0:
            return 'none'
        elif scan_count <= 2:
            return 'low'
        elif scan_count <= 5:
            return 'medium'
        elif scan_count <= 10:
            return 'high'
        else:
            return 'very-high'