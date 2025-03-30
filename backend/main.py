from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
import requests
from dotenv import load_dotenv
import os
import re
import sqlite3

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

load_dotenv()
openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
if not openrouter_api_key:
    raise ValueError("OpenRouter API Key missing! Check your .env file.")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FOLDER = os.path.join(BASE_DIR, "data")
VECTOR_FOLDER = os.path.join(DATA_FOLDER, "whatsapp_vectors")

if not os.path.exists(os.path.join(VECTOR_FOLDER, "index.faiss")):
    raise FileNotFoundError(f"FAISS index not found at {VECTOR_FOLDER}/index.faiss. Run `store_vectors.py` first.")

embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
vector_store = FAISS.load_local(
    VECTOR_FOLDER,
    embeddings,
    allow_dangerous_deserialization=True
)

class ChatRequest(BaseModel):
    query: str

DB_PATH = os.path.join(BASE_DIR, "data", "whatsapp.db")
db_connection = None

@app.on_event("startup")
async def startup():
    global db_connection
    db_connection = sqlite3.connect(DB_PATH)
    print("Database connection established")

@app.on_event("shutdown")
async def shutdown():
    global db_connection
    if db_connection:
        db_connection.close()
        print("Database connection closed")

def get_message_from_db(message_id, first_messsage_of_context=False):
    global db_connection
    cursor = db_connection.cursor()
    if(first_messsage_of_context):
        cursor.execute("SELECT message, timestamp, sender FROM messages WHERE message_id = ?", (message_id,))
        result = cursor.fetchone()
        if result:
            message, timestamp, sender = result
            return timestamp+", " + sender + ": " + message
        else:
            print("Message not found")
            return None
    else:
        cursor.execute("SELECT message, sender FROM messages WHERE message_id = ?", (message_id,))
        result = cursor.fetchone()
        if result:
            message, sender = result
            return sender + ": " + message
        else:
            print("Message not found")
            return None

def attach_context_messages(top_msgs, current_msg, bottom_msgs):
    context_messages = "\n".join([msg for msg in top_msgs])
    context_messages += "\n" + current_msg + "\n"
    context_messages += "\n".join([msg for msg in bottom_msgs])
    return context_messages

def get_top_k_context_messages(message_id, top_k):    
    messages = []
    try:
        for i in range(top_k):
            message_id -= 1
            message = get_message_from_db(message_id, first_messsage_of_context= i==0)
            if(message is None):
                return messages
            messages.append(message)
        return messages
    except Exception as e:
        print(f"Error retrieving bottom messages: {e}")
        print("No more messages.")
        return []

def get_bottom_k_context_messages(message_id, bottom_k):
    messages = []
    try:
        for i in range(bottom_k):
            message_id += 1
            message = get_message_from_db(message_id)
            if(message is None):
                return messages
            messages.append(message)
        return messages
    except Exception as e:
        print(f"Error retrieving bottom messages: {e}")
        print("No more messages.")
        return []

def get_context_messages(message):
    current_message_id = get_message_id_from_message(message)
    top_msgs = get_top_k_context_messages(current_message_id, top_k=3)
    current_msg = get_message_from_db(current_message_id)
    bottom_msgs = get_bottom_k_context_messages(current_message_id, bottom_k=2)
    return attach_context_messages(top_msgs, current_msg, bottom_msgs)
    
def get_message_id_from_message(message):
    pattern = r"\( message_id: (\d+) \)"
    match = re.search(pattern, message)
    message_id = match.group(1)
    return int(message_id)

def search_whatsapp(query, top_k):
    all_context_msgs = []
    try:
        retrieved_docs = vector_store.similarity_search(query, k=top_k)        
        for doc in retrieved_docs:
            context_msgs = get_context_messages(doc.page_content)
            all_context_msgs.append(context_msgs)
        return all_context_msgs
    except Exception as e:
        print(f"FAISS Retrieval Error: {e}")
        return []

def call_openrouter(query, retrieved_messages):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {openrouter_api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "openchat/openchat-7b:free",
        "temperature": 0,
        "messages": [
            {
                "role": "system",
                "content": "You are an AI assistant analyzing WhatsApp messages. Only respond using the provided query and related messages. Do not add information that is not explicitly stated in the query. Do not infer or assume details beyond what is given. When a message says 'he' or 'she,' it refers to a third person, not the sender or recipient. When 'you' is used, it refers to the recipient if the message is from the sender. If the message is from the recipient, 'you' refers to the sender. 'I' always refers to the person who sent the message. Stick strictly to this format."
            },
            {
                "role": "user",
                "content": f"Query: {query}\n\nRelated messages:\n{retrieved_messages}"
            }
        ]
    }

    response = requests.post(url, json=data, headers=headers)
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        return f"OpenRouter API Error: {response.text}"

@app.post("/chat")
async def chat(request: ChatRequest):
    query = request.query
    retrieved_messages = search_whatsapp(query, top_k=5)
    if not retrieved_messages:
        return {"response": "No matching messages found."}
    ai_response = call_openrouter(query+" please look into messages they are bundled of day time context and make decisions on text or bundle they are also seperated by \n for each message", ["Chat context between myself and PersonX on particular day:" + msg for msg in retrieved_messages[0:2]])
    return {"search_results": retrieved_messages, "ai_response": ai_response}
