# filename: time_utils.py

from datetime import datetime, timedelta
import pytz
from typing import Dict

def is_valid_send_time(
    current_time: datetime,
    recipient_timezone: str,
    sending_rules: Dict
) -> bool:
    """
    Check if it's a valid time to send an email based on:
    - Recipient's local time (7 AM - 5 PM)
    - Not on Saturday
    """
    # Convert to recipient's timezone
    recipient_time = current_time.astimezone(pytz.timezone(recipient_timezone))
    
    # Check if it's Saturday
    if recipient_time.strftime('%A') in sending_rules['excluded_days']:
        return False
    
    # Parse allowed hours
    start_hour = int(sending_rules['allowed_hours']['start'].split(':')[0])
    end_hour = int(sending_rules['allowed_hours']['end'].split(':')[0])
    
    # Check if within allowed hours
    return start_hour <= recipient_time.hour < end_hour

def calculate_next_valid_time(
    base_time: datetime,
    recipient_timezone: str,
    sending_rules: Dict = None
) -> datetime:
    """
    Calculate the next valid sending time from a base time
    """
    if sending_rules is None:
        sending_rules = {
            "allowed_hours": {"start": "07:00", "end": "18:00"},
            "excluded_days": ["Sunday"],
            "min_time_between_emails": 20
        }
    
    # Convert to recipient's timezone
    recipient_tz = pytz.timezone(recipient_timezone)
    local_time = base_time.astimezone(recipient_tz)
    
    # Parse allowed hours
    start_hour = int(sending_rules['allowed_hours']['start'].split(':')[0])
    end_hour = int(sending_rules['allowed_hours']['end'].split(':')[0])
    
    # If it's after end_hour, move to next day at start_hour
    if local_time.hour >= end_hour:
        next_day = local_time + timedelta(days=1)
        local_time = next_day.replace(
            hour=start_hour,
            minute=0,
            second=0,
            microsecond=0
        )
    
    # If it's before start_hour, move to start_hour
    elif local_time.hour < start_hour:
        local_time = local_time.replace(
            hour=start_hour,
            minute=0,
            second=0,
            microsecond=0
        )
    
    # Check if it's Saturday
    while local_time.strftime('%A') in sending_rules['excluded_days']:
        local_time += timedelta(days=1)
        local_time = local_time.replace(
            hour=start_hour,
            minute=0,
            second=0,
            microsecond=0
        )
    
    # Convert back to UTC
    return local_time.astimezone(pytz.UTC)

def format_datetime(dt: datetime) -> str:
    """Format datetime for JSON serialization"""
    return dt.isoformat() if dt else None

def parse_datetime(dt_str: str) -> datetime:
    """Parse datetime from JSON string"""
    return datetime.fromisoformat(dt_str) if dt_str else None