// ----- DOM ELEMENTS -----
const chatMessages = document.getElementById('chatMessages');
const messageInput = document.getElementById('messageInput');
const sendBtn = document.getElementById('sendBtn');
const typingIndicator = document.getElementById('typingIndicator');
const clearChatBtn = document.getElementById('clearChat');
const exportChatBtn = document.getElementById('exportChat');
const themeToggle = document.getElementById('themeToggle');

// ----- STATE -----
let isDarkMode = true;
let messageHistory = [];

// ----- QUICK ACTION BUTTONS -----
document.querySelectorAll('.quick-btn').forEach((btn) => {
    btn.addEventListener('click', function () {
        const prompt = this.getAttribute('data-prompt');
        messageInput.value = prompt;
        sendMessage();
    });
});

// ----- SEND MESSAGE -----
function sendMessage() {
    const message = messageInput.value.trim();
    if (!message) return;

    addMessage(message, 'user');
    messageInput.value = '';
    messageInput.focus();

    typingIndicator.style.display = 'flex';
    chatMessages.scrollTop = chatMessages.scrollHeight;

    fetch('/chat', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message: message }),
    })
        .then((res) => res.json())
        .then((data) => {
            typingIndicator.style.display = 'none';
            if (data.response) {
                addMessage(data.response, 'bot');
            } else if (data.error) {
                addMessage('⚠️ Sorry, something went wrong. Please try again.', 'bot');
            }
            chatMessages.scrollTop = chatMessages.scrollHeight;
        })
        .catch((error) => {
            typingIndicator.style.display = 'none';
            addMessage('⚠️ Network error. Please check your connection.', 'bot');
            console.error('Error:', error);
        });
}

// ----- ADD MESSAGE TO UI -----
function addMessage(text, sender) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}-message`;

    const avatarHTML = `
        <div class="avatar">
            <img src="https://ui-avatars.com/api/?name=${sender === 'user' ? 'You' : 'Wi+Ha+Joon'}&background=${sender === 'user' ? 'c77dff' : 'c77dff'}&color=fff&size=40&bold=true" alt="${sender}" />
        </div>
    `;

    const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    const bubbleHTML = `
        <div class="bubble">
            <p>${formatMessage(text)}</p>
            <span class="timestamp">${timestamp}</span>
        </div>
    `;

    messageDiv.innerHTML = avatarHTML + bubbleHTML;
    chatMessages.appendChild(messageDiv);
    messageHistory.push({ sender, text, timestamp });
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// ----- FORMAT MESSAGE -----
function formatMessage(text) {
    text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    text = text.replace(/\n/g, '<br>');
    return text;
}

// ----- EVENT LISTENERS -----
sendBtn.addEventListener('click', sendMessage);

messageInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

messageInput.addEventListener('input', function () {
    this.style.height = 'auto';
    this.style.height = Math.min(this.scrollHeight, 120) + 'px';
});

// ----- CLEAR CHAT -----
clearChatBtn.addEventListener('click', function () {
    if (confirm('Clear all chat messages?')) {
        chatMessages.innerHTML = `
            <div class="message bot-message">
                <div class="avatar">
                    <img src="https://ui-avatars.com/api/?name=Wi+Ha+Joon&background=c77dff&color=fff&size=40&bold=true" alt="Wi Ha Joon" />
                </div>
                <div class="bubble">
                    <p>✨ Chat cleared. How can I help you with your schedule today?</p>
                    <span class="timestamp">Just now</span>
                </div>
            </div>
        `;
        messageHistory = [];
    }
});

// ----- EXPORT CHAT -----
exportChatBtn.addEventListener('click', function () {
    let text = '=== Wi Ha Joon - Schedule Chat ===\n\n';
    document.querySelectorAll('.message').forEach((msg) => {
        const sender = msg.classList.contains('user-message') ? 'You' : 'Wi Ha Joon';
        const bubbleText = msg.querySelector('.bubble p')?.innerText || '';
        const timestamp = msg.querySelector('.timestamp')?.innerText || '';
        text += `[${timestamp}] ${sender}: ${bubbleText.replace(/<br>/g, '\n')}\n\n`;
    });
    text += '\n=== End of Chat ===';

    const blob = new Blob([text], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `chat_export_${new Date().toISOString().slice(0, 10)}.txt`;
    a.click();
    URL.revokeObjectURL(url);
});

// ----- THEME TOGGLE -----
themeToggle.addEventListener('click', function () {
    isDarkMode = !isDarkMode;
    const icon = this.querySelector('i');

    if (isDarkMode) {
        document.body.style.background = '#0d0a14';
        document.querySelector('.container').style.background = '#1a1424';
        document.querySelector('.chat-area').style.background = '#120c1a';
        document.body.classList.remove('light-mode');  // ← ADD THIS LINE
        icon.className = 'fas fa-moon';
    } else {
        document.body.style.background = '#f5edff';
        document.querySelector('.container').style.background = '#ffffff';
        document.querySelector('.chat-area').style.background = '#faf6ff';
        document.body.classList.add('light-mode')
        icon.className = 'fas fa-sun';
    }
});

// ----- VOICE BUTTON (FIXED) -----
document.getElementById('voiceBtn')?.addEventListener('click', function () {
    const button = this; // ✅ Save reference to button
    
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    
    if (!SpeechRecognition) {
        alert('❌ Voice recognition not supported. Please use Google Chrome.');
        return;
    }

    if (button.classList.contains('recording')) {
        button.classList.remove('recording');
        button.innerHTML = '<i class="fas fa-microphone"></i>';
        button.style.color = '#7a5f92';
        return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = 'en-US';
    recognition.continuous = false;
    recognition.interimResults = false;

    button.classList.add('recording');
    button.innerHTML = '<i class="fas fa-circle" style="color: #ff4444;"></i>';
    button.style.color = '#ff4444';

    recognition.start();

    recognition.onresult = function(event) {
        const transcript = event.results[0][0].transcript;
        console.log('🎤 You said:', transcript);
        messageInput.value = transcript;
        setTimeout(() => {
            sendMessage();
        }, 200);
    };

    recognition.onerror = function(event) {
        console.error('❌ Speech error:', event.error);
        button.classList.remove('recording'); // ✅ Use button, not this
        button.innerHTML = '<i class="fas fa-microphone"></i>';
        button.style.color = '#7a5f92';
        
        let errorMsg = '';
        switch(event.error) {
            case 'not-allowed':
                errorMsg = 'Please allow microphone access.';
                break;
            case 'no-speech':
                errorMsg = 'No speech detected. Please try again.';
                break;
            case 'audio-capture':
                errorMsg = 'No microphone found.';
                break;
            default:
                errorMsg = 'Please try again.';
        }
        alert('🎤 ' + errorMsg);
    };

    recognition.onend = function() {
        button.classList.remove('recording'); // ✅ Use button, not this
        button.innerHTML = '<i class="fas fa-microphone"></i>';
        button.style.color = '#7a5f92';
    };
});

// ----- GENERATE IMAGE -----
document.getElementById('imageBtn')?.addEventListener('click', function () {
    const lastUserMessage = document.querySelector('.user-message:last-child .bubble p');
    const prompt = lastUserMessage ? lastUserMessage.innerText : 'Create a beautiful weekly schedule planner';
    
    this.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    this.disabled = true;
    
    const chat = document.getElementById('chatMessages');
    const genMsg = document.createElement('div');
    genMsg.className = 'message bot-message';
    genMsg.id = 'generatingMsg';
    genMsg.innerHTML = `
        <div class="avatar">
            <img src="https://ui-avatars.com/api/?name=Wi+Ha+Joon&background=c77dff&color=fff&size=40&bold=true" alt="Wi Ha Joon" />
        </div>
        <div class="bubble">
            <p>🎨 Generating your schedule image... Please wait.</p>
        </div>
    `;
    chat.appendChild(genMsg);
    chat.scrollTop = chat.scrollHeight;
    
    fetch('/generate-image', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ prompt: prompt }),
    })
    .then(res => res.json())
    .then(data => {
        const genMsgEl = document.getElementById('generatingMsg');
        if (genMsgEl) genMsgEl.remove();
        
        this.innerHTML = '<i class="fas fa-image"></i>';
        this.disabled = false;
        
        if (data.image_url) {
            const imgDiv = document.createElement('div');
            imgDiv.className = 'message bot-message';
            imgDiv.innerHTML = `
                <div class="avatar">
                    <img src="https://ui-avatars.com/api/?name=Wi+Ha+Joon&background=c77dff&color=fff&size=40&bold=true" alt="Wi Ha Joon" />
                </div>
                <div class="bubble">
                    <p>📸 Here's your schedule image:</p>
                    <img src="${data.image_url}?t=${Date.now()}" style="max-width:100%; border-radius:12px; margin-top:10px; border: 2px solid #c77dff;" />
                    <br>
                    <a href="${data.image_url}" download style="color: #c77dff; text-decoration: none; font-weight: 600; display: inline-block; margin-top: 10px;">
                        <i class="fas fa-download"></i> Download Image
                    </a>
                    <span class="timestamp">Just now</span>
                </div>
            `;
            chat.appendChild(imgDiv);
            chat.scrollTop = chat.scrollHeight;
        } else {
            addMessage('❌ Failed to generate image. Please try again.', 'bot');
        }
    })
    .catch(error => {
        this.innerHTML = '<i class="fas fa-image"></i>';
        this.disabled = false;
        const genMsgEl = document.getElementById('generatingMsg');
        if (genMsgEl) genMsgEl.remove();
        addMessage('❌ Error generating image: ' + error.message, 'bot');
    });
});

// ----- KEYBOARD SHORTCUTS -----
document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === '/') {
        e.preventDefault();
        messageInput.focus();
    }
});

// ----- FILE UPLOAD (Paperclip Icon - WITH FILE SENDING) -----
document.querySelector('.attachment-icon')?.addEventListener('click', function () {
    const fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.accept = 'image/*,.pdf,.doc,.docx,.txt,.csv,.xlsx';
    fileInput.style.display = 'none';
    document.body.appendChild(fileInput);
    
    fileInput.click();
    
    fileInput.addEventListener('change', function (event) {
        const file = event.target.files[0];
        if (!file) return;
        
        const reader = new FileReader();
        reader.onload = function(e) {
            const fileData = e.target.result;
            
            // Show file name in input
            messageInput.value = `📎 I uploaded: ${file.name}. Please help me with this file.`;
            messageInput.placeholder = `📎 ${file.name} uploaded`;
            
            // Add a message about the upload
            addMessage(`📎 Uploaded: ${file.name} (${(file.size / 1024).toFixed(1)} KB)`, 'user');
            
            // Send the file to the backend
            sendMessageWithFile(fileData);
        };
        reader.readAsDataURL(file);
        
        this.remove();
    });
});

// ----- SEND MESSAGE WITH FILE -----
function sendMessageWithFile(fileData) {
    const message = messageInput.value.trim();
    if (!message && !fileData) return;

    addMessage(message, 'user');
    messageInput.value = '';
    messageInput.focus();

    typingIndicator.style.display = 'flex';
    chatMessages.scrollTop = chatMessages.scrollHeight;

    fetch('/chat', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
            message: message,
            file: fileData
        }),
    })
    .then((res) => res.json())
    .then((data) => {
        typingIndicator.style.display = 'none';
        if (data.response) {
            addMessage(data.response, 'bot');
        } else if (data.error) {
            addMessage('⚠️ Sorry, something went wrong. Please try again.', 'bot');
        }
        chatMessages.scrollTop = chatMessages.scrollHeight;
    })
    .catch((error) => {
        typingIndicator.style.display = 'none';
        addMessage('⚠️ Network error. Please check your connection.', 'bot');
        console.error('Error:', error);
    });
}

// Initial focus
messageInput.focus();

console.log('🤖 Wi Ha Joon - Schedule Chatbot loaded successfully!');