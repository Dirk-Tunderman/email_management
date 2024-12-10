from datetime import datetime, timedelta
import pytz
import logging
from typing import List, Dict
from src.email_management.src.lib.supabase_client import supabase_client
from src.email_management.sendreply import send_reply
import re
logger = logging.getLogger(__name__)

class FollowUpManager:
    def __init__(self):
        self.supabase = supabase_client
        self.follow_up_template = """
Have you seen my email? i was wondering what you thought of it?
"""

    def get_emails_needing_followup(self) -> List[Dict]:
        """
        Fetch emails that:
        1. Were sent 5 days ago
        2. Haven't received a reply
        3. Haven't had a follow-up sent yet
        4. Are initial emails (not replies)
        """
        five_days_ago = datetime.now(pytz.UTC) - timedelta(days=5)
        print(f"five_days_ago: {five_days_ago}")
        try:
            response = self.supabase.client.from_("received_email") \
                .select("*") \
                .lt("created_at", five_days_ago.isoformat()) \
                .eq("replied", False) \
                .eq("followup_send", False) \
                .eq("email_type", "initial") \
                .execute()
            print(f"response: {response}")
            return response.data
        except Exception as e:
            logger.error(f"Error fetching emails for follow-up: {str(e)}")
            return []

    async def send_follow_up(self, original_email: Dict) -> bool:
        """Send a follow-up email for the given original email"""
        try:
            print(f"original_email: {original_email}\n\n")
            # Prepare follow-up content
            follow_up_subject = f"Re: {original_email['subject']}"
            follow_up_body = self._generate_follow_up_content(original_email)
            print(f"follow_up_body: {follow_up_body[:50]}")
            # Send the follow-up email
            success, error = send_reply(
                sender=original_email['sender'],
                recipient=original_email['recipient'],
                subject=follow_up_subject,
                body=follow_up_body,
                original_email_id=original_email['email_id'],
                time_zone=original_email.get('time_zone', 'Europe/Amsterdam')
            )

            if success:
                # Update the original email record
                self.supabase.client.from_("received_email") \
                    .update({"followup_send": True}) \
                    .eq("id", original_email['id']) \
                    .execute()
                
                logger.info(f"Follow-up sent successfully for email {original_email['id']}")
                return True
            else:
                logger.error(f"Failed to send follow-up for email {original_email['id']}: {error}")
                return False

        except Exception as e:
            logger.error(f"Error in send_follow_up: {str(e)}")
            return False

    def _generate_follow_up_content(self, original_email: Dict) -> str:
        """Generate follow-up email content based on the original email"""
        # Extract recipient name from email or use a default
        recipient_name = original_email.get('recipient_name', 'there')
        
        # Clean up the subject by removing any 'Re:', 'Fwd:', etc.
        clean_subject = re.sub(r'^(Re:\s*|Fwd:\s*)*', '', original_email['subject'])
        
        return self.follow_up_template.format(
            recipient_name=recipient_name,
            subject=clean_subject,
            sender_name=original_email.get('sender_name', ''),
            original_body=original_email.get('body', '')
        )
 