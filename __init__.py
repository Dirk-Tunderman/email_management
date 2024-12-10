# src/email_management/__init__.py
from .src.lib import EmailSender
from .sendreply import send_reply

__all__ = ['EmailSender', 'send_reply']

