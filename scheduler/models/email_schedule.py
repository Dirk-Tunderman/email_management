# filename: email_schedule.py

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

@dataclass
class EmailData:
    """Represents a single email to be sent"""
    campaign_id: str
    scheduled_time: datetime
    receiver_timezone: str
    receiver_local_time: datetime
    status: str  # pending, sent, failed
    attempt_count: int
    email_content: dict  # Original email data
    sender_email: Optional[str] = None  # Assigned sender
    rescheduled_count: int = 0
    last_attempt: Optional[datetime] = None

@dataclass
class SenderSchedule:
    """Represents a sender's schedule and limits"""
    email: str
    daily_limit: int
    emails_sent_today: int
    last_reset_date: datetime
    last_scheduled_time: datetime
    region: str
    email_queue: List[EmailData]

@dataclass
class CampaignTracker:
    """Tracks campaign progress"""
    campaign_id: str
    created_at: datetime
    total_emails: int
    emails_scheduled: int
    emails_sent: int
    emails_failed: int
    status: str  # new, in_progress, completed, failed

@dataclass
class EmailTracker:
    """Main tracking structure"""
    sending_rules: dict
    senders: dict[str, SenderSchedule]
    campaigns: dict[str, CampaignTracker]
    meta: dict