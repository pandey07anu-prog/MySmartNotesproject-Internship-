/**
 * Smart Notes Assistant - Work & Deadline Notification Hub
 * Handles smart task detection ("You have to complete this work"),
 * real-time reminders, Web Audio API chimes, and browser push notifications.
 */

const Notifications = {
  isOpen: false,
  activeFilter: 'action', // 'action' | 'upcoming' | 'ai' | 'done' | 'all'
  chimeEnabled: localStorage.getItem('notif_sound_enabled') !== 'false',
  audioCtx: null,

  // Initialize
  init() {
    this.updateBadge();
    // Re-check periodically every 60 seconds for due tasks
    setInterval(() => {
      this.updateBadge();
      this.checkAndFireDueAlerts();
    }, 60000);

    // Close flyout on outside click
    document.addEventListener('click', (e) => {
      const wrapper = document.getElementById('notif-dropdown-wrapper');
      if (this.isOpen && wrapper && !wrapper.contains(e.target)) {
        this.closeFlyout();
      }
    });
  },

  // Toggle Flyout dropdown
  toggleFlyout(e) {
    if (e) e.stopPropagation();
    this.isOpen = !this.isOpen;
    const flyout = document.getElementById('notif-flyout');
    const bellBtn = document.getElementById('notif-bell-btn');
    if (flyout) {
      if (this.isOpen) {
        flyout.classList.add('active');
        if (bellBtn) bellBtn.classList.add('active');
        this.renderFlyoutContent();
      } else {
        flyout.classList.remove('active');
        if (bellBtn) bellBtn.classList.remove('active');
      }
    }
  },

  closeFlyout() {
    this.isOpen = false;
    const flyout = document.getElementById('notif-flyout');
    const bellBtn = document.getElementById('notif-bell-btn');
    if (flyout) flyout.classList.remove('active');
    if (bellBtn) bellBtn.classList.remove('active');
  },

  setFilter(filter) {
    this.activeFilter = filter;
    this.renderFlyoutContent();
  },

  // Synthesize a pleasant Apple-style chime using Web Audio API (0 dependencies)
  playChime() {
    if (!this.chimeEnabled) return;
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (!AudioCtx) return;
      if (!this.audioCtx || this.audioCtx.state === 'closed') {
        this.audioCtx = new AudioCtx();
      }
      if (this.audioCtx.state === 'suspended') {
        this.audioCtx.resume();
      }

      const now = this.audioCtx.currentTime;
      const notes = [
        { freq: 523.25, time: 0.00, dur: 0.12 }, // C5
        { freq: 659.25, time: 0.09, dur: 0.14 }, // E5
        { freq: 783.99, time: 0.18, dur: 0.35 }  // G5
      ];

      notes.forEach(n => {
        const osc = this.audioCtx.createOscillator();
        const gain = this.audioCtx.createGain();
        osc.type = 'sine';
        osc.frequency.setValueAtTime(n.freq, now + n.time);

        gain.gain.setValueAtTime(0, now + n.time);
        gain.gain.linearRampToValueAtTime(0.18, now + n.time + 0.02);
        gain.gain.exponentialRampToValueAtTime(0.0001, now + n.time + n.dur);

        osc.connect(gain);
        gain.connect(this.audioCtx.destination);

        osc.start(now + n.time);
        osc.stop(now + n.time + n.dur);
      });
    } catch (e) {
      console.warn('Audio chime error:', e);
    }
  },

  toggleSound() {
    this.chimeEnabled = !this.chimeEnabled;
    localStorage.setItem('notif_sound_enabled', this.chimeEnabled ? 'true' : 'false');
    if (this.chimeEnabled) {
      this.playChime();
      App.showToast('🔔 Notification chime enabled', 'success');
    } else {
      App.showToast('🔕 Notification chime muted', 'info');
    }
    this.renderFlyoutContent();
  },

  // Browser Native Push Notifications Request
  async requestDesktopPermission() {
    if (!('Notification' in window)) {
      App.showToast('Desktop notifications not supported in this browser.', 'error');
      return;
    }

    if (Notification.permission === 'granted') {
      this.sendDesktopNotification(
        '🔔 Smart Notes Notifications Active',
        'You will receive reminders when work deadlines are approaching!'
      );
      App.showToast('Desktop alerts already enabled.', 'success');
      this.renderFlyoutContent();
      return;
    }

    try {
      const perm = await Notification.requestPermission();
      if (perm === 'granted') {
        this.sendDesktopNotification(
          '🔔 Notifications Enabled!',
          'Smart Notes Assistant will alert you when you have pending work to complete.'
        );
        App.showToast('Desktop alerts enabled successfully!', 'success');
      } else {
        App.showToast('Notification permission denied.', 'info');
      }
    } catch (err) {
      console.warn(err);
    }
    this.renderFlyoutContent();
  },

  sendDesktopNotification(title, body, noteId = null) {
    if (!('Notification' in window) || Notification.permission !== 'granted') return;
    try {
      const notif = new Notification(title, {
        body,
        icon: '/favicon.ico',
        badge: '/favicon.ico'
      });
      notif.onclick = () => {
        window.focus();
        if (noteId) {
          window.location.hash = '#notes';
          setTimeout(() => {
            const card = document.getElementById(`note-card-${noteId}`);
            if (card) {
              card.scrollIntoView({ behavior: 'smooth', block: 'center' });
              card.style.outline = '2px solid var(--purple-vibrant)';
              setTimeout(() => card.style.outline = 'none', 3000);
            }
          }, 300);
        }
      };
    } catch (e) {
      console.warn('Failed to send desktop notification:', e);
    }
  },

  // Gather & Classify All Notes Into Actionable Work Items
  getWorkNotifications() {
    const pool = (window.App && App.allUserNotes && App.allUserNotes.length > 0)
      ? App.allUserNotes
      : (window.App && App.notes) || [];

    const now = new Date();
    const nowMs = now.getTime();
    const actionItems = [];
    const upcomingItems = [];
    const completedItems = [];
    const aiNudges = [];

    // Helper: Detect action phrasing in note text
    const actionPattern = /\b(have to|need to|must|submit|pay|buy|book|call|finish|complete|prepare|send|order|clean|due|assignment|exam|project|bill|flight|hotel|ticket)\b/i;

    pool.forEach(n => {
      const isDone = localStorage.getItem('note_done_' + n.note_id) === 'true';
      const isSnoozed = (() => {
        const s = localStorage.getItem('notif_snooze_' + n.note_id);
        return s && Number(s) > nowMs;
      })();

      const customDueStr = localStorage.getItem('note_due_' + n.note_id);
      let dueDate = null;
      let diffHours = null;
      let isOverdue = false;
      let isDueToday = false;

      if (customDueStr) {
        dueDate = new Date(customDueStr);
        if (!isNaN(dueDate.getTime())) {
          const diffMs = dueDate.getTime() - nowMs;
          diffHours = diffMs / (1000 * 60 * 60);
          isOverdue = diffMs < 0;
          isDueToday = diffHours >= 0 && diffHours <= 24;
        }
      }

      // Check text-based urgency keywords
      const textLower = (n.text || '').toLowerCase();
      const hasActionVerb = actionPattern.test(n.text || '');
      const hasTodayKw = textLower.includes('today') || textLower.includes('tonight') || textLower.includes('urgent') || textLower.includes('asap');
      const hasTomorrowKw = textLower.includes('tomorrow') || textLower.includes('tmrw');

      const prio = window.App && App.getTimePriority ? App.getTimePriority(n) : { level: 'normal' };
      const isHighPriority = prio.level === 'high';

      // Clean up text snippet into an actionable pitch
      let workPitch = n.text;
      if (hasActionVerb) {
        workPitch = n.text.replace(/^(i\s+have\s+to|i\s+need\s+to|i\s+must)\s+/i, '');
        workPitch = workPitch.charAt(0).toUpperCase() + workPitch.slice(1);
      }

      const item = {
        note_id: n.note_id,
        text: n.text,
        workPitch,
        category: n.category,
        uncertain: n.uncertain,
        dueDate,
        diffHours,
        isOverdue,
        isDueToday,
        isDone,
        isSnoozed,
        isHighPriority,
        relativeTime: prio.relativeTime || 'Recent'
      };

      if (isDone) {
        completedItems.push(item);
        return;
      }

      if (isSnoozed) return;

      // Classify as Action Required (Urgent Today / Overdue / High Priority)
      if (isOverdue || isDueToday || hasTodayKw || isHighPriority || (hasActionVerb && !hasTomorrowKw)) {
        actionItems.push({
          ...item,
          urgencyBadge: isOverdue ? '⚠️ Overdue' : isDueToday ? '🔥 Due Today' : '⚡ Action Required',
          urgencyClass: isOverdue ? 'overdue' : 'urgent'
        });
      } else {
        // Upcoming
        upcomingItems.push({
          ...item,
          urgencyBadge: hasTomorrowKw ? '⚡ Due Tomorrow' : '📅 Scheduled',
          urgencyClass: 'upcoming'
        });
      }

      // AI Smart Nudge if note is uncertain
      if (n.uncertain) {
        aiNudges.push({
          note_id: n.note_id,
          title: 'Review Machine Learning Prediction',
          desc: `Note #${n.note_id} "${n.text.substring(0, 35)}..." has low confidence (${Math.round((n.confidence || 0) * 100)}%). Confirm or edit category.`,
          type: 'review'
        });
      }
    });

    // Milestone AI Nudge
    if (pool.length > 0) {
      aiNudges.push({
        note_id: null,
        title: 'Productivity Habit Streak 🔥',
        desc: `You have ${pool.length} total organized notes in your workspace. Keep up your active momentum!`,
        type: 'streak'
      });
    }

    return {
      action: actionItems,
      upcoming: upcomingItems,
      completed: completedItems,
      ai: aiNudges,
      totalActiveUrgent: actionItems.length
    };
  },

  // Update Bell Badge Count & Pulsing Animation
  updateBadge() {
    const data = this.getWorkNotifications();
    const badge = document.getElementById('notif-count-badge');
    const bellBtn = document.getElementById('notif-bell-btn');
    const count = data.action.length;

    if (badge) {
      badge.innerText = count > 9 ? '9+' : count;
      if (count > 0) {
        badge.style.display = 'inline-flex';
        badge.classList.add('has-urgent');
      } else {
        badge.style.display = 'none';
        badge.classList.remove('has-urgent');
      }
    }

    if (bellBtn) {
      if (count > 0) {
        bellBtn.classList.add('pulse-urgent');
      } else {
        bellBtn.classList.remove('pulse-urgent');
      }
    }

    // Refresh Dashboard Urgent Banner if visible
    this.refreshDashboardBanner(data);
  },

  // Complete Task Action
  completeTask(noteId, e) {
    if (e) e.stopPropagation();
    localStorage.setItem('note_done_' + noteId, 'true');
    this.playChime();
    App.showToast('🎉 Work marked completed! Great job.', 'success');
    this.updateBadge();
    this.renderFlyoutContent();

    // Re-render notes view or dashboard if active to show strikethrough/checkbox update
    if (window.App && (App.currentView === 'notes' || App.currentView === 'dashboard')) {
      App.render();
    }
  },

  // Undo / Re-activate Task Action
  uncompleteTask(noteId, e) {
    if (e) e.stopPropagation();
    localStorage.removeItem('note_done_' + noteId);
    App.showToast('Note re-activated.', 'info');
    this.updateBadge();
    this.renderFlyoutContent();
    if (window.App && (App.currentView === 'notes' || App.currentView === 'dashboard')) {
      App.render();
    }
  },

  // Snooze Task for 2 hours
  snoozeTask(noteId, e) {
    if (e) e.stopPropagation();
    const twoHoursFromNow = Date.now() + (2 * 60 * 60 * 1000);
    localStorage.setItem('notif_snooze_' + noteId, twoHoursFromNow.toString());
    App.showToast('⏱️ Reminder snoozed for 2 hours.', 'info');
    this.updateBadge();
    this.renderFlyoutContent();
  },

  // Open note in library and highlight it
  jumpToNote(noteId, e) {
    if (e) e.stopPropagation();
    this.closeFlyout();
    window.location.hash = '#notes';
    setTimeout(() => {
      const card = document.getElementById(`note-card-${noteId}`);
      if (card) {
        card.scrollIntoView({ behavior: 'smooth', block: 'center' });
        card.style.boxShadow = '0 0 0 3px var(--purple-vibrant), 0 8px 24px rgba(108, 82, 238, 0.4)';
        setTimeout(() => card.style.boxShadow = '', 2500);
      }
    }, 200);
  },

  // Periodic check to fire native browser alerts when tasks are due
  checkAndFireDueAlerts() {
    if (!('Notification' in window) || Notification.permission !== 'granted') return;
    const data = this.getWorkNotifications();
    const overdueOrToday = data.action.filter(a => a.isOverdue || a.isDueToday);

    if (overdueOrToday.length > 0) {
      const lastFired = Number(localStorage.getItem('notif_last_fired_time') || 0);
      // Fire at most once every 30 minutes to avoid spam
      if (Date.now() - lastFired > 30 * 60 * 1000) {
        localStorage.setItem('notif_last_fired_time', Date.now().toString());
        const top = overdueOrToday[0];
        this.sendDesktopNotification(
          '⚡ You have work to complete today!',
          `"You have to complete: ${top.workPitch}"`,
          top.note_id
        );
      }
    }
  },

  // Render Flyout Content
  renderFlyoutContent() {
    const container = document.getElementById('notif-flyout');
    if (!container) return;

    const data = this.getWorkNotifications();
    const hasDesktopPermission = ('Notification' in window) && Notification.permission === 'granted';

    let displayList = [];
    if (this.activeFilter === 'action') displayList = data.action;
    else if (this.activeFilter === 'upcoming') displayList = data.upcoming;
    else if (this.activeFilter === 'done') displayList = data.completed;
    else if (this.activeFilter === 'all') displayList = [...data.action, ...data.upcoming];

    container.innerHTML = `
      <div class="notif-flyout-header">
        <div style="display:flex; align-items:center; gap:8px;">
          <div class="notif-header-title">🔔 Work &amp; Reminders</div>
          <span class="notif-count-pill">${data.action.length} Urgent</span>
        </div>
        <div class="notif-header-controls">
          <button class="notif-sound-btn ${this.chimeEnabled ? 'active' : ''}" onclick="Notifications.toggleSound()" title="${this.chimeEnabled ? 'Mute Chime Sound' : 'Enable Chime Sound'}">
            ${this.chimeEnabled ? '🔊 Sound On' : '🔇 Muted'}
          </button>
          <button class="notif-desktop-btn ${hasDesktopPermission ? 'granted' : ''}" onclick="Notifications.requestDesktopPermission()" title="Enable Desktop Browser Notifications">
            ${hasDesktopPermission ? '📢 Desktop Alerts: On' : '📢 Enable Desktop Alerts'}
          </button>
        </div>
      </div>

      <!-- Category Filter Tabs -->
      <div class="notif-tabs">
        <button class="notif-tab ${this.activeFilter === 'action' ? 'active' : ''}" onclick="Notifications.setFilter('action')">
          🚨 Action Required (${data.action.length})
        </button>
        <button class="notif-tab ${this.activeFilter === 'upcoming' ? 'active' : ''}" onclick="Notifications.setFilter('upcoming')">
          ⏰ Upcoming (${data.upcoming.length})
        </button>
        <button class="notif-tab ${this.activeFilter === 'ai' ? 'active' : ''}" onclick="Notifications.setFilter('ai')">
          💡 AI Nudges (${data.ai.length})
        </button>
        <button class="notif-tab ${this.activeFilter === 'done' ? 'active' : ''}" onclick="Notifications.setFilter('done')">
          ✅ Done (${data.completed.length})
        </button>
      </div>

      <!-- Notifications Scroll Area -->
      <div class="notif-list-area">
        ${this.activeFilter === 'ai' ? `
          <div class="notif-ai-list">
            ${data.ai.map(a => `
              <div class="notif-card notif-ai-card">
                <div class="notif-card-header">
                  <span class="notif-badge-pill ai">✨ Smart Nudge</span>
                </div>
                <div class="notif-card-title">${a.title}</div>
                <div class="notif-card-desc">${a.desc}</div>
                ${a.note_id ? `
                  <div class="notif-actions">
                    <button class="btn btn-sm btn-primary notif-action-btn" onclick="Notifications.jumpToNote('${a.note_id}', event)">
                      Review Note #${a.note_id}
                    </button>
                  </div>
                ` : ''}
              </div>
            `).join('')}
          </div>
        ` : displayList.length === 0 ? `
          <div class="notif-empty-state">
            <div class="notif-empty-icon">${this.activeFilter === 'done' ? '📋' : '🎉'}</div>
            <div class="notif-empty-title">
              ${this.activeFilter === 'done' ? 'No completed tasks yet' : 'All caught up! No pending work.'}
            </div>
            <div class="notif-empty-sub">
              ${this.activeFilter === 'done' ? 'Tasks you mark as done will appear here with 1-click undo.' : 'Write notes with action phrases like "have to", "pay", or set a due date to get smart alerts!'}
            </div>
          </div>
        ` : `
          <div class="notif-cards-list">
            ${displayList.map(item => `
              <div class="notif-card ${item.urgencyClass || ''} ${item.isDone ? 'is-done' : ''}">
                <div class="notif-card-header">
                  <div style="display:flex; align-items:center; gap:6px;">
                    <span class="notif-cat-tag cat-${item.category.toLowerCase()}">${item.category}</span>
                    <span class="notif-badge-pill ${item.urgencyClass}">${item.urgencyBadge || 'Work Task'}</span>
                  </div>
                  <span class="notif-time-text">${item.relativeTime}</span>
                </div>

                <div class="notif-pitch-block" onclick="Notifications.jumpToNote('${item.note_id}', event)">
                  <div class="notif-work-lead">👉 You have to complete this work:</div>
                  <div class="notif-work-body">${App.escapeHtml(item.workPitch)}</div>
                </div>

                <div class="notif-actions-row">
                  ${!item.isDone ? `
                    <button class="notif-btn complete-btn" onclick="Notifications.completeTask('${item.note_id}', event)">
                      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"></polyline></svg>
                      <span>Mark Complete</span>
                    </button>
                    <button class="notif-btn snooze-btn" onclick="Notifications.snoozeTask('${item.note_id}', event)" title="Snooze reminder for 2 hours">
                      ⏱️ Snooze 2h
                    </button>
                    <button class="notif-btn view-btn" onclick="Notifications.jumpToNote('${item.note_id}', event)" title="Open Note in Library">
                      ↗ Note #${item.note_id}
                    </button>
                  ` : `
                    <span style="font-size:12px; color:#059669; font-weight:600; display:inline-flex; align-items:center; gap:4px;">
                      ✅ Completed
                    </span>
                    <button class="notif-btn view-btn" onclick="Notifications.uncompleteTask('${item.note_id}', event)" style="margin-left:auto;">
                      ↩ Re-open Task
                    </button>
                  `}
                </div>
              </div>
            `).join('')}
          </div>
        `}
      </div>

      <div class="notif-flyout-footer">
        <span style="font-size:11.5px; color:var(--text-muted);">
          ⚡ Auto-detects urgency from deadlines &amp; keywords
        </span>
        <button class="notif-footer-link" onclick="Notifications.jumpToAllNotes()">
          View Notes Library →
        </button>
      </div>
    `;
  },

  jumpToAllNotes() {
    this.closeFlyout();
    window.location.hash = '#notes';
  },

  // Refresh floating banner on Dashboard
  refreshDashboardBanner(data) {
    const bannerContainer = document.getElementById('dashboard-urgent-banner-slot');
    if (!bannerContainer) return;

    if (!data) data = this.getWorkNotifications();

    if (data.action.length === 0) {
      bannerContainer.innerHTML = '';
      return;
    }

    const topTask = data.action[0];
    bannerContainer.innerHTML = `
      <div class="dashboard-work-banner animate-slide-in">
        <div class="work-banner-left">
          <div class="work-banner-bell-icon">⚡</div>
          <div class="work-banner-text-group">
            <div class="work-banner-lead">
              <strong>Action Required:</strong> You have to complete this work today!
            </div>
            <div class="work-banner-task-title">
              "${App.escapeHtml(topTask.workPitch)}"
            </div>
            <div class="work-banner-meta">
              <span class="badge ${'badge-' + topTask.category.toLowerCase()}" style="font-size:10px; padding:1px 6px;">${topTask.category}</span>
              ${data.action.length > 1 ? `<span class="work-more-count">+${data.action.length - 1} other tasks pending</span>` : ''}
            </div>
          </div>
        </div>

        <div class="work-banner-actions">
          <button class="btn btn-sm btn-primary" onclick="Notifications.completeTask('${topTask.note_id}')" title="Mark this task done">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"></polyline></svg>
            <span>Complete Work</span>
          </button>
          <button class="btn btn-sm btn-secondary" onclick="Notifications.toggleFlyout(event)">
            <span>View All (${data.action.length})</span>
          </button>
        </div>
      </div>
    `;
  }
};

window.Notifications = Notifications;

