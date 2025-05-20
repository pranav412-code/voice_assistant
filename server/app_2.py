import logging
import json
import os
from datetime import datetime
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
import time
import google.generativeai as genai
import sounddevice as sd
import queue
import numpy as np
from vosk import Model, KaldiRecognizer
import threading
import scipy.io.wavfile as wavfile
from pydub import AudioSegment

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# --- Configuration ---
MENU_FILE = "menu.json"
API_PORT = 5000
GEMINI_API_KEY = "AIzaSyAASh4afqyGSSTGRzW0SIe_ABh9iTpFX54"  # Replace with actual Gemini API key
GEMINI_MODEL = "gemini-1.5-flash"
VOSK_MODEL_PATH = "../Model/vosk-model-small-en-us-0.15"
SILENCE_TIMEOUT = 5.0
SAMPLE_RATE = 16000
CHANNELS = 1

# --- Flask Setup ---
app = Flask(__name__)
CORS(app, origins=["http://localhost:5500"])

# --- Audio Processing ---
audio_queue = queue.Queue()
recognizer = KaldiRecognizer(Model(VOSK_MODEL_PATH), SAMPLE_RATE)
interrupt_event = threading.Event()

# --- Sample Menu ---
SAMPLE_MENU = [
    # Appetizers
    {
        "name": "Bruschetta",
        "description": "Toasted bread topped with tomatoes, garlic, and basil",
        "price": 5.99,
        "category": "Appetizer",
        "is_special": False,
        "special_date": ""
    },
    {
        "name": "Mozzarella Sticks",
        "description": "Crispy breaded mozzarella with marinara sauce",
        "price": 6.49,
        "category": "Appetizer",
        "is_special": True,
        "special_date": datetime.now().strftime("%Y-%m-%d")
    },

    # Main Courses
    {
        "name": "Chicken Alfredo",
        "description": "Creamy Alfredo pasta with grilled chicken",
        "price": 14.99,
        "category": "Main Course",
        "is_special": False,
        "special_date": ""
    },
    {
        "name": "Vegan Buddha Bowl",
        "description": "Quinoa, roasted veggies, chickpeas, and tahini dressing",
        "price": 11.50,
        "category": "Main Course",
        "is_special": False,
        "special_date": ""
    },
    {
        "name": "BBQ Ribs",
        "description": "Slow-cooked ribs with BBQ sauce and sides",
        "price": 24.00,
        "category": "Main Course",
        "is_special": True,
        "special_date": datetime.now().strftime("%Y-%m-%d")
    },

    # Desserts
    {
        "name": "Cheesecake",
        "description": "Creamy cheesecake with a graham cracker crust",
        "price": 6.99,
        "category": "Dessert",
        "is_special": False,
        "special_date": ""
    },
    {
        "name": "Ice Cream Sundae",
        "description": "Vanilla ice cream with chocolate sauce and nuts",
        "price": 4.99,
        "category": "Dessert",
        "is_special": False,
        "special_date": ""
    },

    # Drinks
    {
        "name": "Iced Tea",
        "description": "Freshly brewed iced tea with lemon",
        "price": 2.49,
        "category": "Drink",
        "is_special": False,
        "special_date": ""
    },
    {
        "name": "Craft Beer",
        "description": "Local craft IPA on tap",
        "price": 5.99,
        "category": "Drink",
        "is_special": False,
        "special_date": ""
    },

    # Sides
    {
        "name": "French Fries",
        "description": "Crispy golden fries with ketchup",
        "price": 3.99,
        "category": "Side",
        "is_special": False,
        "special_date": ""
    },
    {
        "name": "Garlic Bread",
        "description": "Buttery garlic breadsticks",
        "price": 3.49,
        "category": "Side",
        "is_special": False,
        "special_date": ""
    }
]


# --- JSON Menu Management ---
def setup_menu():
    try:
        if not os.path.exists(MENU_FILE):
            with open(MENU_FILE, 'w') as f:
                json.dump(SAMPLE_MENU, f, indent=4)
            logger.info(f"Created menu file with {len(SAMPLE_MENU)} items.")
        else:
            logger.info(f"Menu file {MENU_FILE} already exists.")
    except Exception as e:
        logger.error(f"Error setting up menu file: {e}")

def load_menu():
    try:
        with open(MENU_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading menu: {e}")
        return []

# --- Menu Query Tool ---
def query_menu(prompt: str) -> str:
    try:
        menu = load_menu()
        prompt = prompt.lower().strip()
        today = datetime.now().strftime("%Y-%m-%d")

        def format_items(items):
            return "\n".join([f"{item['name']}: {item['description']} (${item['price']})" for item in items])

        if "menu" in prompt or "items" in prompt or "what do you have" in prompt:
            if not menu:
                return "Sorry, the menu is currently unavailable."
            return f"Here is our menu:\n{format_items(sorted(menu, key=lambda x: x['name']))}"

        elif "price of" in prompt or "cost of" in prompt:
            for item in menu:
                if item['name'].lower() in prompt:
                    return f"{item['name']} costs ${item['price']}"
            return "Sorry, I couldn't find that item on the menu."

        elif "low cost" in prompt or "cheap" in prompt or "affordable" in prompt:
            threshold = 10.0
            items = [item for item in menu if item['price'] <= threshold]
            if not items:
                items = sorted(menu, key=lambda x: x['price'])[:5]
                if not items:
                    return "Sorry, no low-cost dishes are available."
            return f"Here are some affordable dishes:\n{format_items(sorted(items, key=lambda x: x['price']))}"

        elif "high cost" in prompt or "expensive" in prompt or "premium" in prompt:
            threshold = 20.0
            items = [item for item in menu if item['price'] >= threshold]
            if not items:
                items = sorted(menu, key=lambda x: x['price'], reverse=True)[:5]
                if not items:
                    return "Sorry, no high-cost dishes are available."
            return f"Here are some premium dishes:\n{format_items(sorted(items, key=lambda x: x['price'], reverse=True))}"

        elif any(phrase in prompt for phrase in ["today's special", "todays special", "today special", "daily special"]):
            items = [item for item in menu if item['is_special'] and item['special_date'] == today]
            if not items:
                return "There are no specials available today."
            return f"Today's specials:\n{format_items(sorted(items, key=lambda x: x['name']))}"

        elif any(category.lower() in prompt for category in ["appetizer", "main course", "dessert"]):
            for category in ["Appetizer", "Main Course", "Dessert"]:
                if category.lower() in prompt:
                    items = [item for item in menu if item['category'] == category]
                    if not items:
                        return f"Sorry, no {category.lower()} items are available."
                    return f"Here are our {category.lower()}s:\n{format_items(sorted(items, key=lambda x: x['name']))}"

        return ""

    except Exception as e:
        logger.error(f"Error querying menu: {e}")
        return ""

# --- Gemini API Integration ---
def query_gemini(prompt: str) -> str:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel(GEMINI_MODEL)

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

        response = model.generate_content(full_prompt)
        return response.text.strip()

    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        return ""

# --- Audio Processing ---
def process_audio(audio_data, sample_rate):
    try:
        recognizer = KaldiRecognizer(Model(VOSK_MODEL_PATH), sample_rate)
        recognizer.AcceptWaveform(audio_data.tobytes())
        result = json.loads(recognizer.FinalResult())
        return result.get('text', '')
    except Exception as e:
        logger.error(f"Error processing audio: {e}")
        return ""

# --- Audio Conversion ---
def convert_to_wav(input_path, output_path):
    try:
        audio = AudioSegment.from_file(input_path)
        audio = audio.set_channels(CHANNELS).set_frame_rate(SAMPLE_RATE)
        audio.export(output_path, format="wav")
        logger.info(f"Converted audio to WAV: {output_path}")
    except Exception as e:
        logger.error(f"Error converting audio to WAV: {e}")
        raise

# --- Flask API Endpoints ---
@app.route('/api/query', methods=['POST'])
def handle_query():
    try:
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({"error": "No query provided"}), 400
        
        query = data['query']
        logger.info(f"Received text query: {query}")

        # --- Add this block ---
        if query.lower().strip() == "start conversation":
            response = "Hello! Welcome to our restaurant. How can I help you today?"
        else:
            # Normal LLM response
            response = query_menu(query)
            if not response:
                logger.info("Querying Gemini API with menu context...")
                response = query_gemini(query)
        # --- End block ---

        if response:
            return jsonify({"response": response})
        else:
            return jsonify({"error": "No response generated"}), 500
    except Exception as e:
        logger.error(f"API error: {e}")
        return jsonify({"error": str(e)}), 500
    
@app.route('/api/welcome', methods=['GET'])
def welcome_prompt():
    try:
        prompt = "Greet the customer and ask if they want today's special or see the full menu."
        logger.info("Sending welcome prompt via Gemini")
        response = query_gemini(prompt)
        return jsonify({"response": response})
    except Exception as e:
        logger.error(f"Welcome prompt error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/audio', methods=['POST'])
def handle_audio():
    try:
        if 'audio' not in request.files:
            return jsonify({"error": "No audio file provided"}), 400
        
        audio_file = request.files['audio']
        input_path = "temp_audio.webm"
        output_path = "temp_audio.wav"
        audio_file.save(input_path)
        
        # Convert WebM to WAV
        convert_to_wav(input_path, output_path)
        
        # Read WAV file
        sample_rate, audio_data = wavfile.read(output_path)
        if len(audio_data.shape) > 1:
            audio_data = audio_data[:, 0]
        
        # Process audio
        transcript = process_audio(audio_data, sample_rate)
        if not transcript:
            os.remove(input_path)
            os.remove(output_path)
            return jsonify({"error": "Could not transcribe audio"}), 400
        
        logger.info(f"Transcribed audio: {transcript}")
        
        # Query menu or Gemini
        response = query_menu(transcript)
        if not response:
            logger.info("Querying Gemini API with menu context...")
            response = query_gemini(transcript)
        
        os.remove(input_path)
        os.remove(output_path)
        
        if response:
            return jsonify({"transcript": transcript, "response": response})
        else:
            return jsonify({"error": "No response generated"}), 500
    except Exception as e:
        logger.error(f"Audio API error: {e}")
        for path in [input_path, output_path]:
            if os.path.exists(path):
                os.remove(path)
        return jsonify({"error": str(e)}), 500

# --- Run Flask ---
def run_flask():
    app.run(port=API_PORT, debug=False, use_reloader=False)

if __name__ == "__main__":
    setup_menu()
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logger.info(f"Flask API running on http://localhost:{API_PORT}")
    logger.info("Backend initialized. Frontend can send queries to /api/query or /api/audio.")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Backend stopped by user.")