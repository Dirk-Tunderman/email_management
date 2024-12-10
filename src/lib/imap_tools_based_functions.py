import msal
import requests
import time
from datetime import datetime, timezone
from rich.console import Console
from typing import List, Dict, Optional
from dataclasses import dataclass
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
import traceback
from src.email_management.src.lib.supabase_client import supabase_client
import os
import json
console = Console()

@dataclass
class EmailConfig:
    client_id: str
    client_secret: str
    tenant_id: str
    username: str

class ConnectionError(Exception):
    pass

class EmailManager: ###
    def __init__(self, client_id: str, client_secret: str, tenant_id: str, username: str):
        self.config = EmailConfig(
            client_id=client_id,
            client_secret=client_secret,
            tenant_id=tenant_id,
            username=username
        )
        self.access_token: Optional[str] = None
        self._email_cache: Dict[str, bool] = {}
        self.session = self._create_session()
        self.graph_url = "https://graph.microsoft.com"  # Base Graph API URL

    def _create_session(self) -> requests.Session:
        """Create a session with retry logic"""
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    def authenticate(self) -> bool:
        """Authenticate with Microsoft Graph API"""
        try:
            app = msal.ConfidentialClientApplication(
                self.config.client_id,
                authority=f"https://login.microsoftonline.com/{self.config.tenant_id}",
                client_credential=self.config.client_secret,
            )

            result = app.acquire_token_for_client(
                scopes=["https://graph.microsoft.com/.default"]
            )

            if "access_token" in result:
                self.access_token = result["access_token"]
                # Update session headers with the token
                self.session.headers.update({
                    'Authorization': f'Bearer {self.access_token}',
                    'Content-Type': 'application/json'
                })
                console.log("[green]Authentication successful[/green]")
                return True
            else:
                console.log("[red]Authentication failed[/red]")
                console.log(f"Error: {result.get('error')}")
                console.log(f"Error description: {result.get('error_description')}")
                return False

        except Exception as e:
            console.log(f"[red]Authentication error: {str(e)}[/red]")
            return False

    def test_connection(self) -> bool:
        """Test the connection to Microsoft Graph API"""
        return self.authenticate()

    def fetch_recent_emails(self, since_time: datetime, size: int = 10) -> List[Dict]:
        """Fetch emails received since the given time"""
        if not self.authenticate():
            raise ConnectionError("Failed to authenticate with Microsoft Graph API")
        
        endpoint = f"{self.graph_url}/v1.0/users/{self.config.username}/messages"
        
        params = {
            "$select": "*",
            "$expand": "attachments",  # Simplified for now
            "$top": size,
            "$orderby": "receivedDateTime desc",
            "$filter": f"receivedDateTime ge {since_time.isoformat()}"
        }
        
        try:
            response = self.session.get(endpoint, params=params)
            response.raise_for_status()
            return response.json().get('value', [])
            
        except Exception as e:
            console.log(f"[red]Error fetching emails: {str(e)}[/red]")
            return []

    def _extract_email_headers(self, message: Dict) -> Dict:
        """Extract relevant headers from the email message"""
        headers = {}
        
        if 'internetMessageHeaders' in message:
            header_map = {
                header['name'].lower(): header['value'] 
                for header in message['internetMessageHeaders']
            }
            
            # Thread-related headers
            headers.update({
                'thread_topic': header_map.get('thread-topic'),
                'thread_index': header_map.get('thread-index'),
                'references': header_map.get('references'),
                'in_reply_to': header_map.get('in-reply-to'),
                'message_id': header_map.get('message-id'),
            })
            
            # Security and authentication headers
            headers.update({
                'authentication_results': header_map.get('authentication-results'),
                'dkim_signature': header_map.get('dkim-signature'),
                'arc_authentication_results': header_map.get('arc-authentication-results'),
                'ms_antispam': header_map.get('x-microsoft-antispam'),
            })
            
            # Routing headers
            headers.update({
                'return_path': header_map.get('return-path'),
                'network_message_id': header_map.get('x-ms-exchange-organization-network-message-id'),
                'tenant_id': header_map.get('x-ms-exchange-crosstenant-id'),
                'transport_latency': header_map.get('x-ms-exchange-transport-endtoendlatency'),
            })
            
            # Classification headers
            headers.update({
                'scl': header_map.get('x-ms-exchange-organization-scl'),
                'traffic_type': header_map.get('x-ms-publictraffictype'),
                'directionality': header_map.get('x-ms-exchange-organization-messagedirectionality'),
            })
        
        return headers

    def _process_email(self, email: Dict) -> Dict:
        """Process a single email and extract relevant information"""
        return {
            'id': email.get('id'),
            'conversation_id': email.get('conversationId'),
            'created_datetime': email.get('createdDateTime'),
            'last_modified_datetime': email.get('lastModifiedDateTime'),
            'received_datetime': email.get('receivedDateTime'),
            'sent_datetime': email.get('sentDateTime'),
            'has_attachments': email.get('hasAttachments', False),
            'subject': email.get('subject'),
            'body_preview': email.get('bodyPreview'),
            'importance': email.get('importance'),
            'parent_folder_id': email.get('parentFolderId'),
            'sender': email.get('sender', {}).get('emailAddress', {}),
            'from': email.get('from', {}).get('emailAddress', {}),
            'to_recipients': [r.get('emailAddress', {}) for r in email.get('toRecipients', [])],
            'cc_recipients': [r.get('emailAddress', {}) for r in email.get('ccRecipients', [])],
            'bcc_recipients': [r.get('emailAddress', {}) for r in email.get('bccRecipients', [])],
            'is_read': email.get('isRead', False),
            'is_draft': email.get('isDraft', False),
            'web_link': email.get('webLink'),
            'body': email.get('body', {}),
            'headers': self._extract_email_headers(email),
        }

  