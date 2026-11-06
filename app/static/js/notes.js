/**
 * Smart Notes Assistant - Notes Management & Search Module
 * Handles note CRUD, live classification preview, filtering, TF-IDF search, and starter seeding.
 */

let classifyDebounceTimer = null;

const Notes = {
  // Safe JSON response parser guarding against non-JSON / 500 HTML responses
  async safeJson(res, defaultMsg = 'Request failed') {
    let data = null;
    try {
      data = await res.json();
    } catch (_) {
      data = null;
    }
    if (!res.ok) {
      const errDetail = (data && data.detail) || (res.status === 401 ? 'Please sign in to continue.' : `${defaultMsg} (${res.status})`);
      throw new Error(errDetail);
    }
    return data || {};
  },

  // Live ML classification preview as user types
  previewClassification(text, targetElementId) {
    clearTimeout(classifyDebounceTimer);
    const targetEl = document.getElementById(targetElementId);
    if (!targetEl) return;

    const trimmed = text.trim();
    if (!trimmed) {
      targetEl.innerHTML = `<span class="text-muted">Enter text to see live ML categorization</span>`;
      return;
    }

    targetEl.innerHTML = `<span class="text-muted"><span class="mini-spinner" style="display:inline-block; vertical-align:middle; margin-right:4px;"></span> Analyzing...</span>`;

    classifyDebounceTimer = setTimeout(async () => {
      try {
        const res = await fetch('/classify', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text: trimmed })
        });
        if (!res.ok) return;
        const data = await res.json();

        const badgeClass = `badge-${data.category.toLowerCase()}`;
        let html = `<span>Predicted: <span class="badge ${badgeClass}">${data.category}</span></span>`;

        if (data.uncertain) {
          html += ` <span class="badge badge-uncertain" title="Confidence is below 50% operational threshold">Needs Review</span>`;
        }

        // Live Time-Priority Detection & Dynamic Auto Button Sync
        if (window.App && App.getTimePriority) {
          const prio = App.getTimePriority({ text: trimmed });
          html += ` <span style="margin: 0 4px; color: var(--text-muted);">•</span> <span>Priority: <span class="badge-priority ${prio.badgeClass}" style="font-size:11px; padding:2px 7px;">${prio.icon} ${prio.label}</span></span>`;

          const autoBtn = document.getElementById('prio-opt-auto');
          const currentChoice = (document.getElementById('modal-priority-choice') || {}).value || 'auto';
          if (autoBtn && currentChoice === 'auto') {
            autoBtn.innerHTML = `🤖 Auto (${prio.shortLabel})`;
          }
        }

        targetEl.innerHTML = html;
      } catch (e) {
        console.warn('Live classification error:', e);
      }
    }, 250);
  },

  // Fetch all notes with optional category filter
  async fetchNotes(category = null, uncertainOnly = false) {
    let url = '/notes';
    const params = [];
    if (category && category !== 'all' && category !== 'uncertain') {
      params.push(`category=${encodeURIComponent(category)}`);
    }
    if (uncertainOnly || category === 'uncertain') {
      params.push('uncertain_only=true');
    }
    if (params.length > 0) {
      url += '?' + params.join('&');
    }

    try {
      const res = await fetch(url);
      const notes = await this.safeJson(res, 'Failed to load notes');
      App.notes = Array.isArray(notes) ? notes : [];
      if (!category || category === 'all') {
        App.allUserNotes = App.notes;
      }
      return App.notes;
    } catch (e) {
      App.showToast('Could not load notes from database.', 'error');
      return [];
    }
  },

  // Refresh Dashboard Statistics
  async fetchStats() {
    try {
      const res = await fetch('/stats');
      if (res.ok) {
        const stats = await this.safeJson(res, 'Could not fetch stats');
        App.stats = stats;
        if (!App.allUserNotes || App.allUserNotes.length === 0) {
          fetch('/notes')
            .then(r => r.ok ? r.json() : [])
            .then(allNotes => {
              if (Array.isArray(allNotes)) {
                App.allUserNotes = allNotes;
                if (window.App && App.updateSidebarCounts) {
                  App.updateSidebarCounts();
                }
              }
            })
            .catch(() => {});
        }
        return stats;
      }
    } catch (e) {
      console.warn('Could not fetch stats:', e);
    }
    return null;
  },

  // Save new note
  async saveNewNote(text) {
    if (!text || !text.trim()) {
      App.showToast('Note text cannot be empty.', 'error');
      return null;
    }

    try {
      const res = await fetch('/notes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: text.trim() })
      });
      const data = await this.safeJson(res, 'Could not save note');

      App.allUserNotes = null;
      App.showToast(`Saved note ${data.note_id} as ${data.category}`, 'success');
      await this.fetchStats();
      await this.fetchNotes(App.activeCategoryFilter);
      App.render();
      return data;
    } catch (err) {
      App.showToast(err.message, 'error');
      return null;
    }
  },

  // Update existing note
  async updateNote(noteId, text) {
    if (!text || !text.trim()) {
      App.showToast('Note text cannot be empty.', 'error');
      return null;
    }

    try {
      const res = await fetch(`/notes/${encodeURIComponent(noteId)}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: text.trim() })
      });
      const data = await this.safeJson(res, 'Could not update note');

      App.allUserNotes = null;
      App.showToast(`Updated note ${data.note_id}`, 'success');
      await this.fetchStats();
      await this.fetchNotes(App.activeCategoryFilter);
      App.render();
      return data;
    } catch (err) {
      App.showToast(err.message, 'error');
      return null;
    }
  },

  // Delete note
  async deleteNote(noteId) {
    if (!confirm(`Are you sure you want to delete note ${noteId}?`)) return;

    try {
      const res = await fetch(`/notes/${encodeURIComponent(noteId)}`, {
        method: 'DELETE'
      });
      await this.safeJson(res, 'Failed to delete note');

      App.allUserNotes = null;
      App.showToast(`Note ${noteId} deleted.`, 'info');
      await this.fetchStats();
      await this.fetchNotes(App.activeCategoryFilter);
      App.render();
    } catch (err) {
      App.showToast(err.message, 'error');
    }
  },

  // Seed Starter Notes (N001-N012)
  async seedStarterNotes() {
    try {
      const res = await fetch('/notes/seed', { method: 'POST' });
      const data = await this.safeJson(res, 'Failed to seed starter notes');
      App.allUserNotes = null;
      App.showToast(data.message || 'Starter notes loaded.', 'success');
      await this.fetchStats();
      await this.fetchNotes(App.activeCategoryFilter);
      App.render();
    } catch (e) {
      App.showToast(e.message || 'Failed to seed starter notes.', 'error');
    }
  },

  // Reclassify all existing notes using upgraded 98% accuracy model
  async reclassifyAll() {
    App.showToast('Analyzing and reclassifying your notes with the upgraded ML model...', 'info');
    try {
      const res = await fetch('/notes/reclassify', { method: 'POST' });
      const data = await this.safeJson(res, 'Reclassification failed');
      App.allUserNotes = null;
      App.showToast(data.message || 'All notes reclassified successfully.', 'success');
      await this.fetchStats();
      await this.fetchNotes(App.activeCategoryFilter);
      App.render();
    } catch (e) {
      App.showToast(e.message || 'Failed to reclassify notes.', 'error');
    }
  },

  // Search Notes (TF-IDF or Keyword)
  async searchNotes(query, method = 'tfidf') {
    if (!query || !query.trim()) {
      return [];
    }

    const url = `/search?q=${encodeURIComponent(query.trim())}&method=${encodeURIComponent(method)}&top_k=20`;
    try {
      const res = await fetch(url);
      if (!res.ok) throw new Error('Search request failed.');
      const data = await res.json();
      return data.results || [];
    } catch (err) {
      App.showToast('Search error.', 'error');
      return [];
    }
  },

  // Open Edit Modal
  openEditModal(noteId, text) {
    const modal = document.getElementById('note-modal');
    const title = document.getElementById('modal-title');
    const textarea = document.getElementById('modal-note-text');
    const noteIdInput = document.getElementById('modal-note-id');
    const preview = document.getElementById('modal-live-preview');

    if (!modal) return;
    title.innerText = noteId ? `Edit Note ${noteId}` : 'Create New Note';
    noteIdInput.value = noteId || '';
    textarea.value = text || '';
    const charCounter = document.getElementById('modal-char-counter');
    if (charCounter) charCounter.innerText = (text ? text.length : 0) + ' chars';
    preview.innerHTML = '';
    if (text) {
      this.previewClassification(text, 'modal-live-preview');
    }

    if (window.App && App.setModalPriority) {
      const existingPrio = noteId ? (localStorage.getItem('note_prio_' + noteId) || 'auto') : 'auto';
      App.setModalPriority(existingPrio);
    }

    const dueDateInput = document.getElementById('modal-due-date');
    if (dueDateInput) {
      dueDateInput.value = noteId ? (localStorage.getItem('note_due_' + noteId) || '') : '';
    }

    modal.classList.add('active');
    textarea.focus();
  },

  closeModal() {
    const modal = document.getElementById('note-modal');
    if (modal) modal.classList.remove('active');
    if (window.App && App.stopVoiceDictation) {
      App.stopVoiceDictation();
    }
  }
};

