# filename: email_distributor.py

from datetime import datetime, timedelta
from typing import List, Dict
import pytz
from .models.email_schedule import EmailData, SenderSchedule
from .utils.time_utils import calculate_next_valid_time

class EmailDistributor:
    def distribute_emails(
        self,
        emails: List[Dict],
        senders: Dict[str, SenderSchedule],
        start_time: datetime
    ) -> Dict[str, List[EmailData]]:
        """
        Distribute emails among available senders considering their regions and limits
        """
        # Convert sender dict to list for round-robin distribution
        available_senders = list(senders.values())
        if not available_senders:
            raise ValueError("No senders available")

        # Initialize result dictionary
        distribution = {sender.email: [] for sender in available_senders}
        
        # Calculate emails per sender (try to distribute evenly)
        base_count = len(emails) // len(available_senders)
        remainder = len(emails) % len(available_senders)
        
        # Assign base counts
        sender_counts = {sender.email: base_count for sender in available_senders}
        
        # Distribute remainder
        for i in range(remainder):
            sender_counts[available_senders[i].email] += 1
            
        # Current scheduling time starts from the provided start_time
        current_time = start_time
        
        # Track emails assigned to each sender
        assigned_counts = {sender.email: 0 for sender in available_senders}
        
        # Distribute emails
        for email_data in emails:
            # Find best sender for this email
            sender = self._find_best_sender(
                email_data,
                available_senders,
                sender_counts,
                assigned_counts
            )
            
            if not sender:
                continue
                
            # Calculate next valid send time
            current_time = calculate_next_valid_time(
                current_time + timedelta(minutes=20),
                email_data.get('timezone', 'Europe/Amsterdam')
            )
            
            # Create EmailData object
            email_obj = EmailData(
                campaign_id=email_data.get('campaign_id', 'default'),
                scheduled_time=current_time,
                receiver_timezone=email_data.get('timezone', 'Europe/Amsterdam'),
                receiver_local_time=current_time.astimezone(
                    pytz.timezone(email_data.get('timezone', 'Europe/Amsterdam'))
                ),
                status='pending',
                attempt_count=0,
                email_content=email_data,
                sender_email=sender.email
            )
            
            # Add to distribution
            distribution[sender.email].append(email_obj)
            assigned_counts[sender.email] += 1
            
        return distribution
    
    def _find_best_sender(
        self,
        email_data: Dict,
        available_senders: List[SenderSchedule],
        target_counts: Dict[str, int],
        current_counts: Dict[str, int]
    ) -> SenderSchedule:
        """Find the best sender for a given email based on various criteria"""
        recipient_email = email_data.get('email_recipient', [''])[0]
        
        # Try to match by region first
        if '.de' in recipient_email:
            german_senders = [s for s in available_senders if s.region == 'germany']
            if german_senders:
                return self._select_least_loaded_sender(
                    german_senders, target_counts, current_counts
                )
        
        elif '.nl' in recipient_email:
            dutch_senders = [s for s in available_senders if s.region == 'netherland']
            if dutch_senders:
                return self._select_least_loaded_sender(
                    dutch_senders, target_counts, current_counts
                )
        
        # If no region match or no capacity, select least loaded sender
        return self._select_least_loaded_sender(
            available_senders, target_counts, current_counts
        )
    
    def _select_least_loaded_sender(
        self,
        senders: List[SenderSchedule],
        target_counts: Dict[str, int],
        current_counts: Dict[str, int]
    ) -> SenderSchedule:
        """Select sender with most remaining capacity"""
        valid_senders = [
            s for s in senders
            if current_counts[s.email] < target_counts[s.email]
        ]
        
        if not valid_senders:
            return None
            
        return min(
            valid_senders,
            key=lambda s: current_counts[s.email] / target_counts[s.email]
        )