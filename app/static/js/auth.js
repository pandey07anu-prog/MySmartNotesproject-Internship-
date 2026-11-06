/**
 * Smart Notes Assistant - Authentication Module
 * Handles registration, login, logout, password reset, profile, and password strength.
 */

const Auth = {
  // Safe JSON response parser guarding against non-JSON / 500 HTML responses
  async safeJson(res, defaultMsg = 'Request failed') {
    let data = null;
    try {
      data = await res.json();
    } catch (_) {
      data = null;
    }
    if (!res.ok) {
      const errDetail = (data && data.detail) || `${defaultMsg} (${res.status})`;
      throw new Error(errDetail);
    }
    return data || {};
  },

  // Password Strength Checker
  calculatePasswordStrength(password) {
    if (!password) return { score: 0, text: 'None', color: 'transparent', width: '0%' };
    let score = 0;
    if (password.length >= 8) score += 1;
    if (password.length >= 12) score += 1;
    if (/[a-z]/.test(password) && /[A-Z]/.test(password)) score += 1;
    if (/\d/.test(password)) score += 1;
    if (/[^A-Za-z0-9]/.test(password)) score += 1;

    switch (score) {
      case 1:
      case 2:
        return { score: 1, text: 'Weak', color: '#EF4444', width: '30%' };
      case 3:
      case 4:
        return { score: 2, text: 'Good', color: '#F59E0B', width: '70%' };
      case 5:
        return { score: 3, text: 'Strong', color: '#10B981', width: '100%' };
      default:
        return { score: 0, text: 'Very Weak', color: '#EF4444', width: '15%' };
    }
  },

  // Toggle Password Visibility
  togglePassword(inputId, btn) {
    const input = document.getElementById(inputId);
    if (!input) return;
    if (input.type === 'password') {
      input.type = 'text';
      btn.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path><line x1="1" y1="1" x2="23" y2="23"></line></svg>`;
    } else {
      input.type = 'password';
      btn.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>`;
    }
  },

  // Check Current Session on startup
  async checkSession() {
    try {
      const res = await fetch('/auth/me', {
        headers: { 'Accept': 'application/json' }
      });
      if (res.ok) {
        const data = await res.json();
        App.currentUser = data.user;
        return data.user;
      }
    } catch (e) {
      console.warn('No active session found:', e);
    }
    App.currentUser = null;
    return null;
  },

  // Registration Submit
  async register(event) {
    event.preventDefault();
    const name = document.getElementById('reg-name').value.trim();
    const email = document.getElementById('reg-email').value.trim();
    const password = document.getElementById('reg-password').value;
    const confirmPassword = document.getElementById('reg-confirm-password').value;

    if (password !== confirmPassword) {
      App.showToast('Passwords do not match.', 'error');
      return;
    }
    if (password.length < 8) {
      App.showToast('Password must be at least 8 characters.', 'error');
      return;
    }

    const submitBtn = event.target.querySelector('button[type="submit"]');
    submitBtn.disabled = true;
    submitBtn.innerText = 'Creating account...';

    try {
      const res = await fetch('/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: name,
          email: email,
          password: password,
          confirm_password: confirmPassword
        })
      });

      const data = await this.safeJson(res, 'Registration failed');
      App.currentUser = data.user;
      App.showToast('Welcome! Account created successfully.', 'success');

      window.location.hash = '#dashboard';
      App.initWorkspace();
    } catch (err) {
      App.showToast(err.message, 'error');
    } finally {
      submitBtn.disabled = false;
      submitBtn.innerText = 'Create Account';
    }
  },

  // Login Submit
  async login(event) {
    event.preventDefault();
    const email = document.getElementById('login-email').value.trim();
    const password = document.getElementById('login-password').value;
    const rememberMe = document.getElementById('login-remember') ? document.getElementById('login-remember').checked : false;

    const submitBtn = event.target.querySelector('button[type="submit"]');
    submitBtn.disabled = true;
    submitBtn.innerText = 'Signing in...';

    try {
      const res = await fetch('/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: email,
          password: password,
          remember_me: rememberMe
        })
      });

      const data = await this.safeJson(res, 'Invalid email or password');
      App.currentUser = data.user;
      App.showToast('Signed in successfully.', 'success');
      window.location.hash = '#dashboard';
      App.initWorkspace();
    } catch (err) {
      App.showToast(err.message, 'error');
    } finally {
      submitBtn.disabled = false;
      submitBtn.innerText = 'Sign In';
    }
  },

  // Logout Submit
  async logout() {
    try {
      await fetch('/auth/logout', { method: 'POST' });
    } catch (e) {
      console.warn('Logout network error:', e);
    }
    App.currentUser = null;
    App.showToast('Signed out.', 'info');
    window.location.hash = '#landing';
    App.render();
  },

  // Email Verification Request
  async verifyEmail(token) {
    if (!token) return;
    try {
      const res = await fetch('/auth/verify-email', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: token })
      });
      const data = await res.json();
      if (res.ok) {
        App.showToast('Email verified successfully! You have full access.', 'success');
        if (App.currentUser) App.currentUser.is_verified = true;
        setTimeout(() => { window.location.hash = '#dashboard'; }, 1500);
      } else {
        App.showToast(data.detail || 'Verification token is invalid or expired.', 'error');
      }
    } catch (err) {
      App.showToast('Verification failed.', 'error');
    }
  },

  // Forgot Password Submit
  async forgotPassword(event) {
    event.preventDefault();
    const email = document.getElementById('forgot-email').value.trim();
    const submitBtn = event.target.querySelector('button[type="submit"]');
    submitBtn.disabled = true;
    submitBtn.innerText = 'Sending...';

    try {
      const res = await fetch('/auth/forgot-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email })
      });
      const data = await res.json();
      App.showToast(data.message, 'info');
      document.getElementById('forgot-feedback').style.display = 'block';
    } catch (err) {
      App.showToast('Request failed. Please try again.', 'error');
    } finally {
      submitBtn.disabled = false;
      submitBtn.innerText = 'Send Reset Link';
    }
  },

  // Reset Password Submit
  async resetPassword(event) {
    event.preventDefault();
    const token = document.getElementById('reset-token').value.trim();
    const newPassword = document.getElementById('reset-new-password').value;
    const confirmPassword = document.getElementById('reset-confirm-password').value;

    if (newPassword !== confirmPassword) {
      App.showToast('Passwords do not match.', 'error');
      return;
    }

    const submitBtn = event.target.querySelector('button[type="submit"]');
    submitBtn.disabled = true;
    submitBtn.innerText = 'Updating password...';

    try {
      const res = await fetch('/auth/reset-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          token: token,
          new_password: newPassword,
          confirm_password: confirmPassword
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Password reset failed.');

      App.showToast(data.message, 'success');
      setTimeout(() => { window.location.hash = '#login'; }, 1500);
    } catch (err) {
      App.showToast(err.message, 'error');
    } finally {
      submitBtn.disabled = false;
      submitBtn.innerText = 'Reset Password';
    }
  },

  // Change Password in Profile
  async changePassword(event) {
    event.preventDefault();
    const currentPass = document.getElementById('profile-current-pass').value;
    const newPass = document.getElementById('profile-new-pass').value;
    const confirmPass = document.getElementById('profile-confirm-pass').value;

    if (newPass !== confirmPass) {
      App.showToast('New passwords do not match.', 'error');
      return;
    }

    try {
      const res = await fetch('/auth/change-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          current_password: currentPass,
          new_password: newPass,
          confirm_password: confirmPass
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to update password.');

      App.showToast('Password changed successfully.', 'success');
      event.target.reset();
    } catch (err) {
      App.showToast(err.message, 'error');
    }
  },

  // Update Profile Name or Picture
  async updateProfile(event) {
    event.preventDefault();
    const name = document.getElementById('profile-name').value.trim();
    const picInput = document.getElementById('profile-pic-url');
    const picUrl = picInput ? picInput.value.trim() : null;

    try {
      const res = await fetch('/users/me', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: name,
          profile_picture: picUrl || null
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Update failed.');

      App.currentUser.name = data.name;
      App.currentUser.profile_picture = data.profile_picture;
      App.showToast('Profile updated.', 'success');
      App.render();
    } catch (err) {
      App.showToast(err.message, 'error');
    }
  },

  // Delete User Account
  async deleteAccount() {
    if (!confirm('CAUTION: Are you absolutely certain you want to delete your account? All your notes and personal records will be permanently erased.')) {
      return;
    }

    try {
      const res = await fetch('/users/me', { method: 'DELETE' });
      const data = await res.json();
      App.currentUser = null;
      App.showToast('Account permanently deleted.', 'info');
      window.location.hash = '#landing';
      App.render();
    } catch (err) {
      App.showToast('Failed to delete account.', 'error');
    }
  }
};

