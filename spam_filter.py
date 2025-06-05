import os.path
import pickle
import base64
import re
import time
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from dotenv import load_dotenv
import os
import cohere

load_dotenv()
api_key = os.getenv("COHERE_API_KEY")
co = cohere.Client(api_key)

SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
PROCESSED_IDS_FILE = 'processed_emails.txt'

# Rule-based spam keywords/patterns
SPAM_KEYWORDS = [
    r"win prize",
    r"free money",
    r"urgent response",
    r"claim your reward",
    r"click here",
    r"limited time offer",
    r"congratulations",
]

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

def is_spam_rule_based(text):
    text_lower = text.lower()
    for pattern in SPAM_KEYWORDS:
        if re.search(pattern, text_lower):
            return True
    return False

def is_spam_llm(text):
    prompt = f"""Decide if the following message is spam. Answer only "Spam" or "Not Spam".

Message: \"\"\"{text}\"\"\"
"""
    try:
        response = co.generate(
            model='command',
            prompt=prompt,
            max_tokens=5,
            temperature=0,
            stop_sequences=["\n"]
        )
        answer = response.generations[0].text.strip().lower().rstrip('.')
        print(f"Cohere model answer: '{answer}'")

        if answer == "spam":
            return True
        elif answer == "not spam":
            return False
        else:
            print(f"Unclear model answer: '{answer}', defaulting to Not Spam.")
            return False

    except Exception as e:
        print(f"Cohere API error: {e}")
        raise e  # Let caller handle fallback

def is_spam_hybrid(text):
    rule_result = is_spam_rule_based(text)
    print(f"Rule-based prediction: {'spam' if rule_result else 'not spam'}")

    try:
        cohere_result = is_spam_llm(text)
    except Exception:
        print("Cohere API call failed, falling back to rule-based decision.")
        return rule_result

    print(f"Cohere prediction: {'spam' if cohere_result else 'not spam'}")

    if rule_result == cohere_result:
        print("Both agree. Final decision:", "Spam" if cohere_result else "Not Spam")
        return cohere_result
    else:
        print("Disagreement detected. Final decision by Cohere:", "Spam" if cohere_result else "Not Spam")
        return cohere_result

def move_to_spam(service, msg_id, user_id='me'):
    try:
        service.users().messages().modify(
            userId=user_id,
            id=msg_id,
            body={
                'addLabelIds': ['SPAM'],
                'removeLabelIds': ['INBOX', 'UNREAD']
            }
        ).execute()
        print(f"Moved email {msg_id} to SPAM.")
    except Exception as e:
        print(f"Failed to move email {msg_id} to spam: {e}")

def load_processed_ids():
    if not os.path.exists(PROCESSED_IDS_FILE):
        return set()
    with open(PROCESSED_IDS_FILE, 'r') as f:
        return set(line.strip() for line in f.readlines())

def save_processed_id(msg_id):
    with open(PROCESSED_IDS_FILE, 'a') as f:
        f.write(msg_id + '\n')

def fetch_and_filter_emails(service, user_id='me'):
    processed_ids = load_processed_ids()
    results = service.users().messages().list(userId=user_id, labelIds=['UNREAD']).execute()
    messages = results.get('messages', [])

    if not messages:
        print("No unread emails found.")
        return

    for msg in messages:
        msg_id = msg['id']
        if msg_id in processed_ids:
            print(f"Email {msg_id} already processed. Skipping.")
            continue

        message = service.users().messages().get(userId=user_id, id=msg_id, format='full').execute()

        headers = message['payload'].get('headers', [])
        subject = sender = None
        for header in headers:
            if header['name'] == 'Subject':
                subject = header['value']
            elif header['name'] == 'From':
                sender = header['value']

        parts = message['payload'].get('parts', [])
        body = ""
        if parts:
            for part in parts:
                if part['mimeType'] == 'text/plain':
                    body_data = part['body'].get('data')
                    if body_data:
                        body = base64.urlsafe_b64decode(body_data).decode('utf-8')
                        break
                elif part['mimeType'] == 'text/html':
                    body_data = part['body'].get('data')
                    if body_data:
                        body = base64.urlsafe_b64decode(body_data).decode('utf-8')
                        break
        else:
            body_data = message['payload']['body'].get('data')
            if body_data:
                body = base64.urlsafe_b64decode(body_data).decode('utf-8')

        combined_text = f"Subject: {subject}\nBody: {body}"

        print("="*50)
        print(f"From: {sender}")
        print(f"Subject: {subject}")
        print(f"Body snippet: {body[:200]}")
        print("-"*50)

        if is_spam_hybrid(combined_text):
            move_to_spam(service, msg_id, user_id)
        else:
            print("Not spam. Email left in inbox.")

        save_processed_id(msg_id)
        print("="*50)

def main_loop():
    gmail_service = get_gmail_service()
    print("Starting email spam filter service. Checking every 60 seconds...")
    while True:
        try:
            fetch_and_filter_emails(gmail_service)
        except Exception as e:
            print(f"Error during email fetch/filter: {e}")
        time.sleep(60)  # wait 60 seconds before next check

if __name__ == '__main__':
    main_loop()
