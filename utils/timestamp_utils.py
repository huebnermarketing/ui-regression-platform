"""
Timestamp Utility Module for PixelPulse UI Regression Platform

Provides consistent timestamp handling across the entire application.
All timestamps are stored in UTC and converted to IST for display.
"""

from datetime import datetime, timezone
import pytz

# IST timezone constant
IST_TIMEZONE = pytz.timezone('Asia/Kolkata')
UTC_TIMEZONE = timezone.utc

def utc_now():
    """Get current UTC datetime with timezone info"""
    return datetime.now(UTC_TIMEZONE)

def ist_now():
    """Get current IST datetime with timezone info"""
    return datetime.now(IST_TIMEZONE)

def to_utc(dt):
    """Convert any datetime to UTC"""
    if dt is None:
        return None
    
    if dt.tzinfo is None:
        # Assume naive datetime is in UTC
        return pytz.utc.localize(dt)
    else:
        # Convert timezone-aware datetime to UTC
        return dt.astimezone(UTC_TIMEZONE)

def to_ist(dt):
    """Convert any datetime to IST"""
    if dt is None:
        return None
    
    if dt.tzinfo is None:
        # Assume naive datetime is in UTC
        utc_dt = pytz.utc.localize(dt)
    else:
        # Convert timezone-aware datetime to UTC first
        utc_dt = dt.astimezone(UTC_TIMEZONE)
    
    # Convert UTC to IST
    return utc_dt.astimezone(IST_TIMEZONE)

def format_ist_date(dt):
    """Format datetime as IST date (DD/MM/YYYY)"""
    if dt is None:
        return 'Never'
    
    ist_dt = to_ist(dt)
    return ist_dt.strftime('%d/%m/%Y')

def format_ist_time(dt):
    """Format datetime as IST time (HH:MM AM/PM)"""
    if dt is None:
        return 'Never'
    
    ist_dt = to_ist(dt)
    return ist_dt.strftime('%I:%M %p')

def format_ist_datetime(dt):
    """Format datetime as IST datetime (DD/MM/YYYY HH:MM AM/PM)"""
    if dt is None:
        return 'Never'
    
    ist_dt = to_ist(dt)
    return ist_dt.strftime('%d/%m/%Y %I:%M %p')

def format_ist_short_datetime(dt):
    """Format datetime as IST short datetime (DD/MM HH:MM AM/PM)"""
    if dt is None:
        return 'Never'
    
    ist_dt = to_ist(dt)
    return ist_dt.strftime('%d/%m %I:%M %p')

def parse_timestamp_string(timestamp_str, format_str='%Y%m%d-%H%M%S'):
    """Parse timestamp string and return timezone-aware UTC datetime"""
    try:
        # Parse as naive datetime first
        naive_dt = datetime.strptime(timestamp_str, format_str)
        # Assume it's in IST and convert to UTC
        ist_dt = IST_TIMEZONE.localize(naive_dt)
        return ist_dt.astimezone(UTC_TIMEZONE)
    except ValueError:
        return None

def generate_timestamp_string(dt=None, format_str='%Y%m%d-%H%M%S'):
    """Generate timestamp string in IST timezone"""
    if dt is None:
        dt = utc_now()
    
    ist_dt = to_ist(dt)
    return ist_dt.strftime(format_str)

def format_jobs_history_datetime(dt):
    """Format datetime for Jobs History display (MMM DD, YYYY, hh:mm AM/PM) in IST"""
    if dt is None:
        return 'Never'
    
    ist_dt = to_ist(dt)
    return ist_dt.strftime('%b %d, %Y, %I:%M %p')
