// Real-Time Query Communication & Chat Engine

document.addEventListener('DOMContentLoaded', () => {
  const chatContainer = document.getElementById('chatContainer');
  if (!chatContainer) return;

  const queryId = chatContainer.dataset.queryId;
  const currentUserId = parseInt(chatContainer.dataset.userId);
  const currentUserName = chatContainer.dataset.userName;
  const chatMessages = document.getElementById('chatMessages');
  const chatForm = document.getElementById('chatForm');
  const messageInput = document.getElementById('messageInput');
  const typingStatus = document.getElementById('typingStatus');

  // Scroll messages to bottom on initial load
  scrollToBottom();

  if (typeof io === 'undefined') return;

  const socket = io();

  // Join the query-specific chat room
  socket.emit('join_query', { query_id: queryId });

  // Listen for incoming chat messages
  socket.on('chat_message', (msg) => {
    appendMessage(msg, currentUserId);
    scrollToBottom();
  });

  // Listen for live status changes
  socket.on('status_update', (data) => {
    const statusBadge = document.getElementById('queryStatusBadge');
    if (statusBadge) {
      statusBadge.textContent = data.status;
      statusBadge.className = `badge badge-status-${data.status.toLowerCase().replace(/ /g, '-')}`;
    }
  });

  // Typing indicator broadcast
  let typingTimeout;
  if (messageInput) {
    messageInput.addEventListener('input', () => {
      socket.emit('typing_indicator', { query_id: queryId, user_name: currentUserName, is_typing: true });
      clearTimeout(typingTimeout);
      typingTimeout = setTimeout(() => {
        socket.emit('typing_indicator', { query_id: queryId, user_name: currentUserName, is_typing: false });
      }, 1500);
    });
  }

  socket.on('user_typing', (data) => {
    if (typingStatus) {
      if (data.is_typing) {
        typingStatus.textContent = `${data.user_name} is typing...`;
        typingStatus.style.display = 'block';
      } else {
        typingStatus.style.display = 'none';
      }
    }
  });

  // Handle Form Submission with AJAX
  if (chatForm) {
    chatForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const formData = new FormData(chatForm);
      const text = messageInput ? messageInput.value.trim() : '';

      if (!text && !formData.get('attachment')?.name) return;

      fetch(`/query/${queryId}/message`, {
        method: 'POST',
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
        body: formData
      })
      .then(res => res.json())
      .then(data => {
        if (data.status === 'success') {
          if (messageInput) messageInput.value = '';
          const attachInput = document.getElementById('chatAttachment');
          if (attachInput) attachInput.value = '';
          socket.emit('typing_indicator', { query_id: queryId, user_name: currentUserName, is_typing: false });
        }
      })
      .catch(err => {
        console.error('Message post error:', err);
        // Fallback to standard form submit if needed
        chatForm.submit();
      });
    });
  }

  function appendMessage(msg, myUserId) {
    const isMe = msg.sender_id === myUserId;
    const bubble = document.createElement('div');
    bubble.className = `message-bubble ${isMe ? 'sent' : 'received'} ${msg.is_internal_note ? 'internal-note' : ''}`;

    let roleBadge = `<span class="badge badge-sm badge-status-assigned">${msg.sender_role.toUpperCase()}</span>`;
    if (msg.sender_role === 'student') {
      roleBadge = `<span class="badge badge-sm badge-low">STUDENT</span>`;
    } else if (msg.sender_role === 'faculty') {
      roleBadge = `<span class="badge badge-sm badge-medium">FACULTY</span>`;
    }

    let attachmentHtml = '';
    if (msg.attachment_filename) {
      attachmentHtml = `
        <div style="margin-top: 8px; font-size: 0.8rem; background: rgba(0,0,0,0.05); padding: 6px 10px; border-radius: 6px;">
          📎 <a href="/uploads/${msg.attachment_path}" target="_blank" style="font-weight: 600; text-decoration: underline;">${msg.attachment_filename}</a>
        </div>
      `;
    }

    bubble.innerHTML = `
      <div class="message-meta">
        <strong>${msg.sender_name}</strong> ${roleBadge} <span>${msg.timeago}</span>
        ${msg.is_internal_note ? '<span class="badge badge-urgent">Internal Note</span>' : ''}
      </div>
      <div class="message-body">
        ${escapeHtml(msg.message)}
        ${attachmentHtml}
      </div>
    `;

    chatMessages.appendChild(bubble);
  }

  function scrollToBottom() {
    if (chatMessages) {
      chatMessages.scrollTop = chatMessages.scrollHeight;
    }
  }

  function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }
});
