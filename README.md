# Restraurent_voice_assistant

This is a Flask-based web application that allows users to interact using voice commands. It captures audio through the browser, transcribes it using Vosk (an offline speech-to-text engine), and displays the recognized text in the UI.

Tech Stack
-Python 3.12
-Flask
-Vosk (Speech Recognition)
-HTML / JavaScript (with MediaRecorder API)
=Tailwind CSS (for frontend styling - optional)

Features
Press the "V" key or click the microphone button to start/stop voice recording
Converts spoken audio into text
Fully offline speech recognition using Vosk
Simple and responsive frontend interface

Project Structure
restaurant-voice-assistant/
│
├── app.py                   # Flask backend server
├── templates/
│   └── index.html           # Frontend UI
├── static/
│   └── script.js            # JavaScript for audio recording
├── model/
│   └── vosk-model-small-en-us-0.15/   # Vosk speech model (downloaded separately)
├── audio/
│   └── (temp audio files)
├── requirements.txt
└── README.md

🛠️ Installation & Setup
1. Clone the Repository

git clone https://github.com/your-username/restaurant-voice-assistant.git
cd restaurant-voice-assistant

2. Set Up Python Environment

python -m venv venv
source venv/Scripts/activate   # On Windows: venv\Scripts\activate

pip install -r requirements.txt

▶️ Running the App

cd server
python app.py

cd frontend 
python -m http.server 5500
open http//localhost:5500
 
🎙️ Usage
Press the "V" key or click the 🎤 mic button
Speak into your microphone
Your speech will be transcribed and displayed as text on the page

📌 Notes
Ensure your browser has microphone permissions enabled
For best performance, use Chrome or Firefox
All transcription is done locally — no internet is required once the model is downloaded

📄 License
This project is for educational/demo use. Check Vosk’s license for speech model terms.
