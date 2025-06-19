import os.path 
import pickle
import base64
import re
import time
from email.mime.text import MIMEText
from email.utils import formataddr
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from dotenv import load_dotenv
import cohere
import csv
from datetime import datetime

load_dotenv()
api_key = os.getenv("COHERE_API_KEY")
co = cohere.Client(api_key)

SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
PROCESSED_IDS_FILE = 'processed_emails.txt'
LOG_FILE = 'sent_emails_log.csv'
SUPPORT_EMAIL = "inboxsageai@gmail.com"  

SPAM_KEYWORDS = [
    r"win prize", r"free money", r"urgent response", r"claim your reward",
    r"click here", r"limited time offer", r"congratulations",
]

# Ensure CSV log file exists
if not os.path.exists(LOG_FILE):
    with open(LOG_FILE, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Sender', 'Category', 'Timestamp'])

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
    return build('gmail', 'v1', credentials=creds)

def is_spam_rule_based(text):
    text_lower = text.lower()
    return any(re.search(pattern, text_lower) for pattern in SPAM_KEYWORDS)

def is_spam_llm(text):
    prompt = f"""Decide if the following message is spam. Answer only "Spam" or "Not Spam".\n\nMessage: \"\"\"{text}\"\"\""""
    try:
        response = co.generate(model='command', prompt=prompt, max_tokens=5, temperature=0, stop_sequences=["\n"])
        return response.generations[0].text.strip().lower().rstrip('.') == "spam"
    except Exception as e:
        print(f"Cohere API error: {e}")
        return False

def is_spam_hybrid(text):
    return is_spam_rule_based(text) or is_spam_llm(text)

def move_to_spam(service, msg_id, user_id='me'):
    try:
        service.users().messages().modify(userId=user_id, id=msg_id, body={'addLabelIds': ['SPAM'], 'removeLabelIds': ['INBOX', 'UNREAD']}).execute()
    except Exception as e:
        print(f"Failed to move email {msg_id} to spam: {e}")

def categorize_email(text):
    prompt = f"""Classify the following email into one of these categories:\n1. Complaint\n2. Feedback\n3. Product/Service Question\n4. Other\n\nOnly respond with the category name.\n\nEmail:\n\"\"\"{text}\"\"\""""
    try:
        response = co.generate(model='command', prompt=prompt, max_tokens=10, temperature=0.3, stop_sequences=["\n"])
        return response.generations[0].text.strip()
    except Exception:
        return "Other"

def is_reply_email(email_body, subject):
    reply_markers = [r"^On .+ wrote:", r"^>+", r"---+ Original Message", r"From:", r"Sent:", r"Subject:"]
    # Check body markers
    if any(re.search(pattern, email_body, re.MULTILINE | re.IGNORECASE) for pattern in reply_markers):
        return True
    # Check subject prefix for replies/forwards
    if subject and subject.strip().lower().startswith(("re:", "fwd:")):
        return True
    return False

# New function to count own replies in the thread
def count_own_replies_in_thread(service, thread_id, support_email=SUPPORT_EMAIL, user_id='me'):
    try:
        thread = service.users().threads().get(userId=user_id, id=thread_id).execute()
        own_reply_count = 0
        for msg in thread['messages']:
            headers = msg['payload'].get('headers', [])
            for header in headers:
                if header['name'] == 'From' and support_email.lower() in header['value'].lower():
                    own_reply_count += 1
        return own_reply_count
    except Exception as e:
        print(f"Error counting replies in thread {thread_id}: {e}")
        return 0

def generate_response(text, category, subject):
    if is_reply_email(text, subject ):
        return "Thank you for your reply. Please contact 9197384953 for more details.\n\nKind regards,\nCustomer Support"

    prompt = f"""You are a polite and helpful customer support assistant.
The user has sent the following message categorized as "{category}".
Write a formal and concise reply without using placeholders.
End the reply exactly with:
Kind regards,
Customer Support

Email:
\"\"\"{text}\"\"\""""
    try:
        response = co.generate(model='command', prompt=prompt, max_tokens=300, temperature=0.4, stop_sequences=["--END--"])
        return response.generations[0].text.strip()
    except Exception as e:
        print(f"Error generating reply: {e}")
        return "Thank you for reaching out. We'll get back to you shortly.\n\nKind regards,\nCustomer Support"

def check_quality_and_formatting(reply_text):
    prompt = f"""Improve the following email for grammar, clarity, and formal tone.
Do not change the closing line. Only return the improved email without explanation.

{reply_text}"""
    try:
        response = co.generate(model='command', prompt=prompt, max_tokens=300, temperature=0.2, stop_sequences=["--END--"])
        return response.generations[0].text.strip()
    except Exception:
        return reply_text

import re

def clean_subject(subject):
    # Remove all repeating "Re:" prefixes
    return re.sub(r'^(Re:\s*)+', '', subject, flags=re.IGNORECASE).strip()

def send_email(service, to_email, subject, message_text, user_id='me'):
    try:
        message = MIMEText(message_text)
        message['to'] = to_email
        message['from'] = user_id
        clean_subj = clean_subject(subject)
        message['subject'] = f"Re: {clean_subj}"
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        service.users().messages().send(userId=user_id, body={'raw': raw_message}).execute()
    except Exception as e:
        print(f"Error sending email: {e}")


def load_processed_ids():
    if not os.path.exists(PROCESSED_IDS_FILE):
        return set()
    with open(PROCESSED_IDS_FILE, 'r') as f:
        return set(line.strip() for line in f.readlines())

def save_processed_id(msg_id):
    with open(PROCESSED_IDS_FILE, 'a') as f:
        f.write(msg_id + '\n')

def log_sent_email(sender, category):
    with open(LOG_FILE, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([sender, category, datetime.now().isoformat()])

def fetch_and_filter_emails(service, user_id='me'):
    processed_ids = load_processed_ids()
    results = service.users().messages().list(userId=user_id, labelIds=['INBOX', 'UNREAD']).execute()
    messages = results.get('messages', [])

    for msg in messages:
        msg_id = msg['id']
        if msg_id in processed_ids:
            continue

        message = service.users().messages().get(userId=user_id, id=msg_id, format='full').execute()
        headers = message['payload'].get('headers', [])
        subject = sender = None
        for header in headers:
            if header['name'] == 'Subject':
                subject = header['value']
            elif header['name'] == 'From':
                sender = header['value']

        # Skip own emails
        if sender.lower().startswith("me") or SUPPORT_EMAIL.lower() in sender.lower():
            save_processed_id(msg_id)
            continue

        parts = message['payload'].get('parts', [])
        body = ""
        if parts:
            for part in parts:
                if part['mimeType'] == 'text/plain':
                    body_data = part['body'].get('data')
                    if body_data:
                        body = base64.urlsafe_b64decode(body_data).decode('utf-8')
                        break
        else:
            body_data = message['payload']['body'].get('data')
            if body_data:
                body = base64.urlsafe_b64decode(body_data).decode('utf-8')

        combined_text = f"Subject: {subject}\nBody: {body}"

        if is_spam_hybrid(combined_text):
            move_to_spam(service, msg_id, user_id)
        else:
            # Check how many times support email has replied in this thread
            own_reply_count = count_own_replies_in_thread(service, message['threadId'], SUPPORT_EMAIL, user_id)
            if own_reply_count >= 2:
                print(f"Reached max replies (2) for thread {message['threadId']}, skipping.")
            else:
                category = categorize_email(combined_text)
                reply = generate_response(body, category, subject)
                checked_reply = check_quality_and_formatting(reply)
                send_email(service, sender, subject, checked_reply)
                log_sent_email(sender, category)

        save_processed_id(msg_id)

def main_loop():
    gmail_service = get_gmail_service()
    print("Starting email support agent. Checking every 10 seconds...")
    while True:
        try:
            fetch_and_filter_emails(gmail_service)
        except Exception as e:
            print(f"Error during processing: {e}")
        time.sleep(10)

if __name__ == '__main__':
    main_loop()
