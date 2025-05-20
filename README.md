# Restaurant Voice Assistant

A Flask-based web application that allows users to interact with a restaurant menu using voice commands. It captures audio through the browser, transcribes it using Vosk (offline speech-to-text), processes queries using a JSON-based menu and the Gemini API, and provides spoken responses via text-to-speech.

## Tech Stack
- **Python 3.12**: Backend logic
- **Flask**: Web server framework
- **Vosk**: Offline speech recognition
- **Google Gemini API**: Query processing for non-menu questions
- **pydub/FFmpeg**: Audio format conversion (WebM to WAV)
- **HTML/JavaScript**: Frontend with `MediaRecorder` API for audio capture
- **Tailwind CSS**: Frontend styling

## Features
- Press the "V" key or click the microphone button to start/stop voice recording
- Captures audio in the browser and sends it to the backend for transcription
- Transcribes speech offline using Vosk
- Queries a JSON-based restaurant menu for items, prices, specials, low-cost/high-cost dishes, and categories
- Falls back to Gemini API for general questions
- Displays transcribed text and responses in the UI
- Speaks responses aloud using browser-based text-to-speech
- Responsive frontend interface


##Project Structure

<!-- TREEVIEW START -->
    
       voice_assistant/
       │
       ├── frontend/
       │   ├── index.html
       │   └── script.js
       ├── Model/
       │   └── vosk-model-small-en-us-0.15 
       ├── server/
       │   ├── app_2.py
       │   └── menu.json
       ├── venv/
       ├── README.md
       └── requirements.txt


## Installation & Setup
#-Clone the Repository

git clone https://github.com/your-username/voice_assistant.git

cd voice_assistant

#-Vosk speech recognition model is already installed and is there folder called Model

## Running the App

Before running server and frontend activate venv in both terminal

# Step 1. in a terminal

cd server

Set Up Python virtual Environment

python -m venv venv

venv\Scripts\activate

Run python app.py

# Step 2. in another terminal

cd frontend 

python -m http.server 5500

open http//localhost:5500 on browser
 
## Usage

Press the "V" key or click the 🎤 mic button

Speak into your microphone

Your speech will be transcribed and displayed as text on the page

## Notes

Ensure your browser has microphone permissions enabled

For best performance, use Chrome or Firefox

All transcription is done locally — no internet is required once the model is downloaded

## License

This project is for educational/demo use. Check Vosk’s license for speech model terms.
