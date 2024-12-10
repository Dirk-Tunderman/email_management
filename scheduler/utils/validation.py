# filename: validation.py

from typing import Dict, List
import pytz
from datetime import datetime

def validate_email_data(email_data: Dict) -> bool:
    """
    Validate required fields in email data
    """
    required_fields = [
        'email_recipient',
        'subjectline',
        'email_content',
        'timezone'
    ]
    
    # Check required fields
    for field in required_fields:
        if field not in email_data:
            return False
    
    # Validate email recipients
    recipients = email_data['email_recipient']
    if not isinstance(recipients, (str, list)) or not recipients:
        return False
    
    # Validate timezone
    try:
        pytz.timezone(email_data['timezone'])
    except pytz.exceptions.UnknownTimeZoneError:
        return False
    
    return True

def validate_sender_config(sender_config: Dict) -> bool:
    """
    Validate sender configuration
    """
    required_fields = [
        'email',
        'daily_limit',
        'region'
    ]
    
    for field in required_fields:
        if field not in sender_config:
            return False
            
    # Validate daily limit
    if not isinstance(sender_config['daily_limit'], int) or sender_config['daily_limit'] <= 0:
        return False
        
    return True

def validate_sending_rules(rules: Dict) -> bool:
    """
    Validate sending rules configuration
    """
    required_fields = [
        'allowed_hours',
        'excluded_days',
        'min_time_between_emails',
        'daily_limit_per_sender'
    ]
    
    for field in required_fields:
        if field not in rules:
            return False
    
    # Validate allowed hours
    hours = rules['allowed_hours']
    if not isinstance(hours, dict) or 'start' not in hours or 'end' not in hours:
        return False
        
    # Validate excluded days
    if not isinstance(rules['excluded_days'], list):
        return False
        
    # Validate time between emails
    if not isinstance(rules['min_time_between_emails'], (int, float)) or rules['min_time_between_emails'] <= 0:
        return False
        
    return True