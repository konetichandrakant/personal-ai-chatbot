from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
import requests
from dotenv import load_dotenv
import os

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

def search_whatsapp(query, top_k):
    try:
        retrieved_docs = vector_store.similarity_search(query, k=top_k)
        return [doc.page_content for doc in retrieved_docs]
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
    retrieved_messages = search_whatsapp(query, top_k=15)
    if not retrieved_messages:
        return {"response": "No matching messages found."}
    retrieved_messages_str = "\n".join(retrieved_messages)
    ai_response = call_openrouter(query, retrieved_messages_str)
    return {"search_results": retrieved_messages, "ai_response": ai_response}
