'use strict';
const messages = document.getElementById('messages');
const form = document.getElementById('chat-form');
const input = document.getElementById('message');
const send = document.getElementById('send');
const notice = document.getElementById('notice');
let sessionId = null;
let busy = false;
function bubble(text, role) {
  const node = document.createElement('div');
  node.className = 'bubble ' + role;
  node.textContent = text.replace(/\*\*(.*?)\*\*/gs, '$1'); // Plain text only; never render LLM HTML.
  messages.appendChild(node);
  messages.scrollTop = messages.scrollHeight;
  return node;
}
async function submit(question) {
  if (busy || !question.trim()) return;
  busy = true;
  send.disabled = true;
  input.disabled = true;
  bubble(question, 'user');
  const pending = bubble('Checking information...', 'assistant pending');
  notice.textContent = 'Waiting for a response';
  try {
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({message: question, session_id: sessionId})
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Agent request failed.');
    sessionId = data.session_id;
    pending.textContent = data.reply.replace(/\*\*(.*?)\*\*/gs, '$1');
    notice.textContent = 'Response received';
  } catch (error) {
    pending.textContent = 'Could not complete request: ' + error.message;
    notice.textContent = 'Request error';
  } finally {
    pending.classList.remove('pending');
    busy = false;
    send.disabled = false;
    input.disabled = false;
    input.focus();
  }
}
form.addEventListener('submit', event => {
  event.preventDefault();
  const value = input.value.trim();
  input.value = '';
  submit(value);
});
document.querySelectorAll('[data-question]').forEach(button => button.addEventListener('click', () => submit(button.dataset.question)));
document.getElementById('reset').addEventListener('click', () => {
  if (busy) return;
  sessionId = null;
  messages.replaceChildren();
  bubble('New conversation started. How can I help?', 'assistant');
  notice.textContent = 'Conversation history cleared';
});
