import logging
import sounddevice as sd
import queue
import json
from vosk import Model, KaldiRecognizer
import requests
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure
import pyttsx3
import threading
import numpy as np
from datetime import datetime
import time  # Added explicit import for time module
from flask import Flask, request, jsonify
from flask_cors import CORS, cross_origin  # ✅ include cross_origin

app = Flask(__name__)
CORS(app, origins=["http://localhost:5500"])  # general CORS setup


# ✅ Optional: Allow all headers & methods (safe for local dev)
# CORS(app, resources={r"/api/*": {"origins": "*"}})

# --- Logging ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)



# --- Configuration ---
MONGO_URI = "mongodb://localhost:27017"
DB_NAME = "restaurant_db"
OLLAMA_URL = "http://localhost:11434/api/generate"
VOSK_MODEL_PATH = "../Model/vosk-model-small-en-us-0.15"
SILENCE_TIMEOUT = 5.0  # Seconds of silence before stopping audio capture
API_PORT = 5000  # Flask API port

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# --- Globals ---
audio_queue = queue.Queue()
recognizer = KaldiRecognizer(Model(VOSK_MODEL_PATH), 16000)
interrupt_event = threading.Event()
engine_lock = threading.Lock()

# --- Sample Menu for Initialization ---
SAMPLE_MENU = [
    {
        "name": "Margherita Pizza",
        "description": "Classic pizza with tomato, mozzarella, and basil",
        "price": 12.99,
        "category": "Main Course",
        "is_special": True,
        "special_date": datetime.now().strftime("%Y-%m-%d")
    },
    {
        "name": "Spaghetti Marinara",
        "description": "Spaghetti with house-made marinara sauce",
        "price": 9.99,
        "category": "Main Course",
        "is_special": False,
        "special_date": ""
    },
    {
        "name": "Caesar Salad",
        "description": "Fresh romaine with Caesar dressing and croutons",
        "price": 6.99,
        "category": "Appetizer",
        "is_special": False,
        "special_date": ""
    },
    {
        "name": "Chocolate Lava Cake",
        "description": "Warm cake with a molten chocolate center",
        "price": 7.99,
        "category": "Dessert",
        "is_special": True,
        "special_date": datetime.now().strftime("%Y-%m-%d")
    },
    {
        "name": "Grilled Salmon",
        "description": "Salmon fillet with lemon herb sauce",
        "price": 22.50,
        "category": "Main Course",
        "is_special": False,
        "special_date": ""
    }
]

# --- MongoDB Setup ---
def setup_menu():
    """Initialize MongoDB with sample menu items and create indexes."""
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        logger.info("Connected to MongoDB successfully.")

        db = client[DB_NAME]
        menu_collection = db["menu"]
        
        # Clear existing menu items (comment out in production)
        result = menu_collection.delete_many({})
        logger.info(f"Cleared {result.deleted_count} existing menu items.")
        
        # Insert sample menu items
        result = menu_collection.insert_many(SAMPLE_MENU)
        logger.info(f"Inserted {len(result.inserted_ids)} menu items: {[doc['name'] for doc in SAMPLE_MENU]}")
        
        # Create indexes for efficient querying
        menu_collection.create_index([("price", 1)])
        menu_collection.create_index([("category", 1)])
        menu_collection.create_index([("is_special", 1), ("special_date", 1)])
        logger.info("Created indexes on price, category, and is_special/special_date fields.")
        
        # Verify insertion
        count = menu_collection.count_documents({})
        logger.info(f"Menu collection now has {count} documents.")

    except ConnectionFailure as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
    except OperationFailure as e:
        logger.error(f"MongoDB operation failed: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
    finally:
        client.close()
        logger.info("MongoDB connection closed.")

# --- MongoDB Query ---
def query_menu(prompt: str) -> str:
    """Query the MongoDB menu collection based on user input."""
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        db = client[DB_NAME]
        menu_collection = db["menu"]
        
        prompt = prompt.lower().strip()
        today = datetime.now().strftime("%Y-%m-%d")

        # Helper function to format menu items
        def format_items(items):
            return "\n".join([f"{item['name']}: {item['description']} (${item['price']})" for item in items])

        # General menu query
        if "menu" in prompt or "items" in prompt or "what do you have" in prompt:
            items = menu_collection.find().sort("name", 1)
            items_list = list(items)
            if not items_list:
                return "Sorry, the menu is currently unavailable."
            return f"Here is our menu:\n{format_items(items_list)}"

        # Price of a specific item
        elif "price of" in prompt or "cost of" in prompt:
            for item in menu_collection.find():
                if item['name'].lower() in prompt:
                    return f"{item['name']} costs ${item['price']}"
            return "Sorry, I couldn't find that item on the menu."

        # Low-cost dishes
        elif "low cost" in prompt or "cheap" in prompt or "affordable" in prompt:
            threshold = 10.0
            items = menu_collection.find({"price": {"$lte": threshold}}).sort("price", 1).limit(5)
            items_list = list(items)
            if not items_list:
                items = menu_collection.find().sort("price", 1).limit(5)
                items_list = list(items)
                if not items_list:
                    return "Sorry, no low-cost dishes are available."
            return f"Here are some affordable dishes:\n{format_items(items_list)}"

        # High-cost dishes
        elif "high cost" in prompt or "expensive" in prompt or "premium" in prompt:
            threshold = 20.0
            items = menu_collection.find({"price": {"$gte": threshold}}).sort("price", -1).limit(5)
            items_list = list(items)
            if not items_list:
                items = menu_collection.find().sort("price", -1).limit(5)
                items_list = list(items)
                if not items_list:
                    return "Sorry, no high-cost dishes are available."
            return f"Here are some premium dishes:\n{format_items(items_list)}"

        # Today's special
        elif "today's special" in prompt or "daily special" in prompt:
            items = menu_collection.find({"is_special": True, "special_date": today}).sort("name", 1)
            items_list = list(items)
            if not items_list:
                return "There are no specials available today."
            return f"Today's specials:\n{format_items(items_list)}"

        # Category-based queries
        elif any(category.lower() in prompt for category in ["appetizer", "main course", "dessert"]):
            for category in ["Appetizer", "Main Course", "Dessert"]:
                if category.lower() in prompt:
                    items = menu_collection.find({"category": category}).sort("name", 1)
                    items_list = list(items)
                    if not items_list:
                        return f"Sorry, no {category.lower()} items are available."
                    return f"Here are our {category.lower()}s:\n{format_items(items_list)}"

        return ""  # Fallback to LLM

    except Exception as e:
        logger.error(f"Error querying menu: {e}")
        return ""
    finally:
        client.close()

# --- Query LLaMA ---
def query_ollama(prompt: str) -> str:
    try:
        # Choose context based on query
        context = ""
        prompt_lower = prompt.lower().strip()
        if "low cost" in prompt_lower or "cheap" in prompt_lower:
            context = query_menu("low cost") or "No low-cost dishes available."
        elif "today's special" in prompt_lower or "daily special" in prompt_lower:
            context = query_menu("today's special") or "No specials available."
        elif "dessert" in prompt_lower or "appetizer" in prompt_lower or "main course" in prompt_lower:
            for category in ["Appetizer", "Main Course", "Dessert"]:
                if category.lower() in prompt_lower:
                    context = query_menu(category.lower()) or f"No {category.lower()}s available."
        else:
            context = query_menu("menu") or "No menu data available."
        
        full_prompt = f"Restaurant Menu Context:\n{context}\n\nUser Question: {prompt}\nAnswer based on the menu context if relevant, or provide a general response."
        
        response = requests.post(
            OLLAMA_URL,
            json={"model": "llama3.2:3b", "prompt": full_prompt},
            stream=True
        )
        full_response = ""
        for line in response.iter_lines():
            if line:
                data = json.loads(line)
                full_response += data.get("response", "")
                if data.get("done", False):
                    break
        return full_response.strip()
    except Exception as e:
        logger.error(f"Ollama error: {e}")
        return ""

# --- Flask API Endpoint ---
@app.route('/api/query', methods=['POST'])
def handle_query():
    try:
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({"error": "No query provided"}), 400
        
        query = data['query']
        logger.info(f"Received API query: {query}")
        
        # Try MongoDB first
        response = query_menu(query)
        if not response:
            logger.info("Querying LLaMA with menu context...")
            response = query_ollama(query)
        
        if response:
            return jsonify({"response": response})
        else:
            return jsonify({"error": "No response generated"}), 500
    except Exception as e:
        logger.error(f"API error: {e}")
        return jsonify({"error": str(e)}), 500

# --- Run Flask and Assistant ---
def run_flask():
    app.run(port=API_PORT, debug=False, use_reloader=False)

if __name__ == "__main__":
    # Initialize menu
    setup_menu()
    
    # Start Flask in a separate thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    logger.info(f"Flask API running on http://localhost:{API_PORT}")
    logger.info("Backend initialized. Frontend can send queries to /api/query.")
    
    # Keep the script running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Backend stopped by user.")

