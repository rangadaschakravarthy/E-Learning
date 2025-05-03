function sendMessage() {
    const userInput = document.getElementById('user-input').value;
    if (userInput.trim() === '') return;

    const chatBox = document.getElementById('chat-box');
    chatBox.innerHTML += `<p class="user-message">${userInput}</p>`;
    document.getElementById('user-input').value = '';

    fetch('/get_response', {
        method: 'POST',
        body: new URLSearchParams('user_input=' + userInput),
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    })
    .then(response => response.json())
    .then(data => {
        const botResponse = data.response;
        chatBox.innerHTML += `<p class="bot-message">${botResponse}</p>`;
        chatBox.scrollTop = chatBox.scrollHeight; // Auto-scroll to bottom
    });
}
