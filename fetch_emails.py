import os.path
import pickle
import base64
import email
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def get_gmail_service():
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token_file:
            creds = pickle.load(token_file)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.pickle', 'wb') as token_file:
            pickle.dump(creds, token_file)
    service = build('gmail', 'v1', credentials=creds)
    return service

def fetch_unread_emails(service, user_id='me'):
    # Fetch list of unread emails
    results = service.users().messages().list(userId=user_id, labelIds=['UNREAD']).execute()
    messages = results.get('messages', [])

    if not messages:
        print("No unread emails found.")
        return

    for msg in messages:
        msg_id = msg['id']
        message = service.users().messages().get(userId=user_id, id=msg_id, format='full').execute()

        # Extract headers
        headers = message['payload'].get('headers', [])
        subject = sender = None
        for header in headers:
            if header['name'] == 'Subject':
                subject = header['value']
            elif header['name'] == 'From':
                sender = header['value']

        # Extract snippet (short preview)
        snippet = message.get('snippet')

        # Extract body (handle plain text and HTML)
        parts = message['payload'].get('parts', [])
        body = None
        if parts:
            for part in parts:
                if part['mimeType'] == 'text/plain':
                    body_data = part['body'].get('data')
                    if body_data:
                        body = base64.urlsafe_b64decode(body_data).decode('utf-8')
                        break
                elif part['mimeType'] == 'text/html':
                    # Optional: parse HTML if needed, else use snippet
                    body_data = part['body'].get('data')
                    if body_data:
                        body = base64.urlsafe_b64decode(body_data).decode('utf-8')
                        break
        else:
            # If no parts, payload body might have data
            body_data = message['payload']['body'].get('data')
            if body_data:
                body = base64.urlsafe_b64decode(body_data).decode('utf-8')

        print(f"From: {sender}")
        print(f"Subject: {subject}")
        print(f"Snippet: {snippet}")
        print(f"Body: {body[:200] if body else 'No body found'}")  # Print first 200 chars
        print("="*50)

if __name__ == '__main__':
    service = get_gmail_service()
    fetch_unread_emails(service)
