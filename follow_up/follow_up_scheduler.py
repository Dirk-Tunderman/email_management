import asyncio
import logging
from datetime import datetime
import time
from typing import Optional
from .follow_up_manager import FollowUpManager

logger = logging.getLogger(__name__)

class FollowUpScheduler:
    def __init__(self, check_interval: int = 432000):  # 900 seconds = 15 minutes
        self.manager = FollowUpManager()
        self.check_interval = check_interval
        self.is_running = False
        self._last_run: Optional[datetime] = None

    async def start(self):
        """Start the follow-up scheduler"""
        self.is_running = True
        logger.info("Follow-up scheduler started")
        
        while self.is_running:
            try:
                # Get emails needing follow-up
                emails = self.manager.get_emails_needing_followup()
                
                if emails:
                    logger.info(f"Found {len(emails)} emails needing follow-up")
                    
                    # Process each email
                    for email in emails:
                        await self.manager.send_follow_up(email)
                        # Add a small delay between sends to avoid overwhelming the email server
                        await asyncio.sleep(2)
                
                self._last_run = datetime.now()
                
                # Wait for the next check interval
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Error in follow-up scheduler: {str(e)}")
                # Wait a bit before retrying after an error
                await asyncio.sleep(60)

    def stop(self):
        """Stop the follow-up scheduler"""
        self.is_running = False
        logger.info("Follow-up scheduler stopped")

    @property
    def last_run(self) -> Optional[datetime]:
        return self._last_run 