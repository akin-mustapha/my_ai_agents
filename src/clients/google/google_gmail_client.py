# google_gmail_client.py

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv
import os
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import io

# Use absolute paths for directories and files
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class GmailClient:
    """
    A reusable client for interacting with the Google Gmail API.

    Handles OAuth 2.0 authentication and provides methods for searching emails,
    retrieving content, and downloading attachments.
    """
    _instance = None # Singleton pattern support

    # Class-level variables for consistency with Google API docs
    # These are the minimum scopes for reading emails and attachments.
    # If you need to modify labels or mark as read, you'd need:
    # 'https://www.googleapis.com/auth/gmail.modify'
    # For full access, use 'https://mail.google.com/' (but less secure/less granular)
    DEFAULT_SCOPES = [
        'https://www.googleapis.com/auth/gmail.readonly'
    ]

    def __new__(cls, *args, **kwargs):
        """Implements a simple Singleton pattern to ensure only one instance of GmailClient exists."""
        if cls._instance is None:
            cls._instance = super(GmailClient, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """
        Initializes the GmailClient and authenticates.
        This method should only be called once due to the Singleton pattern.

        It reads configuration from environment variables:
        - GOOGLE_CLIENT_SECRETS_FILE: Path to client_secrets.json
        - GOOGLE_GMAIL_TOKEN_FILE: Path to token file for Gmail API
        - GOOGLE_GMAIL_SCOPES: Space-separated list of scopes (default is read-only)

        If these variables are not set, it will use default values.
        Loads credentials from .env and client_secrets.json.
        """
        if hasattr(self, '_initialized') and self._initialized:
            return # Prevent re-initialization if already initialized by Singleton

        load_dotenv()

        self.client_secrets_file = os.getenv("GOOGLE_CLIENT_SECRETS_FILE", "client_secrets.json")
        self.token_file = os.getenv("GOOGLE_GMAIL_TOKEN_FILE", "gmail_token.json") # Different token file for Gmail
        
        # Allow scopes to be overridden by .env or use default
        scopes_str = os.getenv("GOOGLE_GMAIL_SCOPES", " ".join(self.DEFAULT_SCOPES))
        self.SCOPES = scopes_str.split(' ')

        self.service = self._authenticate()
        self._initialized = True

    # Private Helper Method for Authentication
    def _authenticate(self):
        """
        Authenticates with Gmail API using OAuth 2.0.
        Handles token storage and refresh automatically.
        """
        creds = None
        if os.path.exists(self.token_file):
            creds = Credentials.from_authorized_user_file(self.token_file, self.SCOPES)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                print("Refreshing Gmail access token...")
                creds.refresh(Request())
            else:
                print("Initiating Gmail OAuth 2.0 flow...")
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.client_secrets_file, self.SCOPES)
                creds = flow.run_local_server(port=0) # Use random available port
            
            with open(self.token_file, 'w') as token:
                token.write(creds.to_json())
            print(f"Gmail token saved to {self.token_file}")

        try:
            service = build('gmail', 'v1', credentials=creds)
            print("Gmail client authenticated successfully.")
            return service
        except HttpError as error:
            print(f'An error occurred during Gmail authentication: {error}')
            print("Please check your client_secrets.json and network connection.")
            return None

    def search_messages(self, query='is:unread', max_results=100):
        """
        Searches for Gmail messages based on a query.

        Args:
            query (str): The Gmail search query string (e.g., "from:noreply@remarkable.com has:attachment subject:'Notes'").
                         Default is 'is:unread'.
            max_results (int): Maximum number of messages to return.

        Returns:
            list: A list of message IDs found, or an empty list if none found or error.
        """
        if not self.service:
            print("Client not authenticated. Cannot search messages.")
            return []

        try:
            response = self.service.users().messages().list(userId='me', q=query, maxResults=max_results).execute()

            messages = response.get('messages', [])
            if messages:
                print(f"Found {len(messages)} messages matching query: '{query}'")
            else:
                print(f"No messages found matching query: '{query}'")
            return [msg['id'] for msg in messages]
        except HttpError as error:
            print(f'An error occurred while searching messages: {error}')
            return []

    def get_message(self, msg_id):
        """
        Retrieves the full content of a specific message.

        Args:
            msg_id (str): The ID of the message to retrieve.

        Returns:
            dict: The full message payload, or None if not found or error.
        """
        if not self.service:
            print("Client not authenticated. Cannot retrieve message.")
            return None

        try:
            # Use format='full' or 'raw' to ensure all parts, including attachments, are included.
            message = self.service.users().messages().get(userId='me', id=msg_id, format='full').execute()
            return message
        except HttpError as error:
            print(f'An error occurred while retrieving message {msg_id}: {error}')
            return None

    def download_attachments(self, message, download_dir="attachments"):
        """
        Downloads all attachments from a given message to a specified directory.

        Args:
            message (dict): The full message payload obtained from get_message().
            download_dir (str): The directory where attachments should be saved.

        Returns:
            list: A list of file paths to the downloaded attachments.
        """
        if not self.service:
            print("Client not authenticated. Cannot download attachments.")
            return []

        attachments_downloaded = []
        os.makedirs(download_dir, exist_ok=True) # Ensure directory exists

        # Helper to get parts recursively
        def get_all_parts(parts):
            all_parts = []
            if parts:
                for part in parts:
                    all_parts.append(part)
                    if 'parts' in part:
                        all_parts.extend(get_all_parts(part['parts']))
            return all_parts

        try:
            payload = message.get('payload')
            if not payload:
                print(f"No payload found for message {message['id']}.")
                return []
            
            parts = get_all_parts(payload.get('parts', []))

            for part in parts:
                if part.get('filename') and part.get('body') and part.get('body').get('attachmentId'):
                    filename = part['filename']
                    attachment_id = part['body']['attachmentId']
                    
                    print(f"Found attachment: {filename} (ID: {attachment_id})")

                    attachment = self.service.users().messages().attachments().get(
                        userId='me', messageId=message['id'], id=attachment_id).execute()
                    
                    # Attachment data is base64url encoded
                    data = attachment.get('data')
                    if data:
                        file_data = base64.urlsafe_b64decode(data)
                        file_path = os.path.join(download_dir, filename)
                        with open(file_path, 'wb') as f:
                            f.write(file_data)
                        attachments_downloaded.append(file_path)
                        print(f"Downloaded '{filename}' to '{file_path}'")
                    else:
                        print(f"No data found for attachment '{filename}'.")
                elif part.get('filename'): # Sometimes files are inline or smaller and have 'data' directly in body
                    filename = part['filename']
                    data = part.get('body', {}).get('data')
                    if data:
                        file_data = base64.urlsafe_b64decode(data)
                        file_path = os.path.join(download_dir, filename)
                        with open(file_path, 'wb') as f:
                            f.write(file_data)
                        attachments_downloaded.append(file_path)
                        print(f"Downloaded inline attachment '{filename}' to '{file_path}'")
        except HttpError as error:
            print(f'An error occurred while downloading attachments for message {message["id"]}: {error}')
        except Exception as e:
            print(f"An unexpected error occurred during attachment download: {e}")
        
        return attachments_downloaded

    def mark_message_as_read(self, msg_id):
        """
        Marks a specific message as read.
        Requires 'https://www.googleapis.com/auth/gmail.modify' scope.
        """
        if not self.service:
            print("Client not authenticated. Cannot modify message.")
            return False
        
        if 'https://www.googleapis.com/auth/gmail.modify' not in self.SCOPES and 'https://mail.google.com/' not in self.SCOPES:
            print("Error: 'gmail.modify' or 'mail.google.com' scope not enabled for marking as read.")
            print("Please update GOOGLE_GMAIL_SCOPES in your .env and re-authenticate.")
            return False

        try:
            self.service.users().messages().modify(
                userId='me',
                id=msg_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()
            print(f"Message {msg_id} marked as read.")
            return True
        except HttpError as error:
            print(f'An error occurred while marking message {msg_id} as read: {error}')
            return False

    # Example: Moving a message to a custom label (e.g., 'Processed')
    def move_message_to_label(self, msg_id, label_name):
        """
        Moves a message to a specific label. Creates the label if it doesn't exist.
        Requires 'https://www.googleapis.com/auth/gmail.modify' scope.
        """
        if not self.service:
            print("Client not authenticated. Cannot modify message.")
            return False

        if 'https://www.googleapis.com/auth/gmail.modify' not in self.SCOPES and 'https://mail.google.com/' not in self.SCOPES:
            print("Error: 'gmail.modify' or 'mail.google.com' scope not enabled for moving to label.")
            print("Please update GOOGLE_GMAIL_SCOPES in your .env and re-authenticate.")
            return False
            
        try:
            # Check if label exists, create if not
            label_id = None
            labels_response = self.service.users().labels().list(userId='me').execute()
            labels = labels_response.get('labels', [])
            for label in labels:
                if label['name'].lower() == label_name.lower():
                    label_id = label['id']
                    break
            
            if not label_id:
                # Create the label
                created_label = self.service.users().labels().create(userId='me', body={'name': label_name}).execute()
                label_id = created_label['id']
                print(f"Created new label: '{label_name}' (ID: {label_id})")

            # Modify message to add the label
            self.service.users().messages().modify(
                userId='me',
                id=msg_id,
                body={'addLabelIds': [label_id]}
            ).execute()
            print(f"Message {msg_id} moved to label '{label_name}'.")
            return True
        except HttpError as error:
            print(f'An error occurred while moving message {msg_id} to label {label_name}: {error}')
            return False


if __name__ == "__main__":
    # Example usage of the GmailClient to get messages and download attachments
    gmail_client = GmailClient()
    if gmail_client.service:
        print("Gmail client is ready to use.")
    else:
        print("Failed to initialize Gmail client. Check authentication setup.")

    # Example: Search for unread messages
    messages = gmail_client.search_messages(query='is:unread', max_results=5)
    if messages:
        for msg_id in messages:
            print(f"Found message ID: {msg_id}")
            # print(f"Found unread message: {msg['snippet']}")
            # # Example: Download attachments for each message
            msg = gmail_client.get_message(msg_id)
            gmail_client.download_attachments(msg, download_dir='downloads/')