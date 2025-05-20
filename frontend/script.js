const recordButton = document.getElementById('recordButton');
const status = document.getElementById('status');
const conversation = document.getElementById('conversation');
const enableAudioBtn = document.getElementById('enableAudioBtn');
let recognition;
let isRecording = false;
let isSpeaking = false; // Track if assistant is speaking
let currentUtterance = null; // Track current speech utterance

// Initialize Web Speech API
if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
    recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
    recognition.lang = 'en-US';
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    recognition.onstart = () => {
        // Stop any ongoing speech when user starts speaking
        if (isSpeaking) {
            window.speechSynthesis.cancel(); // Cancel current speech
            isSpeaking = false;
            currentUtterance = null;
        }
        isRecording = true;
        recordButton.textContent = 'Stop Speaking';
        recordButton.classList.remove('bg-blue-500', 'hover:bg-blue-600');
        recordButton.classList.add('bg-red-500', 'hover:bg-red-600');
        status.textContent = 'Listening...';
    };

    recognition.onresult = async (event) => {
        const transcript = event.results[0][0].transcript;
        appendToConversation('You', transcript);

        // Send to backend
        try {
            status.textContent = 'Processing...';
            const response = await fetch('http://localhost:5000/api/query', {
                method: 'POST',
                mode: 'cors',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify({ query: transcript })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
            }

            const data = await response.json();

            if (data.error) {
                appendToConversation('Assistant', `Error: ${data.error}`);
            } else {
                appendToConversation('Assistant', data.response);
                // Interrupt any ongoing speech and speak the new response
                if (isSpeaking) {
                    window.speechSynthesis.cancel();
                    isSpeaking = false;
                }
                speak(data.response);
            }
        } catch (error) {
            console.error('Fetch error:', error);
            appendToConversation('Assistant', `Error: ${error.message}`);
            status.textContent = 'Connection error. Please try again.';
        } finally {
            if (!isRecording) {
                status.textContent = 'Ready. Click button or press V to speak.';
            }
        }
    };

    recognition.onend = () => {
        isRecording = false;
        recordButton.textContent = 'Start Speaking (or Press V)';
        recordButton.classList.remove('bg-red-500', 'hover:bg-red-600');
        recordButton.classList.add('bg-blue-500', 'hover:bg-blue-600');
        if (!status.textContent.includes('Processing')) {
            status.textContent = 'Ready. Click button or press V to speak.';
        }
    };

    recognition.onerror = (event) => {
        appendToConversation('Assistant', `Speech recognition error: ${event.error}`);
        status.textContent = 'Ready. Click button or press V to speak.';
    };
} else {
    status.textContent = 'Speech recognition not supported in this browser.';
}

// Button click to start/stop recording
recordButton.addEventListener('click', () => {
    if (isRecording) {
        recognition.stop();
    } else if (recognition) {
        recognition.start();
    }
});

// Keyboard 'V' press
document.addEventListener('keydown', (event) => {
    if (event.key.toLowerCase() === 'v' && !isRecording) {
        if (recognition) {
            recognition.start();
        }
    }
});

// Append to conversation
function appendToConversation(speaker, text) {
    const div = document.createElement('div');
    div.className = `mb-2 ${speaker === 'You' ? 'text-blue-600' : 'text-green-600'}`;
    div.textContent = `${speaker}: ${text}`;
    conversation.appendChild(div);
    conversation.scrollTop = conversation.scrollHeight;
}

// Modified speak function
function speak(text, onEndCallback) {
    // Cancel any ongoing speech
    window.speechSynthesis.cancel();
    isSpeaking = false;

    currentUtterance = new SpeechSynthesisUtterance(text);
    currentUtterance.rate = 1.2;
    currentUtterance.volume = 1.0;

    currentUtterance.onstart = () => {
        isSpeaking = true;
    };

    currentUtterance.onend = () => {
        isSpeaking = false;
        currentUtterance = null;
        if (onEndCallback) {
            onEndCallback();
        }
    };

    window.speechSynthesis.speak(currentUtterance);
}

enableAudioBtn.addEventListener('click', () => {
    fetch('http://localhost:5000/api/query', {
        method: 'POST',
        mode: 'cors',
        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
        body: JSON.stringify({ query: "start conversation" })
    })
    .then(res => res.json())
    .then(data => {
        if (data.response) {
            appendToConversation('Assistant', data.response);
            // Speak then enable the button after speech ends
            speak(data.response, () => {
                recordButton.disabled = false;
                recordButton.classList.remove('opacity-50', 'cursor-not-allowed');
            });
        }
    })
    .catch(error => {
        console.error('Failed to fetch welcome:', error);
        appendToConversation('Assistant', 'Welcome! (Failed to contact mildew)');
        // Enable button anyway to not block user
        recordButton.disabled = false;
        recordButton.classList.remove('opacity-50', 'cursor-not-allowed');
    });

    enableAudioBtn.style.display = 'none';
});