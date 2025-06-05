import os
from dotenv import load_dotenv
import cohere

load_dotenv()
api_key = os.getenv("COHERE_API_KEY")

if not api_key:
    raise ValueError("Please set COHERE_API_KEY in your environment variables")

co = cohere.Client(api_key)

def test_spam_detection(text):
    prompt = f"""Decide if the following message is spam. Answer only "Spam" or "Not Spam".

Message: \"\"\"{text}\"\"\"
"""
    try:
        response = co.generate(
            model='command',   # You can try 'large' or 'medium' if 'command' is unavailable
            prompt=prompt,
            max_tokens=5,
            temperature=0,
            stop_sequences=["\n"]
        )
        raw_text = response.generations[0].text.strip()
        print(f"Raw model output: '{raw_text}'")
        answer = raw_text.lower()

        if answer == "spam":
            return True
        elif answer == "not spam":
            return False
        else:
            print(f"Unclear model answer: '{raw_text}', defaulting to Not Spam.")
            return False
    except Exception as e:
        print(f"Cohere API error: {e}")
        return False

if __name__ == "__main__":
    test_messages = [
        "Win a free prize now! Click here to claim your reward.",
        "Hello, I wanted to check on the status of my order.",
        "Limited time offer, buy one get one free!",
        "Dear customer, your invoice is attached.",
    ]

    for msg in test_messages:
        print(f"\nTesting message:\n{msg}")
        is_spam = test_spam_detection(msg)
        print(f"Detected as spam? {is_spam}")
