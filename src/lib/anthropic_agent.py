import anthropic, os, sys, dotenv
import json
from anthropic import Anthropic
import os, dotenv
from imap_tools import MailMessage
import re
dotenv.load_dotenv(dotenv.find_dotenv())

class AnthropicAgent:
    def __init__(self, api_key):
        self.client = Anthropic(api_key=api_key)
    def generate(self, prompt, model="claude-3-haiku-20240307", temp=0.5, max_tokens=1000, content=None):
        """
        the generate method takes a prompt and returns the response from the Anthropic API
        :param prompt: the prompt to be sent to the Anthropic API
        :return: the response from the Anthropic API
        """
        res = self.client.messages.create(
            model=model,
            system=prompt,
            messages=[
                    {"role": "user", "content": content}
            ],
            temperature=float(temp),
            max_tokens=int(max_tokens),
            stream=False,
        )
        return res

# to be continued once the core functionality is implemented