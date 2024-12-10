import json
import os
from pathlib import Path
import pytz, re
import logging
from rich.console import Console
from dotenv import load_dotenv
from src.email_management.src.lib.smtp_based_funcions import EmailSender
from src.email_management.scheduler.utils.tracker_utils import load_tracker
from src.email_management.scheduler.utils.scheduling_utils import calculate_schedule_time, group_by_timezone
import time
import datetime
# Add imports if not already present at top of sender.py
from datetime import datetime, timedelta
import pytz
import json
import logging
import time
from typing import Dict, Any, Tuple, List, Optional
import random
import math
import pandas as pd
from src.email_management.src.lib.supabase_client import post, get_one, get_all, update, delete, post_email
import uuid 
from src.email_management.src.lib.supabase_client import supabase_client
import traceback
import base64
import asyncio  # Add this import at the top
 
console = Console()
logger = logging.getLogger(__name__)




# The optimized scheduler implementation (in src/email_management/scheduler/optimized_scheduler.py)
import pytz
from datetime import datetime, timedelta
from typing import Dict, List
import logging
import time
from msal import ConfidentialClientApplication
import requests
from datetime import datetime, timedelta
import os
import logging

logger = logging.getLogger(__name__)




class TimeWindow:
    def __init__(self, start_time: datetime, end_time: datetime):
        self.start_time = start_time
        self.end_time = end_time
        self.scheduled_emails = []
    
    def get_available_slots(self, recipient_tz: str) -> List[datetime]:
        """Find all available 20-min slots in window that respect recipient hours"""
        slots = []
        current = self.start_time
        
        while current < self.end_time:
            recipient_time = current.astimezone(pytz.timezone(recipient_tz))
            if 7 <= recipient_time.hour < 18:
                if self._is_valid_slot(current):
                    slots.append(current)
            current += timedelta(minutes=20)
        
        return slots
    
    def _is_valid_slot(self, time: datetime) -> bool:
        for scheduled in self.scheduled_emails:
            if abs((time - scheduled).total_seconds()) < 1200:
                return False
        return True



# Universal salutations that are commonly used across languages
UNIVERSAL_SALUTATIONS = {
    "hi": True,
    "hey": True,
    "hello": True,
    "hoi": True,
    "hallo": True,
    "hola": True
}

# Language-specific salutations and greetings
SALUTATIONS = {
    "en": {
        "formal": ["Dear", "To"],
        "informal": [],  # Moved to UNIVERSAL_SALUTATIONS
        "morning": "Good morning",
        "afternoon": "Good afternoon"
    },
    "de": {
        "formal": ["Sehr geehrte", "Sehr geehrter"],
        "informal": [],  # Most informal ones are in UNIVERSAL_SALUTATIONS
        "morning": "Guten Morgen",
        "afternoon": "Guten Tag"
    },
    "nl": {
        "formal": ["Geachte", "Beste"],
        "informal": ["Dag"],  # Most moved to UNIVERSAL_SALUTATIONS
        "morning": "Goedemorgen",
        "afternoon": "Goedemiddag"
    },
    "es": {
        "formal": ["Estimado", "Estimada", "Distinguido", "Distinguida"],
        "informal": ["Querido", "Querida"],  # Most common ones moved to UNIVERSAL_SALUTATIONS
        "morning": "Buenos días",
        "afternoon": "Buenas tardes"
    }
}


# At the top of the file, after imports
def load_root_env(): ###
    """Load environment variables from root .env file"""
    try:
        # Get the current working directory
        env_path = os.path.join(os.getcwd(), '.env')
        console.log(f"Loading .env from: {env_path}")
        
        if not os.path.exists(env_path):
            raise FileNotFoundError(f"Could not find .env file at {env_path}")
            
        # Load environment variables
        load_dotenv(dotenv_path=env_path, override=True)
        
        # Verify worker count was loaded
        worker_count = int(os.getenv('WORKER_EMAILS_COUNT', 4))
        console.log(f"Found {worker_count} worker emails in configuration")
        
        return True
    except Exception as e:
        console.log(f"[red]Error loading environment: {str(e)}[/red]")
        return False



def is_universal_salutation(word: str) -> bool:
    """
    Check if a word is a universal salutation.
    """
    return word.lower() in UNIVERSAL_SALUTATIONS


def detect_salutation(email_content: str) -> Tuple[Optional[str], Optional[str], bool]:
    """
    Detect the salutation in the email content and return:
    (salutation, language, is_universal)
    Returns (None, None, False) if no salutation is found.
    """
    if not email_content:
        return None, None, False
    
    # Get the first line of the email
    first_line = email_content.strip().split('\n')[0].strip()
    first_word = first_line.split()[0] if first_line else ""
    
    # First check for universal salutations
    if is_universal_salutation(first_word):
        return first_word, None, True
    
    # Find the longest matching language-specific salutation
    longest_match = (None, None, False, 0)  # (salutation, language, is_universal, length)
    
    for lang, sals in SALUTATIONS.items():
        # Check both formal and informal salutations
        all_sals = sals["formal"] + sals["informal"]
        for sal in all_sals:
            # Case insensitive comparison
            if first_line.lower().startswith(sal.lower()):
                if len(sal) > longest_match[3]:
                    longest_match = (sal, lang, False, len(sal))
    
    if longest_match[0] is None:
        return None, None, False
    
    return longest_match[0], longest_match[1], longest_match[2]













def clean_subject(subject: str) -> str:
    """
    Clean email subject by removing all variations of 'Re:' prefixes
    Args:
        subject: Original email subject
    Returns:
        Cleaned subject string
    """
    # Handle multiple 'Re:' prefixes and variations in case
    cleaned = re.sub(r'^(?:Re:\s*)+', '', subject, flags=re.IGNORECASE)
    # Remove any leading/trailing whitespace
    cleaned = cleaned.strip()
    print(f"Cleaned subject: '{cleaned}' (original: '{subject}')")
    return cleaned







def generate_conversation_id() -> str:
    """Generate a unique conversation ID for new email threads"""
    return f"VF_{int(time.time())}_{uuid.uuid4().hex[:8]}"




def get_time_based_greeting(timestamp: str, language: str) -> str:
    """
    Get the appropriate greeting based on time and language.
    """
    try:
        # Parse the timestamp
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        
        # Check if time is before 11:55
        is_morning = dt.hour < 11 or (dt.hour == 11 and dt.minute < 55)
        
        # Get the appropriate greeting
        if language in SALUTATIONS:
            return SALUTATIONS[language]["morning" if is_morning else "afternoon"]
        else:
            # Default to English if language not found
            return SALUTATIONS["en"]["morning" if is_morning else "afternoon"]
            
    except (ValueError, AttributeError):
        # If there's any error parsing the time, default to afternoon greeting in English
        return SALUTATIONS["en"]["afternoon"]





def process_email(email_data: Dict) -> Dict:
    """
    Process the email data and replace salutations based on time and language.
    """
    try:
        # Extract necessary information
        email_content = email_data.get('email_data', {}).get('email_content', '')
        recipient_time = email_data.get('recipient_time', '')
        specified_language = email_data.get('email_data', {}).get('language', 'en')
        
        if not email_content or not recipient_time:
            return email_data
        
        # Detect the salutation
        salutation, detected_lang, is_universal = detect_salutation(email_content)
        
        if salutation is None:
            return email_data
        
        # Determine which language to use for the greeting
        if is_universal:
            # For universal salutations, use the language specified in the email
            lang_to_use = specified_language
        else:
            # For language-specific salutations, use the detected language
            lang_to_use = detected_lang or specified_language
        
        # Get the appropriate time-based greeting
        new_greeting = get_time_based_greeting(recipient_time, lang_to_use)
        
        # Replace the salutation in the email content
        # Using case-insensitive replacement to catch any capitalization
        if is_universal:
            # For universal salutations, replace just the first word
            words = email_content.split(maxsplit=1)
            if len(words) > 1:
                new_content = new_greeting + ' ' + words[1]
            else:
                new_content = new_greeting
        else:
            # For language-specific salutations, replace the entire salutation
            new_content = email_content.replace(salutation, new_greeting, 1)
            
        email_data['email_data']['email_content'] = new_content
        return email_data
        
    except Exception as e:
        print(f"Error processing email: {str(e)}")
        return email_data









def calculate_total_capacity(days: int, sender_count: int) -> int: ####
    """Calculate total email capacity for given days and senders"""
    return days * sender_count * 30


def initialize_scheduling_windows(current_time: datetime, days: int = 10) -> List[TimeWindow]: ####
    """Create initial scheduling windows for specified number of days"""
    return [TimeWindow(
        start_time=current_time,
        end_time=current_time + timedelta(days=days)
    )]


def extend_scheduling_windows(windows: List[TimeWindow], additional_days: int = 10) -> List[TimeWindow]: #####
    """Extend existing windows by adding more days"""
    last_window = windows[-1]
    new_window = TimeWindow(
        start_time=last_window.end_time,
        end_time=last_window.end_time + timedelta(days=additional_days)
    )
    windows.append(new_window)
    return windows







def find_next_available_day(tracker: Dict, sender_email: str, current_day: str) -> str:
    """Find next day with available capacity, creating new days as needed"""
    current_date = datetime.strptime(current_day, "%Y-%m-%d")
    
    while True:
        day_str = current_date.strftime("%Y-%m-%d")
        sender_data = tracker['sending_accounts'][sender_email]
        
        # If day doesn't exist in daily_schedule_count, create it
        if day_str not in sender_data['daily_schedule_count']:
            sender_data['daily_schedule_count'][day_str] = 0
            logger.info(f"Created new day {day_str} for {sender_email}")
            return day_str
        
        # If day exists but not full, use it
        daily_count = sender_data['daily_schedule_count'][day_str]
        if daily_count < 30:
            return day_str
        
        # If day is full, move to next day
        current_date += timedelta(days=1)
        logger.info(f"Day {day_str} full for {sender_email}, checking {current_date.strftime('%Y-%m-%d')}")


def check_time_interval(sender_queue: List[Dict], proposed_time: datetime) -> bool:
    """Check if proposed time maintains 20-min interval with existing emails"""
    for email in sender_queue:
        scheduled_time = datetime.fromisoformat(email['scheduled_time'])
        time_diff = abs((proposed_time - scheduled_time).total_seconds())
        if time_diff < 1200:  # 20 minutes in seconds
            return False
    return True





def get_schedule_day(time: datetime) -> str: #####
    """
    Get the schedule day for a given time.
    Schedule days run from 7AM to 7AM next day UTC.
    """
    # Convert to UTC for consistent handling
    utc_time = time.astimezone(pytz.UTC)
    
    # If time is before 7 AM, it belongs to previous day's schedule
    if utc_time.hour < 7:
        return (utc_time.date() - timedelta(days=1)).strftime("%Y-%m-%d")
    return utc_time.date().strftime("%Y-%m-%d")





def find_optimal_slot(email: Dict, windows: List[TimeWindow], sender_queue: List[Dict], 
                     tracker: Dict, sender_email: str) -> Optional[datetime]:
    current_time = datetime.now(pytz.UTC)
    current_day = get_schedule_day(current_time)
    days_tried = set()
    
    while len(days_tried) < 10:  # Try up to 10 days
        # Get next available day
        target_day = find_next_available_day(tracker, sender_email, current_day)
        if target_day in days_tried:
            current_day = (datetime.strptime(target_day, "%Y-%m-%d") + 
                         timedelta(days=1)).strftime("%Y-%m-%d")
            continue
            
        days_tried.add(target_day)
        
        # Get slots for this day
        all_slots = []
        for window in windows:
            slots = get_available_slots_for_day(window, email['time_zone'], target_day)
            all_slots.extend(slots)
        
        # Check each slot
        for slot in sorted(all_slots):
            if check_time_interval(sender_queue, slot):
                emails_in_window = len([
                    e for e in sender_queue
                    if slot - timedelta(hours=24) <= datetime.fromisoformat(e['scheduled_time']) <= slot
                ])
                if emails_in_window < 30:
                    return slot
        
        # Move to next day if no slots found
        current_day = (datetime.strptime(target_day, "%Y-%m-%d") + 
                      timedelta(days=1)).strftime("%Y-%m-%d")
    
    return None


def get_available_slots_for_day(window: TimeWindow, recipient_tz: str, target_day: str) -> List[datetime]:
    """Get available slots specifically for target day"""
    slots = []
    current = window.start_time
    
    while current < window.end_time:
        slot_day = get_schedule_day(current)
        if slot_day == target_day:
            recipient_time = current.astimezone(pytz.timezone(recipient_tz))
            if 7 <= recipient_time.hour < 18:
                if window._is_valid_slot(current):
                    slots.append(current)
        current += timedelta(minutes=20)
    
    return slots

def update_daily_schedule_count(tracker: Dict, sender_email: str, schedule_time: datetime) -> None: ####
    """Update the daily schedule count for a sender"""
    schedule_day = get_schedule_day(schedule_time)
    sender_data = tracker['sending_accounts'][sender_email]
    
    # Initialize the day if it doesn't exist
    if schedule_day not in sender_data['daily_schedule_count']:
        # Get all days between current and scheduled
        current_date = datetime.now(pytz.UTC).date()
        scheduled_date = datetime.fromisoformat(schedule_time).date()
        
        # Add any missing days in between
        while current_date <= scheduled_date:
            day_str = current_date.strftime("%Y-%m-%d")
            if day_str not in sender_data['daily_schedule_count']:
                sender_data['daily_schedule_count'][day_str] = 0
            current_date += timedelta(days=1)
    
    # Update count for scheduled day
    sender_data['daily_schedule_count'][schedule_day] += 1





def initialize_sender_in_tracker(tracker: Dict, sender_email: str, daily_limit: int) -> None:
    """Initialize a new sender in the tracker with default values"""
    if 'sending_accounts' not in tracker:
        tracker['sending_accounts'] = {}
        
    if sender_email not in tracker['sending_accounts']:
        current_date = datetime.now(pytz.UTC).date()
        
        tracker['sending_accounts'][sender_email] = {
            "daily_limit": daily_limit,
            "time_between_emails": 20,
            "emails_sent_today": 0,
            "last_reset_date": current_date.strftime("%Y-%m-%d"),
            "last_scheduled_time": datetime.now(pytz.UTC).isoformat(),
            "daily_schedule_count": {
                current_date.strftime("%Y-%m-%d"): 0  # Only initialize current day
            },
            "email_queue": []
        }











def schedule_emails_optimized(email_data: List[Dict], senders: Dict, tracker: Dict, campaign_id: str): ###
    """Schedule emails optimizing for window utilization with balanced distribution"""
    logger.info("Starting optimized email scheduling")
    print(f"emaildata: {email_data} ")
    # Initialize tracker for all senders first
    for sender_email, sender in senders.items():
        initialize_sender_in_tracker(tracker, sender_email, sender.daily_limit)
    
    current_time = datetime.now(pytz.UTC)
    
    # Calculate if we need more than initial 10 days
    total_emails = len(email_data)
    initial_days = 10
    total_capacity = calculate_total_capacity(initial_days, len(senders))
    
    # Create initial windows
    windows = initialize_scheduling_windows(current_time, initial_days)
    
    # If emails exceed capacity, create additional windows
    if total_emails > total_capacity:
        additional_days_needed = math.ceil(total_emails / (len(senders) * 30)) - initial_days
        if additional_days_needed > 0:
            windows = extend_scheduling_windows(windows, additional_days_needed)
            logger.info(f"Extended scheduling windows by {additional_days_needed} days")
    
    emails_scheduled = 0
    email_data = list(email_data)
    random.shuffle(email_data)
    
    for email in email_data:
        slot = None
        sender_email = None
        attempts = 0
        max_attempts = len(senders) * 3  # Try each sender multiple times
        
        # Keep trying until we find a slot or run out of attempts
        while slot is None and attempts < max_attempts:
            # Randomly select a sender
            potential_sender = random.choice(list(senders.keys()))
            sender_queue = tracker["sending_accounts"][potential_sender]["email_queue"]
            sender_data = tracker["sending_accounts"][potential_sender]
            
            # Get current day
            current_day = get_schedule_day(current_time)
            
            # Try to find a slot
            potential_slot = find_optimal_slot(
                email, windows, sender_queue, tracker, potential_sender
            )
            
            if potential_slot:
                schedule_day = get_schedule_day(potential_slot)
                # Check if this day exists and create if not
                if schedule_day not in sender_data['daily_schedule_count']:
                    sender_data['daily_schedule_count'][schedule_day] = 0
                    
                # Verify day isn't full
                if sender_data['daily_schedule_count'][schedule_day] < 30:
                    slot = potential_slot
                    sender_email = potential_sender
                    break
            
            attempts += 1
            if attempts % len(senders) == 0:
                # After trying all senders, move to next day
                current_time += timedelta(days=1)
                logger.info(f"Tried all senders, moving to next day: {get_schedule_day(current_time)}")
        
        if slot:
            # Convert slot to recipient timezone for salutation
            recipient_time = slot.astimezone(
                pytz.timezone(email['time_zone'])
            ).isoformat()
            
            # Create a temporary email data structure for salutation processing
            temp_email_data = {
                'recipient_time': recipient_time,
                'email_data': {
                    'email_content': email['email_content'],
                    'language': email['language']  # Using the existing language field
                }
            }
            
            # Process salutations
            processed_email = process_email(temp_email_data)
            
            # Create email entry with processed content
            email_entry = {
                "campaign_id": campaign_id,
                "scheduled_time": slot.isoformat(),
                "recipient_time": recipient_time,
                "status": "pending",
                "attempt_count": 0,
                "last_attempt": None,
                "email_data": {
                    **email,  # Original email data
                    'email_content': processed_email['email_data']['email_content']  # Updated content
                }
            }
            print(f"mail_entry: {email}")
            # Add to queue and update tracking
            tracker["sending_accounts"][sender_email]["email_queue"].append(email_entry)
            tracker["sending_accounts"][sender_email]["last_scheduled_time"] = slot.isoformat()
            update_daily_schedule_count(tracker, sender_email, slot)
            
            emails_scheduled += 1
            
            # Log scheduling info
            schedule_day = get_schedule_day(slot)
            daily_count = tracker["sending_accounts"][sender_email]["daily_schedule_count"][schedule_day]
            logger.info(f"Scheduled email for {sender_email} on {schedule_day} (day count: {daily_count})")
        else:
            logger.warning(f"Failed to find slot for email after {attempts} attempts")
            # Here we could potentially add to a failed_to_schedule list or handle differently
    
    # Log final distribution
    logger.info("Final email distribution:")
    for sender_email in senders.keys():
        counts = tracker["sending_accounts"][sender_email]["daily_schedule_count"]
        logger.info(f"{sender_email}: {counts}")
    
    tracker["campaigns"][campaign_id]["emails_scheduled"] = emails_scheduled
    logger.info(f"Successfully scheduled {emails_scheduled} emails")




def initialize_email_senders():
    """Initialize email senders with enterprise configuration"""
    senders = {}
    worker_emails_count = int(os.getenv('WORKER_EMAILS_COUNT', 5))
    logger.info(f"Initializing {worker_emails_count} email senders...")
    
    for i in range(1, worker_emails_count + 1):
        email = os.getenv(f'MS365_EMAIL_{i}')
        if email:
            logger.info(f"Initializing sender for {email}")
            try:
                # Create sender with Graph API credentials
                sender = EmailSender(
                    email=email,
                    app_password=os.getenv(f'MS365_APP_PASSWORD_{i}'),
                    daily_limit=int(os.getenv(f'DAILY_LIMIT_{i}', 30)),
                    region=os.getenv(f'REGION_{i}', 'global'),
                    client_id=os.getenv(f'CLIENT_ID_{i}'),
                    client_secret=os.getenv(f'CLIENT_SECRET_{i}'),
                    tenant_id=os.getenv(f'TENANT_ID_{i}')
                )
                senders[email] = sender
            except Exception as e:
                logger.error(f"Failed to initialize {email}: {str(e)}")
                
    return senders




def log_outbound_email(email_data: dict, success: bool):
    """Log outbound email details to JSON file"""
    try:
        # Create logs directory if it doesn't exist
        os.makedirs('email_logs', exist_ok=True)
        
        # Generate log filename with current date
        log_file = f'email_logs/initial_sendinglog_{datetime.now().strftime("%Y%m%d")}.json'
        
        # Prepare log entry
        log_entry = {
            "timestamp": datetime.now(pytz.UTC).isoformat(),
            "success": success,
            "email_data": {
                "message_id": email_data.get("email_id"),
                "subject": email_data.get("subject"),
                "sender": email_data.get("sender"),
                "recipient": email_data.get("recipient"),
                "thread_id": email_data.get("thread_id"),
                "conversation_index": email_data.get("conversation_index"),
                "conversation_topic": email_data.get("conversation_topic"),
                "headers": {
                    "message_id": email_data.get("internet_message_id"),
                    "in_reply_to": email_data.get("in_reply_to"),
                    "references": email_data.get("reference_list"),
                    "thread_topic": email_data.get("conversation_topic"),
                    "conversation_index": email_data.get("conversation_index_header"),
                },
                "time_zone": email_data.get("time_zone"),
                "email_type": email_data.get("email_type"),
                "convo_id": email_data.get("convo_id")
            }
        }
        
        # Read existing logs or create new list
        try:
            with open(log_file, 'r') as f:
                logs = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            logs = []
            
        # Append new log
        logs.append(log_entry)
        
        # Write updated logs
        with open(log_file, 'w') as f:
            json.dump(logs, f, indent=2)
            
    except Exception as e:
        logger.error(f"Error logging outbound email: {str(e)}")





async def process_scheduled_emails(tracker: Dict, senders: Dict):
    """Process scheduled emails efficiently"""
    amsterdam_tz = pytz.timezone('Europe/Amsterdam')

    while True:
        current_time = datetime.now(amsterdam_tz)
        emails_remaining = False
        
        for sender_email, sender_data in tracker["sending_accounts"].items():
            queue_copy = sender_data["email_queue"].copy()
            
            for email in queue_copy:
                if email["status"] == "pending" and datetime.fromisoformat(email["scheduled_time"]) <= current_time:
                    try:
                        # Extract recipient (handling both single and list formats)
                        recipient_email = email["email_data"]["email_recipient"][0] if isinstance(
                            email["email_data"]["email_recipient"], list
                        ) else email["email_data"]["email_recipient"]
                        
                        # Minimal required headers
                        headers = {
                            'Thread-Topic': email["email_data"]["subjectline"],
                            'References': [],
                            'In-Reply-To': None
                        }
  
                        # Execute email sending
                        success, sent_headers = senders[sender_email].send_email(
                            recipient=recipient_email,
                            subject=email["email_data"]["subjectline"],
                            body=email["email_data"]["email_content"],
                            time_zone=email["email_data"].get('time_zone', 'Europe/Amsterdam'),
                            headers=headers
                        )
                        
                        if success:
                            outbound_data = {
                                'sender': sender_email,
                                'recipient': recipient_email,
                                'subject': email["email_data"]["subjectline"],
                                'body': email["email_data"]["email_content"],
                                'created_at': datetime.now(pytz.UTC),
                                'direction': 'outbound',
                                'time_zone': email["email_data"].get('time_zone', 'Europe/Amsterdam'),
                                'thread_topic': email["email_data"]["subjectline"],
                                'message_id': sent_headers.get('message_id'),
                                'conversation_id': sent_headers.get('conversation_id'),
                                'email_id': sent_headers.get('email_id'),
                                'parent_folder_id': sent_headers.get('parent_folder_id'),
                                'campaign_id': email['campaign_id']
                            }
                            
                            # Record keeping
                            post_email(outbound_data, 'outbound')
                            log_outbound_email(outbound_data, success)
                            
                            # Campaign management
                            campaign_id = email['campaign_id']
                            tracker["campaigns"][campaign_id]["emails_sent"] += 1
                            emails_remaining = True
                        else:
                            print("no email campaign id!!!!!")
                            tracker["campaigns"][email["campaign_id"]]["emails_failed"] += 1
                            
                        # Queue management
                        sender_data["email_queue"].remove(email)
                        
                        # Tracker persistence
                        with open('src/email_management/trackers/sending_tracker.json', 'w') as f:
                            json.dump(tracker, f, indent=2)
                            
                    except Exception as e:
                        logger.error(f"Email sending error: {str(e)}")
                        sender_data["email_queue"].remove(email)
                        tracker["campaigns"][email["campaign_id"]]["emails_failed"] += 1
        
        if not emails_remaining:
            break
            
        # Use asyncio.sleep instead of time.sleep
        await asyncio.sleep(1200)  # Rate limiting













# In sender.py
# Update the entrypoint function to use these
async def entrypoint(email_data, campaign_id):
    amsterdam_tz = pytz.timezone('Europe/Amsterdam')
    current_time = datetime.now(amsterdam_tz) 

    # Initialize senders
    senders = initialize_email_senders()
    if not senders:
        logger.error("No email senders were initialized.")
        return False
    logger.info(f"Initialized {len(senders)} email senders")

    try:
        # Load tracker and ensure proper initialization
        tracker = load_tracker()
        logger.info("Loaded email tracker")
        
        # Initialize campaign
        if 'campaigns' not in tracker:
            tracker['campaigns'] = {}
            
        tracker["campaigns"][campaign_id] = {
            "created_at": current_time.isoformat(),
            "total_emails": len(email_data),
            "emails_scheduled": 0,
            "emails_sent": 0,
            "emails_failed": 0,
            "status": "new"
        }
        
        # Ensure trackers directory exists
        os.makedirs('src/email_management/trackers', exist_ok=True)
        
        # Schedule emails with initialized tracker
        schedule_emails_optimized(email_data, senders, tracker, campaign_id)
        
        # Save updated tracker
        with open('src/email_management/trackers/sending_tracker.json', 'w') as f:
            json.dump(tracker, f, indent=2)

        logger.info(f"Campaign {campaign_id} initialized with {tracker['campaigns'][campaign_id]['emails_scheduled']} emails")
        
        # Start processing
        await process_scheduled_emails(tracker, senders)
        
        return True
        
    except Exception as e:
        logger.error(f"Error in entrypoint: {str(e)}")
        logger.error("Full error: ", exc_info=True)
        return False
    










