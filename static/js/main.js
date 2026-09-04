// Main Portal UI, Animations & SocketIO Client Handling

document.addEventListener('DOMContentLoaded', () => {
  initSidebarToggle();
  initNotificationDropdown();
  initDemoAccountSwitcher();
  initClassifierPreview();
  initSocketGlobal();
  initCounterAnimations();
  initInteractiveElevations();
  initPushNotificationPermission();
});

/* Browser Web Push Notification Permission Handler */
function initPushNotificationPermission() {
  const banner = document.getElementById('pushNotificationBanner');
  const btnAllow = document.getElementById('btnAllowPush');
  const btnDeny = document.getElementById('btnDenyPush');

  if (!banner) return;

  // Immediately hide if notifications already granted/denied or previously dismissed
  if (!('Notification' in window) || Notification.permission !== 'default' || localStorage.getItem('dqm_push_prompt_dismissed') === 'true') {
    banner.style.display = 'none';
    return;
  }

  // Otherwise show the prompt banner
  banner.style.display = 'flex';

  if (btnAllow) {
    btnAllow.addEventListener('click', () => {
      banner.style.display = 'none';
      localStorage.setItem('dqm_push_prompt_dismissed', 'true');
      
      if ('Notification' in window) {
        Notification.requestPermission().then(permission => {
          banner.style.display = 'none';
          localStorage.setItem('dqm_push_prompt_dismissed', 'true');
          if (permission === 'granted') {
            showToastAlert('✅ Push Notifications enabled! You will receive live alerts.', 'info');
            triggerNativeNotification('🔔 Real-Time Alerts Activated', 'You will receive instant browser alerts for query replies and status updates.');
          }
        }).catch(() => {
          banner.style.display = 'none';
        });
      }
    });
  }

  if (btnDeny) {
    btnDeny.addEventListener('click', () => {
      banner.style.display = 'none';
      localStorage.setItem('dqm_push_prompt_dismissed', 'true');
    });
  }
}

/* Global Native Browser Notification Trigger */
function triggerNativeNotification(title, body, url = window.location.href) {
  if (!('Notification' in window) || Notification.permission !== 'granted') return;

  try {
    const notif = new Notification(title, {
      body: body,
      icon: '/static/img/icon.png', // optional icon
      badge: '/static/img/icon.png',
      tag: 'dqm-notification',
      vibrate: [200, 100, 200]
    });

    notif.onclick = function() {
      window.focus();
      if (url && url !== window.location.href) {
        window.location.href = url;
      }
      notif.close();
    };
  } catch (e) {
    console.log('Push notification display bypassed:', e);
  }
}

/* Global SocketIO Notifications for Department Staff & Online Presence */
function initSocketGlobal() {
  if (typeof io === 'undefined') return;

  const socket = io();
  const userRole = document.body.dataset.userRole;
  const userDept = document.body.dataset.userDept;
  const userId = document.body.dataset.userId;

  // Emit heartbeat presence if logged in
  if (userId) {
    socket.emit('user_presence_connect', { user_id: parseInt(userId) });
  }

  // If department staff, faculty or admin, join department room
  if ((userRole === 'staff' || userRole === 'admin' || userRole === 'faculty') && userDept) {
    socket.emit('join_department', { department: userDept });

    socket.on('new_query_alert', (data) => {
      showToastAlert(`🔴 New ${data.priority} Query: "${data.title}" by ${data.user_name}`, data.priority === 'Urgent' ? 'urgent' : 'info');
      triggerNativeNotification(`🔴 New ${data.priority} Query (${data.department})`, `${data.title} by ${data.user_name}`);
      
      // Update new query badge if on department dashboard
      const newQueryBadge = document.getElementById('statNewQueries');
      if (newQueryBadge) {
        let count = parseInt(newQueryBadge.textContent) || 0;
        newQueryBadge.textContent = count + 1;
      }
    });
  }
}

/* Toast Alert Notification System */
function showToastAlert(message, type = 'info') {
  let container = document.getElementById('toastContainer');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toastContainer';
    container.style.position = 'fixed';
    container.style.top = '20px';
    container.style.right = '20px';
    container.style.zIndex = '9999';
    container.style.display = 'flex';
    container.style.flexDirection = 'column';
    container.style.gap = '10px';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = `alert alert-${type === 'urgent' ? 'danger' : 'info'}`;
  toast.style.boxShadow = '0 10px 15px -3px rgba(0,0,0,0.15)';
  toast.style.minWidth = '280px';
  toast.style.maxWidth = '400px';
  toast.style.animation = 'fadeInUp 0.3s ease-out';
  toast.innerHTML = `<strong>Alert:</strong> ${message}`;

  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(20px)';
    toast.style.transition = 'all 0.3s ease-out';
    setTimeout(() => toast.remove(), 300);
  }, 5000);
}
function initSidebarToggle() {
  const sidebar = document.getElementById('appSidebar');
  const toggleBtn = document.getElementById('sidebarToggle');
  const closeBtn = document.getElementById('sidebarCloseBtn');
  const overlay = document.getElementById('sidebarOverlay');

  if (!sidebar) return;

  // Restore desktop collapsed state from storage
  const isCollapsed = localStorage.getItem('dqm_sidebar_collapsed') === 'true';
  if (window.innerWidth > 900 && isCollapsed) {
    sidebar.classList.add('collapsed');
  }

  function toggleSidebar() {
    if (window.innerWidth <= 900) {
      // Mobile drawer toggle
      sidebar.classList.toggle('open');
      if (overlay) overlay.classList.toggle('active', sidebar.classList.contains('open'));
    } else {
      // Desktop collapse toggle
      sidebar.classList.toggle('collapsed');
      localStorage.setItem('dqm_sidebar_collapsed', sidebar.classList.contains('collapsed'));
    }
  }

  function closeSidebar() {
    sidebar.classList.remove('open');
    if (window.innerWidth <= 900) {
      sidebar.classList.remove('collapsed');
    }
    if (overlay) overlay.classList.remove('active');
  }

  if (toggleBtn) {
    toggleBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      toggleSidebar();
    });
  }

  if (closeBtn) {
    closeBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      if (window.innerWidth <= 900) {
        closeSidebar();
      } else {
        sidebar.classList.add('collapsed');
        localStorage.setItem('dqm_sidebar_collapsed', 'true');
      }
    });
  }

  if (overlay) {
    overlay.addEventListener('click', closeSidebar);
  }

  // Close on Escape key
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      closeSidebar();
    }
  });
}

/* Number Count-Up Animation on Stat Cards */
function initCounterAnimations() {
  const statNumbers = document.querySelectorAll('.stat-info h3');
  statNumbers.forEach(el => {
    const rawText = el.textContent.trim();
    const cleanNum = parseInt(rawText.replace(/\D/g, ''));
    if (!isNaN(cleanNum) && cleanNum > 0) {
      let current = 0;
      const increment = Math.max(1, Math.ceil(cleanNum / 20));
      const suffix = rawText.includes('+') ? '+' : '';
      const timer = setInterval(() => {
        current += increment;
        if (current >= cleanNum) {
          current = cleanNum;
          clearInterval(timer);
        }
        el.textContent = current + suffix;
      }, 25);
    }
  });
}

/* Interactive Card & Button Elevations */
function initInteractiveElevations() {
  const statCards = document.querySelectorAll('.stat-card');
  statCards.forEach((card, idx) => {
    card.style.animationDelay = `${idx * 0.06}s`;
    card.classList.add('animate-fade-in-up');
  });
}

/* Notification Dropdown */
function initNotificationDropdown() {
  const notifBtn = document.getElementById('notifBtn');
  const notifDropdown = document.getElementById('notifDropdown');

  if (notifBtn && notifDropdown) {
    notifBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      notifDropdown.classList.toggle('show');
    });

    document.addEventListener('click', (e) => {
      if (!notifDropdown.contains(e.target) && !notifBtn.contains(e.target)) {
        notifDropdown.classList.remove('show');
      }
    });
  }
}

/* Quick 1-Click Demo Account Login Switcher */
function initDemoAccountSwitcher() {
  const demoButtons = document.querySelectorAll('.demo-account-btn');
  const emailInput = document.getElementById('email');
  const passwordInput = document.getElementById('password');

  if (demoButtons.length && emailInput && passwordInput) {
    demoButtons.forEach(btn => {
      btn.addEventListener('click', () => {
        const email = btn.dataset.email;
        const pass = btn.dataset.password;
        emailInput.value = email;
        passwordInput.value = pass;
        
        // Highlight inputs briefly with pulse
        emailInput.style.borderColor = '#4f46e5';
        passwordInput.style.borderColor = '#4f46e5';
        emailInput.style.boxShadow = '0 0 0 3px rgba(79, 70, 229, 0.2)';
        passwordInput.style.boxShadow = '0 0 0 3px rgba(79, 70, 229, 0.2)';
        setTimeout(() => {
          emailInput.style.borderColor = '';
          passwordInput.style.borderColor = '';
          emailInput.style.boxShadow = '';
          passwordInput.style.boxShadow = '';
        }, 800);
      });
    });
  }
}

/* Real-Time Debounced Query Classification Preview on /submit-query */
function initClassifierPreview() {
  const titleInput = document.getElementById('queryTitle');
  const descInput = document.getElementById('queryDesc');
  const previewBox = document.getElementById('aiPreviewBox');

  if (!titleInput || !descInput || !previewBox) return;

  const deptBadge = document.getElementById('previewDept');
  const catBadge = document.getElementById('previewCat');
  const prioBadge = document.getElementById('previewPrio');
  const confText = document.getElementById('previewConf');
  const reasonText = document.getElementById('previewReason');

  let debounceTimer;

  function updatePreview() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      const title = titleInput.value.trim();
      const description = descInput.value.trim();

      if (!title && !description) {
        previewBox.style.display = 'none';
        return;
      }

      fetch('/api/classify-preview', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, description })
      })
      .then(res => res.json())
      .then(data => {
        previewBox.style.display = 'block';
        if (deptBadge) deptBadge.textContent = data.department;
        if (catBadge) catBadge.textContent = data.category;
        if (prioBadge) {
          prioBadge.textContent = data.priority;
          prioBadge.className = `badge badge-${data.priority.toLowerCase()}`;
        }
        if (confText) confText.textContent = `${Math.round(data.confidence * 100)}% Confidence`;
        if (reasonText) reasonText.textContent = data.explanation;
      })
      .catch(err => console.error('Classifier preview error:', err));
    }, 300);
  }

  titleInput.addEventListener('input', updatePreview);
  descInput.addEventListener('input', updatePreview);
}


