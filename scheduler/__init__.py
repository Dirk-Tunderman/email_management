# Location: src/email_management/scheduler/__init__.py

from .schedule_manager import ScheduleManager
from .email_distributor import EmailDistributor
from .models.email_schedule import EmailData, SenderSchedule, CampaignTracker, EmailTracker

__all__ = [
    'ScheduleManager',
    'EmailDistributor',
    'EmailData',
    'SenderSchedule',
    'CampaignTracker',
    'EmailTracker'
]

__version__ = '1.0.0'