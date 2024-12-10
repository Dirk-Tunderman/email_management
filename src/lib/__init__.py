# Import the classes and functions you want to expose
from .smtp_based_funcions import EmailSender


# You can define __all__ to specify which names are exported when using 'from lib import *'
__all__ = [
    'EmailSender'
]