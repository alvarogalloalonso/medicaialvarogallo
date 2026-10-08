/* Lógica del Chat del Paciente */

let ws = null;
let currentSessionId = null;
let currentMessageDiv = null;
let reconnectAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 5;
const RECONNECT_BASE_DELAY = 1000; // 1 segundo

// DOM Elements
const messagesArea = document.getElementById('messagesArea');
const chatInput = document.getElementById('chatInput');
const sendBtn = document.getElementById('sendBtn');
const typingIndicator = document.getElementById('typingIndicator');
const statusBanner = document.getElementById('statusBanner');
const endSessionBtn = document.getElementById('endSessionBtn');
const finishBanner = document.getElementById('finishBanner');
const newSessionBtn = document.getElementById('newSessionBtn');

function connectWebSocket() {
    // Determine WS URL based on current host
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host || 'localhost:8000';
    const wsUrl = `${protocol}//${host}/ws/chat`;

    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        reconnectAttempts = 0; // Reset counter on successful connection
        statusBanner.textContent = 'Conectado al prototipo local';
        statusBanner.style.background = 'rgba(16, 185, 129, 0.1)';
        statusBanner.style.color = 'var(--success)';
        setTimeout(() => statusBanner.classList.remove('active'), 2000);
        
        chatInput.disabled = false;
        sendBtn.disabled = false;
    };

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleServerMessage(data);
    };

    ws.onclose = (event) => {
        // Don't reconnect if session was completed normally (report_ready closes ws)
        if (finishBanner.classList.contains('active')) {
            return;
        }

        chatInput.disabled = true;
        sendBtn.disabled = true;

        if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
            reconnectAttempts++;
            const delay = RECONNECT_BASE_DELAY * Math.pow(2, reconnectAttempts - 1); // Exponential backoff
            statusBanner.textContent = `Conexión perdida. Reconectando en ${Math.round(delay/1000)}s... (intento ${reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS})`;
            statusBanner.style.background = 'rgba(245, 158, 11, 0.1)';
            statusBanner.style.color = 'var(--warning)';
            statusBanner.classList.add('active');

            setTimeout(() => {
                connectWebSocket();
            }, delay);
        } else {
            statusBanner.textContent = 'No se pudo reconectar. Actualiza la página para iniciar una nueva sesión.';
            statusBanner.style.background = 'rgba(239, 68, 68, 0.1)';
            statusBanner.style.color = 'var(--danger)';
            statusBanner.classList.add('active');
        }
    };
    
    ws.onerror = (err) => {
        console.error('WebSocket Error:', err);
    };
}

function handleServerMessage(data) {
    switch (data.type) {
        case 'session_start':
            currentSessionId = data.session_id;
            break;
            
        case 'message':
            typingIndicator.classList.remove('active');
            addMessage(data.content, data.role);
            break;
            
        case 'thinking':
            typingIndicator.classList.add('active');
            scrollToBottom('messagesArea');
            break;
            
        case 'token':
            typingIndicator.classList.remove('active');
            if (!currentMessageDiv) {
                currentMessageDiv = createMessageDiv('assistant');
                messagesArea.insertBefore(currentMessageDiv, typingIndicator);
            }
            
            currentMessageDiv.textContent += data.content;
            scrollToBottom('messagesArea');
            break;
            
        case 'stream_end':
            if (currentMessageDiv) {
                currentMessageDiv = null;
            }
            scrollToBottom('messagesArea');
            break;
            
        case 'can_finalize':
            endSessionBtn.style.display = 'inline-flex';
            endSessionBtn.classList.add('fade-in');
            break;
            
        case 'status':
            statusBanner.textContent = data.message;
            statusBanner.classList.add('active');
            break;
            
        case 'report_ready':
            statusBanner.classList.remove('active');
            finishBanner.classList.add('active');
            endSessionBtn.style.display = 'none';
            chatInput.disabled = true;
            sendBtn.disabled = true;
            ws.close();
            break;
            
        case 'error':
            alert(`Error: ${data.message}`);
            typingIndicator.classList.remove('active');
            break;
    }
}

function addMessage(content, role) {
    const div = createMessageDiv(role);
    div.textContent = content;
    div.style.whiteSpace = 'pre-wrap';
    messagesArea.insertBefore(div, typingIndicator);
    scrollToBottom('messagesArea');
}

function createMessageDiv(role) {
    const div = document.createElement('div');
    div.className = `message ${role} fade-in`;
    return div;
}

function sendMessage() {
    const text = chatInput.value.trim();
    if (!text || !ws || ws.readyState !== WebSocket.OPEN) return;

    // Remove markdown for UI display of user message
    addMessage(text, 'user');
    
    ws.send(JSON.stringify({
        type: 'message',
        message: text
    }));

    chatInput.value = '';
    chatInput.focus();
}

// Event Listeners
sendBtn.addEventListener('click', sendMessage);

chatInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

endSessionBtn.addEventListener('click', () => {
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    
    if (confirm('¿Estás seguro de que deseas finalizar la entrevista y enviar los datos al doctor?')) {
        ws.send(JSON.stringify({ type: 'finalize' }));
        chatInput.disabled = true;
        sendBtn.disabled = true;
        endSessionBtn.disabled = true;
    }
});

newSessionBtn.addEventListener('click', () => {
    window.location.reload();
});

// Auto-resize textarea
chatInput.addEventListener('input', function() {
    this.style.height = 'auto';
    this.style.height = (this.scrollHeight) + 'px';
    if (this.value === '') {
        this.style.height = 'auto';
    }
});

// Inicializar
window.addEventListener('DOMContentLoaded', async () => {
    statusBanner.classList.add('active');
    try {
        const health = await fetch('/api/health').then(r => r.json());
        statusBanner.textContent = health.demo_mode ? 'Demo offline: selecciona un caso ficticio. No se usa LLM ni ML.' : 'Modo experimental: utiliza solo información ficticia.';
        const cases = await fetch('/api/demo/cases').then(r => r.json());
        const panel = document.getElementById('demoCases');
        cases.cases.forEach(example => {
            const button = document.createElement('button');
            button.className = 'btn btn-outline';
            button.textContent = example.label;
            button.addEventListener('click', async () => {
                button.disabled = true;
                try {
                    const response = await fetch(`/api/demo/${example.id}`, {method: 'POST'});
                    if (!response.ok) throw new Error('No se pudo generar el caso');
                    const report = await response.json();
                    addMessage(example.text, 'user');
                    addMessage(report.clinical_summary, 'assistant');
                    const link = document.createElement('a');
                    link.href = `/doctor#${report.report_id}`;
                    link.textContent = 'Ver el informe de este caso ficticio';
                    messagesArea.insertBefore(link, typingIndicator);
                } catch (error) { statusBanner.textContent = error.message; }
                finally { button.disabled = false; }
            });
            panel.appendChild(button);
        });
        if (!health.demo_mode) connectWebSocket();
    } catch (error) { statusBanner.textContent = 'No se pudo conectar al backend local.'; }
});

