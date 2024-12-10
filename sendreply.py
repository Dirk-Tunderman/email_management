from datetime import datetime
from zoneinfo import ZoneInfo
import pytz
import json
import os
import logging
import time
import uuid
import random
import base64
import traceback
from typing import Dict, List, Tuple, Optional
from rich.console import Console
from dotenv import load_dotenv

from src.email_management.src.lib.smtp_based_funcions import EmailSender
from src.email_management.src.lib.supabase_client import (
    post_email, update, supabase_client
)

# Initialize logging and console
console = Console()
logger = logging.getLogger(__name__)

def load_root_env() -> bool:
    """Load environment variables from root .env file"""
    try:
        env_path = os.path.join(os.getcwd(), '.env')
        console.log(f"Loading .env from: {env_path}")
        
        if not os.path.exists(env_path):
            raise FileNotFoundError(f"Could not find .env file at {env_path}")
            
        load_dotenv(dotenv_path=env_path, override=True)
        worker_count = int(os.getenv('WORKER_EMAILS_COUNT', 4))
        console.log(f"Found {worker_count} worker emails in configuration")
        return True
    except Exception as e:
        console.log(f"[red]Error loading environment: {str(e)}[/red]")
        return False






def update_original_email_status(original_email: Dict) -> None:
    """Update status of replied-to email"""
    try:
        update_data = {
            "replied": True,
            "reply_count": original_email.get('reply_count', 0) + 1,
            "first_response_time": original_email.get('first_response_time') 
                or datetime.now(ZoneInfo("UTC")).isoformat()
        }
        update("received_email", original_email['id'], update_data)
    except Exception as e:
        logger.error(f"Failed to update original email status: {e}")

def init_sender(email: str) -> Optional[EmailSender]:
    """Initialize email sender"""
    if not load_root_env():
        return None

    try:
        worker_count = int(os.getenv('EMAILS_COUNT', 0))
        for i in range(worker_count):
            current = i + 1
            if email == os.getenv(f'MS365_EMAIL_{current}'):
                return EmailSender(
                    email=email,
                    app_password=os.getenv(f'MS365_APP_PASSWORD_{current}'),
                    daily_limit=int(os.getenv(f'DAILY_LIMIT_{current}', 30)),
                    region=os.getenv(f'REGION_{current}', "global")
                )
    except Exception as e:
        logger.error(f"Failed to initialize sender {email}: {e}")
    return None

def send_reply(
    sender: str,
    recipient: str, 
    subject: str,
    body: str,
    original_email_id: str,
    time_zone: Optional[str] = None
) -> Tuple[bool, str]:
    """Send a reply email with proper threading"""
    try:
        print("\n=== Starting Reply Process ===")
        print(f"1. Initial parameters:")
        print(f"- Sender: {sender}")
        print(f"- Recipient: {recipient}")
        print(f"- Subject: {subject}")
        print(f"- Original Email ID: {original_email_id}")

        # Get the original email data
        original_email = supabase_client.client.from_("received_email") \
            .select("*") \
            .eq("email_id", original_email_id) \
            .execute()

        if not original_email.data:
            return False, "Original email not found"

        original_email_data = original_email.data[0]
        
        # Extract threading information
        email_data = {
            "sender": sender,
            "recipient": recipient,
            "subject": subject if subject.startswith("Re:") else f"Re: {subject}",
            "body": body,
            "conversational_id": original_email_data.get('conversational_id'),
            "parent_folder_id": original_email_data.get('parent_folder_id'),
            "in_reply_to": original_email_data.get('message_id'),
            "references": original_email_data.get('message_id'),
            "thread_topic": original_email_data.get('thread_topic') or subject.replace("Re: ", ""),
            "thread_index": original_email_data.get('thread_index')
        }

        email_type = "reply_outbound"

        # Initialize email sender
        email_sender = init_sender(sender)
        if not email_sender:
            return False, "Failed to initialize email sender"

        # Send the email with threading information as headers
        print(f"the following email is going to be send in the send_reply funciotn: {body[:100]}")
        success = email_sender.send_email(
            recipient=recipient,
            subject=email_data["subject"],
            body=body,
            time_zone=time_zone,
            headers={
                "conversationId": email_data["conversational_id"],
                "threadTopic": email_data["thread_topic"],
                "threadIndex": email_data["thread_index"],
                "inReplyTo": email_data["in_reply_to"],
                "references": email_data["references"],
                "parentFolderId": email_data["parent_folder_id"],
                "email_type": email_type
            }
        )

        if success:
            # Store the reply in the database with email_type as separate argument
            # post_email(email_data, "reply_outbound")
            # Update the original email's status
            update_original_email_status(original_email_data)
            return True, "Reply sent successfully"
        
        return False, "Failed to send reply"

    except Exception as e:
        print(f"\n❌ Error in send_reply: {str(e)}")
        traceback.print_exc()
        return False, str(e)

