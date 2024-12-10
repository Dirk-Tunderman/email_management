import os
from supabase import create_client, Client
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional
import json
from datetime import datetime
from typing import Optional, List, Dict
import traceback
import uuid 
import base64
from pydantic import BaseModel, Field
import pytz

# Models remain the same
class sentEmail(BaseModel):
    email_id: str = Field(..., description="The unique identifier of the email")
    subject: str = Field(..., description="The subject of the email")
    body: str = Field(..., description="The body of the email")
    sender: str = Field(..., description="The sender of the email")
    recipient: str = Field(..., description="The recipient of the email")
    time_zone: str = Field(..., description="The time zone of the email")


# In supabase_client.py
class ReceivedEmail(BaseModel):
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    sender: str
    recipient: str
    level_of_interest: Optional[str] = None
    email_id: str
    subject: str
    body: str
    # Threading fields
    thread_id: Optional[str] = None
    conversation_index: Optional[str] = None
    internet_message_id: Optional[str] = None
    in_reply_to: Optional[str] = None
    reference_list: Optional[List[str]] = None
    references_col: Optional[str] = None  # String version of references for easier querying
    conversation_topic: Optional[str] = None
    # Additional MS Exchange headers
    conversation_index_header: Optional[str] = None
    # Status and conversation tracking
    convo_id: Optional[str] = None
    sequence: Optional[int] = None
    is_reply: Optional[bool] = False
    replied: Optional[bool] = False
    reply_count: Optional[int] = 0
    first_response_time: Optional[datetime] = None
    # Add new header fields
    message_id: Optional[str] = None
    thread_topic: Optional[str] = None
    thread_index: Optional[str] = None
    references: Optional[str] = None
    return_path: Optional[str] = None
    authentication_results: Optional[str] = None
    dkim_signature: Optional[str] = None
    arc_authentication_results: Optional[str] = None
    ms_antispam: Optional[str] = None
    network_message_id: Optional[str] = None
    tenant_id: Optional[str] = None
    transport_latency: Optional[str] = None
    scl: Optional[str] = None
    traffic_type: Optional[str] = None
    directionality: Optional[str] = None

class OutboundEmail(BaseModel):
    email_id: str
    subject: str
    body: str
    sender: str
    recipient: str
    time_zone: str
    email_type: str  # 'initial' or 'reply'
    # Threading fields
    thread_id: Optional[str] = None
    conversation_index: Optional[str] = None
    internet_message_id: Optional[str] = None
    in_reply_to: Optional[str] = None
    reference_list: Optional[List[str]] = None
    references_col: Optional[str] = None
    conversation_topic: Optional[str] = None
    # Additional MS Exchange headers
    conversation_index_header: Optional[str] = None
    # Status and conversation tracking
    convo_id: Optional[str] = None
    sequence: Optional[int] = None
    direction: Optional[str] = 'outbound'
    has_reply: Optional[bool] = False
    last_reply_at: Optional[datetime] = None
    reply_count: Optional[int] = 0


class SupabaseClient:
    def __init__(self):
        self.url: str = os.environ.get("SUPABASE_URL")
        self.key: str = os.environ.get("SUPABASE_KEY")
        if not self.url or not self.key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")
        self.client: Client = create_client(self.url, self.key)

    def post(self, table_name: str, data: Dict[str, Any]) -> Dict:
        """Insert a row into a table"""
        print(f"Posting to table {table_name}, data: {json.dumps(data, indent=2)}")
        result = self.client.from_(table_name).insert(data).execute()
        print(f"Post result: {json.dumps(result.data, indent=2)}")
        return result.data

    def get_one(self, table_name: str, row: str, uid: str) -> Optional[Dict]:
        """Get one row from a table"""
        print(f"Getting from table {table_name}, where {row} = {uid}")
        result = self.client.from_(table_name).select("*").eq(row, uid).execute()
        print(f"Get one result: {json.dumps(result.data, indent=2)}")
        return result.data[0] if result.data else None

    def get_all(self, table_name: str) -> List[Dict]:
        """Get all rows from a table"""
        print(f"Getting all from table {table_name}")
        result = self.client.from_(table_name).select("*").execute()
        print(f"Get all result: {json.dumps(result.data, indent=2)}")
        return result.data

    def update(self, table_name: str, uid: str, data: Dict[str, Any]) -> Dict:
        """Update a row in a table"""
        result = self.client.from_(table_name).update(data).eq("id", uid).execute()
        return result.data

    def delete(self, table_name: str, uid: str) -> Dict:
        """Delete a row from a table"""
        result = self.client.from_(table_name).delete().eq("id", uid).execute()
        return result.data

# Initialize the global client
supabase_client = SupabaseClient()


def post_email(email_data: Dict[str, Any], email_type: str) -> Dict:
    """Post email to received_email table with proper type"""
    print(f"Posting email with type: {email_type}")
    try:
        # Check if email already exists in database
        email_id = email_data.get('email_id')
        if email_id:
            existing_email = supabase_client.client.from_('received_email')\
                .select('email_id')\
                .eq('email_id', email_id)\
                .execute()
            
            if existing_email.data:
                print(f"Email with ID {email_id} already exists in database. Skipping...")
                return {}

        table = 'received_email'
        
        # Convert datetime objects to ISO format strings
        if isinstance(email_data.get('created_at'), datetime):
            email_data['created_at'] = email_data['created_at'].isoformat()
        if isinstance(email_data.get('last_reply_at'), datetime):
            email_data['last_reply_at'] = email_data['last_reply_at'].isoformat()
        if isinstance(email_data.get('first_response_time'), datetime):
            email_data['first_response_time'] = email_data['first_response_time'].isoformat()

        print(f"email_data in supabase post_email: {email_data}")
        if email_type == 'outbound':
            # Initial outbound email
            cleaned_data = {
                'email_id': email_data.get('email_id'),
                'sender': email_data.get('sender'),
                'recipient': email_data.get('recipient'),
                'subject': email_data.get('subject'),
                'body': email_data.get('body', ''),
                'conversational_id': email_data.get('conversation_id'),
                'message_id': email_data.get('message_id'),
                'thread_topic': email_data.get('thread_topic'),
                'thread_index': email_data.get('thread_index'),
                'network_message_id': email_data.get('network_message_id'),
                'tenant_id': email_data.get('tenant_id'),
                'scl': email_data.get('scl'),
                'in_reply_to': email_data.get('in_reply_to'),
                'references': email_data.get('references'),
                'created_at': email_data.get('created_at'),
                'parent_folder_id': email_data.get('parent_folder_id'),
                'replied': False,
                'followup_send': False,
                # Set email_type based on parameter
                'email_type': 'initial',
                'campaign_id': email_data.get('campaign_id')
            

            }
        elif email_type == 'reply_outbound':
            # Our replies to received emails
            cleaned_data = {
                'email_id': email_data.get('email_id'),
                'sender': email_data.get('sender'),
                'recipient': email_data.get('recipient'),
                'subject': email_data.get('subject'),
                'body': email_data.get('body', ''),
                'conversational_id': email_data.get('conversation_id'),
                'message_id': email_data.get('message_id'),
                'thread_topic': email_data.get('threadTopic'),
                'thread_index': email_data.get('threadIndex'),
                'network_message_id': email_data.get('network_message_id'),
                'tenant_id': email_data.get('tenant_id'),
                'scl': email_data.get('scl'),
                'in_reply_to': email_data.get('inReplyTo'),
                'references': email_data.get('references'),
                'created_at': email_data.get('created_at'),
                'time_zone': email_data.get('time_zone'),
                'replied': False,
                'followup_send': True,

                
                # Set email_type based on parameter

                'email_type': 'reply_outbound',
                
                # Additional fields that might be present in received emails
                'return_path': email_data.get('return_path'),
                'authentication_results': email_data.get('authentication_results'),
                'dkim_signature': email_data.get('dkim_signature'),
                'arc_authentication_results': email_data.get('arc_authentication_results'),
                'ms_antispam': email_data.get('ms_antispam'),
                'transport_latency': email_data.get('transport_latency'),
                'traffic_type': email_data.get('traffic_type'),
                'level_of_interest': None,
                'parent_folder_id': email_data.get('parent_folder_id')
            }

        elif email_type == 'received':
            # Common mapping for both outbound and received emails
            cleaned_data = {
                'email_id': email_data.get('email_id'),
                'sender': email_data.get('sender'),
                'recipient': email_data.get('recipient'),
                'subject': email_data.get('subject'),
                'body': email_data.get('body', ''),
                'conversational_id': email_data.get('conversation_id'),
                'message_id': email_data.get('message_id'),
                'thread_topic': email_data.get('thread_topic'),
                'thread_index': email_data.get('thread_index'),
                'network_message_id': email_data.get('network_message_id'),
                'tenant_id': email_data.get('tenant_id'),
                'scl': email_data.get('scl'),
                'in_reply_to': email_data.get('in_reply_to'),
                'references': email_data.get('references'),
                'created_at': email_data.get('created_at'),
                'time_zone': email_data.get('time_zone'),
                'replied': False,
                'followup_send': True,
                
                # Set email_type based on parameter

                'email_type': 'reply_inbound',
                
                # Additional fields that might be present in received emails
                'return_path': email_data.get('return_path'),
                'authentication_results': email_data.get('authentication_results'),
                'dkim_signature': email_data.get('dkim_signature'),
                'arc_authentication_results': email_data.get('arc_authentication_results'),
                'ms_antispam': email_data.get('ms_antispam'),
                'transport_latency': email_data.get('transport_latency'),
                'traffic_type': email_data.get('traffic_type'),
                'level_of_interest': None,
                'parent_folder_id': email_data.get('parent_folder_id')
            }
        else:
            raise ValueError(f"Invalid email type: {email_type}")

        # Remove None values to prevent database errors
        cleaned_data = {k: v for k, v in cleaned_data.items() if v is not None}

        try:
            # Try to insert
            result = supabase_client.client.from_(table).insert(cleaned_data).execute()
            print(f"Successfully stored email in {table}")
            return result.data[0] if result.data else {}
        except Exception as e:
            if '23505' in str(e):  # Duplicate key error
                print(f"Email already exists, updating: {cleaned_data.get('email_id')}")
                # Try to update instead
                result = supabase_client.client.from_(table)\
                    .update(cleaned_data)\
                    .eq('email_id', cleaned_data['email_id'])\
                    .execute()
                return result.data[0] if result.data else {}
            raise

    except Exception as e:
        print(f"Error storing email in database: {str(e)}")
        traceback.print_exc()
        return {}




# Export the methods
def post(table_name: str, data: Dict[str, Any]) -> Dict:
    return supabase_client.post(table_name, data)

def get_one(table_name: str, row: str, uid: str) -> Optional[Dict]:
    return supabase_client.get_one(table_name, row, uid)

def get_all(table_name: str) -> List[Dict]:
    return supabase_client.get_all(table_name)

def update(table_name: str, uid: str, data: Dict[str, Any]) -> Dict:
    return supabase_client.update(table_name, uid, data)

def delete(table_name: str, uid: str) -> Dict:
    return supabase_client.delete(table_name, uid)

class EmailAttachment(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    contentType: Optional[str] = None
    size: Optional[int] = None
    contentBytes: Optional[str] = None

class EmailAddress(BaseModel):
    name: Optional[str] = None
    address: str

class EmailMessage(BaseModel):
    id: str
    createdDateTime: str
    lastModifiedDateTime: str
    receivedDateTime: str
    sentDateTime: str
    subject: str
    bodyPreview: str
    importance: str
    conversationId: str
    isRead: bool
    isDraft: bool
    body: Dict[str, str]
    sender: Dict[str, EmailAddress]
    from_: Dict[str, EmailAddress] = Field(alias="from")
    toRecipients: List[Dict[str, EmailAddress]]
    ccRecipients: List[Dict[str, EmailAddress]]
    bccRecipients: List[Dict[str, EmailAddress]]
    attachments: List[EmailAttachment] = []
    uniqueBody: Optional[Dict[str, str]] = None
    
    class Config:
        allow_population_by_field_name = True