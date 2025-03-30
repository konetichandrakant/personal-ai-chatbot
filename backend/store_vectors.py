import os
import re
import sqlite3
from datetime import datetime
from sentence_transformers import SentenceTransformer
from langchain_community.vectorstores import FAISS
from langchain.embeddings import HuggingFaceEmbeddings

# Define Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FOLDER = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_FOLDER, "whatsapp.db")
INPUT_TXT_FILE = os.path.join(DATA_FOLDER, "whatsapp_msgs_personx_structured.txt")
VECTOR_STORE_PATH = os.path.join(DATA_FOLDER, "whatsapp_vectors")

# Ensure Data Folder Exists
os.makedirs(DATA_FOLDER, exist_ok=True)

# SQLite DB Setup
def create_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id INTEGER UNIQUE NOT NULL,
            sender TEXT NOT NULL,
            message TEXT NOT NULL,
            timestamp TEXT NOT NULL
        );
    """)
    conn.commit()
    conn.close()

# Parse WhatsApp Messages with Incremental ID
def parse_whatsapp_chat():
    messages = []
    pattern = re.compile(r"(\d{2}/\d{2}/\d{2}) - ([^:]+): (.+)")

    if not os.path.exists(INPUT_TXT_FILE):
        raise FileNotFoundError(f"File {INPUT_TXT_FILE} not found.")

    message_id = 1

    with open(INPUT_TXT_FILE, "r", encoding="utf-8") as f:
        for line in f:
            match = pattern.match(line.strip())
            if match:
                date, sender, message = match.groups()
                try:
                    timestamp = datetime.strptime(date, "%d/%m/%y").strftime("%Y-%m-%d")
                    messages.append((message_id, sender, message, timestamp))
                    message_id += 1
                except ValueError as e:
                    print(f"Skipping invalid date format in line: {line.strip()} - Error: {e}")

    print(f"Extracted {len(messages)} messages from {INPUT_TXT_FILE}")
    return messages

# Insert Messages into SQLite
def store_messages_in_db():
    messages = parse_whatsapp_chat()
    if not messages:
        raise ValueError("No messages found to store in database.")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    for msg_id, sender, message, timestamp in messages:
        try:
            cursor.execute("""
                INSERT INTO messages (message_id, sender, message, timestamp)
                VALUES (?, ?, ?, ?);
            """, (msg_id, sender, message, timestamp))
        except sqlite3.IntegrityError:
            print(f"Skipping duplicate message ID: {msg_id}")

    conn.commit()
    conn.close()
    print("Messages stored in database successfully.")

# Store WhatsApp Messages as FAISS Vectors
def store_whatsapp_vectors():
    parsed_messages = parse_whatsapp_chat()
    text_data = [f"{timestamp}, {sender}: {message} ( message_id: {msg_id} )" for msg_id, sender, message, timestamp in parsed_messages]

    model_name = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_model = HuggingFaceEmbeddings(model_name=model_name)
    vector_store = FAISS.from_texts(text_data, embedding=embedding_model)
    vector_store.save_local(VECTOR_STORE_PATH)

    print(text_data[:5])
    print(f"Stored {len(text_data)} messages as vector embeddings in FAISS at {VECTOR_STORE_PATH}")

if __name__ == "__main__":
    create_database()  # Step 1: Create DB if not exists
    store_messages_in_db()  # Step 2: Store messages in DB
    store_whatsapp_vectors()  # Step 3: Store embeddings in FAISS