
        const recordButton = document.getElementById('recordButton');
        const status = document.getElementById('status');
        const conversation = document.getElementById('conversation');
        let recognition;
        let isRecording = false;

        // Initialize Web Speech API
        if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
            recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
            recognition.lang = 'en-US';
            recognition.interimResults = false;
            recognition.maxAlternatives = 1;

            recognition.onstart = () => {
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
                // Replace your existing fetch code with this:
                try {
                    status.textContent = 'Processing...';
                    // Update your fetch URL to match the origin you're serving from
                    const response = await fetch('http://localhost:5000/api/query', {
                        method: 'POST',
                        mode: 'cors',  // Explicitly enable CORS mode
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

        // Text-to-speech
        function speak(text) {
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.rate = 1.2;
            utterance.volume = 1.0;
            window.speechSynthesis.speak(utterance);
        }