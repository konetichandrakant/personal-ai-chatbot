import re
import os

# Define Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_FILE = os.path.join(BASE_DIR, "whatsapp_msgs_personx.txt")
OUTPUT_FILE = os.path.join(BASE_DIR, "whatsapp_msgs_personx_structured.txt")

# Step 1: Read the WhatsApp chat from the file
with open(INPUT_FILE, "r", encoding="utf-8") as file:
    whatsapp_chat = file.read()

# Step 2: Extract messages and remove time (keep only date)
def extract_messages(chat_text):
    pattern = re.compile(r'(\d{2}/\d{2}/\d{2}), \d{1,2}:\d{2}\s?[ap]m - (.*?): (.*)')
    messages = pattern.findall(chat_text)
    return [[date, user, message] for date, user, message in messages if "<Media omitted>" not in message]

extracted_messages = extract_messages(whatsapp_chat)

# Step 3: Process each message (No Translation, Just Structuring)
structured_messages = []
structured_texts = []

for message_data in extracted_messages:
    date, user, message = message_data  # Extract list elements
    
    # Store structured data in list format
    structured_messages.append([date, user, message])
    structured_texts.append(f"{date} - {user}: {message}")

# Step 4: Save the structured text to the output file
with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
    file.write("\n".join(structured_texts))

print("Structuring complete!")