import json
import logging
from datetime import datetime
import pytz
from typing import Dict, Optional
import os
logger = logging.getLogger(__name__)

TRACKER_FILE = 'src/email_management/trackers/sending_tracker.json'

def load_tracker() -> Dict:
    """
    Load or create tracker file with proper error handling
    """
    tracker_path = 'src/email_management/trackers/sending_tracker.json'
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(tracker_path), exist_ok=True)
    
    try:
        # Try to load existing tracker
        with open(tracker_path, 'r') as f:
            tracker = json.load(f)
            logger.info("Loaded existing tracker file")
            return tracker
    except FileNotFoundError:
        logger.info("No tracker file found, creating new one")
        tracker = create_new_tracker()
    except json.JSONDecodeError:
        logger.warning("Tracker file corrupted, creating new one")
        tracker = create_new_tracker()
    except Exception as e:
        logger.error(f"Error loading tracker: {str(e)}")
        tracker = create_new_tracker()
    
    # Save new tracker
    try:
        with open(tracker_path, 'w') as f:
            json.dump(tracker, f, indent=2)
        logger.info("Created new tracker file")
    except Exception as e:
        logger.error(f"Error saving new tracker: {str(e)}")
    
    return tracker

def create_new_tracker() -> Dict:
    """Create new tracker with default structure"""
    return {
        "sending_accounts": {},
        "campaigns": {},
        "meta": {
            "last_updated": datetime.now(pytz.UTC).isoformat(),
            "version": "1.0"
        }
    }