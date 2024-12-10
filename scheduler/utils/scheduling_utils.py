from datetime import datetime, timedelta
import pytz
from typing import Dict, List, Tuple

def group_by_timezone(emails: List[Dict]) -> Dict[str, List[Dict]]: #####
    """
    Group emails by recipient timezone
    """
    grouped_emails = {}
    
    for email in emails:
        timezone = email.get('time_zone', 'Europe/Amsterdam')  # Default to Amsterdam
        if timezone not in grouped_emails:
            grouped_emails[timezone] = []
        grouped_emails[timezone].append(email)
        
    return grouped_emails

def get_next_sending_window(timezone: str, current_time: datetime = None) -> Tuple[datetime, datetime]: ####
    """
    Calculate the next available sending window for a timezone
    Returns: (window_start, window_end)
    """
    if current_time is None:
        current_time = datetime.now(pytz.UTC)
        
    tz = pytz.timezone(timezone)
    local_time = current_time.astimezone(tz)
    
    # Create window for today
    window_start = local_time.replace(hour=7, minute=0, second=0, microsecond=0)
    window_end = local_time.replace(hour=17, minute=0, second=0, microsecond=0)
    
    # If current time is past today's window, move to next day
    if local_time >= window_end:
        window_start += timedelta(days=1)
        window_end += timedelta(days=1)
    
    # If current time is before today's window, use today's window
    elif local_time < window_start:
        pass  # Use the window_start/end as already calculated
        
    # Skip Saturday
    while window_start.strftime('%A') == 'Saturday':
        window_start += timedelta(days=1)
        window_end += timedelta(days=1)
        
    return window_start, window_end

def calculate_schedule_time(timezone: str, base_time: datetime, sender_schedule: List[datetime]) -> datetime:
    """
    Calculate next available schedule time considering:
    1. Recipient's business hours (7 AM - 5 PM in their timezone)
    2. 20-minute gap from sender's last scheduled email
    3. No restriction on local sending time
    
    Args:
        timezone: Recipient's timezone
        base_time: Current time or starting point
        sender_schedule: List of already scheduled times for this sender
    """
    tz = pytz.timezone(timezone)
    recipient_time = base_time.astimezone(tz)
    
    # Start with the earliest possible time considering sender's schedule
    if sender_schedule:
        # Get the latest scheduled time for this sender
        latest_send = max(sender_schedule)
        next_available = latest_send + timedelta(minutes=20)
        # Use the later of base_time or next_available
        proposed_time = max(base_time, next_available)
    else:
        proposed_time = base_time
    
    # Convert to recipient's timezone to check business hours
    recipient_time = proposed_time.astimezone(tz)
    
    # Adjust to next business hours if needed
    while True:
        hour = recipient_time.hour
        is_saturday = recipient_time.strftime('%A') == 'Saturday'
        
        if is_saturday:
            # Skip to Monday 7 AM
            recipient_time += timedelta(days=2)
            recipient_time = recipient_time.replace(hour=7, minute=0, second=0, microsecond=0)
        elif hour < 7:
            # Move to 7 AM same day
            recipient_time = recipient_time.replace(hour=7, minute=0, second=0, microsecond=0)
        elif hour >= 17:
            # Move to 7 AM next day
            recipient_time += timedelta(days=1)
            recipient_time = recipient_time.replace(hour=7, minute=0, second=0, microsecond=0)
        else:
            break
    
    return recipient_time