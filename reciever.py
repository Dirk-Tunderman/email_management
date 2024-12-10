import os
import json
from datetime import datetime, timezone, timedelta, date
from dotenv import load_dotenv
from src.email_management.src.lib.imap_tools_based_functions import EmailManager
from src.email_management.src.lib.anthropic_agent import AnthropicAgent
from src.email_management.src.lib.prompts import system_prompt
from rich.console import Console
from pydantic import BaseModel, Field
from src.email_management.src.lib.gpt_agent import get_beta_generation
from src.email_management.src.lib.supabase_client import post, update, get_one, supabase_client, post_email
from src.email_management.sender import clean_subject
import traceback
import re
import uuid
import base64
from pathlib import Path
from typing import Dict
from bs4 import BeautifulSoup

console = Console()

COMPANY_DOMAINS = [
    'veloxforce.de',
    'veloxforce.nl',
    'veloxforceit.com',
    'veloxforceai.com',
    'toveloxforce.com'
]

class Reply(BaseModel):
    subject: str = Field(..., description="The subject of the reply email")
    body: str = Field(..., description="The body of the reply email")

class ProccessedEmailAnalysis(BaseModel): ##
    level_of_interest: str = Field(..., description="The level of interest of the user that sent the reply (e.g., 'high', 'medium', 'low', 'not_intrested','rude')")
    is_related: bool = Field(..., description="True if the reply is related to the email of the campaign, False if unrelated.")
    reply: Reply = Field(..., description="Based on the level of interest, generate an appropriate response. If the level of interest is low and the behavior is rude, generate a polite apology, else generate a tailored response.")


LAST_RUN_FILE = 'last_run.json'
PROCESSED_EMAILS_FILE = 'processed_emails.json'


def load_last_run_time(): ###
    if os.path.exists(LAST_RUN_FILE):
        with open(LAST_RUN_FILE, 'r') as f:
            data = json.load(f)
        return datetime.fromisoformat(data['last_run'])
    return datetime.now(timezone.utc) - timedelta(days=7)  # Default to 7 days ago if no last run


def save_last_run_time(): ###
    with open(LAST_RUN_FILE, 'w') as f:
        json.dump({'last_run': datetime.now(timezone.utc).isoformat()}, f)








def find_parent_email(email_data):
    """Find the original outbound email that this is a reply to"""
    print("\n=== Email Matching Debug ===")
    print(f"Incoming email from: {email_data['sender'].lower()}")
    print(f"Incoming email to: {email_data['recipient'].lower()}")
    print(f"Original subject: {email_data['subject']}")
    
    # Clean the subject
    cleaned_subject = clean_subject(email_data['subject'])
    print(f"Cleaned subject: {cleaned_subject}")
    
    # Try to find by subject first
    result = supabase_client.client.from_("outbound_email") \
        .select("*") \
        .or_(f"subject.eq.{cleaned_subject},conversation_topic.eq.{cleaned_subject}") \
        .execute()
    
    print(f"\nQuery returned {len(result.data)} potential matches")
    
    matching_emails = []
    for email in result.data:
        print(f"\nChecking potential match:")
        print(f"DB Email ID: {email['email_id']}")
        print(f"DB Sender: {email['sender']}")
        print(f"DB Recipient: {email['recipient']}")
        print(f"DB Subject: {email['subject']}")
        print(f"DB Conv Topic: {email.get('conversation_topic', '')}")
        
        # Compare email addresses case-insensitively
        sender_matches = email['recipient'].lower() == email_data['sender'].lower()
        recipient_matches = email['sender'].lower() == email_data['recipient'].lower()
        
        print(f"Sender match result: {sender_matches}")
        print(f"Recipient match result: {recipient_matches}")
        
        if sender_matches and recipient_matches:
            matching_emails.append(email)
            print(f"MATCH FOUND!")
            print(f"ID: {email['email_id']}")
            print(f"Subject: {email['subject']}")
            print(f"Created at: {email['created_at']}")
            print(f"Convo ID: {email['convo_id']}")
    
    if matching_emails:
        # Return the most recent matching email
        print("\nFound multiple matches, using most recent")
        return sorted(matching_emails, key=lambda x: x['created_at'])[-1]
    
    print("\nNo matching email found")
    return None


def extract_first_message(html_content):
    # Parse HTML
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Find the first div with class 'elementToProof'
    first_message = soup.find('div', class_='elementToProof')
    
    # Return the text if found, otherwise return None
    return first_message.text.strip() if first_message else None

# Usage example:
html_content = """your HTML content here"""
main_message = extract_first_message(html_content)


def process_raw_email(raw_email: Dict) -> Dict:
    """Extract relevant fields from raw email data and store in database"""
    # Extract headers from internetMessageHeaders if available
    headers = {}
    #dump raw email in json file in current directory
    current_directory = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(current_directory, 'raw_email.json'), 'w') as f:
        json.dump(raw_email, f)
        
    if 'internetMessageHeaders' in raw_email:
        headers = {
            header['name'].lower(): header['value'] 
            for header in raw_email['internetMessageHeaders']
        }
    
    print("\n=== Processing Raw Email ===")
    print(f"Raw email ID: {raw_email}")
    
    # Extract sender and recipient with better error handling
    sender = None
    if 'sender' in raw_email:
        sender_data = raw_email['sender'].get('emailAddress', {})
        sender = sender_data.get('address')
    
    recipient = None
    if 'toRecipients' in raw_email and raw_email['toRecipients']:
        recipient_data = raw_email['toRecipients'][0].get('emailAddress', {})
        recipient = recipient_data.get('address')
    
    # Extract body with HTML content support
    body = ''
    if 'body' in raw_email:
        body = raw_email['body'].get('content', '')
    elif 'bodyPreview' in raw_email:
        body = raw_email['bodyPreview']

    processed_email = {
        # Core email fields
        'email_id': raw_email.get('id'),
        'sender': sender,
        'recipient': recipient,
        'subject': raw_email.get('subject'),
        'body': body,
        'created_at': raw_email.get('createdDateTime'),
        'email_type': 'reply',
        'direction': 'inbound',
        
        # Message IDs and threading
        'message_id': raw_email.get('internetMessageId') or headers.get('message-id'),
        'thread_topic': headers.get('thread-topic'),
        'threadTopic': headers.get('threadtopic'),
        'thread_index': headers.get('thread-index'),
        'threadIndex': headers.get('threadindex'),
        'reference_list': headers.get('references'),
        'in_reply_to': headers.get('in-reply-to'),
        'inReplyTo': headers.get('inreplyto'),
        
        # Routing and authentication
        'return_path': headers.get('return-path'),
        'authentication_results': headers.get('authentication-results'),
        'dkim_signature': headers.get('dkim-signature'),
        'arc_authentication_results': headers.get('arc-authentication-results'),
        
        # MS Exchange specific
        'ms_antispam': headers.get('x-microsoft-antispam'),
        'network_message_id': headers.get('x-ms-exchange-organization-network-message-id'),
        'tenant_id': headers.get('x-ms-exchange-crosstenant-id'),
        'transport_latency': headers.get('x-ms-exchange-transport-endtoendlatency'),
        'scl': headers.get('x-ms-exchange-organization-scl'),
        'traffic_type': headers.get('x-ms-publictraffictype'),
        'directionality': headers.get('x-ms-exchange-organization-messagedirectionality'),
        
        # Additional metadata
        'conversation_id': raw_email.get('conversationId'),
        'received_datetime': raw_email.get('receivedDateTime'),
        'sent_datetime': raw_email.get('sentDateTime'),
        'has_attachments': raw_email.get('hasAttachments'),
        'importance': raw_email.get('importance'),
        'parent_folder_id': raw_email.get('parentFolderId'),
        'is_read': raw_email.get('isRead'),
        'is_draft': raw_email.get('isDraft'),
        'web_link': raw_email.get('webLink'),
        'last_modified_datetime': raw_email.get('lastModifiedDateTime')
    }

    # Debug logging
    print("\n=== Extracted Email Data ===")
    print(f"Email ID: {processed_email['email_id']}")
    print(f"Sender: {processed_email['sender']}")
    print(f"Recipient: {processed_email['recipient']}")
    print(f"Subject: {processed_email['subject']}")
    print(f"Created at: {processed_email['created_at']}")
    
    print(f"Message ID: {processed_email['message_id']}")
    print(f"Conversation ID: {processed_email['conversation_id']}")


    if processed_email['conversation_id']:
        # Query for matching conversation_id but different email_id
        result = supabase_client.client.from_("received_email") \
            .select("*") \
            .eq("conversational_id", processed_email['conversation_id']) \
            .neq("email_id", processed_email['email_id'])  \
            .execute()
        
        print(f"Found {len(result.data)} matching conversations")
        
        # Update status for all emails in same conversation but different email_id
        if result.data:
            for row in result.data:
                if not row.get('replied'):
                    update_result = supabase_client.client.from_("received_email") \
                        .update({"replied": True}) \
                        .eq("email_id", row['email_id']) \
                        .execute()
                    print(f"Updated replied status for email_id: {row['email_id']}")

    # Extract direction from headers
    # Extract direction from headers
    email_direction = headers.get('x-ms-exchange-organization-messagedirectionality', '').lower()
    print(f"Email direction: {email_direction}")
    # Determine if email is incoming or outgoing
    if email_direction == 'incoming':
        body = extract_first_message(processed_email['body'])
        print(f"body: {body}")

        processed_email['body'] = body
    
        post_email(processed_email, email_type='received')
    else:
        # If not explicitly incoming, treat as outgoing
        print('go into processing outcound reply')
        post_email(processed_email, email_type='reply_outbound')

    
    # Remove None values for cleaner output
    processed_email = {k: v for k, v in processed_email.items() if v is not None}
    
    return processed_email


def main(size: int = 10):
    try:
        print('\n=== Starting New Email Processing Session ===')
        
        WORKER_EMAILS_COUNT = int(os.getenv('WORKER_EMAILS_COUNT', 0))
        print(f'Found {WORKER_EMAILS_COUNT} worker email accounts')
        
        last_run_time = load_last_run_time()
        print(f"Checking for emails since: {last_run_time}")
        processed_emails = []

        for i in range(WORKER_EMAILS_COUNT):
            current_account = i + 1
            worker_email = os.getenv(f'MS365_EMAIL_{current_account}')
            print(f"\n=== Checking Account {current_account}: {worker_email} ===")
            
            email_manager = EmailManager(
                client_id=os.getenv(f'CLIENT_ID_{current_account}'),
                client_secret=os.getenv(f'CLIENT_SECRET_{current_account}'),
                tenant_id=os.getenv(f'TENANT_ID_{current_account}'),
                username=worker_email
            )
            
            # Fetch raw emails with size limit
            raw_emails = email_manager.fetch_recent_emails(last_run_time, size)
            print(f"raw_emailszzzz: {len(raw_emails)}")
            # Process each email
            for raw_email in raw_emails:
                processed_email = process_raw_email(raw_email)
                print(f"processed email: {processed_email}")
                processed_emails.append(processed_email)
            
                
            print(f"Processed {len(raw_emails)} emails from {worker_email}")

        save_last_run_time()
        return processed_emails[:size]  # Limit total results to requested size

    except Exception as e:
        print(f"FATAL ERROR: {str(e)}")
        traceback.print_exc()
        return []




if __name__ == "__main__":
    mail = main(True)
