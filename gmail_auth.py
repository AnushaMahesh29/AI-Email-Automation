import os.path
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Gmail API scope for reading emails and sending
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

def get_gmail_service():
    creds = None
    # Token file stores user access and refresh tokens
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token_file:
            creds = pickle.load(token_file)
    # If no valid creds, run OAuth flow to get new credentials
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
        creds = flow.run_local_server(port=0)
        with open('token.pickle', 'wb') as token_file:
            pickle.dump(creds, token_file)
    # Build Gmail API client
    service = build('gmail', 'v1', credentials=creds)
    return service

def test_gmail_connection(service):
    try:
        results = service.users().labels().list(userId='me').execute()
        labels = results.get('labels', [])
        print("Gmail API connected! Labels found:")
        for label in labels:
            print(f" - {label['name']}")
    except Exception as e:
        print("Error connecting to Gmail API:", e)

if __name__ == '__main__':
    service = get_gmail_service()
    test_gmail_connection(service)
