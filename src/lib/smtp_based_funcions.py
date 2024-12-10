# In src/email_management/src/lib/smtp_based_funcions.py

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import email.utils
from datetime import datetime, timedelta
import pytz
import logging
import os
import json
import uuid
import base64
import time
import requests
from msal import ConfidentialClientApplication
import requests
from datetime import datetime, timedelta
import os
import logging
import time
import traceback


logger = logging.getLogger(__name__)



class GraphAPIClient:
    def __init__(self, client_id: str, client_secret: str, tenant_id: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.tenant_id = tenant_id
        self.app = ConfidentialClientApplication(
            client_id=self.client_id,
            client_credential=self.client_secret,
            authority=f"https://login.microsoftonline.com/{self.tenant_id}"
        )
    
    def get_access_token(self):
        """Get Microsoft Graph API access token"""
        try:
            result = self.app.acquire_token_for_client(
                scopes=["https://graph.microsoft.com/.default"]
            )
            if "access_token" in result:
                return result["access_token"]
            else:
                logger.error(f"Failed to get token: {result.get('error_description')}")
                return None
        except Exception as e:
            logger.error(f"Error getting access token: {str(e)}")
            return None

    def get_sent_email(self, user_email: str, subject: str, sent_time: datetime):
        """Fetch details of a recently sent email using Microsoft Graph API"""
        try:
            access_token = self.get_access_token()
            if not access_token:
                logger.error("Failed to get access token")
                return None

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            # Simplify the time filter - look at messages from last 5 minutes
            time_window = (sent_time - timedelta(minutes=5)).isoformat()
            
            # Query for sent messages
            url = f"https://graph.microsoft.com/v1.0/users/{user_email}/mailFolders/SentItems/messages"
            params = {
                "$filter": f"sentDateTime gt {time_window}",
                "$orderby": "sentDateTime desc",
                "$top": 10,
                "$select": "id,conversationId,internetMessageId,subject,conversationIndex,sender,toRecipients,internetMessageHeaders"
            }
            
            response = requests.get(url, headers=headers, params=params)
            logger.info(f"Graph API Response: {response.status_code}")
            
            if response.status_code == 200:
                emails = response.json().get('value', [])
                # Find the matching email by subject
                for email in emails:
                    if email.get('subject') == subject:
                        # Get full message details including headers
                        message_id = email.get('id')
                        detail_url = f"https://graph.microsoft.com/v1.0/users/{user_email}/messages/{message_id}"
                        detail_response = requests.get(detail_url, headers=headers)
                        
                        if detail_response.status_code == 200:
                            logger.info("Successfully retrieved email details from Graph API")
                            return detail_response.json()
                        else:
                            logger.error(f"Failed to get message details: {detail_response.status_code}")
                
                logger.error(f"No matching email found for subject: {subject}")
            else:
                logger.error(f"Failed to fetch emails: {response.status_code} {response.text}")
            
            return None

        except Exception as e:
            logger.error(f"Error fetching sent email details: {str(e)}")
            logger.error(f"Full error: {traceback.format_exc()}")
            return None



class EmailSender:
    def __init__(self, email, app_password, daily_limit=30, region="global", 
                 client_id=None, client_secret=None, tenant_id=None):
        self.email = email
        self.app_password = app_password
        self.daily_limit = daily_limit
        self.region = region
        self.last_sent_time = datetime.min.replace(tzinfo=pytz.UTC)
        self.emails_sent_today = 0
        self.domain = email.split('@')[1]
        
        # Initialize Graph API client if credentials are provided
        if client_id and client_secret and tenant_id:
            self.graph_client = GraphAPIClient(
                client_id=client_id,
                client_secret=client_secret,
                tenant_id=tenant_id
            )
        else:
            logger.warning(f"No Graph API credentials provided for {email}")
            self.graph_client = None

    def _build_enterprise_headers(self):
        """Build streamlined enterprise-grade headers"""
        return {
            'X-Mailer': 'Microsoft-MacOutlook/16.73.0.231104',
            'X-MS-Exchange-Organization-AuthAs': 'Internal',
            'X-MS-Exchange-Organization-AuthMechanism': '04',
            'X-MS-Exchange-Organization-AuthSource': self.domain,
            'X-MS-Exchange-Organization-SCL': '-1',
            'X-MS-Exchange-CrossTenant-id': f"{uuid.uuid4().hex}",
            'X-MS-Exchange-Transport-CrossTenantHeadersStamped': 'true',
            'X-Microsoft-Antispam': 'BCL:0;'
        }

    def send_email(self, recipient, subject, body, time_zone="`Europe/Amserdam", headers=None):
        try:
            msg = MIMEMultipart('alternative')
            
            # Base headers
            msg['From'] = f"{self.email.split('@')[0].title()} <{self.email}>"
            msg['To'] = recipient if isinstance(recipient, str) else recipient[0]
            msg['Subject'] = subject
            msg['Date'] = email.utils.formatdate(localtime=True)
            
            # Add custom headers if provided
            if headers:
                for key, value in headers.items():
                    if value:  # Only add if value exists
                        msg[key] = value
            
            # Add body
            cleaned_body = (body.replace('\\n', '\n')
                              .replace('\n\n\n', '\n\n')
                              .replace('\\t', '    ')
                              .replace('\\r', ''))
            
            msg.attach(MIMEText(cleaned_body, 'plain', 'utf-8'))
            
            sent_headers = {}
            
            # Send email and capture response
            with smtplib.SMTP('smtp.office365.com', 587) as server:
                server.starttls()
                server.login(self.email, self.app_password)
                
                # Send and get response
                to_addrs = recipient if isinstance(recipient, list) else [recipient]
                response = server.send_message(msg)
                
                # Get the full message with generated headers
                full_msg = msg.as_string()
                parsed_email = email.message_from_string(full_msg)
                
                # Capture all headers
                sent_headers = {
                    'Message-ID': parsed_email.get('Message-ID'),
                    'Thread-Topic': parsed_email.get('Thread-Topic') or subject,
                    'Thread-Index': parsed_email.get('Thread-Index'),
                    'In-Reply-To': parsed_email.get('In-Reply-To'),
                    'References': parsed_email.get('References'),
                    'X-MS-Exchange-Organization-Network-Message-Id': parsed_email.get('X-MS-Exchange-Organization-Network-Message-Id'),
                    'X-MS-Exchange-CrossTenant-id': parsed_email.get('X-MS-Exchange-CrossTenant-id'),
                    'X-MS-Exchange-Organization-SCL': parsed_email.get('X-MS-Exchange-Organization-SCL'),
                    'conversation_id': None,
                    'email_id': None
                }
                
                # Update with provided headers
                if headers:
                    sent_headers.update(headers)
                
                self.last_sent_time = datetime.now(pytz.UTC)
                self.emails_sent_today += 1
                
                # If Graph API client exists, try to get additional details
                if self.graph_client:
                    time.sleep(3)
                    email_details = self.graph_client.get_sent_email(
                        user_email=self.email,
                        subject=subject,
                        sent_time=self.last_sent_time
                    )
                    print(f"email_details complete: {email_details}")
                    if email_details:
                        # Update headers with Graph API data
                        graph_headers = {
                            'message_id': email_details.get('internetMessageId'),
                            'conversation_id': email_details.get('conversationId'),
                            'conversationIndex': email_details.get('conversationIndex'),
                            'parent_folder_id': email_details.get('parentFolderId'),
                            'email_id': email_details.get('id'),
                            'network_message_id': None,
                            'tenant_id': None,
                            'scl': None
                        }
                        
                        # Extract additional headers from internetMessageHeaders
                        headers_array = email_details.get('internetMessageHeaders', [])
                        for header in headers_array:
                            header_name = header.get('name', '').lower()
                            header_value = header.get('value')
                            
                            if header_name == 'x-ms-exchange-organization-network-message-id':
                                graph_headers['network_message_id'] = header_value
                            elif header_name == 'x-ms-exchange-organization-scl':
                                graph_headers['scl'] = header_value
                            elif header_name == 'x-ms-exchange-crosstenant-id':
                                graph_headers['tenant_id'] = header_value
                        
                        # Update sent_headers with Graph API data
                        sent_headers.update(graph_headers)
                        
                        # # Prepare outbound email data for database
                        # outbound_data = {
                        #     'email_id': graph_headers['email_id'],
                        #     'message_id': graph_headers['message_id'],
                        #     'conversation_id': graph_headers['conversation_id'],
                        #     'thread_index': graph_headers['conversationIndex'],
                        #     'thread_topic': sent_headers['Thread-Topic'],
                        #     'network_message_id': graph_headers['network_message_id'],
                        #     'tenant_id': graph_headers['tenant_id'],
                        #     'scl': graph_headers['scl'],
                        #     'sender': self.email,
                        #     'recipient': recipient,
                        #     'subject': subject,
                        #     'body': cleaned_body,
                        #     'time_zone': time_zone,
                        #     'direction': 'outbound',
                        #     'email_type': headers.get('email_type', 'initial') if headers else 'initial',
                        #     'created_at': self.last_sent_time.isoformat(),
                        #     'in_reply_to': sent_headers.get('In-Reply-To'),
                        #     'references': sent_headers.get('References'),
                        # }
                        
                        # Post to database using the new function

                
                return True, sent_headers

        except Exception as e:
            logger.error(f"Error sending email from {self.email}: {str(e)}")
            logger.error(f"Full error: {traceback.format_exc()}")
            return False, {}
            
    def reset_daily_count(self):
        self.emails_sent_today = 0
        self.last_sent_time = datetime.min.replace(tzinfo=pytz.UTC)