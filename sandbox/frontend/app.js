const chatBox = document.getElementById('chat-box');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');

const appendMessage = (text, role) => {
    const div = document.createElement('div');
    div.className = `message ${role}-message`;
    div.innerText = text;
    chatBox.appendChild(div);
    chatBox.scrollTop = chatBox.scrollHeight;
};

const sendMessage = async () => {
    const message = userInput.value.trim();
    if (!message) return;

    appendMessage(message, 'user');
    userInput.value = '';

    try {
        const response = await fetch('http://localhost:5000/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message })
        });

        const data = await response.json();
        if (data.response) {
            appendMessage(data.response, 'bot');
        } else {
            appendMessage(`Error: ${data.error || 'Unknown error'}`, 'bot');
        }
    } catch (err) {
        appendMessage(`Error: Could not connect to backend.`, 'bot');
    }
};

sendBtn.addEventListener('click', sendMessage);
userInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendMessage();
});
