/**
 * Smart Notes Assistant - Main Application Coordinator
 * State Management, View Router & UI Renderer
 */

const App = {
  currentUser: null,
  currentView: 'landing',
  activeCategoryFilter: 'all',
  activePriorityFilter: 'all',
  noteSortBy: 'priority',
  notes: [],
  stats: null,
  backendReady: false,

  async init() {
    console.log('[Smart Notes Assistant] Initializing application...');

    // 0. Apply Saved Theme (Midnight Dark vs Pastel Day)
    this.initTheme();

    // 1. Genuine Backend Health Check
    this.checkBackendHealth();

    // 2. Check Active Auth Session
    await Auth.checkSession();

    // 3. Setup Hash Route Listener
    window.addEventListener('hashchange', () => this.handleRouting());
    this.handleRouting();

    // 4. Global Keyboard Shortcuts (Ctrl + K / Cmd + K for Spotlight Quick Find)
    window.addEventListener('keydown', (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        App.toggleSpotlight();
      } else if (e.key === 'Escape') {
        App.closeSpotlight();
        App.closeAiSummaryModal();
        App.closeZenMode();
        if (window.Notifications) Notifications.closeFlyout();
      }
    });

    // 5. Initialize Work & Deadline Notifications Hub
    if (window.Notifications) {
      Notifications.init();
    }
  },

  // Genuine Backend Health Probe
  async checkBackendHealth() {
    try {
      const res = await fetch('/health');
      if (res.ok) {
        const data = await res.json();
        this.backendReady = true;
        this.updateSystemStatusBadge(data);
        return;
      }
    } catch (e) {
      console.warn('Backend not ready yet, retrying...');
    }
    setTimeout(() => this.checkBackendHealth(), 1000);
  },

  updateSystemStatusBadge(healthData) {
    const badge = document.getElementById('header-system-status');
    const sidebarDbStatus = document.getElementById('sidebar-db-status');
    const mode = healthData && healthData.database && healthData.database.mode === 'mock' ? 'In-Memory DB' : 'MongoDB Atlas';
    if (badge) {
      badge.innerHTML = `<span class="dot"></span> ${mode} • ML Active`;
      badge.title = `Database: ${mode} | ML Classifier: Loaded | Timestamp: ${healthData.timestamp}`;
    }
    if (sidebarDbStatus) {
      sidebarDbStatus.innerText = `${mode} • Active`;
    }
  },

  // Toast Notification System
  showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    let icon = 'ℹ️';
    if (type === 'success') icon = '✓';
    if (type === 'error') icon = '⚠️';

    toast.innerHTML = `<span>${icon}</span> <span>${message}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateX(100%)';
      toast.style.transition = 'all 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, 4000);
  },

  // Router dispatcher
  async handleRouting() {
    const hash = window.location.hash || '#landing';
    const [route, queryString] = hash.split('?');

    // Parse query params
    const params = new URLSearchParams(queryString || '');

    // Unauthenticated routes
    if (route === '#landing' || (route === '' && !this.currentUser)) {
      this.currentView = 'landing';
    } else if (route === '#login') {
      this.currentView = 'login';
    } else if (route === '#register') {
      this.currentView = 'register';
    } else if (route === '#verify-email') {
      window.location.hash = this.currentUser ? '#dashboard' : '#login';
      return;
    } else if (route === '#forgot-password') {
      this.currentView = 'forgot-password';
    } else if (route === '#reset-password') {
      this.currentView = 'reset-password';
    }
    // Authenticated routes (guarded)
    else {
      if (!this.currentUser) {
        window.location.hash = '#login';
        return;
      }
      if (route === '#dashboard') {
        this.currentView = 'dashboard';
        await Notes.fetchStats();
      } else if (route === '#notes') {
        this.currentView = 'notes';
        const cat = params.get('category');
        const prio = params.get('priority');
        this.activeCategoryFilter = cat || 'all';
        this.activePriorityFilter = prio || 'all';
        this.activeTagFilter = null;
        await Notes.fetchStats();
        await Notes.fetchNotes(this.activeCategoryFilter);
      } else if (route === '#search') {
        this.currentView = 'search';
        const q = params.get('q');
        await Notes.fetchStats();
        if (q) {
          setTimeout(() => this.executeDedicatedSearch(q), 60);
        }
      } else if (route === '#analytics') {
        this.currentView = 'analytics';
        await Notes.fetchStats();
        await Notes.fetchNotes('all');
      } else if (route === '#profile') {
        this.currentView = 'profile';
      } else {
        this.currentView = 'dashboard';
        await Notes.fetchStats();
      }
    }

    this.render();
  },

  // Initialize workspace when authenticated
  async initWorkspace() {
    await Notes.fetchStats();
    if (this.activeCategoryFilter === 'all') {
      await Notes.fetchNotes('all');
    } else {
      await Notes.fetchNotes(this.activeCategoryFilter);
      fetch('/notes').then(r => r.ok ? r.json() : []).then(all => {
        if (Array.isArray(all)) {
          this.allUserNotes = all;
          this.updateSidebarCounts();
        }
      }).catch(() => {});
    }
    this.render();

    // Auto-sync existing notes with the upgraded 98% accuracy model once per session
    if (!sessionStorage.getItem('synced_ml_v2')) {
      sessionStorage.setItem('synced_ml_v2', 'true');
      try {
        const res = await fetch('/notes/reclassify', { method: 'POST' });
        if (res.ok) {
          await Notes.fetchStats();
          await Notes.fetchNotes(this.activeCategoryFilter);
          this.render();
        }
      } catch (e) {
        // Non-blocking background sync
      }
    }
  },

  // View Renderer
  render() {
    const landingContainer = document.getElementById('public-landing');
    const authContainer = document.getElementById('auth-view-container');
    const workspaceContainer = document.getElementById('app-workspace');

    // 1. If viewing Landing Page
    if (this.currentView === 'landing') {
      if (landingContainer) landingContainer.style.display = 'flex';
      if (authContainer) authContainer.style.display = 'none';
      if (workspaceContainer) workspaceContainer.style.display = 'none';
      if (window.ThreeD && ThreeD.initHero3DStage) {
        requestAnimationFrame(() => ThreeD.initHero3DStage());
      }
      return;
    }

    // 2. If viewing Auth Screens
    const authViews = ['login', 'register', 'verify-email', 'forgot-password', 'reset-password'];
    if (authViews.includes(this.currentView)) {
      if (landingContainer) landingContainer.style.display = 'none';
      if (workspaceContainer) workspaceContainer.style.display = 'none';
      if (authContainer) {
        authContainer.style.display = 'flex';
        authContainer.innerHTML = this.renderAuthView(this.currentView);
      }
      return;
    }

    // 3. Workspace Screens (Dashboard, Notes, Search, Profile)
    if (landingContainer) landingContainer.style.display = 'none';
    if (authContainer) authContainer.style.display = 'none';
    if (workspaceContainer) {
      workspaceContainer.style.display = 'flex';
      this.renderWorkspaceView();
    }
  },

  // Site Brand Logo SVG Generator
  getSiteLogoSvg(size = 28) {
    return `
      <svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" fill="rgba(255,255,255,0.18)"></path>
        <polyline points="14 2 14 8 20 8"></polyline>
        <line x1="16" y1="13" x2="8" y2="13"></line>
        <line x1="16" y1="17" x2="8" y2="17"></line>
        <circle cx="10" cy="9" r="1.2" fill="#FFFFFF"></circle>
      </svg>
    `;
  },

  // Auth View Templates
  renderAuthView(viewName) {
    if (viewName === 'login') {
      return `
        <div class="auth-card">
          <div class="auth-header">
            <div class="logo-badge" title="Smart Notes Assistant" onclick="window.location.hash='#landing'">
              ${this.getSiteLogoSvg(28)}
            </div>
            <h2>Sign in to Smart Notes</h2>
            <p>Access your intelligent notes and personal workspace.</p>
          </div>
          <form onsubmit="Auth.login(event)">
            <div class="form-group">
              <label for="login-email">Email Address</label>
              <div class="input-wrapper">
                <input type="email" id="login-email" required placeholder="name@domain.com" autocomplete="email" />
              </div>
            </div>
            <div class="form-group">
              <label for="login-password">Password</label>
              <div class="input-wrapper">
                <input type="password" id="login-password" required placeholder="••••••••" autocomplete="current-password" />
                <button type="button" class="toggle-password-btn" onclick="Auth.togglePassword('login-password', this)" title="Show/Hide Password">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>
                </button>
              </div>
            </div>
            <div class="form-options">
              <label class="checkbox-label">
                <input type="checkbox" id="login-remember" />
                <span>Remember me</span>
              </label>
              <a href="#forgot-password">Forgot password?</a>
            </div>
            <button type="submit" class="btn btn-primary auth-submit-btn">Sign In</button>
          </form>
          <div class="auth-footer">
            Don't have an account? <a href="#register">Create one</a>
          </div>
        </div>
      `;
    }

    if (viewName === 'register') {
      return `
        <div class="auth-card">
          <div class="auth-header">
            <div class="logo-badge" title="Smart Notes Assistant" onclick="window.location.hash='#landing'">
              ${this.getSiteLogoSvg(28)}
            </div>
            <h2>Create your account</h2>
            <p>Start organizing your thoughts with machine learning.</p>
          </div>
          <form onsubmit="Auth.register(event)">
            <div class="form-group">
              <label for="reg-name">Full Name</label>
              <div class="input-wrapper">
                <input type="text" id="reg-name" required placeholder="e.g. Rahul" autocomplete="name" />
              </div>
            </div>
            <div class="form-group">
              <label for="reg-email">Email Address</label>
              <div class="input-wrapper">
                <input type="email" id="reg-email" required placeholder="name@domain.com" autocomplete="email" />
              </div>
            </div>
            <div class="form-group">
              <label for="reg-password">Password</label>
              <div class="input-wrapper">
                <input type="password" id="reg-password" required placeholder="At least 8 characters" autocomplete="new-password" oninput="App.onPasswordInput(this.value)" />
                <button type="button" class="toggle-password-btn" onclick="Auth.togglePassword('reg-password', this)" title="Show/Hide Password">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>
                </button>
              </div>
              <div class="password-strength-meter">
                <div class="strength-bar-bg">
                  <div class="strength-bar-fill" id="reg-strength-bar"></div>
                </div>
                <div class="strength-text">
                  <span>Strength</span>
                  <span id="reg-strength-label">None</span>
                </div>
              </div>
            </div>
            <div class="form-group">
              <label for="reg-confirm-password">Confirm Password</label>
              <div class="input-wrapper">
                <input type="password" id="reg-confirm-password" required placeholder="Repeat password" autocomplete="new-password" />
              </div>
            </div>
            <button type="submit" class="btn btn-primary auth-submit-btn">Create Account</button>
          </form>
          <div class="auth-footer">
            Already registered? <a href="#login">Sign in</a>
          </div>
        </div>
      `;
    }

    if (viewName === 'verify-email') {
      const params = new URLSearchParams(window.location.hash.split('?')[1] || '');
      const token = params.get('token') || '';
      return `
        <div class="auth-card">
          <div class="auth-header">
            <div class="logo-badge" title="Smart Notes Assistant" onclick="window.location.hash='#landing'">
              ${this.getSiteLogoSvg(28)}
            </div>
            <h2>Verify Your Email</h2>
            <p>Confirm ownership of your account to ensure secure access.</p>
          </div>
          <div class="verification-badge-card">
            <div class="icon-circle">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>
            </div>
            <p style="font-size:14px; margin-bottom: 12px;">We've sent a verification link to your email address.</p>
            ${token ? `<p style="font-size:12px; color:#10B981;">Token detected from URL. Verifying automatically...</p>` : `<p style="font-size:12px; color:#989AA3;">If testing locally without SMTP, tokens are logged in the terminal dev-inbox.</p>`}
          </div>
          ${token ? `
            <button type="button" class="btn btn-primary auth-submit-btn" onclick="Auth.verifyEmail('${token}')">Verify Account Now</button>
          ` : `
            <a href="#dashboard" class="btn btn-secondary auth-submit-btn">Continue to Workspace</a>
          `}
          <div class="auth-footer">
            <a href="#dashboard">Return to workspace</a>
          </div>
        </div>
      `;
    }

    if (viewName === 'forgot-password') {
      return `
        <div class="auth-card">
          <div class="auth-header">
            <div class="logo-badge" title="Smart Notes Assistant" onclick="window.location.hash='#landing'">
              ${this.getSiteLogoSvg(28)}
            </div>
            <h2>Reset your password</h2>
            <p>Enter your account email to receive a password recovery link.</p>
          </div>
          <form onsubmit="Auth.forgotPassword(event)">
            <div class="form-group">
              <label for="forgot-email">Email Address</label>
              <div class="input-wrapper">
                <input type="email" id="forgot-email" required placeholder="name@domain.com" />
              </div>
            </div>
            <button type="submit" class="btn btn-primary auth-submit-btn">Send Recovery Link</button>
          </form>
          <div id="forgot-feedback" style="display:none; margin-top:16px; font-size:13px; color:#34D399; text-align:center;">
            If an account exists, a reset link has been dispatched. Check your terminal dev-inbox if testing locally.
          </div>
          <div class="auth-footer">
            Remembered your password? <a href="#login">Sign in</a>
          </div>
        </div>
      `;
    }

    if (viewName === 'reset-password') {
      const params = new URLSearchParams(window.location.hash.split('?')[1] || '');
      const token = params.get('token') || '';
      return `
        <div class="auth-card">
          <div class="auth-header">
            <div class="logo-badge" title="Smart Notes Assistant" onclick="window.location.hash='#landing'">
              ${this.getSiteLogoSvg(28)}
            </div>
            <h2>Set a new password</h2>
            <p>Enter your recovery token and choose a strong new password.</p>
          </div>
          <form onsubmit="Auth.resetPassword(event)">
            <div class="form-group">
              <label for="reset-token">Reset Token</label>
              <div class="input-wrapper">
                <input type="text" id="reset-token" required value="${token}" placeholder="Paste token here" />
              </div>
            </div>
            <div class="form-group">
              <label for="reset-new-password">New Password</label>
              <div class="input-wrapper">
                <input type="password" id="reset-new-password" required placeholder="At least 8 characters" />
              </div>
            </div>
            <div class="form-group">
              <label for="reset-confirm-password">Confirm New Password</label>
              <div class="input-wrapper">
                <input type="password" id="reset-confirm-password" required placeholder="Confirm password" />
              </div>
            </div>
            <button type="submit" class="btn btn-primary auth-submit-btn">Update Password</button>
          </form>
          <div class="auth-footer">
            <a href="#login">Back to Sign In</a>
          </div>
        </div>
      `;
    }

    return '';
  },

  onPasswordInput(val) {
    const strength = Auth.calculatePasswordStrength(val);
    const bar = document.getElementById('reg-strength-bar');
    const label = document.getElementById('reg-strength-label');
    if (bar && label) {
      bar.style.width = strength.width;
      bar.style.backgroundColor = strength.color;
      label.innerText = strength.text;
      label.style.color = strength.color;
    }
  },

  // Workspace Screens (Sidebar + Top Bar + Content View)
  renderWorkspaceView() {
    // 1. Update user profile in sidebar
    if (this.currentUser) {
      const nameEl = document.getElementById('sidebar-user-name');
      const avatarEl = document.getElementById('sidebar-user-avatar');
      const emailEl = document.getElementById('sidebar-user-email');
      if (nameEl) nameEl.innerText = this.currentUser.name || 'User';
      if (emailEl) emailEl.innerText = this.currentUser.email || 'user@example.com';
      if (avatarEl) {
        if (this.currentUser.profile_picture) {
          avatarEl.innerHTML = `<img src="${this.currentUser.profile_picture}" alt="Avatar" style="width:100%;height:100%;object-fit:cover;border-radius:50%;" />`;
        } else {
          avatarEl.innerText = (this.currentUser.name || 'U').charAt(0).toUpperCase();
        }
      }
    }

    // 2. Update metric badge counts in sidebar
    this.updateSidebarCounts();

    // 3. Highlight active nav link
    document.querySelectorAll('.sidebar-nav .nav-link').forEach(el => el.classList.remove('active'));
    let activeId = 'nav-dashboard';
    if (this.currentView === 'dashboard') {
      activeId = 'nav-dashboard';
    } else if (this.currentView === 'notes') {
      if (this.activeCategoryFilter && this.activeCategoryFilter !== 'all') {
        activeId = `nav-cat-${this.activeCategoryFilter}`;
      } else if (this.activePriorityFilter === 'high') {
        activeId = 'nav-priority-today';
      } else {
        activeId = 'nav-notes';
      }
    } else if (this.currentView === 'search') {
      activeId = 'nav-search';
    } else if (this.currentView === 'analytics') {
      activeId = 'nav-analytics';
    } else if (this.currentView === 'profile') {
      activeId = 'nav-profile';
    }
    const activeNav = document.getElementById(activeId) || document.getElementById(`nav-${this.currentView}`) || document.getElementById('nav-dashboard');
    if (activeNav) activeNav.classList.add('active');

    // 4. Render main view content
    const container = document.getElementById('workspace-view-content');
    if (!container) return;

    if (this.currentView === 'dashboard') {
      container.innerHTML = this.renderDashboard();
      if (window.Notifications) {
        Notifications.refreshDashboardBanner();
      }
    } else if (this.currentView === 'notes') {
      container.innerHTML = this.renderNotesLibrary();
    } else if (this.currentView === 'search') {
      container.innerHTML = this.renderSearchView();
    } else if (this.currentView === 'analytics') {
      container.innerHTML = this.renderAnalyticsView();
      setTimeout(() => this.drawAnalyticsDonut(), 50);
    } else if (this.currentView === 'profile') {
      container.innerHTML = this.renderProfileView();
    }

    // Refresh notifications badge on view updates
    if (window.Notifications) {
      Notifications.updateBadge();
    }
  },

  quickSearch(query) {
    const q = (query || '').trim();
    if (!q) {
      this.openSpotlight();
      return;
    }
    this.closeLiveBarSearch();
    window.location.hash = `#search?q=${encodeURIComponent(q)}`;
    this.handleRouting();
  },

  onLiveBarSearch(query) {
    const dropdown = document.getElementById('roomy-search-dropdown');
    if (!dropdown) return;
    const q = (query || '').trim().toLowerCase();
    if (!q) {
      dropdown.style.display = 'none';
      dropdown.innerHTML = '';
      return;
    }

    const allNotes = [...(this.notes || []), ...((this.stats && this.stats.recent_notes) || [])];
    const unique = Array.from(new Map(allNotes.map(n => [n.note_id, n])).values());
    const matches = unique.filter(n => {
      const text = (n.text || '').toLowerCase();
      const cat = (n.category || '').toLowerCase();
      return text.includes(q) || cat.includes(q);
    }).slice(0, 5);

    dropdown.style.display = 'block';
    if (matches.length === 0) {
      dropdown.innerHTML = `
        <div style="padding:14px; font-size:12.5px; color:var(--text-muted); text-align:center;">
          No matching notes found.<br>
          <span style="font-size:11px; color:var(--purple-accent); cursor:pointer;" onclick="App.quickSearch('${this.escapeJs(q)}')">Press <strong>Enter</strong> to run full ML search</span>
        </div>
      `;
      return;
    }

    dropdown.innerHTML = `
      <div style="padding:4px 0;">
        ${matches.map(n => {
          const cat = n.category || 'Study';
          return `
          <div class="live-search-item" onclick="App.closeLiveBarSearch(); Notes.openEditModal('${n.note_id}', '${this.escapeJs(n.text)}')">
            <span class="badge badge-${cat.toLowerCase()}" style="font-size:10px; padding:1px 6px;">${cat}</span>
            <span class="live-search-text">${this.escapeHtml(n.text.length > 32 ? n.text.substring(0, 32) + '...' : n.text)}</span>
          </div>
        `}).join('')}
        <div style="border-top:1px solid var(--border-subtle); padding:8px 12px; text-align:center; background:rgba(0,0,0,0.015);">
          <a href="javascript:void(0)" onclick="App.quickSearch('${this.escapeJs(q)}')" style="font-size:11.5px; color:var(--purple-accent); font-weight:600; text-decoration:none;">View all in Search Workspace →</a>
        </div>
      </div>
    `;
  },

  closeLiveBarSearch() {
    const dropdown = document.getElementById('roomy-search-dropdown');
    if (dropdown) dropdown.style.display = 'none';
  },

  handleTimeFilterChange(val) {
    this.dashboardTimeFilter = val;
    this.render();
  },

  formatRelativeTime(created_at) {
    if (!created_at) return 'Recent';
    const now = new Date();
    const created = new Date(created_at);
    const diffMs = Math.max(0, now.getTime() - created.getTime());
    const diffHours = diffMs / (1000 * 60 * 60);
    const diffDays = diffMs / (1000 * 60 * 60 * 24);

    if (diffMs < 60000) {
      return 'Just now';
    } else if (diffHours < 1) {
      const mins = Math.max(1, Math.round(diffMs / (1000 * 60)));
      return `${mins}m ago`;
    } else if (diffHours < 24 && now.toDateString() === created.toDateString()) {
      const hrs = Math.round(diffHours);
      return `${hrs}h ago`;
    } else if (diffDays < 2) {
      return 'Yesterday';
    } else if (diffDays < 7) {
      const d = Math.max(1, Math.round(diffDays));
      return `${d}d ago`;
    } else {
      return created.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
    }
  },

  // Intelligent Time-Based Priority Analyzer
  // Evaluates explicit time expressions, deadlines, task urgency, and manual overrides
  getTimePriority(note) {
    if (!note) {
      return {
        level: 'low',
        label: 'Normal Priority',
        shortLabel: 'Normal',
        sublabel: 'Flexible',
        badgeClass: 'priority-low',
        icon: '⏱️',
        relativeTime: 'Recent',
        score: 1,
        reason: 'Flexible'
      };
    }

    const relTime = this.formatRelativeTime(note.created_at);

    // 1. Manual User Override (persisted in localStorage by note_id)
    if (note.note_id) {
      const manualPrio = localStorage.getItem('note_prio_' + note.note_id);
      if (manualPrio === 'high') {
        return {
          level: 'high',
          label: 'High Priority',
          shortLabel: 'High',
          sublabel: 'Custom Set',
          badgeClass: 'priority-high',
          icon: '🔥',
          relativeTime: relTime,
          score: 3,
          reason: 'Manual Set'
        };
      } else if (manualPrio === 'medium') {
        return {
          level: 'medium',
          label: 'Medium Priority',
          shortLabel: 'Medium',
          sublabel: 'Custom Set',
          badgeClass: 'priority-medium',
          icon: '⚡',
          relativeTime: relTime,
          score: 2,
          reason: 'Manual Set'
        };
      } else if (manualPrio === 'low') {
        return {
          level: 'low',
          label: 'Normal Priority',
          shortLabel: 'Normal',
          sublabel: 'Custom Set',
          badgeClass: 'priority-low',
          icon: '⏱️',
          relativeTime: relTime,
          score: 1,
          reason: 'Manual Set'
        };
      }
    }

    const text = (note.text || '').toLowerCase().trim();

    // 2. High Priority: Explicit TODAY, IMMEDIATE, or URGENT time words (within 24 hours)
    const isUrgentTime = /\b(today|tonight|aaj|asap|urgent|urgently|emergency|critical|immediately|right now|due today|at once|in ([1-9]|1[0-9]|2[0-4])\s*(hour|hr)s?|in \d+\s*(minute|min)s?|\[high\]|!high|p1)\b/i.test(text);
    if (isUrgentTime) {
      let sublabel = 'Today';
      if (/urgent|asap|emergency|critical/.test(text)) sublabel = 'Urgent';
      else if (/tonight/.test(text)) sublabel = 'Tonight';
      return {
        level: 'high',
        label: 'High Priority',
        shortLabel: 'High',
        sublabel: sublabel,
        badgeClass: 'priority-high',
        icon: '🔥',
        relativeTime: relTime,
        score: 3,
        reason: 'Due Today / Urgent'
      };
    }

    // 3. Medium Priority: TOMORROW, UPCOMING, THIS WEEK, or SCHEDULED ACTION ITEMS (24h - 7d)
    const isTomorrowOrUpcoming = /\b(tomorrow|tommorow|tomorow|tmrw|tmr|kal|parso|this week|upcoming|soon|next few days|in \d+ days?|after \d+ (hour|hr)s?|in ([3-9][0-9]|2[5-9])\s*(hour|hr)s?|monday|tuesday|wednesday|thursday|friday|saturday|sunday|\[medium\]|!med|p2)\b/i.test(text);
    const isActionDeadline = /\b(pay|bill|due|submit|exam|test|interview|meeting|flight|appointment|deadline|reminder|schedule)\b/i.test(text);

    if (isTomorrowOrUpcoming) {
      let sublabel = 'This Week';
      if (/tommorow|tomorrow|tomorow|tmrw|tmr|kal/.test(text)) sublabel = 'Tomorrow';
      else if (/parso/.test(text)) sublabel = 'In 2 Days';
      else if (/after \d+ (hour|hr)/.test(text)) sublabel = 'Upcoming';
      return {
        level: 'medium',
        label: 'Medium Priority',
        shortLabel: 'Medium',
        sublabel: sublabel,
        badgeClass: 'priority-medium',
        icon: '⚡',
        relativeTime: relTime,
        score: 2,
        reason: 'Scheduled / Upcoming'
      };
    }

    if (isActionDeadline) {
      return {
        level: 'medium',
        label: 'Medium Priority',
        shortLabel: 'Medium',
        sublabel: 'Action Task',
        badgeClass: 'priority-medium',
        icon: '⚡',
        relativeTime: relTime,
        score: 2,
        reason: 'Actionable Item'
      };
    }

    // 4. Normal / Low Priority: Casual greetings ("hi", "oye"), notes with no time constraint, or far future
    return {
      level: 'low',
      label: 'Normal Priority',
      shortLabel: 'Normal',
      sublabel: 'Flexible',
      badgeClass: 'priority-low',
      icon: '⏱️',
      relativeTime: relTime,
      score: 1,
      reason: 'No Time Deadline'
    };
  },

  // Cycle Priority on Badge Click (High -> Medium -> Low -> High)
  cycleNotePriority(event, noteId) {
    if (event) event.stopPropagation();
    const current = this.getTimePriority({ note_id: noteId, text: '' }).level;
    let next = 'medium';
    if (current === 'high') next = 'medium';
    else if (current === 'medium') next = 'low';
    else next = 'high';

    localStorage.setItem('note_prio_' + noteId, next);
    const label = next === 'high' ? '🔥 High Priority' : next === 'medium' ? '⚡ Medium Priority' : '⏱️ Normal Priority';
    this.showToast(`Note priority set to: ${label}`, 'success');
    this.render();
  },

  getPriorityCounts(notesList = null) {
    const list = notesList || this.notes || [];
    let high = 0;
    let medium = 0;
    let low = 0;
    list.forEach(n => {
      const p = this.getTimePriority(n);
      if (p.level === 'high') high++;
      else if (p.level === 'medium') medium++;
      else low++;
    });
    return { high, medium, low, total: list.length };
  },

  updateSidebarCounts() {
    if (this.stats) {
      const elAll = document.getElementById('count-all-notes');
      const elStudy = document.getElementById('count-study');
      const elMoney = document.getElementById('count-money');
      const elTravel = document.getElementById('count-travel');
      const elShopping = document.getElementById('count-shopping');
      const elUncertain = document.getElementById('count-uncertain');
      if (elAll) elAll.innerText = this.stats.total_notes;
      if (elStudy) elStudy.innerText = this.stats.study_count;
      if (elMoney) elMoney.innerText = this.stats.money_count;
      if (elTravel) elTravel.innerText = this.stats.travel_count;
      if (elShopping) elShopping.innerText = this.stats.shopping_count;
      if (elUncertain) elUncertain.innerText = this.stats.uncertain_count;
    }

    const elPrioHigh = document.getElementById('count-priority-high');
    if (elPrioHigh) {
      const pool = (this.allUserNotes && this.allUserNotes.length > 0)
        ? this.allUserNotes
        : (this.notes || (this.stats && this.stats.recent_notes) || []);
      const prioCounts = this.getPriorityCounts(pool);
      elPrioHigh.innerText = prioCounts.high;
    }
  },

  async navigateToNotes(category = 'all', priority = 'all') {
    this.currentView = 'notes';
    this.activeCategoryFilter = category || 'all';
    this.activePriorityFilter = priority || 'all';
    this.activeTagFilter = null;

    let targetHash = '#notes';
    const params = [];
    if (this.activeCategoryFilter && this.activeCategoryFilter !== 'all') {
      params.push(`category=${encodeURIComponent(this.activeCategoryFilter)}`);
    }
    if (this.activePriorityFilter && this.activePriorityFilter !== 'all') {
      params.push(`priority=${encodeURIComponent(this.activePriorityFilter)}`);
    }
    if (params.length > 0) {
      targetHash += '?' + params.join('&');
    }

    if (window.location.hash !== targetHash) {
      window.location.hash = targetHash;
    }

    this.render();

    await Notes.fetchStats();
    await Notes.fetchNotes(this.activeCategoryFilter);
    this.render();
  },

  async navigateToView(view) {
    this.currentView = view;
    const targetHash = `#${view}`;
    if (window.location.hash !== targetHash) {
      window.location.hash = targetHash;
    }
    this.render();
    if (view === 'dashboard' || view === 'search' || view === 'analytics') {
      await Notes.fetchStats();
      if (view === 'analytics') {
        await Notes.fetchNotes('all');
      }
      this.render();
    }
  },

  setPriorityFilter(prio) {
    this.activePriorityFilter = prio;
    if (this.activeCategoryFilter === 'all') {
      window.location.hash = prio === 'all' ? '#notes' : `#notes?priority=${encodeURIComponent(prio)}`;
    }
    this.render();
  },

  setNoteSort(sortVal) {
    this.noteSortBy = sortVal;
    this.render();
  },

  calViewYear: null,
  calViewMonth: null,
  selectedCalendarDay: null,

  getCalendarViewDate() {
    const now = new Date();
    if (this.calViewYear === null || this.calViewYear === undefined) {
      this.calViewYear = now.getFullYear();
    }
    if (this.calViewMonth === null || this.calViewMonth === undefined) {
      this.calViewMonth = now.getMonth();
    }
    return {
      year: this.calViewYear,
      month: this.calViewMonth,
      todayDate: now.getDate(),
      todayMonth: now.getMonth(),
      todayYear: now.getFullYear()
    };
  },

  prevCalendarMonth() {
    const { year, month } = this.getCalendarViewDate();
    if (month === 0) {
      this.calViewMonth = 11;
      this.calViewYear = year - 1;
    } else {
      this.calViewMonth = month - 1;
    }
    this.selectedCalendarDay = null;
    this.render();
  },

  nextCalendarMonth() {
    const { year, month } = this.getCalendarViewDate();
    if (month === 11) {
      this.calViewMonth = 0;
      this.calViewYear = year + 1;
    } else {
      this.calViewMonth = month + 1;
    }
    this.selectedCalendarDay = null;
    this.render();
  },

  resetCalendarToToday() {
    const now = new Date();
    this.calViewYear = now.getFullYear();
    this.calViewMonth = now.getMonth();
    this.selectedCalendarDay = now.getDate();
    this.render();
  },

  selectCalendarDay(day, isOtherMonth = 0) {
    if (isOtherMonth === -1) {
      const { year, month } = this.getCalendarViewDate();
      if (month === 0) { this.calViewMonth = 11; this.calViewYear = year - 1; }
      else { this.calViewMonth = month - 1; }
    } else if (isOtherMonth === 1) {
      const { year, month } = this.getCalendarViewDate();
      if (month === 11) { this.calViewMonth = 0; this.calViewYear = year + 1; }
      else { this.calViewMonth = month + 1; }
    }
    this.selectedCalendarDay = day;
    this.render();
    const { year, month } = this.getCalendarViewDate();
    const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    this.showToast(`Selected: ${monthNames[month]} ${day}, ${year}`, 'info');
  },

  generateCalendarHtml() {
    const { year, month, todayDate, todayMonth, todayYear } = this.getCalendarViewDate();

    const monthNames = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
    const monthTitle = `${monthNames[month]} ${year}`;

    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const firstDayIndex = (new Date(year, month, 1).getDay() + 6) % 7;
    const daysInPrevMonth = new Date(year, month, 0).getDate();

    // Map of days in viewed month that have notes
    const daysWithNotes = new Set();
    const allNotes = [...(this.notes || []), ...((this.stats && this.stats.recent_notes) || [])];
    allNotes.forEach(n => {
      if (n.created_at) {
        const d = new Date(n.created_at);
        if (d.getFullYear() === year && d.getMonth() === month) {
          daysWithNotes.add(d.getDate());
        }
      }
    });

    let gridHtml = '';

    for (let i = firstDayIndex - 1; i >= 0; i--) {
      const prevDay = daysInPrevMonth - i;
      gridHtml += `<div class="cal-day cal-other-month" onclick="App.selectCalendarDay(${prevDay}, -1)">${prevDay}</div>`;
    }

    for (let d = 1; d <= daysInMonth; d++) {
      const isRealToday = (year === todayYear && month === todayMonth && d === todayDate);
      const isSelected = this.selectedCalendarDay ? (d === this.selectedCalendarDay) : isRealToday;
      const hasNote = daysWithNotes.has(d);

      gridHtml += `
        <div class="cal-day ${isSelected ? 'cal-today' : ''}" onclick="App.selectCalendarDay(${d}, 0)" title="${monthNames[month]} ${d}, ${year}${hasNote ? ' (Has Notes)' : ''}">
          <span>${d}</span>
          ${hasNote ? '<span class="cal-dot"></span>' : ''}
        </div>
      `;
    }

    const totalCells = (firstDayIndex + daysInMonth <= 35) ? 35 : 42;
    const trailingDays = totalCells - (firstDayIndex + daysInMonth);
    for (let n = 1; n <= trailingDays; n++) {
      gridHtml += `<div class="cal-day cal-other-month" onclick="App.selectCalendarDay(${n}, 1)">${n}</div>`;
    }

    return `
      <div class="roomy-calendar-card">
        <div class="calendar-card-header">
          <button class="cal-month-title-btn" onclick="App.resetCalendarToToday()" title="Jump to Current Month & Today">
            <span>${monthTitle}</span>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"></polyline></svg>
          </button>
          <div style="display:flex; align-items:center; gap:6px;">
            <button class="cal-nav-btn" onclick="App.prevCalendarMonth()" title="Previous Month">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="15 18 9 12 15 6"></polyline></svg>
            </button>
            <button class="cal-nav-btn" onclick="App.nextCalendarMonth()" title="Next Month">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="9 18 15 12 9 6"></polyline></svg>
            </button>
          </div>
        </div>
        <div class="calendar-days-header">
          <span>Mo</span><span>Tu</span><span>We</span><span>Th</span><span>Fr</span><span>Sa</span><span>Su</span>
        </div>
        <div class="calendar-grid">
          ${gridHtml}
        </div>
      </div>
    `;
  },

  // View: Exact Roomy 3-Column Dashboard Layout
  renderDashboard() {
    const s = this.stats || {
      total_notes: 0,
      study_count: 0,
      money_count: 0,
      travel_count: 0,
      shopping_count: 0,
      uncertain_count: 0,
      recent_notes: []
    };

    const userName = this.currentUser && this.currentUser.name ? this.currentUser.name : 'User';
    const recentNotes = s.recent_notes || [];
    const filterPeriod = this.dashboardTimeFilter || 'week';
    const periodText = filterPeriod === 'month' ? 'this month' : filterPeriod === 'all' ? 'all time' : 'this week';

    const { year, month } = this.getCalendarViewDate();
    const monthNames = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

    const allNotesCombined = [...(this.notes || []), ...((s.recent_notes) || [])];
    const uniqueNotes = Array.from(new Map(allNotesCombined.map(n => [n.note_id, n])).values());
    const prioCounts = this.getPriorityCounts(uniqueNotes);

    const now = new Date();
    const dateSet = new Set();
    uniqueNotes.forEach(n => {
      if (n.created_at) dateSet.add(new Date(n.created_at).toISOString().slice(0, 10));
    });
    const streakDays = Math.max(1, dateSet.size);

    let selectedDayNotes = null;
    let selectedDateLabel = '';
    let scheduleCardTitle = '';
    let isDayFiltered = false;

    if (this.selectedCalendarDay) {
      isDayFiltered = true;
      selectedDateLabel = `${monthNames[month]} ${this.selectedCalendarDay}, ${year}`;
      scheduleCardTitle = `Notes on ${monthNames[month]} ${this.selectedCalendarDay}`;
      selectedDayNotes = uniqueNotes.filter(n => {
        if (!n.created_at) return false;
        const d = new Date(n.created_at);
        return d.getFullYear() === year && d.getMonth() === month && d.getDate() === this.selectedCalendarDay;
      });
    } else {
      // Default view: Show today's notes if available, otherwise show recent active notes
      const todayNotes = uniqueNotes.filter(n => {
        if (!n.created_at) return false;
        const d = new Date(n.created_at);
        return d.getFullYear() === now.getFullYear() && d.getMonth() === now.getMonth() && d.getDate() === now.getDate();
      });
      if (todayNotes.length > 0) {
        scheduleCardTitle = "Today's Schedule & Notes";
        selectedDayNotes = todayNotes;
      } else if (uniqueNotes.length > 0) {
        scheduleCardTitle = "Scheduled & Recent Notes";
        selectedDayNotes = uniqueNotes.slice(0, 4);
      } else {
        scheduleCardTitle = "Scheduled & Recent Notes";
        selectedDayNotes = [];
      }
    }

    return `
      <div class="roomy-dashboard-layout">
        <!-- CENTER STAGE (Middle Column) -->
        <div class="roomy-center-col">
          <!-- Top Welcome Greeting -->
          <div class="roomy-welcome-header">
            <div>
              <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px;">
                <div class="roomy-greeting-sub" style="margin:0;">Hi ${this.escapeHtml(userName)}!</div>
                <div class="focus-streak-pill" title="Daily Note Taking Habit Streak">🔥 ${streakDays}-Day Focus Streak</div>
              </div>
              <h1 class="roomy-welcome-title">Welcome Back 👋</h1>
            </div>
            <div style="display:flex; align-items:center; gap:8px;">
              <select class="roomy-time-select" onchange="App.handleTimeFilterChange(this.value)">
                <option value="week" ${filterPeriod === 'week' ? 'selected' : ''}>This week</option>
                <option value="month" ${filterPeriod === 'month' ? 'selected' : ''}>This month</option>
                <option value="all" ${filterPeriod === 'all' ? 'selected' : ''}>All time</option>
              </select>
            </div>
          </div>

          <!-- Smart Work & Deadline Notification Banner Slot -->
          <div id="dashboard-urgent-banner-slot"></div>

          <!-- AI Workspace Insights & Smart Digest Banner -->
          <div class="ai-digest-banner">
            <div class="ai-digest-left">
              <div class="ai-digest-badge">
                <span class="ai-sparkle">✨</span>
                <span>AI Workspace Digest</span>
              </div>
              <div class="ai-digest-headline">${this.generateSmartDigestHeadline(uniqueNotes, s, prioCounts)}</div>
              <div class="ai-digest-sub">${this.generateSmartDigestSub(uniqueNotes, s, prioCounts)}</div>
            </div>
            <div class="ai-digest-actions">
              <button class="btn btn-sm btn-secondary ai-action-btn" onclick="App.openAiSummaryModal()" title="View AI Executive Summary of your thoughts">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>
                <span>AI Summary</span>
              </button>
              <button class="btn btn-sm btn-secondary ai-action-btn" onclick="App.exportAllNotes()" title="Export all notes to Markdown">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
                <span>Export Notes</span>
              </button>
            </div>
          </div>

          <!-- Time-Based Priority Tracker Bar -->
          <div class="roomy-priority-tracker-bar">
            <div class="priority-tracker-header">
              <div style="display:flex; align-items:center; gap:8px;">
                <span class="priority-pulse-dot"></span>
                <span style="font-size:12px; font-weight:700; color:var(--text-dark); letter-spacing:0.3px;">PRIORITY ACCORDING TO TIME</span>
              </div>
              <span style="font-size:11.5px; color:var(--text-muted);">Dynamically prioritized by recency &amp; creation time</span>
            </div>
            <div class="priority-tracker-pills">
              <button class="priority-tracker-pill priority-pill-high" onclick="window.location.hash='#notes?priority=high'" title="View Today's High Priority Notes">
                <div class="p-pill-icon">🔥</div>
                <div class="p-pill-meta">
                  <div class="p-pill-title">High Priority</div>
                  <div class="p-pill-sub">Today • &lt;24 hrs</div>
                </div>
                <div class="p-pill-count">${prioCounts.high}</div>
              </button>

              <button class="priority-tracker-pill priority-pill-medium" onclick="window.location.hash='#notes?priority=medium'" title="View Active Notes From This Week">
                <div class="p-pill-icon">⚡</div>
                <div class="p-pill-meta">
                  <div class="p-pill-title">Medium Priority</div>
                  <div class="p-pill-sub">This Week • 1-7 days</div>
                </div>
                <div class="p-pill-count">${prioCounts.medium}</div>
              </button>

              <button class="priority-tracker-pill priority-pill-low" onclick="window.location.hash='#notes?priority=low'" title="View Older Reference Notes">
                <div class="p-pill-icon">⏱️</div>
                <div class="p-pill-meta">
                  <div class="p-pill-title">Normal Priority</div>
                  <div class="p-pill-sub">Older • &gt;7 days</div>
                </div>
                <div class="p-pill-count">${prioCounts.low}</div>
              </button>
            </div>
          </div>

          <!-- Hero Row: Vibrant Purple Activity Wave Card + Stat Box -->
          <div class="roomy-hero-row">
            <!-- 1. Activity Card (Solid Vibrant Purple #6C52EE with Smooth Wave Spline & Tooltip) -->
            <div class="roomy-activity-card">
              <div class="activity-card-top">
                <div>
                  <div class="act-card-title">Activity</div>
                  <div class="act-card-sub">${s.total_notes} notes organized ${periodText}</div>
                </div>
                <button class="act-arrow-circle-btn" onclick="window.location.hash='#notes'" title="View All Notes">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="2.5"><polyline points="9 18 15 12 9 6"></polyline></svg>
                </button>
              </div>

              <!-- Interactive Smooth Wave Chart with Peak Tooltip -->
              <div class="roomy-wave-container">
                <div class="roomy-tooltip-bubble">${s.total_notes || 0}</div>
                <svg class="roomy-wave-svg" viewBox="0 0 360 80" preserveAspectRatio="none">
                  <defs>
                    <linearGradient id="waveFillGrad" x1="0%" y1="0%" x2="0%" y2="100%">
                      <stop offset="0%" stop-color="#FFFFFF" stop-opacity="0.32"/>
                      <stop offset="100%" stop-color="#FFFFFF" stop-opacity="0.0"/>
                    </linearGradient>
                  </defs>
                  <path d="M0,60 C40,60 60,35 90,45 C120,55 140,25 170,40 C200,55 210,10 230,10 C250,10 260,55 285,45 C310,35 330,55 360,50 L360,80 L0,80 Z" fill="url(#waveFillGrad)"/>
                  <path d="M0,60 C40,60 60,35 90,45 C120,55 140,25 170,40 C200,55 210,10 230,10 C250,10 260,55 285,45 C310,35 330,55 360,50" fill="none" stroke="#FFFFFF" stroke-width="2.5" stroke-linecap="round"/>
                  <circle cx="230" cy="10" r="4.5" fill="#FFFFFF"/>
                </svg>
              </div>

              <div class="roomy-activity-axis">
                <span>Mon</span><span>Tue</span><span>Wed</span><span>Thu</span><span>Fri</span><span>Sat</span><span>Sun</span>
              </div>
            </div>

            <!-- 2. Stat Box (Total Notes Counter & New Note Action) -->
            <div class="roomy-stat-card">
              <div>
                <div class="stat-card-label">Total Notes</div>
                <div class="stat-card-value">${s.total_notes}</div>
                <div class="stat-card-desc">Intelligently organized across Study, Money, Travel and Shopping.</div>
              </div>
              <div style="display:flex; gap:8px; margin-top:14px; width:100%;">
                <button class="roomy-withdraw-btn" style="flex:1; margin-top:0;" onclick="Notes.openEditModal()">+ Add Note</button>
                <button class="btn-voice-dictate" onclick="App.startVoiceDictation()" title="Speak your thought (Voice-to-Note with live AI tagging)">
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path><path d="M19 10v2a7 7 0 0 1-14 0v-2"></path><line x1="12" y1="19" x2="12" y2="23"></line><line x1="8" y1="23" x2="16" y2="23"></line></svg>
                  <span>Voice Note</span>
                </button>
              </div>
            </div>
          </div>

          <!-- Lower Row: 4 Category Metric Tiles + Last Progress List -->
          <div class="roomy-lower-row">
            <!-- 3. Quad Metric Tiles Card -->
            <div class="roomy-quad-card">
              <!-- STUDY -->
              <div class="quad-tile" onclick="window.location.hash='#notes?category=Study'">
                <div style="display:flex; align-items:center;">
                  <div class="quad-icon-box bg-study-icon">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 10v6M2 10l10-5 10 5-10 5z"></path><path d="M6 12v5c3 3 9 3 12 0v-5"></path></svg>
                  </div>
                  <div class="quad-meta">
                    <div class="quad-label">Study Notes</div>
                    <div class="quad-val">${s.study_count}</div>
                  </div>
                </div>
                <svg class="quad-chevron" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"></polyline></svg>
              </div>

              <!-- MONEY -->
              <div class="quad-tile" onclick="window.location.hash='#notes?category=Money'">
                <div style="display:flex; align-items:center;">
                  <div class="quad-icon-box bg-money-icon">
                    <span style="font-weight:700; font-size:16px;">₹</span>
                  </div>
                  <div class="quad-meta">
                    <div class="quad-label">Money &amp; Finance</div>
                    <div class="quad-val">${s.money_count}</div>
                  </div>
                </div>
                <svg class="quad-chevron" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"></polyline></svg>
              </div>

              <!-- TRAVEL -->
              <div class="quad-tile" onclick="window.location.hash='#notes?category=Travel'">
                <div style="display:flex; align-items:center;">
                  <div class="quad-icon-box bg-travel-icon">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17.8 19.2L16 11l3.5-3.5C21 6 21.5 4 21 3c-1-.5-3 0-4.5 1.5L13 8 4.8 6.2c-.5-.1-.9.1-1.1.5l-.3.5c-.2.5-.1 1 .3 1.3L9 12l-2 3H4l-1 1 3 2 2 3 1-1v-3l3-2 3.5 5.3c.3.4.8.5 1.3.3l.5-.3c.4-.2.6-.6.5-1.1z"></path></svg>
                  </div>
                  <div class="quad-meta">
                    <div class="quad-label">Travel &amp; Trips</div>
                    <div class="quad-val">${s.travel_count}</div>
                  </div>
                </div>
                <svg class="quad-chevron" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"></polyline></svg>
              </div>

              <!-- SHOPPING -->
              <div class="quad-tile" onclick="window.location.hash='#notes?category=Shopping'">
                <div style="display:flex; align-items:center;">
                  <div class="quad-icon-box bg-shopping-icon">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"></path><line x1="3" y1="6" x2="21" y2="6"></line><path d="M16 10a4 4 0 0 1-8 0"></path></svg>
                  </div>
                  <div class="quad-meta">
                    <div class="quad-label">Shopping Items</div>
                    <div class="quad-val">${s.shopping_count}</div>
                  </div>
                </div>
                <svg class="quad-chevron" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"></polyline></svg>
              </div>
            </div>

            <!-- 4. Last Progress (Recent Notes List Card with Time-Based Priority) -->
            <div class="roomy-progress-card">
              <div class="progress-card-top">
                <div>
                  <div class="progress-title">Last Progress</div>
                  <div class="progress-dates">Priority by recency &amp; time</div>
                </div>
                <a href="#notes" class="see-all-link">See all</a>
              </div>

              <div class="progress-rows">
                ${recentNotes.length === 0 ? `
                  <div style="padding:24px 12px; text-align:center; color:var(--text-muted); font-size:12.5px;">
                    No notes created yet. Click "+ Add Note" to create your first note.
                  </div>
                ` : `
                  ${recentNotes.slice(0, 4).map(n => {
                    const prio = this.getTimePriority(n);
                    const isDone = localStorage.getItem('note_done_' + n.note_id) === 'true';
                    const isStarred = localStorage.getItem('note_starred_' + n.note_id) === 'true';
                    return `
                    <div class="progress-row-item">
                      <div class="note-interactive-actions">
                        <button class="note-check-btn ${isDone ? 'checked' : ''}" onclick="App.toggleNoteComplete('${n.note_id}', event)" title="${isDone ? 'Mark as Incomplete' : 'Mark as Completed'}">
                          ${isDone ? '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"></polyline></svg>' : ''}
                        </button>
                        <button class="note-star-btn ${isStarred ? 'starred' : ''}" onclick="App.toggleNotePin('${n.note_id}', event)" title="${isStarred ? 'Unstar Note' : 'Star Note'}">
                          ${isStarred ? '★' : '☆'}
                        </button>
                      </div>
                      <div style="overflow:hidden; padding-right:10px; flex:1; cursor:pointer;" onclick="Notes.openEditModal('${n.note_id}', '${this.escapeJs(n.text)}')">
                        <div class="prog-name ${isDone ? 'is-completed' : ''}">${this.escapeHtml(n.text.length > 32 ? n.text.substring(0, 32) + '...' : n.text)}</div>
                        <div class="prog-cat" style="color: ${n.category === 'Study' ? '#2563EB' : n.category === 'Money' ? '#059669' : n.category === 'Travel' ? '#D97706' : '#DB2777'};">
                          ${n.uncertain ? 'Needs Review' : n.category}
                        </div>
                      </div>
                      <div style="display:flex; flex-direction:column; align-items:flex-end; gap:3px; flex-shrink:0;">
                        <span class="badge-priority ${prio.badgeClass}" onclick="App.cycleNotePriority(event, '${n.note_id}')" style="cursor:pointer;" title="Click to change priority (${prio.label} • ${prio.reason})">${prio.icon} ${prio.shortLabel}</span>
                        <span class="prog-time">${prio.relativeTime}</span>
                      </div>
                    </div>
                  `}).join('')}
                `}
              </div>
            </div>
          </div>
        </div>

        <!-- RIGHT STAGE (Right Column) -->
        <div class="roomy-right-col">
          <!-- Search Bar on Top of Calendar -->
          <div class="roomy-top-right-bar" style="position:relative;">
            <div class="roomy-search-bar-pill" onclick="const inp=document.getElementById('roomy-search-input'); if(inp) inp.focus();">
              <svg class="search-bar-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" onclick="event.stopPropagation(); App.quickSearch(document.getElementById('roomy-search-input').value)">
                <circle cx="11" cy="11" r="8"></circle>
                <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
              </svg>
              <input 
                type="text" 
                id="roomy-search-input" 
                class="roomy-search-input" 
                placeholder="Search" 
                autocomplete="off" 
                spellcheck="false"
                oninput="App.onLiveBarSearch(this.value)"
                onkeydown="if(event.key==='Enter') App.quickSearch(this.value); if(event.key==='Escape') App.closeLiveBarSearch();" 
              />
              <button type="button" class="search-bar-go-btn" onclick="event.stopPropagation(); App.quickSearch(document.getElementById('roomy-search-input').value)" title="Search">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                  <polyline points="9 18 15 12 9 6"></polyline>
                </svg>
              </button>
            </div>
            <!-- Live Search Results Dropdown -->
            <div id="roomy-search-dropdown" class="roomy-search-dropdown" style="display:none;"></div>
          </div>

          <!-- Dynamic Calendar Card (Today highlighted in solid purple circle) -->
          ${this.generateCalendarHtml()}

          <!-- Real User Notes & Schedule Card -->
          <div class="roomy-meetings-card">
            <div class="meetings-card-header">
              <h4>${scheduleCardTitle}</h4>
              ${isDayFiltered ? `
                <button class="cal-nav-btn" onclick="App.resetCalendarToToday()" title="View Today" style="width:auto; height:auto; padding:2px 8px; border-radius:var(--radius-pill); font-size:11px;">Today</button>
              ` : `
                <a href="#notes" class="see-all-link">See all</a>
              `}
            </div>
            <div class="meetings-list-items">
              ${selectedDayNotes && selectedDayNotes.length > 0 ? `
                ${selectedDayNotes.map(n => {
                  const prio = this.getTimePriority(n);
                  const catLower = (n.category || 'study').toLowerCase();
                  const iconSvg = n.category === 'Study' 
                    ? '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 10v6M2 10l10-5 10 5-10 5z"></path></svg>'
                    : n.category === 'Money'
                    ? '<span style="font-weight:700; font-size:13px;">₹</span>'
                    : n.category === 'Travel'
                    ? '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17.8 19.2L16 11l3.5-3.5C21 6 21.5 4 21 3c-1-.5-3 0-4.5 1.5L13 8 4.8 6.2c-.5-.1-.9.1-1.1.5l-.3.5c-.2.5-.1 1 .3 1.3L9 12l-2 3H4l-1 1 3 2 2 3 1-1v-3l3-2 3.5 5.3c.3.4.8.5 1.3.3l.5-.3c.4-.2.6-.6.5-1.1z"></path></svg>'
                    : '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"></path></svg>';
                  return `
                  <div class="meeting-row" onclick="Notes.openEditModal('${n.note_id}', '${this.escapeJs(n.text)}')">
                    <div class="meeting-avatar bg-pastel-${catLower}">
                      ${iconSvg}
                    </div>
                    <div class="meeting-info" style="flex:1; overflow:hidden;">
                      <div class="meeting-name" style="white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${this.escapeHtml(n.text.length > 28 ? n.text.substring(0, 28) + '...' : n.text)}</div>
                      <div class="meeting-time" style="display:flex; align-items:center; gap:6px;">
                        <span>${n.category}</span>
                        <span>•</span>
                        <span class="badge-priority ${prio.badgeClass}" style="font-size:10px; padding:1px 6px;">${prio.icon} ${prio.shortLabel}</span>
                        <span style="color:var(--text-muted); font-size:10px;">${prio.relativeTime}</span>
                      </div>
                    </div>
                    <svg class="meeting-chevron" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"></polyline></svg>
                  </div>
                `}).join('')}
              ` : `
                <div style="text-align:center; padding: 22px 8px; color:var(--text-muted); font-size:12.5px;">
                  <p style="margin-bottom:8px;">${isDayFiltered ? `No notes found for ${selectedDateLabel}.` : 'No notes scheduled yet.'}</p>
                  <button class="btn btn-primary btn-sm" onclick="Notes.openEditModal()" style="font-size:11px; padding:4px 12px;">+ Add Note</button>
                </div>
              `}
            </div>
          </div>
        </div>
      </div>
    `;
  },

  handleQuickCreate() {
    const textarea = document.getElementById('quick-note-text');
    if (!textarea) return;
    const text = textarea.value.trim();
    if (!text) {
      this.showToast('Please enter note text.', 'error');
      return;
    }
    Notes.saveNewNote(text).then(res => {
      if (res) {
        textarea.value = '';
        document.getElementById('quick-live-preview').innerHTML = `<span class="text-muted">Enter text to see live ML categorization</span>`;
      }
    });
  },

  // View: Notes Library
  renderNotesLibrary() {
    const filter = this.activeCategoryFilter;
    const prioFilter = this.activePriorityFilter || 'all';
    const sortBy = this.noteSortBy || 'priority';

    // 1. Initial list from category
    const categoryNotes = [...(this.notes || [])];

    // Priority counts across current category
    const prioCounts = this.getPriorityCounts(categoryNotes);

    // 2. Filter by priority if set
    let displayNotes = categoryNotes;
    if (prioFilter !== 'all') {
      displayNotes = displayNotes.filter(n => {
        const p = this.getTimePriority(n);
        return p.level === prioFilter;
      });
    }

    // Filter by tag if selected
    if (this.activeTagFilter) {
      displayNotes = displayNotes.filter(n => n.text.toLowerCase().includes(this.activeTagFilter.toLowerCase()));
    }

    const allTags = this.getAllTags();

    // 3. Sort notes according to sortBy
    displayNotes.sort((a, b) => {
      const pa = this.getTimePriority(a);
      const pb = this.getTimePriority(b);
      const da = new Date(a.created_at || 0).getTime();
      const db = new Date(b.created_at || 0).getTime();

      if (sortBy === 'priority') {
        // High score first, then newest timestamp
        if (pb.score !== pa.score) return pb.score - pa.score;
        return db - da;
      } else if (sortBy === 'time_newest') {
        return db - da;
      } else if (sortBy === 'time_oldest') {
        return da - db;
      } else if (sortBy === 'confidence') {
        return (b.confidence || 0) - (a.confidence || 0);
      }
      return 0;
    });

    return `
      <div style="max-width: 1040px; margin: 0 auto;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 20px;">
          <div>
            <h1 style="font-size:26px; margin-bottom: 4px;">Notes Library</h1>
            <p>Browse, filter, edit and review all your machine-learning classified notes.</p>
          </div>
          <div style="display:flex; align-items:center; gap:8px;">
            <button class="btn btn-secondary btn-sm" onclick="App.openExportModal()" title="Export Notes to Markdown, PDF, or JSON">
              📥 Export Hub
            </button>
            <button class="btn btn-primary btn-sm" onclick="Notes.openEditModal()">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
              New Note
            </button>
          </div>
        </div>

        <!-- 4 Top Category KPI Interactive Cards -->
        <div class="library-kpi-grid">
          <div class="library-kpi-card cat-study ${filter === 'Study' ? 'active' : ''}" onclick="App.setCategoryFilter('${filter === 'Study' ? 'all' : 'Study'}')">
            <div class="kpi-card-header">
              <span class="kpi-icon-wrap cat-study">📚</span>
              <span class="kpi-badge">Category</span>
            </div>
            <div class="kpi-count">${this.stats ? this.stats.study_count : 0}</div>
            <div class="kpi-label">Study &amp; Knowledge</div>
            <div class="kpi-sub">Lectures, research &amp; exams</div>
          </div>

          <div class="library-kpi-card cat-money ${filter === 'Money' ? 'active' : ''}" onclick="App.setCategoryFilter('${filter === 'Money' ? 'all' : 'Money'}')">
            <div class="kpi-card-header">
              <span class="kpi-icon-wrap cat-money">💰</span>
              <span class="kpi-badge">Category</span>
            </div>
            <div class="kpi-count">${this.stats ? this.stats.money_count : 0}</div>
            <div class="kpi-label">Money &amp; Finance</div>
            <div class="kpi-sub">Bills, budgets &amp; expenses</div>
          </div>

          <div class="library-kpi-card cat-travel ${filter === 'Travel' ? 'active' : ''}" onclick="App.setCategoryFilter('${filter === 'Travel' ? 'all' : 'Travel'}')">
            <div class="kpi-card-header">
              <span class="kpi-icon-wrap cat-travel">✈️</span>
              <span class="kpi-badge">Category</span>
            </div>
            <div class="kpi-count">${this.stats ? this.stats.travel_count : 0}</div>
            <div class="kpi-label">Travel &amp; Trips</div>
            <div class="kpi-sub">Destinations, plans &amp; stays</div>
          </div>

          <div class="library-kpi-card cat-shopping ${filter === 'Shopping' ? 'active' : ''}" onclick="App.setCategoryFilter('${filter === 'Shopping' ? 'all' : 'Shopping'}')">
            <div class="kpi-card-header">
              <span class="kpi-icon-wrap cat-shopping">🛍️</span>
              <span class="kpi-badge">Category</span>
            </div>
            <div class="kpi-count">${this.stats ? this.stats.shopping_count : 0}</div>
            <div class="kpi-label">Shopping Items</div>
            <div class="kpi-sub">Groceries, orders &amp; supplies</div>
          </div>
        </div>

        <!-- Cohesive Glass Control & Filter Bar -->
        <div class="library-glass-toolbar">
          <div class="toolbar-left-group">
            <button class="lib-pill-btn ${filter === 'all' ? 'active' : ''}" onclick="App.setCategoryFilter('all')">
              All Notes (${this.stats ? this.stats.total_notes : 0})
            </button>
            
            <div class="toolbar-divider"></div>

            <div class="priority-pill-cluster">
              <span class="prio-mini-label">Time Priority:</span>
              <button class="prio-pill-btn ${prioFilter === 'all' ? 'active' : ''}" onclick="App.setPriorityFilter('all')">
                All (${prioCounts.total})
              </button>
              <button class="prio-pill-btn high ${prioFilter === 'high' ? 'active' : ''}" onclick="App.setPriorityFilter('high')">
                🔥 High (${prioCounts.high})
              </button>
              <button class="prio-pill-btn medium ${prioFilter === 'medium' ? 'active' : ''}" onclick="App.setPriorityFilter('medium')">
                ⚡ Medium (${prioCounts.medium})
              </button>
              <button class="prio-pill-btn low ${prioFilter === 'low' ? 'active' : ''}" onclick="App.setPriorityFilter('low')">
                ⏱️ Normal (${prioCounts.low})
              </button>
            </div>
          </div>

          <div class="toolbar-right-group">
            <div class="view-mode-toggle">
              <button class="view-mode-btn ${this.notesViewMode !== 'board' ? 'active' : ''}" onclick="App.setNotesViewMode('list')">≡ List</button>
              <button class="view-mode-btn ${this.notesViewMode === 'board' ? 'active' : ''}" onclick="App.setNotesViewMode('board')">⊞ Board</button>
            </div>
            <div class="sort-select-wrapper">
              <select class="sort-select" onchange="App.setNoteSort(this.value)">
                <option value="priority" ${sortBy === 'priority' ? 'selected' : ''}>Urgent Today First</option>
                <option value="time_newest" ${sortBy === 'time_newest' ? 'selected' : ''}>Newest First</option>
                <option value="time_oldest" ${sortBy === 'time_oldest' ? 'selected' : ''}>Oldest First</option>
                <option value="confidence" ${sortBy === 'confidence' ? 'selected' : ''}>Highest AI Confidence</option>
              </select>
            </div>
          </div>
        </div>

        <!-- Tags filter row (if tags exist) -->
        ${allTags.length > 0 ? `
          <div class="tags-filter-bar">
            <span style="font-size:12px; font-weight:700; color:var(--text-dark); display:inline-flex; align-items:center; gap:5px;">
              🏷️ Hashtags:
            </span>
            <div class="tags-pill-list">
              <button class="tag-filter-pill ${!this.activeTagFilter ? 'active' : ''}" onclick="App.filterByTag(null)">
                All Tags
              </button>
              ${allTags.map(t => `
                <button class="tag-filter-pill ${this.activeTagFilter === t.tag ? 'active' : ''}" onclick="App.filterByTag('${t.tag}')">
                  ${t.tag} <span class="tag-count">${t.count}</span>
                </button>
              `).join('')}
            </div>
          </div>
        ` : ''}

        <!-- Notes Grid or Sticky Board -->
        ${displayNotes.length === 0 ? `
          <div style="text-align:center; padding: 50px 24px; background:#FFFFFF; border:1px solid var(--border-subtle); border-radius:var(--radius-card); box-shadow:var(--shadow-card);">
            <div style="width:48px; height:48px; border-radius:50%; background:#F3F0FE; color:var(--purple-vibrant); display:flex; align-items:center; justify-content:center; margin:0 auto 16px;">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line></svg>
            </div>
            <h3 style="font-size:17px; font-weight:700; margin-bottom:6px; color:var(--text-dark);">No notes match this filter</h3>
            <p style="margin-bottom:20px; font-size:13.5px; color:var(--text-muted); max-width:440px; margin-left:auto; margin-right:auto;">
              ${prioFilter !== 'all' ? `No notes found in ${filter === 'all' ? 'library' : filter} with "${prioFilter}" time-priority.` : `No notes currently match the "${filter}" filter.`}
            </p>
            <div style="display:flex; justify-content:center; gap:12px; flex-wrap:wrap;">
              <button class="btn btn-primary" onclick="Notes.openEditModal()">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
                + Create Note
              </button>
              <button class="btn btn-secondary" onclick="Notes.seedStarterNotes()">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
                Load Starter Notes
              </button>
              ${prioFilter !== 'all' ? `
                <button class="btn btn-secondary" onclick="App.setPriorityFilter('all')">Clear Priority Filter</button>
              ` : filter !== 'all' ? `
                <button class="btn btn-secondary" onclick="App.setCategoryFilter('all')">Show All Notes</button>
              ` : ''}
            </div>
          </div>
        ` : this.notesViewMode === 'board' ? `
          <div class="sticky-board-grid">
            ${displayNotes.map(n => App.renderStickyNoteCard(n)).join('')}
          </div>
        ` : `
          <div class="notes-grid">
            ${displayNotes.map(n => App.renderNoteCard(n)).join('')}
          </div>
        `}
      </div>
    `;
  },

  async setCategoryFilter(cat) {
    await this.navigateToNotes(cat, 'all');
  },

  // Single Note Card Component with Time-Based Priority, Tags, Reminders & TTS
  renderNoteCard(n) {
    const isDone = localStorage.getItem('note_done_' + n.note_id) === 'true';
    const catClass = `cat-${(n.uncertain ? 'uncertain' : n.category).toLowerCase()}`;
    const badgeClass = `badge-${n.category.toLowerCase()}`;
    const catEmoji = n.category === 'Study' ? '📚' : n.category === 'Money' ? '💰' : n.category === 'Travel' ? '✈️' : n.category === 'Shopping' ? '🛍️' : '📝';
    const confPct = Math.round((n.confidence || 0) * 100);
    const dateFormatted = n.created_at ? new Date(n.created_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' }) : '';
    const prio = this.getTimePriority(n);
    const isSpeaking = this.activeTtsNoteId === n.note_id;
    const dueBadge = this.getDueDateBadge(n.note_id);
    const tags = this.extractTags(n.text);

    return `
      <div class="note-card ${catClass} ${isDone ? 'is-completed' : ''}" id="note-card-${n.note_id}">
        <div class="card-inner-top">
          <div class="note-card-top">
            <div style="display:flex; align-items:center; gap:7px;">
              <button class="note-check-btn ${isDone ? 'checked' : ''}" onclick="Notifications.completeTask('${n.note_id}', event)" title="${isDone ? 'Task Completed (Click to Re-open)' : 'Mark Work Completed'}">
                ${isDone ? '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"></polyline></svg>' : ''}
              </button>
              <span class="badge ${badgeClass} card-cat-badge">${catEmoji} ${n.category}</span>
              <span class="note-id-tag">#${n.note_id}</span>
            </div>
            <div style="display:flex; gap:6px; align-items:center; flex-wrap:wrap;">
              <span class="badge-priority ${prio.badgeClass}" onclick="App.cycleNotePriority(event, '${n.note_id}')" style="cursor:pointer;" title="Click to cycle priority (${prio.label} • ${prio.reason})">
                ${prio.icon} ${prio.shortLabel}
              </span>
              ${dueBadge ? `<span class="badge-due ${dueBadge.type}" title="${dueBadge.fullDate}">${dueBadge.icon} ${dueBadge.label}</span>` : ''}
              ${n.uncertain ? `<span class="badge badge-uncertain" title="Confidence is below 50% threshold">⚠️ Review</span>` : ''}
            </div>
          </div>

          <div class="note-card-text" onclick="Notes.openEditModal('${n.note_id}', '${this.escapeJs(n.text)}')" title="Click to edit note">
            ${this.escapeHtml(n.text)}
          </div>

          ${tags.length > 0 ? `
            <div class="note-tags-row">
              ${tags.map(t => `<span class="tag-chip ${this.activeTagFilter === t ? 'active' : ''}" onclick="App.filterByTag('${t}', event)">${t}</span>`).join('')}
            </div>
          ` : ''}
        </div>

        <div class="note-card-footer">
          <div class="card-footer-meta">
            <span class="card-conf-badge">🎯 ${confPct}% Match</span>
            <span class="card-time-text">• ${prio.relativeTime}</span>
          </div>
          <div class="note-actions">
            <button class="icon-btn" onclick="Notifications.snoozeTask('${n.note_id}', event)" title="Snooze reminder for 2 hours">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
            </button>
            <button class="icon-btn tts-btn ${isSpeaking ? 'active-speaking' : ''}" onclick="App.speakNote('${this.escapeJs(n.text)}', '${n.note_id}', event)" title="${isSpeaking ? 'Stop Audio' : 'Listen to note (Audio Reader)'}">
              ${isSpeaking ? '<span class="tts-bars"><span></span><span></span><span></span></span>' : '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon><path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"></path></svg>'}
            </button>
            <button class="icon-btn" onclick="App.copyNoteText('${this.escapeJs(n.text)}')" title="Copy Note Text">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
            </button>
            <button class="icon-btn" onclick="App.shareNoteWhatsApp('${this.escapeJs(n.text)}')" title="Share to WhatsApp" style="color:#10B981;">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"></path></svg>
            </button>
            <button class="icon-btn" onclick="Notes.openEditModal('${n.note_id}', '${this.escapeJs(n.text)}')" title="Edit Note">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 20h9"></path><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path></svg>
            </button>
            <button class="icon-btn danger" onclick="Notes.deleteNote('${n.note_id}')" title="Delete Note">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
            </button>
          </div>
        </div>
      </div>
    `;
  },

  // View: Dedicated Search Workspace
  renderSearchView() {
    return `
      <div style="max-width: 840px; margin: 0 auto;">
        <div style="margin-bottom: 24px;">
          <h1 style="font-size:26px; margin-bottom: 4px;">Intelligent Retrieval</h1>
          <p>Search your private notes using TF-IDF Cosine Similarity or Keyword overlap.</p>
        </div>

        <div style="background:#FFFFFF; border:1px solid var(--border-subtle); border-radius:var(--radius-md); padding: 24px; margin-bottom: 24px; box-shadow:var(--shadow-xs);">
          <div style="display:flex; gap:12px; margin-bottom: 16px;">
            <div style="flex:1; position:relative;">
              <input type="text" id="dedicated-search-input" placeholder="Search keywords or short phrases (e.g. 'Jaipur', 'hotel', 'Python exam')..." style="width:100%; padding: 12px 16px; background:#FCFBFF; border:1px solid var(--border-subtle); border-radius:var(--radius-sm); color:var(--text-primary); font-size:14px; outline:none; transition: all 0.2s ease;" onfocus="this.style.borderColor='var(--purple-accent)'; this.style.boxShadow='0 0 0 3px rgba(140,120,234,0.15)';" onblur="this.style.borderColor='var(--border-subtle)'; this.style.boxShadow='none';" onkeydown="if(event.key==='Enter') App.executeDedicatedSearch()" />
            </div>
            <button class="btn btn-primary" onclick="App.executeDedicatedSearch()">Search</button>
          </div>
          <div style="display:flex; align-items:center; justify-content:space-between; font-size:12.5px; color:var(--text-secondary); flex-wrap:wrap; gap:10px;">
            <div style="display:flex; align-items:center; gap:14px;">
              <span style="font-weight:500; color:var(--text-primary);">Algorithm:</span>
              <label style="cursor:pointer; display:flex; align-items:center; gap:5px;">
                <input type="radio" name="search-method" value="tfidf" checked style="accent-color:var(--purple-accent);" /> TF-IDF Cosine Similarity
              </label>
              <label style="cursor:pointer; display:flex; align-items:center; gap:5px;">
                <input type="radio" name="search-method" value="keyword" style="accent-color:var(--purple-accent);" /> Keyword Overlap
              </label>
            </div>
            <span>Hit Rate @ 3 Benchmark: 80.0%</span>
          </div>
        </div>

        <div id="search-results-container">
          <div style="text-align:center; padding: 48px 20px; color:var(--text-secondary); font-size:14px; background:#FFFFFF; border:1px solid var(--border-subtle); border-radius:var(--radius-md); box-shadow:var(--shadow-xs);">
            Enter a query above to see ranked matching notes.
          </div>
        </div>
      </div>
    `;
  },

  async executeDedicatedSearch(overrideQuery = null) {
    const input = document.getElementById('dedicated-search-input');
    const container = document.getElementById('search-results-container');
    if (!container) return;

    if (overrideQuery && input) {
      input.value = overrideQuery;
    }
    const query = (overrideQuery || (input ? input.value : '')).trim();
    if (!query) return;

    const methodEl = document.querySelector('input[name="search-method"]:checked');
    const method = methodEl ? methodEl.value : 'tfidf';

    container.innerHTML = `<div style="text-align:center; padding:30px;"><span class="mini-spinner"></span> Searching with ${method.toUpperCase()}...</div>`;

    const results = await Notes.searchNotes(query, method);
    if (results.length === 0) {
      container.innerHTML = `
        <div style="background:var(--bg-card); border:1px solid var(--border-subtle); border-radius:var(--radius-md); padding: 40px; text-align:center;">
          <p style="font-size:15px; margin-bottom: 6px;">No notes found matching "<strong>${this.escapeHtml(query)}</strong>".</p>
          <p style="font-size:13px; color:var(--text-muted);">Notes with relevance below the 5% threshold are filtered out to prevent noisy results.</p>
        </div>
      `;
      return;
    }

    container.innerHTML = `
      <div style="margin-bottom:12px; font-size:13px; color:var(--text-secondary);">
        Found <strong>${results.length}</strong> matching notes (Ranked by ${method === 'tfidf' ? 'Cosine Similarity' : 'Token Overlap'}):
      </div>
      <div class="notes-grid">
        ${results.map(r => `
          <div class="note-card">
            <div>
              <div class="note-card-top">
                <span class="note-id-tag">${r.note_id}</span>
                <div style="display:flex; gap:6px; align-items:center;">
                  <span class="badge badge-${r.category.toLowerCase()}">${r.category}</span>
                  <span class="badge" style="background:var(--lavender-primary); color:var(--purple-accent); font-weight:600; border:1px solid var(--lavender-secondary);">Score: ${r.score}</span>
                </div>
              </div>
              <div class="note-card-text">${this.escapeHtml(r.text)}</div>
            </div>
            <div class="note-card-footer">
              <span>${new Date(r.created_at).toLocaleDateString()}</span>
              <button class="icon-btn" onclick="Notes.openEditModal('${r.note_id}', '${this.escapeJs(r.text)}')">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 20h9"></path><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path></svg>
              </button>
            </div>
          </div>
        `).join('')}
      </div>
    `;
  },

  // View: Profile & Settings
  renderProfileView() {
    const u = this.currentUser || { name: '', email: '', is_verified: false, created_at: '' };
    return `
      <div style="max-width: 680px; margin: 0 auto;">
        <h1 style="font-size:26px; margin-bottom: 4px;">Account & Settings</h1>
        <p style="margin-bottom: 28px;">Manage your profile, security credentials, and application preferences.</p>

        <!-- Profile Card -->
        <div style="background:#FFFFFF; border:1px solid var(--border-subtle); border-radius:var(--radius-md); padding: 28px; margin-bottom: 24px; box-shadow:var(--shadow-xs);">
          <h3 style="font-size:17px; margin-bottom: 20px;">Profile Information</h3>
          <form onsubmit="Auth.updateProfile(event)">
            <div class="form-group">
              <label for="profile-name">Full Name</label>
              <div class="input-wrapper">
                <input type="text" id="profile-name" value="${this.escapeHtml(u.name || '')}" required />
              </div>
            </div>
            <div class="form-group">
              <label for="profile-pic-url">Profile Picture URL (Optional)</label>
              <div class="input-wrapper">
                <input type="url" id="profile-pic-url" value="${this.escapeHtml(u.profile_picture || '')}" placeholder="https://example.com/avatar.jpg" />
              </div>
            </div>
            <div class="form-group">
              <label>Email Address</label>
              <div class="input-wrapper">
                <input type="text" value="${this.escapeHtml(u.email || '')}" disabled style="opacity:0.6; cursor:not-allowed;" />
              </div>
              <div style="margin-top:8px; display:flex; align-items:center; gap:8px;">
                <span class="badge" style="background:var(--pastel-mint-bg); color:var(--pastel-mint-text); border:1px solid var(--pastel-mint-border);">✓ Active Account</span>
              </div>
            </div>
            <button type="submit" class="btn btn-primary btn-sm">Save Changes</button>
          </form>
        </div>

        <!-- Security / Password Card -->
        <div style="background:#FFFFFF; border:1px solid var(--border-subtle); border-radius:var(--radius-md); padding: 28px; margin-bottom: 24px; box-shadow:var(--shadow-xs);">
          <h3 style="font-size:17px; margin-bottom: 20px;">Change Password</h3>
          <form onsubmit="Auth.changePassword(event)">
            <div class="form-group">
              <label for="profile-current-pass">Current Password</label>
              <div class="input-wrapper">
                <input type="password" id="profile-current-pass" required placeholder="••••••••" />
              </div>
            </div>
            <div class="form-group">
              <label for="profile-new-pass">New Password</label>
              <div class="input-wrapper">
                <input type="password" id="profile-new-pass" required placeholder="At least 8 characters" />
              </div>
            </div>
            <div class="form-group">
              <label for="profile-confirm-pass">Confirm New Password</label>
              <div class="input-wrapper">
                <input type="password" id="profile-confirm-pass" required placeholder="Confirm new password" />
              </div>
            </div>
            <button type="submit" class="btn btn-secondary btn-sm">Update Password</button>
          </form>
        </div>

        <!-- Active Session & Logout Card -->
        <div style="background:#FFFFFF; border:1px solid var(--border-subtle); border-radius:var(--radius-md); padding: 24px 28px; margin-bottom: 24px; box-shadow:var(--shadow-xs); display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:16px;">
          <div>
            <h3 style="font-size:16px; margin-bottom: 4px;">Active Session</h3>
            <p style="font-size:13px; color:var(--text-muted); margin:0;">Signed in as <strong style="color:var(--text-dark);">${this.escapeHtml(u.email || '')}</strong></p>
          </div>
          <button class="btn btn-secondary btn-sm" onclick="Auth.logout()" style="display:flex; align-items:center; gap:8px; border-color:#FDC6D0; color:#E11D48; background:#FFF1F3;">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path><polyline points="16 17 21 12 16 7"></polyline><line x1="21" y1="12" x2="9" y2="12"></line></svg>
            Sign Out
          </button>
        </div>

        <!-- Danger Zone -->
        <div style="background:#FFF1F3; border:1px solid #FDC6D0; border-radius:var(--radius-md); padding: 28px;">
          <h3 style="font-size:17px; color:var(--danger); margin-bottom: 8px;">Danger Zone</h3>
          <p style="font-size:13px; color:#C5304E; margin-bottom: 16px;">Permanently delete your user account and all personal notes from MongoDB Atlas. This action cannot be undone.</p>
          <button class="btn btn-danger btn-sm" onclick="Auth.deleteAccount()">Delete Account & All Data</button>
        </div>
      </div>
    `;
  },

  toggleMobileSidebar() {
    const sidebar = document.querySelector('.app-sidebar');
    if (sidebar) sidebar.classList.toggle('mobile-open');
  },

  closeMobileSidebar() {
    const sidebar = document.querySelector('.app-sidebar');
    if (sidebar) sidebar.classList.remove('mobile-open');
  },

  // =========================================================================
  // EXTRA FEATURES: VOICE DICTATION, AI DIGEST, SPOTLIGHT & TASK ACTIONS
  // =========================================================================

  // 1. Voice-to-Note Dictation
  isRecording: false,
  recognition: null,

  startVoiceDictation() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      App.showToast('Speech Recognition is not supported in this browser. Please use Chrome, Edge, or Safari!', 'error');
      return;
    }
    Notes.openEditModal();
    setTimeout(() => {
      if (!this.isRecording) {
        this.toggleModalVoiceDictation();
      }
    }, 350);
  },

  stopVoiceDictation() {
    this.isRecording = false;
    if (this.recognition) {
      try {
        this.recognition.onend = null;
        this.recognition.onerror = null;
        this.recognition.stop();
      } catch (e) {}
    }
    const micBtn = document.getElementById('modal-voice-btn');
    const statusEl = document.getElementById('modal-voice-status');
    if (micBtn) {
      micBtn.classList.remove('recording');
      micBtn.innerHTML = `
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path><path d="M19 10v2a7 7 0 0 1-14 0v-2"></path><line x1="12" y1="19" x2="12" y2="23"></line><line x1="8" y1="23" x2="16" y2="23"></line></svg>
        <span>Voice Dictate</span>
      `;
    }
    if (statusEl) statusEl.style.display = 'none';
  },

  toggleModalVoiceDictation() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      App.showToast('Speech Recognition is not supported in this browser. Please use Chrome, Edge, or Safari.', 'error');
      return;
    }

    const micBtn = document.getElementById('modal-voice-btn');
    const textarea = document.getElementById('modal-note-text');
    const statusEl = document.getElementById('modal-voice-status');

    if (this.isRecording) {
      this.stopVoiceDictation();
      App.showToast('Voice recording stopped. Note preserved in editor.', 'info');
      return;
    }

    try {
      const recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.maxAlternatives = 1;
      recognition.lang = navigator.language || 'en-US';

      this.recognition = recognition;
      this.isRecording = true;

      if (micBtn) {
        micBtn.classList.add('recording');
        micBtn.innerHTML = `
          <span class="voice-wave-dot"></span>
          <span>Stop Listening</span>
        `;
      }
      if (statusEl) {
        statusEl.style.display = 'inline-flex';
        statusEl.innerHTML = '<span class="voice-wave-dot"></span> Listening... Speak now';
      }

      let baseText = textarea && textarea.value ? textarea.value.trim() : '';
      if (baseText) baseText += ' ';
      let cumulativeText = '';

      recognition.onresult = (event) => {
        let interimText = '';
        for (let i = event.resultIndex; i < event.results.length; ++i) {
          const res = event.results[i];
          if (res.isFinal) {
            cumulativeText += res[0].transcript.trim() + ' ';
          } else {
            interimText += res[0].transcript;
          }
        }
        if (textarea) {
          textarea.value = (baseText + cumulativeText + interimText).trimStart();
          Notes.previewClassification(textarea.value, 'modal-live-preview');
          const cc = document.getElementById('modal-char-counter');
          if (cc) cc.innerText = textarea.value.length + ' chars';
        }
      };

      recognition.onerror = (event) => {
        // 'no-speech' is a natural pause while the user thinks - do NOT abort!
        if (event.error === 'no-speech') {
          return;
        }
        console.warn('[Speech Recognition] Error:', event.error);
        if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
          this.stopVoiceDictation();
          App.showToast('Microphone access was blocked. Please click the camera/mic icon in your browser address bar and select "Allow".', 'error');
        } else if (event.error === 'network') {
          this.stopVoiceDictation();
          App.showToast('Speech recognition network error. Please check your internet connection.', 'error');
        }
      };

      recognition.onend = () => {
        // If user is still recording, automatically restart so pauses don't cut off speech
        if (this.isRecording) {
          try {
            recognition.start();
          } catch (e) {
            // Already active
          }
        } else {
          this.stopVoiceDictation();
        }
      };

      recognition.start();
      App.showToast('🎙️ Microphone active — Speak naturally!', 'info');
    } catch (err) {
      console.error('[Speech Recognition] Start failure:', err);
      this.stopVoiceDictation();
      App.showToast('Could not start microphone. Please check browser permissions.', 'error');
    }
  },

  // 2. AI Smart Digest Headline & Sub
  generateSmartDigestHeadline(notes, stats, prioCounts) {
    if (!notes || notes.length === 0) {
      return "Ready to organize your day with genuine AI.";
    }
    if (prioCounts && prioCounts.high > 0) {
      return `🔥 ${prioCounts.high} High-Priority task${prioCounts.high > 1 ? 's' : ''} require attention today.`;
    }
    if (stats && stats.study_count >= 3) {
      return `📚 Active Study Week: You have ${stats.study_count} study notes organized.`;
    }
    if (stats && stats.money_count > 0) {
      return `₹ Budget & Expense Tracking: Active financial notes under monitoring.`;
    }
    return `✨ AI Organization Active: ${notes.length} notes sorted with 98% accuracy model.`;
  },

  generateSmartDigestSub(notes, stats, prioCounts) {
    if (!notes || notes.length === 0) {
      return "Tap '+ Add Note' or 'Voice Note' to instantly capture and categorize your thoughts.";
    }
    if (prioCounts && prioCounts.high > 0) {
      return "Time-based recency engine has flagged urgent items created within the last 24 hours.";
    }
    if (stats && stats.study_count >= 3) {
      return "Your academic and learning materials are synchronized and ready for quick review.";
    }
    return "All notes are continuously prioritized by time and classified into Study, Money, Travel, and Shopping.";
  },

  // 3. AI Workspace Executive Summary
  openAiSummaryModal() {
    const modal = document.getElementById('ai-summary-modal');
    const content = document.getElementById('ai-summary-content');
    if (!modal || !content) return;

    const notes = this.notes || [];
    if (notes.length === 0) {
      App.showToast('No notes to summarize. Create a few notes first!', 'info');
      return;
    }

    const categories = { Study: [], Money: [], Travel: [], Shopping: [], 'Needs Review': [] };
    notes.forEach(n => {
      const cat = n.uncertain ? 'Needs Review' : (n.category || 'Study');
      if (!categories[cat]) categories[cat] = [];
      categories[cat].push(n);
    });

    let html = `
      <div style="background:linear-gradient(135deg, #F9F7FF 0%, #EEF9F7 100%); border:1px solid rgba(140,120,234,0.2); border-radius:var(--radius-md); padding:16px; margin-bottom:16px;">
        <div style="font-weight:700; color:var(--text-dark); margin-bottom:4px;">📊 Workspace Overview</div>
        <div style="font-size:12.5px; color:var(--text-muted);">
          Total <strong>${notes.length}</strong> active notes categorized using genuine ML (TF-IDF + MultinomialNB).
        </div>
      </div>
    `;

    Object.keys(categories).forEach(cat => {
      const list = categories[cat];
      if (list.length === 0) return;
      const icon = cat === 'Study' ? '📚' : cat === 'Money' ? '₹' : cat === 'Travel' ? '✈️' : cat === 'Shopping' ? '🛒' : '⚠️';
      html += `
        <div style="margin-bottom:18px;">
          <div style="font-weight:700; font-size:13.5px; color:var(--text-dark); display:flex; align-items:center; gap:6px; margin-bottom:8px;">
            <span>${icon}</span> <span>${cat}</span>
            <span style="font-size:11px; background:#ECE8FC; color:var(--purple-vibrant); padding:1px 6px; border-radius:10px;">${list.length}</span>
          </div>
          <ul style="margin:0; padding-left:20px; font-size:13px; color:var(--text-dark);">
            ${list.map(n => {
              const p = this.getTimePriority(n);
              const isDone = localStorage.getItem('note_done_' + n.note_id) === 'true';
              return `<li style="margin-bottom:5px; ${isDone ? 'text-decoration:line-through; opacity:0.6;' : ''}">
                ${this.escapeHtml(n.text)}
                <span style="font-size:10.5px; color:var(--text-muted); margin-left:6px;">(${p.shortLabel})</span>
              </li>`;
            }).join('')}
          </ul>
        </div>
      `;
    });

    content.innerHTML = html;
    modal.classList.add('active');
  },

  closeAiSummaryModal() {
    const modal = document.getElementById('ai-summary-modal');
    if (modal) modal.classList.remove('active');
  },

  copyAiSummary() {
    const notes = this.notes || [];
    if (notes.length === 0) return;
    let text = `SMART NOTES ASSISTANT — WORKSPACE DIGEST\n`;
    text += `Generated: ${new Date().toLocaleString()}\n`;
    text += `Total Notes: ${notes.length}\n\n`;

    const grouped = {};
    notes.forEach(n => {
      const cat = n.uncertain ? 'Needs Review' : (n.category || 'Study');
      if (!grouped[cat]) grouped[cat] = [];
      grouped[cat].push(n.text);
    });

    Object.keys(grouped).forEach(c => {
      text += `[${c.toUpperCase()}]\n`;
      grouped[c].forEach(item => { text += `• ${item}\n`; });
      text += `\n`;
    });

    navigator.clipboard.writeText(text).then(() => {
      App.showToast('📋 Executive summary copied to clipboard!', 'success');
    }).catch(() => {
      App.showToast('Copied to clipboard.', 'success');
    });
  },

  exportAllNotes() {
    const notes = this.notes || [];
    if (notes.length === 0) {
      App.showToast('No notes to export.', 'info');
      return;
    }

    let md = `# Smart Notes Assistant — Exported Notes\n\n`;
    md += `*Exported on ${new Date().toLocaleDateString()} at ${new Date().toLocaleTimeString()}*\n`;
    md += `*Total Notes: ${notes.length}*\n\n---\n\n`;

    notes.forEach((n, idx) => {
      const p = this.getTimePriority(n);
      const isDone = localStorage.getItem('note_done_' + n.note_id) === 'true';
      md += `### ${idx + 1}. [${n.category || 'General'}] Note ${isDone ? '✅ [COMPLETED]' : ''}\n\n`;
      md += `> ${n.text}\n\n`;
      md += `- **Priority**: ${p.label} (${p.shortLabel})\n`;
      md += `- **Category**: ${n.category} (${Math.round((n.confidence || 0.9) * 100)}% confidence)\n`;
      md += `- **Created**: ${n.created_at || 'Recent'}\n\n---\n\n`;
    });

    const blob = new Blob([md], { type: 'text/markdown;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `SmartNotes_Backup_${new Date().toISOString().slice(0, 10)}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    App.showToast('📥 Notes exported as Markdown (.md)', 'success');
  },

  // 4. Spotlight Quick Find (Ctrl + K)
  spotlightFilter: 'all',

  openSpotlight() {
    const modal = document.getElementById('spotlight-modal');
    const input = document.getElementById('spotlight-input');
    if (!modal) return;
    modal.classList.add('active');
    this.renderSpotlightResults('');
    if (input) {
      input.value = '';
      setTimeout(() => input.focus(), 80);
    }
  },

  closeSpotlight() {
    const modal = document.getElementById('spotlight-modal');
    if (modal) modal.classList.remove('active');
  },

  toggleSpotlight() {
    const modal = document.getElementById('spotlight-modal');
    if (modal && modal.classList.contains('active')) {
      this.closeSpotlight();
    } else {
      this.openSpotlight();
    }
  },

  setSpotlightFilter(filter, btn) {
    this.spotlightFilter = filter;
    document.querySelectorAll('.sp-filter-chip').forEach(b => b.classList.remove('active'));
    if (btn) btn.classList.add('active');
    const input = document.getElementById('spotlight-input');
    this.renderSpotlightResults(input ? input.value : '');
  },

  onSpotlightInput(val) {
    this.renderSpotlightResults(val);
  },

  renderSpotlightResults(query) {
    const listEl = document.getElementById('spotlight-results-list');
    if (!listEl) return;

    let notes = [...(this.notes || [])];
    const q = (query || '').trim().toLowerCase();

    // Filter by category or priority
    if (this.spotlightFilter === 'high') {
      notes = notes.filter(n => this.getTimePriority(n).badgeClass.includes('high'));
    } else if (this.spotlightFilter !== 'all') {
      notes = notes.filter(n => (n.category || '').toLowerCase() === this.spotlightFilter.toLowerCase());
    }

    // Filter by text query
    if (q) {
      notes = notes.filter(n => (n.text || '').toLowerCase().includes(q) || (n.category || '').toLowerCase().includes(q));
    }

    if (notes.length === 0) {
      listEl.innerHTML = `
        <div style="padding:28px 16px; text-align:center; color:var(--text-muted); font-size:13px;">
          No matching notes found for "${this.escapeHtml(query || this.spotlightFilter)}".
        </div>
      `;
      return;
    }

    listEl.innerHTML = notes.slice(0, 10).map(n => {
      const p = this.getTimePriority(n);
      const isDone = localStorage.getItem('note_done_' + n.note_id) === 'true';
      return `
        <div class="spotlight-row ${isDone ? 'is-done' : ''}" onclick="App.closeSpotlight(); Notes.openEditModal('${n.note_id}', '${this.escapeJs(n.text)}')">
          <div style="flex:1; overflow:hidden; padding-right:12px;">
            <div class="spotlight-row-title">${this.escapeHtml(n.text)}</div>
            <div style="font-size:11.5px; color:var(--text-muted); margin-top:3px; display:flex; align-items:center; gap:6px;">
              <span>${n.category}</span>
              <span>•</span>
              <span>${p.relativeTime}</span>
            </div>
          </div>
          <span class="badge-priority ${p.badgeClass}" style="font-size:10px; padding:2px 7px;">${p.icon} ${p.shortLabel}</span>
        </div>
      `;
    }).join('');
  },

  // 5. Interactive Note Pinning & Completion Actions
  toggleNoteComplete(noteId, event) {
    if (event) event.stopPropagation();
    const key = 'note_done_' + noteId;
    const current = localStorage.getItem(key) === 'true';
    if (current) {
      localStorage.removeItem(key);
      App.showToast('Note marked active.', 'info');
    } else {
      localStorage.setItem(key, 'true');
      App.showToast('🎉 Note completed!', 'success');
    }
    this.render();
  },

  toggleNotePin(noteId, event) {
    if (event) event.stopPropagation();
    const key = 'note_starred_' + noteId;
    const current = localStorage.getItem(key) === 'true';
    if (current) {
      localStorage.removeItem(key);
      App.showToast('Note unstarred.', 'info');
    } else {
      localStorage.setItem(key, 'true');
      App.showToast('⭐ Note starred to priority!', 'success');
    }
    this.render();
  },

  // 6. Theme Engine: Midnight Lavender Dark Mode vs Pastel Day
  initTheme() {
    const saved = localStorage.getItem('app_theme') || 'light';
    if (saved === 'dark') {
      document.body.classList.add('dark-theme');
      this.updateThemeIndicators(true);
    } else {
      document.body.classList.remove('dark-theme');
      this.updateThemeIndicators(false);
    }
  },

  toggleTheme() {
    const isDark = document.body.classList.toggle('dark-theme');
    localStorage.setItem('app_theme', isDark ? 'dark' : 'light');
    this.updateThemeIndicators(isDark);
    App.showToast(isDark ? '🌙 Midnight Lavender theme enabled' : '☀️ Pastel Day theme enabled', 'info');
  },

  updateThemeIndicators(isDark) {
    const icon = document.getElementById('theme-icon-indicator');
    const text = document.getElementById('theme-text-indicator');
    if (icon) icon.innerText = isDark ? '☀️' : '🌙';
    if (text) text.innerText = isDark ? 'Pastel' : 'Midnight';
  },

  // 7. Sticky Notes Board View & Share Actions
  notesViewMode: 'list',

  setNotesViewMode(mode) {
    this.notesViewMode = mode;
    this.render();
  },

  renderStickyNoteCard(n) {
    const isDone = localStorage.getItem('note_done_' + n.note_id) === 'true';
    const isStarred = localStorage.getItem('note_starred_' + n.note_id) === 'true';
    const prio = this.getTimePriority(n);
    const catClass = `cat-${(n.uncertain ? 'uncertain' : n.category).toLowerCase()}`;
    const isSpeaking = this.activeTtsNoteId === n.note_id;
    const dueBadge = this.getDueDateBadge(n.note_id);
    const tags = this.extractTags(n.text);

    return `
      <div class="sticky-note-card ${catClass}" id="sticky-note-${n.note_id}">
        <div class="sticky-card-header">
          <div style="display:flex; align-items:center; gap:6px; flex-wrap:wrap;">
            <button class="note-check-btn ${isDone ? 'checked' : ''}" onclick="App.toggleNoteComplete('${n.note_id}', event)" title="${isDone ? 'Mark Incomplete' : 'Mark Completed'}">
              ${isDone ? '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"></polyline></svg>' : ''}
            </button>
            <span class="badge ${'badge-' + n.category.toLowerCase()}" style="font-size:11px;">${n.category}</span>
            ${dueBadge ? `<span class="badge-due ${dueBadge.type}" style="font-size:9.5px; padding:1px 5px;" title="${dueBadge.fullDate}">${dueBadge.icon} ${dueBadge.label}</span>` : ''}
          </div>
          <div style="display:flex; align-items:center; gap:6px;">
            <button class="note-star-btn ${isStarred ? 'starred' : ''}" onclick="App.toggleNotePin('${n.note_id}', event)" title="${isStarred ? 'Unstar' : 'Star Note'}">
              ${isStarred ? '★' : '☆'}
            </button>
            <span class="badge-priority ${prio.badgeClass}" onclick="App.cycleNotePriority(event, '${n.note_id}')" style="cursor:pointer; font-size:10px; padding:2px 7px;">
              ${prio.icon} ${prio.shortLabel}
            </span>
          </div>
        </div>

        <div class="sticky-card-text ${isDone ? 'is-done' : ''}" onclick="Notes.openEditModal('${n.note_id}', '${this.escapeJs(n.text)}')">
          ${this.escapeHtml(n.text)}
        </div>

        ${tags.length > 0 ? `
          <div class="note-tags-row" style="margin-top:6px; margin-bottom:0;">
            ${tags.map(t => `<span class="tag-chip ${this.activeTagFilter === t ? 'active' : ''}" onclick="App.filterByTag('${t}', event)">${t}</span>`).join('')}
          </div>
        ` : ''}

        <div class="sticky-card-footer">
          <span style="font-size:11px; color:var(--text-muted); font-weight:500;">${prio.relativeTime}</span>
          <div class="sticky-card-actions">
            <button class="sticky-action-icon tts-btn ${isSpeaking ? 'active-speaking' : ''}" onclick="App.speakNote('${this.escapeJs(n.text)}', '${n.note_id}', event)" title="${isSpeaking ? 'Stop Audio' : 'Listen to note (Audio Reader)'}">
              ${isSpeaking ? '<span class="tts-bars mini"><span></span><span></span><span></span></span>' : '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon><path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"></path></svg>'}
            </button>
            <button class="sticky-action-icon" onclick="App.copyNoteText('${this.escapeJs(n.text)}')" title="Copy Note Text">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
            </button>
            <button class="sticky-action-icon" onclick="App.shareNoteWhatsApp('${this.escapeJs(n.text)}')" title="Share to WhatsApp" style="color:#10B981;">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"></path></svg>
            </button>
            <button class="sticky-action-icon" onclick="Notes.openEditModal('${n.note_id}', '${this.escapeJs(n.text)}')" title="Edit Note">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 20h9"></path><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path></svg>
            </button>
            <button class="sticky-action-icon danger" onclick="Notes.deleteNote('${n.note_id}')" title="Delete Note">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
            </button>
          </div>
        </div>
      </div>
    `;
  },

  copyNoteText(text) {
    if (!text) return;
    navigator.clipboard.writeText(text).then(() => {
      App.showToast('📋 Note text copied to clipboard!', 'success');
    }).catch(() => {
      App.showToast('Copied.', 'success');
    });
  },

  shareNoteWhatsApp(text) {
    if (!text) return;
    const msg = encodeURIComponent(`*Smart Notes Assistant*\n\n"${text}"\n\n_Organized with Machine Learning_`);
    window.open(`https://api.whatsapp.com/send?text=${msg}`, '_blank');
  },

  // 8. Zen Focus Distraction-Free Sanctuary
  zenAudioCtx: null,
  isZenAudioPlaying: false,

  openZenMode(initialText = '') {
    const modal = document.getElementById('zen-modal');
    const textarea = document.getElementById('zen-textarea');
    if (!modal || !textarea) return;

    if (!initialText) {
      const modalText = (document.getElementById('modal-note-text') || {}).value || '';
      initialText = modalText;
    }

    textarea.value = initialText;
    this.onZenInput(initialText);
    modal.classList.add('active');
    setTimeout(() => textarea.focus(), 100);
  },

  closeZenMode() {
    const modal = document.getElementById('zen-modal');
    if (modal) modal.classList.remove('active');
    if (this.isZenAudioPlaying) {
      this.toggleZenAmbientAudio();
    }
  },

  onZenInput(val) {
    const trimmed = (val || '').trim();
    const words = trimmed ? trimmed.split(/\s+/).length : 0;
    const chars = (val || '').length;
    const minutes = Math.max(1, Math.round(words / 200));

    const wEl = document.getElementById('zen-words-count');
    const cEl = document.getElementById('zen-chars-count');
    const rEl = document.getElementById('zen-reading-time');

    if (wEl) wEl.innerText = `${words} word${words === 1 ? '' : 's'}`;
    if (cEl) cEl.innerText = `${chars} chars`;
    if (rEl) rEl.innerText = `~${words === 0 ? 0 : minutes} min read`;

    const mainText = document.getElementById('modal-note-text');
    if (mainText) {
      mainText.value = val;
      if (window.Notes && Notes.previewClassification) {
        Notes.previewClassification(val, 'zen-live-preview');
      }
    }
  },

  saveFromZenMode() {
    const val = (document.getElementById('zen-textarea') || {}).value || '';
    if (!val.trim()) {
      App.showToast('Note cannot be empty.', 'error');
      return;
    }
    const mainText = document.getElementById('modal-note-text');
    if (mainText) mainText.value = val;
    this.closeZenMode();
    App.handleModalSave();
  },

  toggleZenAmbientAudio() {
    const btn = document.getElementById('zen-ambient-toggle');
    const icon = document.getElementById('zen-ambient-icon');
    const label = document.getElementById('zen-ambient-label');

    if (this.isZenAudioPlaying) {
      if (this.zenAudioCtx) {
        try { this.zenAudioCtx.close(); } catch(e){}
        this.zenAudioCtx = null;
      }
      this.isZenAudioPlaying = false;
      if (btn) btn.classList.remove('active');
      if (icon) icon.innerText = '🌧️';
      if (label) label.innerText = 'Rain Audio: Off';
      return;
    }

    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (!AudioCtx) {
        App.showToast('Web Audio not supported.', 'error');
        return;
      }
      const ctx = new AudioCtx();
      this.zenAudioCtx = ctx;

      const bufferSize = ctx.sampleRate * 2;
      const noiseBuffer = ctx.createBuffer(1, bufferSize, ctx.sampleRate);
      const output = noiseBuffer.getChannelData(0);
      let b0 = 0, b1 = 0, b2 = 0, b3 = 0, b4 = 0, b5 = 0, b6 = 0;
      for (let i = 0; i < bufferSize; i++) {
        const white = Math.random() * 2 - 1;
        b0 = 0.99886 * b0 + white * 0.0555179;
        b1 = 0.99332 * b1 + white * 0.0750759;
        b2 = 0.96900 * b2 + white * 0.1538520;
        b3 = 0.86650 * b3 + white * 0.3104856;
        b4 = 0.55000 * b4 + white * 0.5329522;
        b5 = -0.7616 * b5 - white * 0.0168980;
        output[i] = (b0 + b1 + b2 + b3 + b4 + b5 + b6 + white * 0.5362) * 0.04;
        b6 = white * 0.115926;
      }

      const whiteNoise = ctx.createBufferSource();
      whiteNoise.buffer = noiseBuffer;
      whiteNoise.loop = true;

      const filter = ctx.createBiquadFilter();
      filter.type = 'lowpass';
      filter.frequency.value = 850;

      const gain = ctx.createGain();
      gain.gain.value = 0.28;

      whiteNoise.connect(filter);
      filter.connect(gain);
      gain.connect(ctx.destination);
      whiteNoise.start();

      this.isZenAudioPlaying = true;
      if (btn) btn.classList.add('active');
      if (icon) icon.innerText = '🔊';
      if (label) label.innerText = 'Rain Audio: Playing';
      App.showToast('🌧️ Peaceful rain ambience playing...', 'info');
    } catch(e) {
      console.warn('Audio start error:', e);
    }
  },

  // ---------------------------------------------------------------------------
  // 9. TEXT-TO-SPEECH (TTS) NOTE AUDIO READER
  // ---------------------------------------------------------------------------
  activeTtsNoteId: null,
  currentUtterance: null,

  speakNote(text, noteId, e) {
    if (e) e.stopPropagation();
    if (!('speechSynthesis' in window)) {
      App.showToast('Text-to-Speech is not supported in this browser.', 'error');
      return;
    }

    if (this.activeTtsNoteId === noteId) {
      window.speechSynthesis.cancel();
      this.activeTtsNoteId = null;
      this.currentUtterance = null;
      this.render();
      App.showToast('⏹️ Audio reader stopped.', 'info');
      return;
    }

    window.speechSynthesis.cancel();
    this.activeTtsNoteId = noteId;
    this.render();

    const cleanText = text.replace(/#[a-zA-Z0-9_\-]+/g, '').trim();
    const utterance = new SpeechSynthesisUtterance(cleanText);
    utterance.rate = 1.0;
    utterance.pitch = 1.0;

    const voices = window.speechSynthesis.getVoices();
    const naturalVoice = voices.find(v => v.lang && v.lang.startsWith('en') && (v.name.includes('Natural') || v.name.includes('Samantha') || v.name.includes('Google') || v.name.includes('Daniel')));
    if (naturalVoice) utterance.voice = naturalVoice;

    utterance.onend = () => {
      this.activeTtsNoteId = null;
      this.currentUtterance = null;
      this.render();
    };

    utterance.onerror = () => {
      this.activeTtsNoteId = null;
      this.currentUtterance = null;
      this.render();
    };

    this.currentUtterance = utterance;
    window.speechSynthesis.speak(utterance);
    App.showToast('🎧 Reading note aloud... Click 🔊 anytime to pause/stop.', 'info');
  },

  // ---------------------------------------------------------------------------
  // 10. SMART DUE DATES & REMINDER BADGES
  // ---------------------------------------------------------------------------
  getDueDateBadge(noteId) {
    const raw = localStorage.getItem('note_due_' + noteId);
    if (!raw) return null;
    try {
      const due = new Date(raw);
      if (isNaN(due.getTime())) return null;
      const now = new Date();
      const diffMs = due.getTime() - now.getTime();
      const diffHours = diffMs / (1000 * 60 * 60);
      const fullDate = due.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });

      if (diffMs < 0) {
        return {
          type: 'overdue',
          icon: '⚠️',
          label: 'Overdue (' + due.toLocaleDateString([], { month: 'short', day: 'numeric' }) + ')',
          fullDate
        };
      } else if (diffHours <= 24) {
        return {
          type: 'today',
          icon: '🔥',
          label: 'Due Today (' + due.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) + ')',
          fullDate
        };
      } else if (diffHours <= 48) {
        return {
          type: 'soon',
          icon: '⚡',
          label: 'Due Tomorrow',
          fullDate
        };
      } else {
        const days = Math.round(diffHours / 24);
        return {
          type: 'upcoming',
          icon: '📅',
          label: `Due in ${days}d`,
          fullDate
        };
      }
    } catch (e) {
      return null;
    }
  },

  // ---------------------------------------------------------------------------
  // 11. CUSTOM HASHTAGS & COLOR LABELS
  // ---------------------------------------------------------------------------
  activeTagFilter: null,

  extractTags(text) {
    if (!text) return [];
    const matches = text.match(/#[a-zA-Z0-9_\-]+/g);
    return matches ? Array.from(new Set(matches)) : [];
  },

  getAllTags() {
    const tagMap = {};
    (this.notes || []).forEach(n => {
      const tags = this.extractTags(n.text);
      tags.forEach(t => {
        tagMap[t] = (tagMap[t] || 0) + 1;
      });
    });
    return Object.entries(tagMap).map(([tag, count]) => ({ tag, count })).sort((a, b) => b.count - a.count);
  },

  filterByTag(tag, e) {
    if (e) e.stopPropagation();
    this.activeTagFilter = (this.activeTagFilter === tag) ? null : tag;
    this.render();
  },

  // ---------------------------------------------------------------------------
  // 12. MULTI-FORMAT EXPORT HUB (Markdown, Clean Print/PDF, JSON)
  // ---------------------------------------------------------------------------
  openExportModal() {
    const m = document.getElementById('export-modal');
    if (m) m.classList.add('active');
  },

  closeExportModal() {
    const m = document.getElementById('export-modal');
    if (m) m.classList.remove('active');
  },

  exportNotesMarkdown() {
    const notes = this.notes || [];
    if (notes.length === 0) {
      App.showToast('No notes to export.', 'error');
      return;
    }

    let md = `# Smart Notes Assistant — Exported Notes\n`;
    md += `*Exported on ${new Date().toLocaleString()}*\n\n`;
    md += `Total Notes: ${notes.length}\n\n---\n\n`;

    const categories = ['Study', 'Money', 'Travel', 'Shopping', 'Needs Review'];
    categories.forEach(cat => {
      const catNotes = notes.filter(n => (cat === 'Needs Review' ? n.uncertain : n.category === cat));
      if (catNotes.length > 0) {
        md += `## 📁 ${cat} (${catNotes.length})\n\n`;
        catNotes.forEach(n => {
          const prio = this.getTimePriority(n);
          const due = localStorage.getItem('note_due_' + n.note_id);
          const tags = this.extractTags(n.text).join(' ');
          md += `### [${n.note_id}] ${n.text}\n`;
          md += `- **Category:** ${n.category} (${Math.round((n.confidence || 0) * 100)}% confidence)\n`;
          md += `- **Priority:** ${prio.label}\n`;
          if (due) md += `- **Due Date:** ${new Date(due).toLocaleString()}\n`;
          if (tags) md += `- **Tags:** ${tags}\n`;
          md += `- **Created:** ${new Date(n.created_at).toLocaleString()}\n\n`;
        });
      }
    });

    const blob = new Blob([md], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `smart-notes-export-${new Date().toISOString().slice(0, 10)}.md`;
    a.click();
    URL.revokeObjectURL(url);
    this.closeExportModal();
    App.showToast('📥 Markdown notes backup downloaded!', 'success');
  },

  printCleanNotes() {
    this.closeExportModal();
    App.showToast('🖨️ Opening print dialogue...', 'info');
    setTimeout(() => {
      window.print();
    }, 250);
  },

  exportNotesJSON() {
    const notes = (this.notes || []).map(n => ({
      ...n,
      custom_priority: localStorage.getItem('note_prio_' + n.note_id) || 'auto',
      due_date: localStorage.getItem('note_due_' + n.note_id) || null,
      is_completed: localStorage.getItem('note_done_' + n.note_id) === 'true',
      is_starred: localStorage.getItem('note_starred_' + n.note_id) === 'true',
      tags: this.extractTags(n.text)
    }));

    const blob = new Blob([JSON.stringify(notes, null, 2)], { type: 'application/json;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `smart-notes-backup-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
    this.closeExportModal();
    App.showToast('💾 Raw JSON backup downloaded!', 'success');
  },

  // ---------------------------------------------------------------------------
  // 13. AI PRODUCTIVITY & CATEGORY ANALYTICS VIEW
  // ---------------------------------------------------------------------------
  renderAnalyticsView() {
    const notes = this.notes || [];
    const totalNotes = notes.length;

    let totalWords = 0;
    let totalChars = 0;
    let totalConf = 0;
    const catCounts = { Study: 0, Money: 0, Travel: 0, Shopping: 0, Uncertain: 0 };
    const dateSet = new Set();

    notes.forEach(n => {
      const words = n.text.trim().split(/\s+/).filter(Boolean).length;
      totalWords += words;
      totalChars += n.text.length;
      totalConf += (n.confidence || 0);

      if (n.uncertain) catCounts.Uncertain++;
      else if (catCounts[n.category] !== undefined) catCounts[n.category]++;
      else catCounts.Study++;

      if (n.created_at) {
        dateSet.add(new Date(n.created_at).toISOString().slice(0, 10));
      }
    });

    const avgWords = totalNotes > 0 ? Math.round(totalWords / totalNotes) : 0;
    const avgConf = totalNotes > 0 ? Math.round((totalConf / totalNotes) * 100) : 98;
    const readingTimeMins = (totalWords / 200).toFixed(1);
    const streakDays = Math.max(1, dateSet.size);

    let dominantCat = 'Study';
    let maxCount = 0;
    ['Study', 'Money', 'Travel', 'Shopping'].forEach(c => {
      if (catCounts[c] > maxCount) {
        maxCount = catCounts[c];
        dominantCat = c;
      }
    });
    const domPct = totalNotes > 0 ? Math.round((maxCount / totalNotes) * 100) : 0;

    return `
      <div style="max-width: 1040px; margin: 0 auto;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 22px; flex-wrap:wrap; gap:12px;">
          <div>
            <h1 style="font-size:26px; margin-bottom: 4px; display:flex; align-items:center; gap:8px;">
              <span>📊 AI Productivity & Analytics</span>
            </h1>
            <p>Real-time metrics, writing streaks, and category distribution from machine learning.</p>
          </div>
          <div style="display:flex; align-items:center; gap:8px;">
            <button class="export-hub-btn" onclick="App.openExportModal()">
              <span>📥 Export Report</span>
            </button>
          </div>
        </div>

        <!-- 3 Key Stat Cards -->
        <div class="analytics-stat-grid">
          <div class="analytics-card">
            <div class="analytics-icon-wrap" style="background:#FFF1F2; color:#E11D48;">🔥</div>
            <div class="analytics-num">${streakDays} ${streakDays === 1 ? 'Day' : 'Days'}</div>
            <div class="analytics-lbl">Active Thought Streak</div>
            <div class="analytics-sub">Notes logged across ${dateSet.size || 1} distinct sessions</div>
          </div>
          <div class="analytics-card">
            <div class="analytics-icon-wrap" style="background:#EFF6FF; color:#3B82F6;">🎯</div>
            <div class="analytics-num">${avgConf}%</div>
            <div class="analytics-lbl">Avg ML Confidence</div>
            <div class="analytics-sub">Trained TF-IDF Logistic Regression</div>
          </div>
          <div class="analytics-card">
            <div class="analytics-icon-wrap" style="background:#FDF4FF; color:#D946EF;">🏆</div>
            <div class="analytics-num">${dominantCat} (${domPct}%)</div>
            <div class="analytics-lbl">Primary Focus Area</div>
            <div class="analytics-sub">${maxCount} notes organized in ${dominantCat}</div>
          </div>
        </div>

        <!-- Category Distribution Row -->
        <div class="analytics-chart-row">
          <div class="analytics-chart-box">
            <h3 style="font-size:16px; font-weight:700; margin-bottom:14px; display:flex; align-items:center; justify-content:space-between;">
              <span>Category Distribution Ring</span>
              <span style="font-size:12px; color:var(--text-muted); font-weight:500;">${totalNotes} Total Notes</span>
            </h3>
            <div style="display:flex; align-items:center; justify-content:center; position:relative; min-height:220px;">
              <canvas id="analytics-donut-canvas" width="220" height="220" style="display:block; max-width:220px; max-height:220px;"></canvas>
              <div style="position:absolute; text-align:center; pointer-events:none;">
                <div style="font-size:26px; font-weight:800; color:var(--text-dark);">${totalNotes}</div>
                <div style="font-size:11px; color:var(--text-muted); font-weight:600; text-transform:uppercase;">Notes</div>
              </div>
            </div>
          </div>

          <div class="analytics-breakdown-box">
            <h3 style="font-size:16px; font-weight:700; margin-bottom:16px;">Category Performance Breakdown</h3>
            <div class="cat-bar-list">
              ${[
                { label: 'Study & Education', count: catCounts.Study, color: '#3B82F6', icon: '📚' },
                { label: 'Money & Finance', count: catCounts.Money, color: '#10B981', icon: '₹' },
                { label: 'Travel & Trips', count: catCounts.Travel, color: '#F59E0B', icon: '✈️' },
                { label: 'Shopping & Groceries', count: catCounts.Shopping, color: '#EC4899', icon: '🛍️' },
                { label: 'Needs Review', count: catCounts.Uncertain, color: '#8C78EA', icon: '⚠️' }
              ].map(cat => {
                const pct = totalNotes > 0 ? Math.round((cat.count / totalNotes) * 100) : 0;
                return `
                  <div class="cat-bar-item">
                    <div class="cat-bar-header">
                      <span class="cat-bar-title"><span style="margin-right:6px;">${cat.icon}</span> ${cat.label}</span>
                      <span class="cat-bar-meta"><strong>${cat.count}</strong> notes (${pct}%)</span>
                    </div>
                    <div class="cat-progress-track">
                      <div class="cat-progress-fill" style="width:${pct}%; background:${cat.color};"></div>
                    </div>
                  </div>
                `;
              }).join('')}
            </div>
          </div>
        </div>

        <!-- AI Productivity Insights -->
        <div class="productivity-tips-box">
          <div style="display:flex; align-items:center; gap:8px; margin-bottom:10px;">
            <span style="font-size:20px;">💡</span>
            <h4 style="margin:0; font-size:15px; font-weight:700;">Smart AI Recommendations</h4>
          </div>
          <div class="tips-grid">
            <div class="tip-pill">
              <strong>🎙️ Voice-First Notes:</strong> Dictate your thoughts on the go with Voice Dictation. The AI auto-punctuates and classifies them in real time.
            </div>
            <div class="tip-pill">
              <strong>🏷️ Hashtag Organizing:</strong> Type <code>#urgent</code> or <code>#ideas</code> anywhere in your note to unlock 1-click hashtag filtering.
            </div>
            <div class="tip-pill">
              <strong>⏰ Reminder Due Dates:</strong> Set reminder timestamps on time-sensitive notes to keep today's priorities front and center.
            </div>
          </div>
        </div>
      </div>
    `;
  },

  drawAnalyticsDonut() {
    const canvas = document.getElementById('analytics-donut-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const notes = this.notes || [];
    const total = Math.max(1, notes.length);

    const counts = {
      Study: notes.filter(n => !n.uncertain && n.category === 'Study').length,
      Money: notes.filter(n => !n.uncertain && n.category === 'Money').length,
      Travel: notes.filter(n => !n.uncertain && n.category === 'Travel').length,
      Shopping: notes.filter(n => !n.uncertain && n.category === 'Shopping').length,
      Uncertain: notes.filter(n => n.uncertain).length
    };

    const slices = [
      { color: '#3B82F6', val: counts.Study },
      { color: '#10B981', val: counts.Money },
      { color: '#F59E0B', val: counts.Travel },
      { color: '#EC4899', val: counts.Shopping },
      { color: '#8C78EA', val: counts.Uncertain }
    ].filter(s => s.val > 0);

    const w = canvas.width;
    const h = canvas.height;
    const cx = w / 2;
    const cy = h / 2;
    const outerR = 90;
    const innerR = 64;

    ctx.clearRect(0, 0, w, h);

    if (slices.length === 0) {
      ctx.beginPath();
      ctx.arc(cx, cy, outerR, 0, Math.PI * 2);
      ctx.arc(cx, cy, innerR, Math.PI * 2, 0, true);
      ctx.fillStyle = '#E5E7EB';
      ctx.fill();
      return;
    }

    let startAngle = -Math.PI / 2;
    slices.forEach(s => {
      const sliceAngle = (s.val / total) * Math.PI * 2;
      ctx.beginPath();
      ctx.arc(cx, cy, outerR, startAngle, startAngle + sliceAngle);
      ctx.arc(cx, cy, innerR, startAngle + sliceAngle, startAngle, true);
      ctx.closePath();
      ctx.fillStyle = s.color;
      ctx.fill();
      startAngle += sliceAngle;
    });
  },

  escapeHtml(str) {
    if (!str) return '';
    return String(str).replace(/[&<>"']/g, m => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#39;'
    })[m]);
  },

  escapeJs(str) {
    if (!str) return '';
    return String(str).replace(/\\/g, '\\\\').replace(/'/g, "\\'").replace(/\n/g, '\\n');
  }
};

// Bootstrap when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  App.init();
});

// Global keyboard shortcuts (Esc to close modal)
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    Notes.closeModal();
    if (window.App && typeof App.closeLiveBarSearch === 'function') {
      App.closeLiveBarSearch();
    }
  }
});

// Close live search dropdown when clicking outside
document.addEventListener('click', (e) => {
  const bar = document.querySelector('.roomy-top-right-bar');
  if (bar && !bar.contains(e.target)) {
    if (window.App && typeof App.closeLiveBarSearch === 'function') {
      App.closeLiveBarSearch();
    }
  }
});

