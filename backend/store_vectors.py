from sentence_transformers import SentenceTransformer
import os
import re
from datetime import datetime
from langchain_community.vectorstores import FAISS
from langchain.embeddings import HuggingFaceEmbeddings

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FOLDER = os.path.join(BASE_DIR, "data")
INPUT_TXT_FILE = os.path.join(DATA_FOLDER, "whatsapp_msgs_personx_structured.txt")
VECTOR_STORE_PATH = os.path.join(DATA_FOLDER, "whatsapp_vectors")

def parse_whatsapp_chat():
    messages = []
    pattern = re.compile(r"(\d{2}/\d{2}/\d{2}) - ([^:]+): (.+)")

    if not os.path.exists(INPUT_TXT_FILE):
        raise FileNotFoundError(f"File {INPUT_TXT_FILE} not found.")

    with open(INPUT_TXT_FILE, "r", encoding="utf-8") as f:
        for line in f:
            match = pattern.match(line.strip())
            if match:
                date, sender, message = match.groups()
                try:
                    timestamp = datetime.strptime(date, "%d/%m/%y").strftime("%Y-%m-%d")
                    messages.append(f"{sender}: {message} ({timestamp})")
                except ValueError as e:
                    print(f"Skipping invalid date format in line: {line.strip()} - Error: {e}")

    print(f"Extracted {len(messages)} messages from {INPUT_TXT_FILE}")
    return messages

def store_whatsapp_vectors():
    text_data = parse_whatsapp_chat()

    if not text_data:
        raise ValueError("No messages found in the file.")

    model_name = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_model = HuggingFaceEmbeddings(model_name=model_name)
    vector_store = FAISS.from_texts(text_data, embedding=embedding_model)
    vector_store.save_local(VECTOR_STORE_PATH)

    print(f"Stored {len(text_data)} messages as vector embeddings in FAISS at {VECTOR_STORE_PATH}")

if __name__ == "__main__":
    store_whatsapp_vectors()