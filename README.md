

# 📬 InboxSage AI - Email Auto-Responder & Spam Filter

InboxSage AI is a Python-based email support automation tool that reads unread Gmail messages, filters spam, classifies legitimate emails, and sends intelligent replies — all automatically. It's built with customer support in mind, reducing manual workload while maintaining professionalism.


## ✨ Features

- ✅ Automatically fetches unread emails
- 🚫 Filters spam using rules + AI (Cohere LLM)
- 🧠 Classifies messages into:
  - Complaint
  - Feedback
  - Product/Service Question
  - Other
- 🤖 Generates polite, context-aware replies
- 📊 Logs every response with category & timestamp
- 🔁 Skips replies if already responded twice



## 🛠️ Tech Stack

- **Python**
- **Gmail API**
- **Cohere AI (LLM for text classification & reply generation)**
- `.env` for secure API keys
- Google OAuth2 (`credentials.json` + `token.pickle`)



## 📁 Project Structure

```text
InboxSage
├── .env                  # Contains COHERE_API_KEY
├── credentials.json      # OAuth credentials from Google Cloud
├── token.pickle          # Auth token generated after login
├── fetch_emails.py       # Utility to fetch unread emails
├── gmail_auth.py         # Gmail API auth + label test
├── spam_filter.py        # Main script: spam filter + reply agent
├── processed_emails.txt  # Keeps track of handled emails
├── sent_emails_log.csv   # Logs all replies
└── README.md             # You're here

````


## 🚀 Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/your-username/inboxsage-ai.git
cd inboxsage-ai
````

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Setup environment

* Create a `.env` file and add your [Cohere API Key](https://dashboard.cohere.com/api-keys):

```
COHERE_API_KEY=your-api-key-here
```

* Get your `credentials.json` from [Google Cloud Console](https://console.cloud.google.com/apis/credentials) (enable Gmail API).

### 4. Run the assistant

```bash
python spam_filter.py
```

InboxSage will check every 10 seconds, filter spam, respond to emails, and log everything.

---

## 📒 Example

**Incoming Email:**

> Subject: Help with my order
> Body: I haven’t received my order #1234, please assist.

**Auto Reply:**

> Thank you for reaching out. We’re sorry to hear about the delay with your order #1234.
> Our team will look into it and get back to you shortly.
>
> Kind regards,
> Customer Support

---

## 📌 Notes

* Automatically avoids replying more than twice to the same thread.
* Spam detection uses both simple keyword rules and LLM-based reasoning.
* Logs are saved in `sent_emails_log.csv`.

---
