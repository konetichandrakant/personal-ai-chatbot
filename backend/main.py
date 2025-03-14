from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
import requests  # ✅ Use requests to call OpenRouter API
from dotenv import load_dotenv
import os

app = FastAPI()

# ✅ Enable CORS for frontend requests from localhost:3000
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # ✅ Allow frontend requests only from localhost:3000
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],  # ✅ Fix OPTIONS 405 Error
    allow_headers=["*"],
)

# Load environment variables
load_dotenv()
openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
if not openrouter_api_key:
    raise ValueError("❌ ERROR: OpenRouter API Key missing! Check your .env file.")

# Define FAISS Index Path Correctly
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # Go one level up
DATA_FOLDER = os.path.join(BASE_DIR, "data")
VECTOR_FOLDER = os.path.join(DATA_FOLDER, "whatsapp_vectors")  # ✅ FAISS expects a directory

if not os.path.exists(os.path.join(VECTOR_FOLDER, "index.faiss")):
    raise FileNotFoundError(f"❌ ERROR: FAISS index not found at {VECTOR_FOLDER}/index.faiss. Run `store_vectors.py` first.")

# Load WhatsApp vector database using the correct embedding model
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")  # ✅ Updated Import
vector_store = FAISS.load_local(
    VECTOR_FOLDER,  # ✅ FAISS expects the directory
    embeddings,
    allow_dangerous_deserialization=True
)

class ChatRequest(BaseModel):
    query: str  # ✅ Define request body schema

def search_whatsapp(query, top_k=10):
    """Searches vector database for relevant messages."""
    try:
        retrieved_docs = vector_store.similarity_search(query, k=top_k)
        return [doc.page_content for doc in retrieved_docs]
    except Exception as e:
        print(f"❌ FAISS Retrieval Error: {e}")
        return []

def call_openrouter(query, retrieved_messages):
    """Calls OpenRouter API to generate a logical response using retrieved messages."""
    url = "https://openrouter.ai/api/v1/chat/completions"  # ✅ OpenRouter API URL

    headers = {
        "Authorization": f"Bearer {openrouter_api_key}",  # ✅ Use OpenRouter API Key
        "Content-Type": "application/json"
    }

    data = {
        "model": "mistralai/mistral-7b-instruct",  # ✅ Free OpenRouter model
        "messages": [
            {"role": "system", "content": "You are an AI assistant analyzing WhatsApp messages and providing useful responses."},
            {"role": "user", "content": f"Query: {query}\n\nRelated messages:\n{retrieved_messages}"}
        ]
    }

    response = requests.post(url, json=data, headers=headers)

    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        return f"❌ OpenRouter API Error: {response.text}"  # ✅ Error Handling

@app.post("/chat")
async def chat(request: ChatRequest):  # ✅ Accept request body as JSON
    query = request.query
    """Handles user queries by retrieving past messages and generating AI response."""

    # Retrieve relevant WhatsApp messages
    retrieved_messages = search_whatsapp(query, top_k=5)

    if not retrieved_messages:
        return {"response": "No matching messages found."}

    retrieved_messages_str = "\n".join(retrieved_messages)

    # Call OpenRouter model to generate a response
    ai_response = call_openrouter(query, retrieved_messages_str)

    return {"search_results": retrieved_messages, "ai_response": ai_response}  # ✅ Returns both search results & AI response
