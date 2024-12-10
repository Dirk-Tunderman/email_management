# filename: schedule_manager.py

from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import pytz

import pytz
from typing import Dict, List, Optional

import logging
from .models.email_schedule import EmailData, SenderSchedule, CampaignTracker, EmailTracker
from .utils.time_utils import is_valid_send_time, calculate_next_valid_time
from .email_distributor import EmailDistributor

logger = logging.getLogger(__name__)

class ScheduleManager:
    def __init__(self, tracker_file_path: str = 'src/email_management/trackers/sending_tracker.json'):
        self.tracker_file_path = tracker_file_path
        self.tracker = self._load_or_create_tracker()
        
    def _load_or_create_tracker(self) -> Dict:
        """Load existing tracker or create new one"""
        if os.path.exists(self.tracker_file_path):
            try:
                with open(self.tracker_file_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading tracker: {str(e)}")
                return self._create_new_tracker()
        return self._create_new_tracker()
        
    def _create_new_tracker(self) -> Dict:
        """Create new tracker with default structure"""
        return {
            "sending_accounts": {},
            "campaigns": {},
            "meta": {
                "last_updated": datetime.now(pytz.UTC).isoformat(),
                "version": "1.0"
            }
        }
        
    def _save_tracker(self):
        """Save current tracker state to file"""
        try:
            with open(self.tracker_file_path, 'w') as f:
                json.dump(self.tracker, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving tracker: {str(e)}")
            
    def get_next_available_time(self, sender_email: str) -> datetime:
        """Find next available sending time for a sender"""
        account = self.tracker["sending_accounts"].get(sender_email, {})
        last_time = datetime.fromisoformat(
            account.get("last_scheduled_time", 
            datetime.now(pytz.UTC).isoformat())
        )
        return last_time + timedelta(minutes=20)
        
    def update_sender_schedule(self, sender_email: str, scheduled_time: datetime,
                             email_data: Dict, campaign_id: str):
        """Add new email to sender's queue"""
        if sender_email not in self.tracker["sending_accounts"]:
            self.tracker["sending_accounts"][sender_email] = {
                "daily_limit": 30,  # Default value
                "time_between_emails": 20,
                "emails_sent_today": 0,
                "last_reset_date": datetime.now(pytz.UTC).strftime("%Y-%m-%d"),
                "last_scheduled_time": scheduled_time.isoformat(),
                "email_queue": []
            }
            
        self.tracker["sending_accounts"][sender_email]["email_queue"].append({
            "campaign_id": campaign_id,
            "scheduled_time": scheduled_time.isoformat(),
            "status": "pending",
            "attempt_count": 0,
            "last_attempt": None,
            "email_data": email_data
        })
        
        self._save_tracker()