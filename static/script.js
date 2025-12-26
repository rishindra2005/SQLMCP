document.addEventListener('DOMContentLoaded', () => {
    const chatLog = document.getElementById('chat-log');
    const chatForm = document.getElementById('chat-form');
    const userInput = document.getElementById('user-input');
    const resetButton = document.getElementById('reset-button');
    const statusDiv = document.getElementById('connection-status');

    const icons = {
        thought: 'fas fa-lightbulb',
        action: 'fas fa-cogs',
        observation: 'fas fa-search',
        final_answer: 'fas fa-check-circle',
        error: 'fas fa-exclamation-triangle',
        user: 'fas fa-user',
        loading: 'fas fa-spinner fa-spin'
    };

    const addMessage = (type, content, id = null) => {
        const messageDiv = document.createElement('div');
        if (id) {
            messageDiv.id = id;
        }
        messageDiv.classList.add('message', type);

        const title = type.replace('_', ' ');
        const iconClass = icons[type] || 'fas fa-info-circle';

        const messageHeader = document.createElement('h3');
        messageHeader.innerHTML = `<i class="${iconClass}"></i> ${title}`;

        const contentDiv = document.createElement('div');
        // Use marked.parse to render markdown content
        contentDiv.innerHTML = marked.parse(content || '');

        messageDiv.appendChild(messageHeader);
        messageDiv.appendChild(contentDiv);
        chatLog.appendChild(messageDiv);
        chatLog.scrollTop = chatLog.scrollHeight;
        return messageDiv;
    };
    
    const updateConnectionStatus = async () => {
        try {
            const response = await fetch('/status');
            const data = await response.json();
            if (response.ok) {
                const dbName = data.includes("No database") ? "None" : data.split("'")[1];
                statusDiv.innerHTML = `<i class="fas fa-database"></i> DB: <strong>${dbName}</strong>`;
                statusDiv.className = 'status-connected';
            } else {
                statusDiv.innerHTML = `<i class="fas fa-exclamation-triangle"></i> Not Connected`;
                statusDiv.className = 'status-disconnected';
            }
        } catch (error) {
            statusDiv.innerHTML = `<i class="fas fa-exclamation-triangle"></i> Server Error`;
            statusDiv.className = 'status-disconnected';
        }
    };

    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const userPrompt = userInput.value.trim();
        if (!userPrompt) return;

        addMessage('user', userPrompt);
        userInput.value = '';
        userInput.style.height = 'auto';
        
        const loadingMessage = addMessage('loading', 'Agent is thinking...', 'loading-message');

        try {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ prompt: userPrompt }),
            });
            
            // Remove the loading message
            loadingMessage.remove();

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const steps = await response.json();
            steps.forEach(step => {
                addMessage(step.type, step.content);
            });
            
            // Final status update
            await updateConnectionStatus();

        } catch (error) {
            console.error('Error during chat:', error);
            loadingMessage.remove();
            addMessage('error', 'An error occurred while communicating with the agent.');
        }
    });

    resetButton.addEventListener('click', async () => {
        try {
            await fetch('/reset', { method: 'POST' });
            chatLog.innerHTML = '';
            addMessage('observation', 'Conversation history has been reset.');
            await updateConnectionStatus();
        } catch (error) {
            console.error('Error resetting conversation:', error);
            addMessage('error', 'Failed to reset conversation.');
        }
    });
    
    // Auto-resize textarea
    userInput.addEventListener('input', () => {
        userInput.style.height = 'auto';
        userInput.style.height = (userInput.scrollHeight) + 'px';
    });

    // Submit on Enter press
    userInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault(); // Prevent new line
            chatForm.dispatchEvent(new Event('submit', { cancelable: true }));
        }
    });

    // Initial status check
    updateConnectionStatus();
});